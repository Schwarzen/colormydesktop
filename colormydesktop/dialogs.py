#!/usr/bin/env python3
# Copyright 2026 Schwarzen
# SPDX-License-Identifier: Apache-2.0
import glob
import os
import re
import json
import shutil
import hashlib
import gi
from gi.repository import Gtk, Adw, Gdk, Gio, GLib, GObject

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")


class DynamicPopupWindow(Adw.Window):
    def __init__(self, parent_window, title, content_widget):
        super().__init__(transient_for=parent_window, title=title)

        self.history_stack = []

        # Core UI Setup
        self.toolbar_view = Adw.ToolbarView()
        self.header_bar = Adw.HeaderBar()
        self.toolbar_view.add_top_bar(self.header_bar)

        self.back_button = Gtk.Button(icon_name="go-previous-symbolic")
        self.back_button.set_valign(Gtk.Align.CENTER)
        self.back_button.add_css_class("flat")
        self.back_button.set_visible(False)
        self.back_button.connect("clicked", self._on_back_clicked)
        self.header_bar.pack_start(self.back_button)

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        #  Safely detach the widget from any dead parent before appending
        self._safe_append(self.content_box, content_widget)

        self.toolbar_view.set_content(self.content_box)
        self.set_content(self.toolbar_view)

        self.current_content = content_widget

        #  Cleanly release all cached singletons when the window is closed
        self.connect("close-request", self._on_window_close)

    def _safe_append(self, container, child):
        """Helper to ensure a widget is parentless before appending it."""
        parent = child.get_parent()
        if parent and hasattr(parent, "remove"):
            parent.remove(child)
        container.append(child)

    @classmethod
    def spawn(cls, parent_window, title, content_widget):
        # 1. Instantiate the window
        win = cls(parent_window, title, content_widget)

        # 2. Bind it explicitly to the main window hierarchy
        if parent_window:
            win.set_transient_for(parent_window)
            win.set_destroy_with_parent(True)

            # Optional: Uncomment if you want to block clicks on the main window until closed
            # win.set_modal(True)

        # 3. Present the window cleanly
        win.present()
        return win

    @classmethod
    def swap_content(cls, current_widget, new_content_widget, new_title=None):
        root_window = current_widget.get_root()
        if not isinstance(root_window, cls):
            return

        # 1. Stash current state before swapping
        root_window.history_stack.append(
            {"widget": root_window.current_content, "title": root_window.get_title()}
        )

        # 2. Swap out the view safely
        root_window.content_box.remove(root_window.current_content)
        root_window._safe_append(root_window.content_box, new_content_widget)
        root_window.current_content = new_content_widget

        # 3. Update Window State
        if new_title:
            root_window.set_title(new_title)

        root_window.back_button.set_visible(True)

    def _on_back_clicked(self, button):
        if not self.history_stack:
            return

        # 1. Pop the last state off the stack
        prev_state = self.history_stack.pop()
        prev_widget = prev_state["widget"]
        prev_title = prev_state["title"]

        # 2. Swap back safely
        self.content_box.remove(self.current_content)
        self._safe_append(self.content_box, prev_widget)
        self.current_content = prev_widget
        self.set_title(prev_title)

        # 3. Hide back button if we are back at the start
        if not self.history_stack:
            self.back_button.set_visible(False)

    def _on_window_close(self, window):
        """Ensures all cached singletons are released and attempts to auto-toggle the target switch."""

        # Pull your tracking states
        from colormydesktop.broker import ContextBroker

        manager = getattr(self, "manager", None) or ContextBroker.manager
        target_switch = getattr(manager, "last_toggled_switch", None)

        # Quietly verify if the setup steps were satisfied
        if target_switch and not target_switch.get_active():
            if manager.verify_switch_permissions_quietly(target_switch):
                print(
                    f"[CLEANUP] Requirements satisfied. Quietly enabling feature switch."
                )
                target_switch.set_active(True)
                manager.last_toggled_switch = None

        # --- Standard Cleanup & UI Tree Pruning ---
        if self.current_content:
            self.content_box.remove(self.current_content)

        for state in self.history_stack:
            widget = state["widget"]
            parent = widget.get_parent()
            if parent and hasattr(parent, "remove"):
                parent.remove(widget)

        return False


class DialogMixin:
    def is_running_in_flatpak(self):
        #  Check for the physical metadata file
        if os.path.exists("/.flatpak-info"):
            return True

        # Check the 'container' env var (Commonly set by Flatpak/Podman)
        if os.environ.get("container") == "flatpak":
            return True

        # Check for FLATPAK_ID but double-check it's not a leaked value
        # If FLATPAK_ID exists but /app does not, it's likely a leaked variable
        if os.environ.get("FLATPAK_ID") and os.path.exists("/app"):
            return True

        return False

    def setup_user_data(self):
        bundled_scss = "/app/share/color-my-desktop/scss"
        # bundled_palettes = "/app/share/color-my-desktop/palettes"
        # Inside Flatpak, XDG_DATA_HOME is usually /var/config/data/ or ~/.local/share/
        xdg_data = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        user_scss_dir = os.path.join(xdg_data, "scss")

        #  Sync SCSS files
        if os.path.exists(bundled_scss):
            os.makedirs(user_scss_dir, exist_ok=True)
            try:
                for root, dirs, files in os.walk(bundled_scss):
                    rel_path = os.path.relpath(root, bundled_scss)
                    dest_path = os.path.join(user_scss_dir, rel_path)
                    os.makedirs(dest_path, exist_ok=True)
                    for file in files:
                        shutil.copy2(
                            os.path.join(root, file), os.path.join(dest_path, file)
                        )
                print(f"Synced SCSS to: {user_scss_dir}")
            except Exception as e:
                print(f"Error updating SCSS: {e}")

        return user_scss_dir

    def setup_palette_data(self):

        bundled_palettes = self.PALETTES
        user_scss_dir = self.SCSS_USR

        if os.path.exists(bundled_palettes):
            os.makedirs(user_scss_dir, exist_ok=True)
            try:
                for file in os.listdir(bundled_palettes):
                    src_file = os.path.join(bundled_palettes, file)
                    dest_file = os.path.join(user_scss_dir, file)  # Placed in root

                    # Guard: Only copy if the file is missing
                    if not os.path.exists(dest_file):
                        shutil.copy2(src_file, dest_file)
                        print(f"Added new palette file to root: {file}")

                print("Palette files synced to SCSS root (No overwrites).")
            except Exception as e:
                print(f"Error syncing palette files: {e}")

        return user_scss_dir

    def on_open_finished(self, launcher, result):
        try:
            # Use the matching finish method
            launcher.open_containing_folder_finish(result)
            print("Folder opened successfully via portal.")
        except GLib.Error as e:
            print(f"Failed to open folder: {e.message}")

    def is_gnome_refresh_ready(self):
        #  Check Systemd Portal Path
        host_path = "~/.config/systemd/user"
        portal_path = getattr(
            self, f"active_portal_{self.get_safe_key(host_path)}", None
        )
        if not portal_path:
            portal_path = self.load_cached_portal_path(host_path)

        if not portal_path or not os.path.exists(portal_path):
            return False

        #  Check for the two refresher files
        path_exists = os.path.isfile(os.path.join(portal_path, "gnome-refresher.path"))
        service_exists = os.path.isfile(
            os.path.join(portal_path, "gnome-refresher.service")
        )
        if not (path_exists and service_exists):
            return False

        return True

    def is_plasma_refresh_ready(self):
        # Check Systemd Portal Path
        host_path = "~/.config/systemd/user"
        portal_path = getattr(
            self, f"active_portal_{self.get_safe_key(host_path)}", None
        )
        if not portal_path:
            portal_path = self.load_cached_portal_path(host_path)

        if not portal_path or not os.path.exists(portal_path):
            return False

        # Check for the two PLASMA refresher files
        path_exists = os.path.isfile(os.path.join(portal_path, "plasma-refresher.path"))
        service_exists = os.path.isfile(
            os.path.join(portal_path, "plasma-refresher.service")
        )
        if not (path_exists and service_exists):
            return False

        return True

    def save_persistent_settings(self, manual_path=None):
        # Use the passed path if available; otherwise fallback to the instance variable
        path_to_save = (
            manual_path
            if manual_path is not None
            else getattr(self, "last_manually_entered_zen_path", "")
        )

        config_dir = os.path.expanduser(
            "~/.var/app/io.github.schwarzen.colormydesktop/config/color-my-desktop/"
        )
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "settings.json")

        data = {"zen_path": path_to_save}

        with open(config_path, "w") as f:
            import json

            json.dump(data, f, indent=4)

        # Update the instance variable so the rest of the app knows the new path
        self.last_manually_entered_zen_path = path_to_save

    def on_dialog_response(self, dialog, response, target_folder):
        if response == "select":
            portal = Gtk.FileDialog.new()
            portal.set_title(f"Select Folder: {target_folder}")

            # Expand the target path to an absolute path
            target_path = os.path.expanduser(target_folder)
            initial_dir = Gio.File.new_for_path(target_path)

            # Hint to the portal where to start
            # Note: Some portals (like KDE) may ignore this, but it is standard for GNOME
            portal.set_initial_folder(initial_dir)
            # Pass the folder to the callback so we know which Entry to update
            portal.select_folder(
                self,
                None,
                lambda dialog, result: self.on_portal_folder_selected(
                    dialog, result, target_folder
                ),
            )

    def on_portal_folder_selected(self, dialog, result, target_folder):
        try:
            folder_file = dialog.select_folder_finish(result)
            if folder_file:
                sandboxed_path = folder_file.get_path()

                # 1. PERSISTENCE: Save to JSON so it survives app restarts
                self.save_portal_path(target_folder, sandboxed_path)

                # 2. SESSION DATA: Keep your existing safe_key logic
                safe_key = self.get_safe_key(target_folder)
                setattr(self, f"active_portal_{safe_key}", sandboxed_path)

                # Existing validation logic
                selected_folder_name = os.path.basename(
                    os.path.normpath(sandboxed_path)
                )
                expected_folder_name = os.path.basename(os.path.normpath(target_folder))

                if not hasattr(self, "portal_access_list"):
                    self.portal_access_list = []

                if sandboxed_path not in self.portal_access_list:
                    self.portal_access_list.append(sandboxed_path)

                # 3. BROKER REFRESH: Notify broker that a new portal path was registered
                from colormydesktop.broker import ContextBroker

                ContextBroker.translate_action(
                    sender_id="ThemeManager",
                    action_type="PORTAL_PATH_UPDATED",
                    payload={
                        "target_folder": target_folder,
                        "sandboxed_path": sandboxed_path,
                    },
                )
        except Exception as e:
            print(f"[PORTAL ERROR] Failed to finalize folder selection: {e}")

    def get_safe_key(self, folder_path):
        """
        Creates a unique attribute name.
        Example: '/path/to/vesktop/themes' -> 'themes_7a8b9c'
        """
        # 1. Get the folder name (e.g., 'themes')
        base_name = os.path.basename(os.path.normpath(folder_path))

        # 2. Create a unique hash of the FULL path
        # This distinguishes vesktop/themes from gnome/themes
        path_hash = hashlib.md5(folder_path.encode()).hexdigest()[:6]

        # 3. Combine into a safe Python attribute name
        raw_key = f"{base_name}_{path_hash}"
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", raw_key).lower()

        return safe_name

    # Helper to get current text for a folder from the UI

    def get_path_argument(self, folder_path):
        # 1. First, check if we have a saved portal path attribute
        # This is the most reliable way to get the /run/user/ path
        safe_key = self.get_safe_key(folder_path)
        saved_path = getattr(self, f"active_portal_{safe_key}", None)
        if saved_path:
            return saved_path

        # 2. If no saved attribute, check the UI widgets
        widgets = self.portal_widgets.get(folder_path)
        if widgets:
            text = widgets["entry"].get_text()
            # Ensure we don't pass the placeholder string to your script
            if text and text != "No folder selected yet...":
                return text

        # 3. Default Fallback: Host path
        return os.path.expanduser(folder_path)

    def clear_specific_portal_cache(self, target_folders):
        # 1. Normalize to list so we can loop through it
        if isinstance(target_folders, str):
            target_folders = [target_folders]

        # 2. Clear from memory immediately
        for folder in target_folders:
            safe_key = self.get_safe_key(folder)
            attr_name = f"active_portal_{safe_key}"
            if hasattr(self, attr_name):
                delattr(self, attr_name)

        # 3. Batch remove entries from JSON
        data_dir = GLib.get_user_data_dir()
        config_file = os.path.join(data_dir, "portal_cache.json")

        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    cache = json.load(f)

                modified = False
                for folder in target_folders:
                    if folder in cache:
                        del cache[folder]
                        modified = True
                        print(f"Cleared {folder} from cache.")

                # 4. Only write to the file once after checking all folders
                if modified:
                    with open(config_file, "w") as f:
                        json.dump(cache, f, indent=4)
                    print("Updated portal_cache.json successfully.")

            except Exception as e:
                print(f"Error updating portal cache: {e}")

    def add_folder_action(self, switch_row, feature_name, folders):
        # Create a uniform button
        folder_button = Gtk.Button.new_from_icon_name("folder-open-symbolic")
        folder_button.add_css_class("flat")
        folder_button.set_valign(Gtk.Align.CENTER)
        folder_button.set_tooltip_text(f"Manage {feature_name} folders")

        #  Connect the click to the permission dialog
        # We use a lambda to pass the specific feature info
        folder_button.connect(
            "clicked",
            lambda b: (
                self.zen_permission_dialog(feature_name, folders)
                if feature_name in ["Zen", "YouTube"]
                else self.show_permission_dialog(feature_name, folders)
            ),
        )

        #  Add to the row
        switch_row.add_suffix(folder_button)

        #  Bind visibility so it only shows when the switch is ON
        switch_row.bind_property(
            "active", folder_button, "visible", GObject.BindingFlags.SYNC_CREATE
        )

        return folder_button
