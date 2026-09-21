#!/usr/bin/env python3
# Copyright 2026 Schwarzen
# SPDX-License-Identifier: Apache-2.0

from contextvars import Context
import os
import re
import subprocess
import threading
import sys
import json
import glob
from gi.repository import Gtk, Adw, Gdk, GLib, Gio
from colormydesktop.mockup import InteractiveMockup
from .dialogs import DialogMixin
from .advancedpref import AdvancedMixin
from colormydesktop.css import BASE_STYLE_SHEET
from colormydesktop.broker import broker

# --- CONFIGURATION ---
if os.environ.get("FLATPAK_ID"):
    # Inside Flatpak, the script is at /app/bin/
    BASH_SCRIPT = "/app/bin/color-my-desktop-backend"
    SCSS_DIR = os.path.expanduser(
        "~/.var/app/io.github.schwarzen.colormydesktop/data/scss"
    )
    SCSS_USR = os.path.expanduser(
        "~/.var/app/io.github.schwarzen.colormydesktop/data/scss"
    )
    PALETTES = "/app/share/color-my-desktop/palettes"
    PYTHON_DIR = "/app/bin/colormydesktop"
else:
    # Native install location
    BASH_SCRIPT = os.path.expanduser("~/.local/bin/color-my-desktop-backend")
    SCSS_DIR = os.path.expanduser("~/.local/share/color-my-desktop/scss")
    SCSS_USR = os.path.expanduser("~/.local/share/color-my-desktop/scss")
    PALETTES = os.path.expanduser("~/.local/share/color-my-desktop/palettes")
    PYTHON_DIR = os.path.expanduser("~/.local/bin/colormydesktop")


class ThemeManager(Adw.ApplicationWindow, DialogMixin, AdvancedMixin):
    def __init__(self, ui_context=None, **kwargs):
        # Explicitly skip passing kwargs to Adw.ApplicationWindow if initialized as a headless engine
        super().__init__(**kwargs)

        # ---------------------------------------------------------
        # PHASE 1: INDEPENDENT STATE DATA ALLOCATION
        # ---------------------------------------------------------
        self._ui_instance = None
        self.portal_widgets = {}
        self.color_entries = {}
        self.last_manually_enterd_zen_path = ""
        self.current_colors = {}
        self.status_labels = {}

        # Core data models are completely safe to allocate without UI visibility
        self.PALETTES = PALETTES
        self.SCSS_USR = SCSS_USR
        self.theme_list = Gtk.StringList.new([])
        self.install_item_list = Gtk.StringList.new(["Install Bundled Palettes"])
        self.model_store = Gio.ListStore.new(Gio.ListModel)
        self.model_store.append(self.theme_list)
        self.model_store.append(self.install_item_list)
        self.combined_model = Gtk.FlattenListModel.new(self.model_store)

    @property
    def ui(self):
        """Dynamically tracks and returns the bound home view instance."""
        return self._ui_instance

    @ui.setter
    def ui(self, new_home_view):
        """
        Reactive Pipeline Trigger.
        Fires automatically the exact millisecond main.py registers the home view.
        """
        if new_home_view is None or self._ui_instance == new_home_view:
            return

        self._ui_instance = new_home_view

        # Execute deferred system & layout setups safely
        self._initialize_core_subsystems()
        self._inject_application_styles()
        self._wire_user_interface_signals(new_home_view)
        self.check_gnome_refresh_status()

    # ---------------------------------------------------------
    # PHASE 2: DEFERRED SUBSYSTEM ORCHESTRATION
    # ---------------------------------------------------------
    def _initialize_core_subsystems(self):
        """Orchestrates configuration directories, file state engines, and disk caching."""
        self.setup_css_providers()
        self.load_persistent_settings()
        self.setup_user_data()
        self.load_all_cached_portals()
        self.is_plasma_refresh_ready()
        self.is_gnome_refresh_ready()

        # --- DYNAMIC DEBUG LOGS ADDED BACK HERE ---
        current_zen_path = getattr(
            self, "last_manually_entered_zen_path", "~/.zen/*/chrome"
        )
        print(f"DEBUG: Loaded Zen Path: {os.path.expanduser(current_zen_path)}")

        # (Assuming SCSS_DIR or SCSS_USR holds your path layout)
        print(f"Synced SCSS to: {getattr(self, 'SCSS_USR', '')}")
        print("Refreshing palette data from bundle...")
        print("Palette files synced to SCSS root (No overwrites).")
        print(f"Palettes are up to date in: {getattr(self, 'SCSS_USR', '')}")

        # Dynamic SCSS parsing safely deferred until workspace variables resolve
        if os.path.exists(SCSS_DIR):
            raw_themes = [
                f[1:-5]
                for f in os.listdir(SCSS_DIR)
                if f.startswith("_") and f.endswith(".scss")
            ]
            raw_themes.sort()
            self.themes = ["Default"] + raw_themes
        else:
            print("CRITICAL: SCSS_DIR missing even after setup_user_data")
            self.themes = ["Default"]

    def _inject_application_styles(self):
        """Applies application overrides directly to the display scope."""
        self.app_icon = Gtk.Image.new_from_icon_name(
            "io.github.schwarzen.colormydesktop"
        )

        css_provider = Gtk.CssProvider()
        css_style = """
            .draggable-frame { background: @window_bg_color; box-shadow: 0 10px 30px 5px rgba(0, 0, 0, 0.5); border-radius: 16px; }
            .ui-overlay-layer, preferencespage, .preferences-group { box-shadow: none !important; border: none; }
            .close-btn-style { color: white; background: rgba(0, 0, 0, 0.2); border-radius: 50%; padding: 6px; }
            .close-btn-style:hover { background-color: #d7191c; box-shadow: 0 0 5px rgba(0,0,0,0.3); }
            .accent { background-color: var(--accent-bg-color); color: rgb(100, 100, 100); border-top: 1px solid rgba(0, 0, 0, 0.1); padding: 8px 12px; margin-top: 4px; font-weight: bold; }
            .accent:hover { background-color: shade(var(--accent-bg-color), 0.9); color: var(--accent-fg-color); }
        """
        css_provider.load_from_data(css_style.encode())

        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def _wire_user_interface_signals(self, target_ui):
        """Binds structural data layers, controllers, and callback routines onto UI elements."""
        # 1. Base Action Triggers
        target_ui.advanced_options_action_btn.connect(
            "clicked", self.on_advanced_options_clicked
        )

        # 2. List Models and Data Factories Configuration
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)

        cr = target_ui.combo_row
        cr.set_model(self.combined_model)
        cr.set_factory(factory)
        cr.connect("notify::selected", self.on_combo_changed)
        cr.set_activatable_widget(cr)
        cr.connect("notify::selected", self.on_theme_select)

        # Crawl files now that the bound widget structure exists in memory
        self.refresh_theme_list()

        # 3. Component Assignments
        self.gnome_switch = target_ui.gnome_switch
        self.gnome_row = target_ui.gnome_row
        self.plasma_switch = target_ui.plasma_switch
        self.plasma_row = target_ui.plasma_row
        self.gtk4_switch = target_ui.gtk4_switch
        self.zen_switch = target_ui.zen_switch
        self.youtube_switch = target_ui.youtube_switch
        self.vesktop_switch = target_ui.vesktop_switch
        self.papirus_switch = target_ui.papirus_switch
        self.build_btn = target_ui.build_btn

        # 4. Input Constraints and Sanitizers
        def on_name_insert_text(editable, new_text, length, position):
            if not re.match(r"^[a-zA-Z0-9_ -]*$", new_text):
                editable.stop_emission_by_name("insert-text")

        # 5. Native Gesture Architecture Routing
        from colormydesktop.lib_gui import GnomeSetupDialog
        from colormydesktop.broker import ContextBroker

        gnome_gesture = Gtk.GestureClick.new()
        gnome_gesture.connect(
            "released",
            lambda g, n, x, y: (
                ContextBroker.navigate(
                    self.gnome_switch, GnomeSetupDialog, "gnome_setup_dialog"
                )
                if y > 30 and 120 < x < 300
                else None
            ),
        )
        self.gnome_switch.add_controller(gnome_gesture)

        gnome_motion = Gtk.EventControllerMotion.new()
        gnome_motion.connect(
            "motion",
            lambda c, x, y: (
                self.gnome_switch.set_cursor(Gdk.Cursor.new_from_name("pointer", None))
                if y > 30 and 120 < x < 300
                else self.gnome_switch.set_cursor(None)
            ),
        )
        self.gnome_switch.add_controller(gnome_motion)

        plasma_gesture = Gtk.GestureClick.new()
        plasma_gesture.connect(
            "released",
            lambda g, n, x, y: (
                self.show_plasma_setup_dialog() if y > 30 and 120 < x < 350 else None
            ),
        )
        self.plasma_switch.add_controller(plasma_gesture)

        plasma_motion = Gtk.EventControllerMotion.new()
        plasma_motion.connect(
            "motion",
            lambda c, x, y: (
                self.plasma_switch.set_cursor(Gdk.Cursor.new_from_name("pointer", None))
                if y > 30 and 120 < x < 350
                else self.plasma_switch.set_cursor(None)
            ),
        )
        self.plasma_switch.add_controller(plasma_motion)

        # 6. Dynamic Evaluation & System Argument Resolution
        current_zen_path = getattr(
            self, "last_manually_entered_zen_path", "~/.zen/*/chrome"
        )
        self.gnome_path = self.get_path_argument("~/.local/share/themes")
        self.plasma_path = self.get_path_argument("~/.local/share/plasma")
        self.schemes_path = self.get_path_argument("~/.local/share/color-schemes")
        self.gtk4_path = self.get_path_argument("~/.config/gtk-4.0")
        self.zen_path = self.get_path_argument(current_zen_path)
        self.vesktop_path = self.get_path_argument("~/.config/vesktop/themes")
        self.papirus_path = self.get_path_argument("~/.local/share/icons")

        # 7. Operational Compilation & Logger Blocks
        self.build_btn.add_css_class("suggested-action")
        self.build_btn.set_margin_top(24)
        self.build_btn.set_margin_bottom(24)
        self.build_btn.connect("clicked", self.on_run_build_clicked)

        self.log_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.log_container.set_visible(False)
        self.progress_bar = Gtk.ProgressBar()
        self.log_container.append(self.progress_bar)

        self.scrolled_window = Gtk.ScrolledWindow(min_content_height=150)
        self.scrolled_window.add_css_class("card")
        self.log_view = Gtk.TextView(editable=False, monospace=True)
        self.scrolled_window.set_child(self.log_view)

    def is_writable(self, path):
        full_path = os.path.expanduser(path)
        return os.access(full_path, os.W_OK)

        # }}}
        # {{{ SECTION: POST-INITIALIZATION
        initial_css = ""
        for cid, hcolor in self.current_colors.items():
            initial_css += f"#{cid}-preview {{ background-color: {hcolor}; border-radius: 6px; min-width: 24px; min-height: 24px; }}\n"
        self.dynamic_color_provider.load_from_string(initial_css)
        # 1. Fill the current_colors registry with the default values from the entries
        if not hasattr(self, "current_colors"):
            self.current_colors = {}

        for css_id, entry_widget in self.color_entries.items():
            # Get the text currently in the box (the default hex you passed)
            hex_val = entry_widget.get_text().strip()
            if hex_val:
                # Ensure it has a #
                clean_hex = hex_val if hex_val.startswith("#") else f"#{hex_val}"
                self.current_colors[css_id] = clean_hex

        self.check_gnome_refresh_status()
        #####self.initial_status()
        ## }}}

    # {{{ SECTION : FUNCTIONS
    def on_delete_clicked(self):
        selected_index = self.ui.combo_row.get_selected()
        selected_theme = self.theme_list.get_string(selected_index)
        if selected_index == 0 or selected_theme == "Default":
            # Don't delete the factory default
            return

            # Create a confirmation dialog
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=f"Delete Profile?",
            body=f"Are you sure you want to permanently delete '{selected_theme}'?",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")

        dialog.connect("response", self.on_delete_confirm, selected_theme)
        dialog.present()

    def on_drag_pressed(self, gesture, n_press, x, y):
        # 1. Get the surface (must be a Gdk.Toplevel)
        surface = self.get_native().get_surface()

        # 2. Get the device and timestamp from the event
        event = gesture.get_last_event()
        device = event.get_device()
        timestamp = event.get_time()

        if surface and device:
            # 3. Use the GTK4 Gdk.Toplevel method: begin_move
            # Parameters: (device, button, x, y, timestamp)
            surface.begin_move(
                device,
                1,  # Left mouse button
                x,
                y,  # Local coordinates (Surface-relative)
                timestamp,
            )

    def _on_factory_setup(self, factory, list_item):
        # Create a container box to hold our label
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        label = Gtk.Label(xalign=0.5, hexpand=True)
        box.append(label)
        list_item.set_child(box)

    def _on_factory_bind(self, factory, list_item):
        box = list_item.get_child()
        label = box.get_first_child()
        item = list_item.get_item()
        text = item.get_string()

        label.set_text(text)

        if text == "Install Bundled Palettes":
            # Apply the style to the BOX so the whole row turns blue/accented
            box.add_css_class("accent")
        else:
            box.remove_css_class("accent")

    def on_combo_changed(self, combo, pspec):
        # 1. Get the selected item object from the model
        selected_item = combo.get_selected_item()
        if not selected_item:
            return

        # 2. Check if the item is a Gtk.StringObject (it should be)
        # Then check the actual text string inside it
        if selected_item.get_string() == "Install Bundled Palettes":
            # --- RUN INSTALL LOGIC ---
            self.on_refresh_palettes_clicked(None)

            # --- RESET SELECTION ---
            # Jump back to 'Default' so the button doesn't stay 'Selected'
            combo.set_selected(0)
        else:
            # --- RUN NORMAL THEME SELECTION ---
            self.on_theme_select(combo, pspec)

    def on_refresh_palettes_clicked(self, button):
        print("Refreshing palette data from bundle...")
        user_path = self.setup_palette_data()
        print(f"Palettes are up to date in: {user_path}")
        self.refresh_theme_list()

    #
    # SECTION: ADVANCED PAGE {{{
    # METHOD: function to call AdvancedPage instance, functions for this page are in advancedpref.py
    def on_advanced_options_clicked(self, button):
        from colormydesktop.lib_gui import AdvancedPage

        home_view = broker.get_page("home_view")

        broker.navigate(
            current_widget=home_view,
            target_page_class=AdvancedPage,
            page_id="advanced_options",
        )

        ########################

    def get_saved_zen_path(self):
        config_path = os.path.expanduser(
            "~/.var/app/io.github.schwarzen.colormydesktop/config/color-my-desktop/settings.json"
        )
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                    return data.get("zen_path", "")
            except (json.JSONDecodeError, IOError):
                return ""
        return ""

    def show_toast(self, message: str):
        from colormydesktop.broker import ContextBroker

        # 1. Try getting overlay attached to self, or fetch active UI view/window from ContextBroker
        ui_context = getattr(self, "main_page_context", None) or ContextBroker.get_page(
            "home_view"
        )
        overlay = getattr(self, "toast_overlay", None) or getattr(
            ui_context, "toast_overlay", None
        )

        # 2. Add toast if UI exists, otherwise print to log
        if overlay:
            overlay.add_toast(Adw.Toast.new(message))
        else:
            print(f"[Toast Fallback]: {message}")

    # }}}

    def verify_switch_permissions_quietly(manager, switch_widget) -> bool:
        """
        Evaluates permissions for a stashed switch widget context.
        Returns True if all required paths pass inspection, otherwise False.
        """
        if not switch_widget or not hasattr(switch_widget, "get_active"):
            return False

        # Extract the tracked properties we stashed on the widget
        folders = getattr(switch_widget, "_assigned_folders", [])
        feature_name = getattr(switch_widget, "_feature_name", "")

        if isinstance(folders, str):
            folders = [folders]

        if not folders:
            return False

        for folder_pattern in folders:
            has_access = False

            # 1. Manual Path Check
            if feature_name in ["Zen", "YouTube"]:
                manual_path = getattr(manager, "last_manually_entered_zen_path", None)
                if manual_path and os.access(os.path.expanduser(manual_path), os.W_OK):
                    has_access = True

            # 2. Portal Check
            if not has_access:
                safe_key = manager.get_safe_key(folder_pattern)
                portal_path = getattr(manager, f"active_portal_{safe_key}", None)
                if portal_path and os.access(portal_path, os.W_OK):
                    has_access = True

            # 3. Host Fallback
            if not has_access:
                expanded_pattern = os.path.expanduser(folder_pattern)
                matches = list(glob.iglob(expanded_pattern))
                if (
                    matches and any(os.access(m, os.W_OK) for m in matches)
                ) or os.access(expanded_pattern, os.W_OK):
                    has_access = True

            # If any single path validation fails, drop out instantly
            if not has_access:
                return False

        return True

    def on_copy_clicked(self, payload: dict):
        """Extracts a path from the payload, expands it, and copies it to the clipboard."""
        path_to_copy = payload.get("path")

        if path_to_copy:
            expanded_path = os.path.expanduser(path_to_copy)
            Gdk.Display.get_default().get_clipboard().set_content(
                Gdk.ContentProvider.new_for_value(expanded_path)
            )

    def find_label_by_text(self, widget, text):
        """Recursively find a Gtk.Label containing specific text."""
        if isinstance(widget, Gtk.Label) and text in (widget.get_text() or ""):
            return widget

        child = widget.get_first_child()
        while child:
            found = self.find_label_by_text(child, text)
            if found:
                return found
            child = child.get_next_sibling()
        return None

    # }}}

    #  auto refresh logic here {{{
    @staticmethod
    def initial_status(self, toggled, accent_blue="#3584e4"):
        # Safely check and get the GNOME refresh switch state
        gnome_options = broker.get_page("gnome_options")
        gnome_refresh_switch = getattr(gnome_options, "refresh_switch", None)
        gnome_toggled = (
            gnome_refresh_switch.get_active() if gnome_refresh_switch else False
        )
        switch_text = (
            "Auto refresh active"
            if gnome_toggled
            else f"Auto refresh inactive - (<span color='{accent_blue}' underline='single'>See advanced GNOME options</span>)"
        )
        if hasattr(self, "gnome_switch"):
            self.gnome_row.set_subtitle(switch_text)
            self.gnome_row.set_use_markup(True)

        kde_options = broker.get_page("kde_options")

        # Safely check and get the KDE/Plasma refresh switch state
        plasma_refresh_switch = getattr(kde_options, "kde_refresh_switch", None)
        plasma_toggled = (
            plasma_refresh_switch.get_active() if plasma_refresh_switch else False
        )

        plasma_switch_text = (
            "Auto refresh active"
            if plasma_toggled
            else f"Auto refresh inactive - (<span color='{accent_blue}' underline='single'>See advanced KDE options</span>)"
        )
        if hasattr(self, "plasma_switch"):
            self.plasma_row.set_subtitle(plasma_switch_text)
            self.plasma_row.set_use_markup(True)

    # }}}

    def check_gnome_refresh_status(self):
        is_flatpak = os.path.exists("/.flatpak-info")

        if not is_flatpak:
            ready = True
        else:
            ready = self.is_gnome_refresh_ready()

        if hasattr(self, "refresh_switch") and hasattr(self, "gnome_handler_id"):
            broker.get_gage("gnome_options").refresh_switch.handler_block(
                self.gnome_handler_id
            )
            broker.get_gage("gnome_options").refresh_switch.set_active(ready)
            broker.get_gage("gnome_options").refresh_switch.handler_unblock(
                self.gnome_handler_id
            )

        return ready

    def check_plasma_refresh_status(self):
        # 1. DETECT ENVIRONMENT
        is_flatpak = os.path.exists("/.flatpak-info")

        # 2. DEFINE READINESS
        if not is_flatpak:
            # Native installs are always 'Ready' because they use direct commands
            ready = True
            status_text = "Status: Active (Native Mode)"
        else:
            # Flatpaks need to check for the systemd trigger files
            ready = self.is_plasma_refresh_ready()
            status_text = "Ready" if ready else "Not Setup - Requires one time install"

        # 3. UPDATE THE UI ROW
        if hasattr(self, "kde_refresh_row"):
            self.kde_refresh_row.set_subtitle(status_text)

        # 4. UPDATE THE SWITCH
        # Use the specific Plasma switch and handler ID
        if hasattr(self, "kde_refresh_switch") and hasattr(self, "plasma_handler_id"):
            self.kde_refresh_switch.handler_block(self.plasma_handler_id)
            self.kde_refresh_switch.set_active(ready)
            self.kde_refresh_switch.handler_unblock(self.plasma_handler_id)

            print(f"DEBUG: Plasma Row updated to {status_text} (Flatpak: {is_flatpak})")

        return ready

    def is_gnome_refresh_ready(self):
        # 1. Check Systemd Portal Path
        host_path = "~/.config/systemd/user"
        portal_path = getattr(
            self, f"active_portal_{self.get_safe_key(host_path)}", None
        )
        if not portal_path:
            portal_path = self.load_cached_portal_path(host_path)

        if not portal_path or not os.path.exists(portal_path):
            return False

        # 2. Check for the two GNOME refresher files
        path_exists = os.path.isfile(os.path.join(portal_path, "gnome-refresher.path"))
        service_exists = os.path.isfile(
            os.path.join(portal_path, "gnome-refresher.service")
        )
        if not (path_exists and service_exists):
            return False

        # 3. Check App Data Trigger
        trigger_file = os.path.expanduser(
            "~/.var/app/io.github.schwarzen.colormydesktop/data/colormydesktop/refresh.trigger"
        )
        if not os.path.isfile(trigger_file):
            return False

        return True

    def install_gnome_host_refresher(self, button=None):
        # These should be bundled in your Flatpak at /app/share/refresher/
        internal_path = "/app/share/refresher/"
        files_to_copy = ["gnome-refresher.path", "gnome-refresher.service"]

        # This is the "abstract" host path for tracking permissions
        host_config_path = "~/.config/systemd/user"

        chooser = Gtk.FileChooserNative.new(
            title="Select systemd folder (usually ~/.config/systemd/user)",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )

        # Start the chooser in the home config dir to help the user find it
        chooser.set_current_folder(
            Gio.File.new_for_path(os.path.expanduser("~/.config/systemd/user"))
        )

        def on_response(dialog, response_id):
            if response_id == Gtk.ResponseType.ACCEPT:
                target_folder_file = dialog.get_file()
                sandboxed_path = target_folder_file.get_path()

                try:
                    # 1. Copy the GNOME systemd files
                    for filename in files_to_copy:
                        src = os.path.join(internal_path, filename)
                        dst = os.path.join(sandboxed_path, filename)

                        if not os.path.exists(src):
                            print(f"Error: {src} not found in sandbox!")
                            continue

                        with open(src, "rb") as f_src:
                            content = f_src.read()

                        g_file_dst = Gio.File.new_for_path(dst)
                        g_file_dst.replace_contents(
                            content,
                            None,
                            False,
                            Gio.FileCreateFlags.REPLACE_DESTINATION,
                            None,
                        )

                    trigger_path = os.path.expanduser(
                        "~/.var/app/io.github.schwarzen.colormydesktop/data/colormydesktop/refresh.trigger"
                    )

                    # Ensure the directory structure exists
                    os.makedirs(os.path.dirname(trigger_path), exist_ok=True)

                    # Create the file if it doesn't exist
                    if not os.path.exists(trigger_path):
                        with open(trigger_path, "w") as f:
                            f.write("trigger")  # Initial content
                        print(f"Trigger file created at: {trigger_path}")
                    # 2. PERSISTENCE: Link host path to the portal path
                    self.save_portal_path(host_config_path, sandboxed_path)

                    # 3. SESSION DATA: Update the safe_key attribute
                    safe_key = self.get_safe_key(host_config_path)
                    setattr(self, f"active_portal_{safe_key}", sandboxed_path)

                    # 4. REFRESH UI: Update the GNOME setup dialog
                    self.show_gnome_setup_dialog()
                    self.toast_overlay.add_toast(
                        Adw.Toast.new("GNOME Installer Successful!")
                    )

                except Exception as e:
                    print(f"Failed to copy GNOME files: {e}")
                    self.toast_overlay.add_toast(
                        Adw.Toast.new("Installation Failed! Check console.")
                    )

            dialog.destroy()

        chooser.connect("response", on_response)
        chooser.show()

    def install_host_refresher(self, button=None):
        internal_path = "/app/share/refresher/"
        files_to_copy = ["plasma-refresher.path", "plasma-refresher.service"]
        # The abstract host path we are targeting
        host_config_path = "~/.config/systemd/user"

        chooser = Gtk.FileChooserNative.new(
            title="Select systemd folder (usually ~/.config/systemd/user)",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )

        chooser.set_current_folder(
            Gio.File.new_for_path(os.path.expanduser("~/.config/systemd/user"))
        )

        def on_response(dialog, response_id):
            if response_id == Gtk.ResponseType.ACCEPT:
                target_folder_file = dialog.get_file()
                sandboxed_path = target_folder_file.get_path()

                try:
                    # 1. Copy the files using your Gio logic
                    for filename in files_to_copy:
                        src = os.path.join(internal_path, filename)
                        dst = os.path.join(sandboxed_path, filename)

                        with open(src, "rb") as f_src:
                            content = f_src.read()

                        g_file_dst = Gio.File.new_for_path(dst)
                        g_file_dst.replace_contents(
                            content,
                            None,
                            False,
                            Gio.FileCreateFlags.REPLACE_DESTINATION,
                            None,
                        )

                    trigger_path = os.path.expanduser(
                        "~/.var/app/io.github.schwarzen.colormydesktop/data/colormydesktop/plasma-refresh.trigger"
                    )

                    # Ensure the directory structure exists
                    os.makedirs(os.path.dirname(trigger_path), exist_ok=True)

                    # Create the file if it doesn't exist
                    if not os.path.exists(trigger_path):
                        with open(trigger_path, "w") as f:
                            f.write("trigger")  # Initial content
                        print(f"Trigger file created at: {trigger_path}")
                    # 2. PERSISTENCE: Save the link between the host path and portal path
                    # This ensures the status boxes turn green after restart
                    self.save_portal_path(host_config_path, sandboxed_path)

                    # 3. SESSION DATA: Update the safe_key attribute
                    safe_key = self.get_safe_key(host_config_path)
                    setattr(self, f"active_portal_{safe_key}", sandboxed_path)

                    # 4. REFRESH UI: Re-run the setup dialog to update icons to green
                    self.toast_overlay.add_toast(Adw.Toast.new("Installer Successful!"))

                except Exception as e:
                    print(f"Failed to copy files: {e}")

            dialog.destroy()

        chooser.connect("response", on_response)
        chooser.show()

    def show_installation_success(self, path):
        # Determine the parent window safely
        parent = self if isinstance(self, Gtk.Window) else self.get_toplevel()

        dialog = Gtk.MessageDialog(
            transient_for=parent,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Units Installed Successfully",
        )

        command = "systemctl --user enable --now plasma-refresher.path"

        # In GTK 3, use set_secondary_text
        dialog.set_secondary_text(
            f"Files copied to: {path}\n\n"
            "To start the refresher trigger, run this on your host terminal:\n\n"
            f"{command}"
        )

        # Add a "Copy Command" button
        dialog.add_button("Copy Command", Gtk.ResponseType.APPLY)

        response = dialog.run()

        # If they clicked "Copy Command" (APPLY)
        if response == Gtk.ResponseType.APPLY:
            clipboard = Gtk.Clipboard.get(Gdk.Selection.CLIPBOARD)
            clipboard.set_text(command, -1)
            # Briefly change text to show it worked
            dialog.set_secondary_text(
                "Command copied to clipboard! You can now paste it into your terminal."
            )
            dialog.run()

        dialog.destroy()

    def trigger_refresh(self):
        import os
        import subprocess
        from colormydesktop.broker import ContextBroker

        # 1. Check local instance "plasma_switch" status
        if (
            not hasattr(self, "plasma_switch")
            or not self.plasma_switch
            or not self.plasma_switch.get_active()
        ):
            print("refresh skipped: local plasma_switch is inactive or missing")
            return

        kde_options = ContextBroker.get_page("kde_options")

        # 2. Check broker "refresh_switch" status (matching the GNOME logic style)
        kde_refresh_switch = getattr(kde_options, "switches", {}).get(
            "kde_refresh_switch"
        )

        if not kde_refresh_switch or not kde_refresh_switch.get_active():
            print("refresh skipped: refresh_switch is inactive or missing")
            return

        # 3. Proceed with execution if both criteria are met
        is_flatpak = os.path.exists("/.flatpak-info")

        if is_flatpak:
            # --- FLATPAK LOGIC: Touch the trigger file ---
            trigger_path = os.path.expanduser(
                "~/.var/app/io.github.schwarzen.colormydesktop/data/colormydesktop/plasma-refresh.trigger"
            )
            try:
                os.makedirs(os.path.dirname(trigger_path), exist_ok=True)
                with open(trigger_path, "a"):
                    os.utime(trigger_path, None)
                print(f"Flatpak: Refresh signal sent to {trigger_path}")
            except Exception as e:
                print(f"Flatpak Trigger Error: {e}")
        else:
            # --- NATIVE LOGIC: Run the command directly ---
            try:
                cmd = "/usr/bin/bash -c '/usr/bin/plasma-apply-colorscheme BreezeDark && sleep 0.5 && /usr/bin/plasma-apply-colorscheme Color-My-Desktop-Scheme'"
                subprocess.Popen(cmd, shell=True)
                print("Native: Direct Plasma refresh command executed.")
            except Exception as e:
                print(f"Native Refresh Error: {e}")

    def save_portal_path(self, folder_path, portal_path):
        # Use the app's specific config directory to ensure it's writable
        config_dir = GLib.get_user_data_dir()
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        config_file = os.path.join(config_dir, "portal_cache.json")
        cache = {}

        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    cache = json.load(f)
            except Exception:
                cache = {}

        cache[folder_path] = portal_path
        with open(config_file, "w") as f:
            json.dump(cache, f)

    def load_cached_portal_path(self, folder_path):
        config_file = os.path.expanduser("~/.config/portal_cache.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    cache = json.load(f)
                    return cache.get(folder_path)
            except Exception:
                return None
        return None

    # Run this during app initialization
    def load_all_cached_portals(self):
        config_dir = GLib.get_user_data_dir()
        config_file = os.path.join(config_dir, "portal_cache.json")
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                cache = json.load(f)
                for host_path, portal_path in cache.items():
                    safe_key = self.get_safe_key(host_path)
                    setattr(self, f"active_portal_{safe_key}", portal_path)

    def on_plasma_refresh_toggled(
        self, is_active, switch_widget, kde_options_page=None
    ):
        import os
        from colormydesktop.broker import ContextBroker

        # NOTE: Update this import to match your actual Plasma Setup page class
        from colormydesktop.lib_gui import KDESetupDialog

        current_widget = kde_options_page if kde_options_page else switch_widget
        is_flatpak = os.path.exists("/.flatpak-info")

        if is_flatpak:
            if is_active and not self.check_plasma_refresh_status():
                # 1. Validation failed: Reset the switch instantly
                if switch_widget:
                    switch_widget.set_active(False)

                # 2. Trigger broker navigation instead of calling a hardcoded dialog
                ContextBroker.navigate(
                    current_widget=current_widget,
                    target_page_class=KDESetupDialog,
                    page_id="kde_setup_dialog",
                )
            elif not is_active:
                print("Plasma Auto-Reload Disabled (Flatpak mode)")
        else:
            if is_active:
                print("Plasma Auto-Reload Enabled (Native mode - direct commands)")

    def on_gnome_refresh_toggled(
        self, is_active, switch_widget, gnome_options_page=None
    ):
        import os
        from colormydesktop.broker import ContextBroker

        # NOTE: Update this import to match your actual Setup page class
        from colormydesktop.lib_gui import GnomeSetupDialog

        current_widget = gnome_options_page if gnome_options_page else switch_widget

        is_flatpak = os.path.exists("/.flatpak-info")

        if is_flatpak:
            if is_active and not self.check_gnome_refresh_status():
                # 1. Validation failed: Reset the switch instantly
                if switch_widget:
                    switch_widget.set_active(False)

                # 2. Trigger broker navigation instead of calling a hardcoded dialog
                # We can use switch_widget as the current_widget reference for the broker
                ContextBroker.navigate(
                    current_widget=current_widget,
                    target_page_class=GnomeSetupDialog,
                    page_id="gnome_setup_dialog",
                )

            elif not is_active:
                print("GNOME Auto-Reload Disabled (Flatpak mode)")
        else:
            if is_active:
                print("GNOME Auto-Reload Enabled (Native mode - direct commands)")

    def trigger_shell_refresh(self):
        from colormydesktop.broker import ContextBroker

        gnome_options = ContextBroker.get_page("gnome_options")
        # 1. Check local instance "plasma_switch" status
        if (
            not hasattr(self, "gnome_switch")
            or not self.gnome_switch
            or not self.gnome_switch.get_active()
        ):
            print("refresh skipped: local gnome_switch is inactive or missing")
            return
        # Check if "refresh" switch exists in gnome_options and is active
        refresh_switch = getattr(gnome_options, "switches", {}).get("refresh_switch")

        if not refresh_switch or not refresh_switch.get_active():
            print("refresh skipped")
            return

        is_flatpak = os.path.exists("/.flatpak-info")

        if is_flatpak:
            # --- FLATPAK LOGIC: Touch the trigger file ---
            trigger_path = os.path.expanduser(
                "~/.var/app/io.github.schwarzen.colormydesktop/data/colormydesktop/refresh.trigger"
            )
            try:
                os.makedirs(os.path.dirname(trigger_path), exist_ok=True)
                with open(trigger_path, "a"):
                    os.utime(trigger_path, None)
                print("Flatpak: GNOME refresh signal sent.")
            except Exception as e:
                print(f"Flatpak Trigger Error: {e}")
        else:
            # --- NATIVE LOGIC: Run dconf commands directly ---
            try:
                # We toggle the theme to empty then back to your theme to force a refresh
                # Use a raw triple-quoted string to handle all internal quotes safely
                cmd = r"""/usr/bin/bash -c '
                dconf write /org/gnome/shell/extensions/user-theme/name " \"\" ";
                sleep 0.2;
                dconf write /org/gnome/shell/extensions/user-theme/name " \"Color-My-Desktop\" "
                '"""

                subprocess.Popen(cmd, shell=True)
                print("Native: Direct GNOME refresh executed via dconf.")
            except Exception as e:
                print(f"Native Refresh Error: {e}")

    # FIX: }}}
    def on_show_contrast_dialog(self, row):
        p_hex = self.primary_row.get_text()
        txt_hex = self.text_row.get_text()
        ratio = self.get_contrast_ratio(p_hex, txt_hex)

        # Create a MessageDialog
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Accessibility Details",
            body=f"Current Ratio: {ratio:.1f}:1\n\nWCAG standards recommend at least 4.5:1 for readable text. Poor contrast can make your theme difficult to use.",
        )

        dialog.add_response("cancel", "Close")

        # Only add the "Fix" button if the contrast is actually bad
        if ratio < 4.5:
            dialog.add_response("fix", "Auto-Fix Contrast")
            dialog.set_response_appearance("fix", Adw.ResponseAppearance.SUGGESTED)

        def on_response(d, response):
            if response == "fix":
                self.on_fix_contrast_clicked(None)
            d.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def on_generate_variants_clicked(self, button):
        primary_hex = self.primary_row.get_text().strip()
        rgba = Gdk.RGBA()

        if not rgba.parse(primary_hex):
            return

        # Calculate Perceived Brightness (Luminance)
        # Range is 0.0 (Black) to 1.0 (White)
        brightness = (rgba.red * 0.299) + (rgba.green * 0.587) + (rgba.blue * 0.114)

        # Determine Offset (Lighter if dark, Darker if light)
        # If brightness < 0.5, we want to lighten for variants
        offset = 0.15 if brightness < 0.5 else -0.15

        def adjust_color(color, amount):
            # Create a new RGBA, clamped between 0 and 1
            new_rgba = Gdk.RGBA()
            new_rgba.red = max(0, min(1, color.red + amount))
            new_rgba.green = max(0, min(1, color.green + amount))
            new_rgba.blue = max(0, min(1, color.blue + amount))
            new_rgba.alpha = 1.0

            # Convert back to HEX
            return "#{:02x}{:02x}{:02x}".format(
                int(new_rgba.red * 255),
                int(new_rgba.green * 255),
                int(new_rgba.blue * 255),
            )

        #  Apply to Secondary and Tertiary rows
        # Secondary is slightly shifted, Tertiary is shifted more
        secondary_hex = adjust_color(rgba, offset)
        tertiary_hex = adjust_color(rgba, offset * 2)

        self.secondary_row.set_text(secondary_hex)
        self.tertiary_row.set_text(tertiary_hex)

        # Trigger UI sync

    def on_delete_confirm(self, dialog, response, theme_name):
        if response == "delete":
            # Construct the file path
            file_path = os.path.join(SCSS_DIR, f"_{theme_name}.scss")

            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Deleted profile file: {file_path}")

                    # Refresh the UI
                    self.refresh_theme_list()

                    # Return to Default profile
                    self.ui.combo_row.set_selected(0)

                    # Show success toast
                    toast = Adw.Toast.new(f"Profile '{theme_name}' deleted")
                    self.toast_overlay.add_toast(toast)
            except Exception as e:
                print(f"Error deleting file: {e}")

        dialog.destroy()

    def get_contrast_ratio(self, hex1, hex2):
        def get_luminance(hex_code):
            rgba = Gdk.RGBA()
            rgba.parse(hex_code)

            # Formula for relative luminance
            def adjust(c):
                return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

            r, g, b = adjust(rgba.red), adjust(rgba.green), adjust(rgba.blue)
            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        l1 = get_luminance(hex1)
        l2 = get_luminance(hex2)

        # Calculate ratio (L_bright + 0.05) / (L_dark + 0.05)
        return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)

    def load_persistent_settings(self):
        config_path = os.path.expanduser(
            "~/.var/app/io.github.schwarzen.colormydesktop/config/color-my-desktop/settings.json"
        )
        if os.path.exists(config_path):
            try:
                import json

                with open(config_path, "r") as f:
                    data = json.load(f)
                    self.last_manually_entered_zen_path = data.get("zen_path", "")
                    print(
                        f"DEBUG: Loaded Zen Path: {self.last_manually_entered_zen_path}"
                    )
            except Exception as e:
                print(f"DEBUG: Failed to load settings: {e}")
                self.last_manually_entered_zen_path = ""

    def on_fix_contrast_clicked(self, button):
        p_hex = self.primary_row.get_text()
        rgba = Gdk.RGBA()
        if not rgba.parse(p_hex):
            return

        # Calculate primary luminance
        def get_lum(c):
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        lum = (
            0.2126 * get_lum(rgba.red)
            + 0.7152 * get_lum(rgba.green)
            + 0.0722 * get_lum(rgba.blue)
        )

        # If background is dark, use White. If light, use Black.
        new_text = "#ffffff" if lum < 0.5 else "#000000"
        self.text_row.set_text(new_text)

    def is_valid_hex(self, color):
        # Strip whitespace to avoid simple input errors
        color = color.strip()

        # Matches SCSS variables (e.g., $primary-color)
        if re.match(r"^\$[A-Za-z0-9_-]+$", color):
            return True

        if re.match(r"^#?([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$", color):
            return True

        # Fallback to Gdk.RGBA.parse (Handles rgba(0,0,0,0), hsl, names, etc.)
        rgba = Gdk.RGBA()
        return rgba.parse(color)

    def update_preview(self, entry, css_id):
        #  Get the current text
        try:
            hex_code = entry.get_text().strip()
        except AttributeError:
            # This happens if 'entry' is actually a GParamSpec
            return

        #  Validation
        rgba = Gdk.RGBA()
        if rgba.parse(hex_code) or (
            hex_code.startswith("#") and len(hex_code) in [4, 7, 9]
        ):
            # --- NEW: BRIGHTNESS CHECK FOR ICON CONTRAST ---
            # Standard perceived luminance formula
            brightness = (rgba.red * 0.299) + (rgba.green * 0.587) + (rgba.blue * 0.114)

            # If brightness > 0.6, the background is light, so use a dark icon
            icon_color = (
                "rgba(0,0,0,0.7)" if brightness > 0.6 else "rgba(255,255,255,0.8)"
            )

            # Store this in your color registry so the CSS builder can see it
            if not hasattr(self, "icon_colors"):
                self.icon_colors = {}
            self.icon_colors[css_id] = icon_color
            clean_hex = hex_code if hex_code.startswith("#") else f"#{hex_code}"

            if not hasattr(self, "current_colors"):
                self.current_colors = {}
            self.current_colors[css_id] = clean_hex

            #  Rebuild the CSS string
            full_css = ""
            for cid, hcolor in self.current_colors.items():
                # Update dots
                full_css += f"#{cid}-preview {{ background-color: {hcolor}; border-radius: 6px; min-width: 24px; min-height: 24px; }}\n"

            # Apply CSS
            if hasattr(self, "dynamic_color_provider"):
                self.dynamic_color_provider.load_from_string(full_css)

    def on_advanced_picker_clicked(self, gesture, n_press, x, y, entry_row):
        # Create the dialog
        dialog = Gtk.ColorChooserDialog(
            title="Advanced Color Editor", transient_for=self
        )

        # Force the sliders/custom menu to be the first thing visible
        dialog.set_property("show-editor", True)

        # Pre-set the current color from the row
        rgba = Gdk.RGBA()
        if rgba.parse(entry_row.get_text().strip()):
            dialog.set_rgba(rgba)

        # Use the standard response pattern
        dialog.connect("response", self.on_advanced_response, entry_row)
        dialog.present()

    def on_quick_picker_clicked(self, gesture, n_press, x, y, entry_row):
        #  Create the dialog
        dialog = Gtk.ColorChooserDialog(title="Select Color", transient_for=self)

        #  FORCE GRID VIEW: Ensure the editor/sliders are hidden by default
        dialog.set_property("show-editor", False)

        #  Pre-set the current color
        rgba = Gdk.RGBA()
        current_text = entry_row.get_text().strip()
        if rgba.parse(
            current_text if current_text.startswith("#") else f"#{current_text}"
        ):
            dialog.set_rgba(rgba)

        # Use existing response handler to save the color back to the row
        dialog.connect("response", self.on_advanced_response, entry_row)
        dialog.present()

    def on_advanced_response(self, dialog, response_id, entry_row):
        if response_id == Gtk.ResponseType.OK:
            rgba = dialog.get_rgba()
            hex_color = "#{:02x}{:02x}{:02x}".format(
                int(rgba.red * 255), int(rgba.green * 255), int(rgba.blue * 255)
            )
            entry_row.set_text(hex_color)
        dialog.destroy()

    def on_eye_dropper_clicked(self, button, dialog, entry_row):
        # This opens the system-level color picker portal
        dialog.choose_rgba(self, None, None, self.on_color_picked, entry_row)

    def on_color_picked(self, dialog, result, entry_row):
        try:
            # Get the color from the result
            rgba = dialog.choose_rgba_finish(result)
            if rgba:
                # Convert RGBA to HEX (standard CSS format)
                hex_color = "#{:02x}{:02x}{:02x}".format(
                    int(rgba.red * 255), int(rgba.green * 255), int(rgba.blue * 255)
                )
                # Update the entry row - this triggers your live preview automatically!
                entry_row.set_text(hex_color)
        except Exception as e:
            print(f"Color picking cancelled or failed: {e}")

    def setup_css_providers(self):
        display = Gdk.Display.get_default()

        #  Attach them to 'self' so they persist as instance attributes
        self.preview_css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            display, self.preview_css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.dynamic_color_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            display,
            self.dynamic_color_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Update the loading logic to use 'self.'
        initial_css = "/* your initial css */"
        self.dynamic_color_provider.load_from_string(initial_css)  # Added self.

        # --- DATA EXTRACTION LOGIC ---

    def get_scss_value(self, filename, variable):
        path = os.path.join(SCSS_DIR, f"_{filename}.scss")
        if not os.path.exists(path):
            return ""

        with open(path, "r") as f:
            content = f.read()
            #  FIXED: \$? makes the dollar sign optional, allowing it to read comments
            match = re.search(rf"\$?{variable}:\s*([^;/\n]+)", content)

            if match:
                # Extract value and strip spaces, trailing semicolons, or comment symbols
                value = match.group(1).strip()
                return value.replace("*/", "").replace("/*", "").strip()

            return ""

    def on_theme_select(self, combo_row, gparamspec):
        selected_index = combo_row.get_selected()
        is_default = combo_row.get_selected() == 0
        selected_index = combo_row.get_selected()

        #  Guard: Ignore index 0 ('Default') or errors
        if selected_index <= 0:
            print("Resetting to Default theme values...")
            self.ui.name_row.set_text("Default")
            self.ui.color_entries["primary"].set_text("#21233b")
            self.ui.color_entries["secondary"].set_text("#241f31")
            self.ui.color_entries["accent"].set_text("#1e1e1e")
            self.ui.color_entries["text"].set_text("#f9f9f9")
            broker.topbar_switch.set_active(False)

            return

            # ---  RESET TO DEFAULT CASE ---
        if is_default:
            print("Resetting to Default theme values...")
            self.name_row.set_text("Default")
            self.ui.color_entries["primary"].set_text("#21233b")
            self.ui.color_entries["secondary"].set_text("#241f31")
            self.ui.color_entries["accent"].set_text("#1e1e1e")
            self.ui.color_entries["text"].set_text("#f9f9f9")

            broker.topbar_switch.set_active(False)
            # Refresh mockup for default values
            return

        selected_theme = self.theme_list.get_string(selected_index)
        if not selected_theme:
            return

        #  Construct the path INSIDE the function
        # Use  defined SCSS_DIR variable or the absolute path
        partial_path = os.path.join(SCSS_DIR, f"_{selected_theme}.scss")

        print(f"Loading {selected_theme} from {partial_path}...")

        if os.path.exists(partial_path):
            with open(partial_path, "r") as f:
                content = f.read()

                #  Helper to extract and sync advanced rows
                def sync_advanced_feature(css_id, var_name):
                    import re

                    pattern = rf"\${re.escape(var_name)}:\s*(#[0-9a-fA-F]{{3,6}})"
                    match = re.search(pattern, content)

                    sw = getattr(self, f"{css_id}_switch", None)
                    en = getattr(self, f"{css_id}_entry", None)

                    if match and sw and en:
                        hex_val = match.group(1).lower()
                        primary_hex = self.primary_row.get_text().lower()

                        # Update the text entry
                        en.set_text(hex_val)

                        if hex_val != primary_hex:
                            sw.set_active(True)
                        else:
                            sw.set_active(False)
                    elif sw:
                        sw.set_active(False)

                #  TRIGGER SYNC
                sync_advanced_feature("nautilus_custom", "nautilus-main")
                sync_advanced_feature("nautilus_custom_sec", "nautilus-secondary")

            #  Update the Name field
            self.ui.name_row.set_text(selected_theme)

            # Update EACH color row specifically
            # Using existing get_scss_value logic
            self.ui.color_entries["primary"].set_text(
                self.get_scss_value(selected_theme, "primary")
            )
            self.ui.color_entries["secondary"].set_text(
                self.get_scss_value(selected_theme, "secondary")
            )
            self.ui.color_entries["accent"].set_text(
                self.get_scss_value(selected_theme, "tertiary")
            )
            self.ui.color_entries["text"].set_text(
                self.get_scss_value(selected_theme, "text")
            )

            tb_val = self.get_scss_value(selected_theme, "topbar-color")
            tb_custom = self.get_scss_value(selected_theme, "CUSTOM_TOPBAR")
            if "yes" in tb_custom:
                broker.topbar_entry.set_text(tb_val)
                broker.topbar_switch.set_active(True)
            else:
                # If the file doesn't have it, reset to a safe default but don't clear it!
                broker.topbar_entry.set_text(
                    self.get_scss_value(selected_theme, "primary")
                )
                broker.topbar_switch.set_active(False)

            clock_val = self.get_scss_value(selected_theme, "clock-color")
            clock_custom = self.get_scss_value(selected_theme, "CUSTOM_CLOCK")
            if "yes" in clock_custom:
                broker.clock_entry.set_text(clock_val)
                broker.clock_switch.set_active(True)
            else:
                # If the file doesn't have it, reset to a safe default but don't clear it!
                broker.clock_entry.set_text(self.get_scss_value(selected_theme, "text"))
                broker.clock_switch.set_active(False)

            gnome_menu_val = f"{self.get_scss_value(selected_theme, 'gnome-menu-start')},{self.get_scss_value(selected_theme, 'gnome-menu-end')}"
            gnome_menu_custom = self.get_scss_value(selected_theme, "CUSTOM_GNOME_MENU")
            if "yes" in gnome_menu_custom:
                broker.datemenu_entry.set_text(gnome_menu_val)
                broker.datemenu_switch.set_active(True)
            else:
                # If the file doesn't have it, reset to a safe default but don't clear it!
                broker.datemenu_entry.set_text(
                    self.get_scss_value(selected_theme, "primary")
                )
                broker.datemenu_switch.set_active(False)

            nautilus_main_val = f"{self.get_scss_value(selected_theme, 'nautilus-start')},{self.get_scss_value(selected_theme, 'nautilus-end')}"
            nautilus_main_custom = self.get_scss_value(
                selected_theme, "CUSTOM_NAUTILUS_MAIN"
            )
            if "yes" in nautilus_main_custom:
                broker.nautilusprimarycolor_entry.set_text(nautilus_main_val)
                broker.nautilusprimarycolor_switch.set_active(True)
            else:
                # If the file doesn't have it, reset to a safe default but don't clear it!
                broker.nautilusprimarycolor_entry.set_text(
                    self.get_scss_value(selected_theme, "primary")
                )
                broker.nautilusprimarycolor_switch.set_active(False)

            nautilus_second_val = (
                f"{self.get_scss_value(selected_theme, 'nautilus-secondary')}"
            )
            nautilus_second_custom = self.get_scss_value(
                selected_theme, "CUSTOM_NAUTILUS_SECOND"
            )
            if "yes" in nautilus_second_custom:
                broker.nautilussecondarycolor_entry.set_text(nautilus_second_val)
                broker.nautilussecondarycolor_switch.set_active(True)
            else:
                # If the file doesn't have it, reset to a safe default but don't clear it!
                broker.nautilussecondarycolor_entry.set_text(
                    self.get_scss_value(selected_theme, "secondary")
                )
                broker.nautilusprimarycolor_switch.set_active(False)
            gradient_val = f"{self.get_scss_value(selected_theme, 'gnome-menu-end')}"
            gradient_custom = self.get_scss_value(selected_theme, "CUSTOM_GRAD")
            if "yes" in gradient_custom:
                primary_val = self.get_scss_value(selected_theme, "primary")
                self.ui.color_entries["primary"].set_text(
                    f"{primary_val} , {gradient_val}"
                )
            else:
                # If the file doesn't have it, reset to a safe default but don't clear it!
                self.ui.color_entries["primary"].set_text(
                    self.get_scss_value(selected_theme, "primary")
                )

    # --- RUN BASH SCRIPT ---
    def on_configure_clicked(self, button):

        self.active_build_button = button
        self.active_build_button.set_sensitive(False)

        # We add "config_only" as the very first argument ($1)
        args = [
            "config_only",
            self.name_row.get_text(),
            self.primary_row.get_text(),
            self.secondary_row.get_text(),
            self.tertiary_row.get_text(),
            self.text_row.get_text(),
        ]

        # Use your existing threading logic
        thread = threading.Thread(target=self.execute_build, args=(args,))
        thread.daemon = True
        thread.start()

        button.set_sensitive(False)

    def refresh_theme_list(self):
        """Rescans SCSS_DIR, updates the model, and selects the new profile."""
        if not os.path.exists(SCSS_DIR):
            return

        # 1. Capture the name the user just saved so we can select it later
        newly_saved_name = self.ui.name_row.get_text()

        #  Collect only the custom themes from the directory
        custom_themes = []
        for f in os.listdir(SCSS_DIR):
            if f.startswith("_") and f.endswith(".scss"):
                name = f[1:-5]  # Strip '_' and '.scss'
                if name != "Default":
                    custom_themes.append(name)

        #  Sort ONLY the custom themes alphabetically
        custom_themes.sort()

        #  Create the final list with "Default" locked at index 0
        final_list = ["Default"] + custom_themes

        #  Update the Gtk.StringList model
        current_count = self.theme_list.get_n_items()
        self.theme_list.splice(0, current_count, final_list)

        #  AUTO-SELECT: Find the index of the newly created profile
        # We loop through the new list to find the match
        for index, theme_name in enumerate(final_list):
            if theme_name == newly_saved_name:
                self.ui.combo_row.set_selected(index)
                break

        print(f"Refreshed dropdown. Selected: {newly_saved_name}")

    # SECTION END FUNCTIONS }}}
    def on_run_build_clicked(self, button):
        from colormydesktop.config import get_default_color_map

        final_colors = get_default_color_map()
        print("\n=== [DEBUG] THEME BUILDER SEES MAP AT CLICK TIME ===")
        print(json.dumps(final_colors, indent=4))
        print("===================================================\n")

        # Standalone parser mirroring the mockup function
        def extract_stops(val, fallback):
            val = str(val).strip() if val else fallback
            if "," in val:
                colors = [c.strip() for c in val.split(",") if c.strip()]
                if len(colors) >= 2:
                    return colors[0], colors[1]
                elif colors:
                    return colors[0], colors[0]
            return val, val

        topbar_start, topbar_end = extract_stops(
            final_colors.get("topbarcolor"), "#1a4d8c"
        )
        gnome_menu_start, gnome_menu_end = extract_stops(
            final_colors.get("datemenucolor"), "#1a4d8c"
        )
        nautilus_start, nautilus_end = extract_stops(
            final_colors.get("nautilusprimarycolor"), "#1a4d8c"
        )

        self.active_build_button = button
        self.active_build_button.set_sensitive(False)
        # Get primary hex and ensure it is a string
        primary_color = str(self.ui.color_entries["primary"].get_text() or "#246cc5")
        secondary_color = str(
            self.ui.color_entries["secondary"].get_text() or "#246cc5"
        )
        text_color = str(self.ui.color_entries["text"].get_text() or "#f9f9f9")
        plasma_path = self.get_path_argument("~/.local/share/plasma")
        schemes_path = self.get_path_argument("~/.local/share/color-schemes")
        gnome_path = self.get_path_argument("~/.local/share/themes")
        #  Dynamic Zen path
        # Get the actual path string first (falling back to the default glob if not set)
        current_zen_val = getattr(
            self, "last_manually_entered_zen_path", "~/.zen/*/chrome"
        )

        # Pass that VALUE to get_path_argument
        zen_path = self.get_path_argument(current_zen_val)
        vesktop_path = self.get_path_argument("~/.config/vesktop/themes")
        gtk4_path = self.get_path_argument("~/.config/gtk-4.0")
        papirus_path = self.get_path_argument("~/.local/share/icons")
        raw_primary = self.ui.color_entries["primary"].get_text().strip()

        # Set up defaults assuming it's a normal single hex color
        solid_primary = raw_primary
        gradient_str = "none"

        # Detect if the user typed a comma-separated gradient sequence
        if "," in raw_primary:
            colors = [c.strip() for c in raw_primary.split(",") if c.strip()]
            if colors:
                solid_primary = colors[
                    0
                ]  # Extracts the first color for st-mix/fallbacks
                gradient_str = ", ".join(colors)

        topbar_val = broker.gnome.get_color_value("topbarcolor", primary_color)
        clock_val = broker.gnome.get_color_value("clockcolor", text_color)
        datemenu_val = broker.gnome.get_color_value("datemenucolor", primary_color)
        n_main_val = broker.nautilus.get_color_value(
            "nautilusprimarycolor", primary_color
        )
        n_sec_val = broker.nautilus.get_color_value(
            "nautilussecondarycolor", secondary_color
        )

        topbar_str = broker.gnome.get_switch_string("topbarcolor")
        clock_str = broker.gnome.get_switch_string("clockcolor")
        gnome_menu_str = broker.gnome.get_switch_string("datemenucolor")

        n_main_str = broker.nautilus.get_switch_string("nautilusprimarycolor")
        n_sec_str = broker.nautilus.get_switch_string("nautilussecondarycolor")

        args = [
            self.ui.name_row.get_text(),
            solid_primary,
            self.ui.color_entries["secondary"].get_text(),
            self.ui.color_entries["accent"].get_text(),
            self.ui.color_entries["text"].get_text(),
            "1" if self.zen_switch.get_active() else "0",
            topbar_str,
            topbar_val,  # topbar_val
            clock_str,  # if self.clock_switch.get_active() else "0",
            clock_val,  # clock_val
            "0",  # if self.trans_switch.get_active() else "0",
            "0.8",
            "1" if self.papirus_switch.get_active() else "0",  # ${13}
            n_main_val,  # n_main_val ($14)
            "#246cc5",  # $15 (Datemenu fallback)
            n_sec_val,  # n_sec_val ($16)
            "1" if self.ui.gnome_switch.get_active() else "0",  # $17
            "1" if self.gtk4_switch.get_active() else "0",  # $18
            "1" if self.plasma_switch.get_active() else "0",  # $19
            "1" if self.youtube_switch.get_active() else "0",  # 20
            "1" if self.vesktop_switch.get_active() else "0",  # 21
            plasma_path,  # $22
            schemes_path,  # $23
            gnome_path,
            zen_path,
            vesktop_path,
            gtk4_path,
            papirus_path,
            gradient_str,  # ${29}
            topbar_start,
            topbar_end,
            gnome_menu_start,
            gnome_menu_end,  # 33
            gnome_menu_str,  # 34
            nautilus_start,  # 35
            nautilus_end,  # 36
            n_main_str,  # 37
            n_sec_str,  # 38
        ]
        self.log_container.set_visible(True)
        self.log_view.get_buffer().set_text("")
        self.progress_bar.set_fraction(0.1)

        # Start the build in a background thread
        thread = threading.Thread(target=self.execute_build, args=(args,))
        thread.daemon = True  # Closes thread if you exit the app
        thread.start()
        button.set_sensitive(False)

    def execute_build(self, args):

        try:
            # Use 'stdbuf -oL' to force Bash to send output line-by-line immediately
            process = subprocess.Popen(
                ["stdbuf", "-oL", BASH_SCRIPT] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                preexec_fn=os.setsid,  #  CRITICAL: Groups shell script + child commands together
            )

            #  NEW: Attach the process instance to a tracking variable where on_window_close can read it
            # (Adjust self.ui, self.window, or your current context reference to pass it to the exit function)
            if hasattr(self, "ui") and self.ui:
                self.ui.current_process = process
            else:
                self.current_process = process

            # Read output in real-time
            for line in iter(process.stdout.readline, ""):
                if line:
                    # 1. Print directly to terminal running the GUI
                    sys.stdout.write(line)
                    sys.stdout.flush()
                    # Use idle_add to update the UI from the background thread safely
                    GLib.idle_add(self.append_log, line)

            process.wait()
        except Exception as e:
            GLib.idle_add(self.append_log, f"Error: {str(e)}\n")
        finally:
            #  NEW: Clear tracking reference once the process naturally finishes
            if hasattr(self, "ui") and self.ui:
                self.ui.current_process = None
            else:
                self.current_process = None

            if args[0] == "config_only":
                GLib.idle_add(self.config_finished_cleanup)
            else:
                # For standard builds, keep your existing logic
                GLib.idle_add(self.trigger_shell_refresh)
                GLib.idle_add(self.trigger_refresh)
                GLib.idle_add(self.build_finished)

    def config_finished_cleanup(self):
        #  Re-enable the button using existing attribute
        if hasattr(self, "active_build_button"):
            self.active_build_button.set_sensitive(True)

        #  Show the success toast
        self.toast_overlay.add_toast(Adw.Toast.new("Configuration Saved!"))

        #  Hide the configuration row since the task is done
        if hasattr(self, "bash_trigger_row"):
            self.bash_trigger_row.set_visible(False)

        self.refresh_theme_list()

        return False

    def append_log(self, text):
        buffer = self.log_view.get_buffer()
        buffer.insert(buffer.get_end_iter(), text)

        # Auto-scroll to the bottom of the log
        adj = self.scrolled_window.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

        self.progress_bar.pulse()  # Makes the progress bar move
        return False

    def build_finished(self):
        self.progress_bar.set_fraction(1.0)
        self.show_toast("Theme Applied Successfully!")
        GLib.timeout_add(3000, self.auto_hide_logs)

    def auto_hide_logs(self):
        # Hide the terminal box and re-enable the build button
        self.log_container.set_visible(False)
        # self.build_button.set_sensitive(True) # Re-enable if you disabled it
        if hasattr(self, "active_build_button"):
            self.active_build_button.set_sensitive(True)

        # Optional: Show a final success toast
        self.show_toast("Build Complete!")

        return False  # CRITICAL: Tells GLib to only run this once

    def show_success_toast(self, theme_name, button):
        """UI update logic."""
        toast = Adw.Toast.new(f"Theme '{theme_name}' applied!")
        self.toast_overlay.add_toast(toast)
        button.set_sensitive(True)

    def show_error_dialog(self, message):
        """replacement for Adw.MessageDialog."""
        #  Create the AlertDialog
        dialog = Adw.AlertDialog.new("Error", message)

        # 'OK' button (response ID, label)
        dialog.add_response("ok", "OK")

        #    Set the default (accented) response
        dialog.set_default_response("ok")

        dialog.choose(self, None, lambda *args: None)

    ### }}}
    @staticmethod
    def on_window_close(window):
        import os
        import signal
        import subprocess

        print("Shutting down cleanly...")

        # Target the window object where we assigned the process group
        if hasattr(window, "current_process") and window.current_process:
            proc = window.current_process
            if proc.poll() is None:  # Process is actively running
                print("Terminating active shell script and all child processes...")
                try:
                    # Signals the group leader (the shell script) and kills all children at once
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)

                    try:
                        proc.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        print("Forcing group closure via SIGKILL...")
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                        proc.wait()  # Reaps the zombie process completely
                except Exception as e:
                    print(f"Error handling process group shutdown: {e}")

        app = window.get_application()
        if app is not None:
            print("closing application")
            app.quit()
        else:
            window.close()
        return False
