import gi
import os
import json
import sys
from colormydesktop.mockup import InteractiveMockup
from colormydesktop.advancedpref import AdvancedMixin
from colormydesktop.dialogs import DialogMixin
from colormydesktop.functions import ThemeManager
from colormydesktop.broker import broker
from gi.repository import Gtk, Adw, Gio, Gdk

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

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


# SECTION: DYNAMIC COLOR ENTRY ROW OBJECT {{{
@Gtk.Template(filename=f"{PYTHON_DIR}/color_row_item.ui")
class ColorEntryRow(Adw.EntryRow):
    __gtype_name__ = "ColorEntryRow"

    advanced_btn = Gtk.Template.Child()
    advanced_bg_box = Gtk.Template.Child()
    advanced_icon = Gtk.Template.Child()
    quick_btn = Gtk.Template.Child()
    quick_bg_box = Gtk.Template.Child()
    quick_icon = Gtk.Template.Child()
    status_label = Gtk.Template.Child()
    fix_btn = Gtk.Template.Child()
    magic_btn = Gtk.Template.Child()

    def __init__(
        self,
        main_page_context,
        label,
        default_hex,
        css_id,
        show_magic=True,
        manager_instance=None,
    ):
        super().__init__()
        self.home_page = main_page_context
        self.css_id = css_id
        self.set_title(label)
        self.set_text(default_hex)

        self.advanced_bg_box.set_name(f"{css_id}-preview")
        self.quick_bg_box.set_name(f"{css_id}-preview")
        self.advanced_icon.set_name(f"{css_id}-icon")
        self.quick_icon.set_name(f"{css_id}-icon")
        self.magic_btn.set_visible(show_magic)

        self.manager = manager_instance

        from colormydesktop.broker import ContextBroker

        # 1. Route text changes to the Broker
        self.connect_after(
            "changed",
            lambda entry: ContextBroker.translate_action(
                sender_id=self.home_page.__class__.__name__,
                action_type="CHANGED_TEXT_INPUT",
                payload={"entry_row": self, "css_id": css_id},
            ),
        )

        # 2. Route Advanced Picker Clicks to the Broker
        adv_gesture = Gtk.GestureClick.new()
        adv_gesture.connect(
            "pressed",
            lambda g, n, x, y: ContextBroker.translate_action(
                sender_id=self.home_page.__class__.__name__,
                action_type="CLICKED_ADVANCED_PICKER",
                payload={"gesture": g, "n_press": n, "x": x, "y": y, "entry_row": self},
            ),
        )
        self.advanced_btn.add_controller(adv_gesture)

        # 3. Route Quick Picker Clicks to the Broker
        quick_gesture = Gtk.GestureClick.new()
        quick_gesture.connect(
            "pressed",
            lambda g, n, x, y: ContextBroker.translate_action(
                sender_id=self.home_page.__class__.__name__,
                action_type="CLICKED_QUICK_PICKER",
                payload={"gesture": g, "n_press": n, "x": x, "y": y, "entry_row": self},
            ),
        )
        self.quick_btn.add_controller(quick_gesture)
        # Connect methods that are now safely declared in PageHomeView below
        # self.magic_btn.connect("clicked", self.home_page.on_generate_variants_clicked)
        # self.fix_btn.connect("clicked", self.home_page.on_fix_contrast_clicked)


# }}}


# SECTION: REQUIREMENTS PAGE {{{
@Gtk.Template(filename=f"{PYTHON_DIR}/requirements_checklist.ui")
class RequirementsPage(Gtk.Box):
    __gtype_name__ = "RequirementsPage"

    zen_manual_path = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # 1. Load the existing path on initialization
        saved_path = self.get_saved_zen_path()
        if saved_path:
            self.zen_manual_path.set_text(saved_path)

        # 2. Connect to text changes to save dynamically
        self.zen_manual_path.connect("notify::text", self._on_zen_path_changed)

    def _on_zen_path_changed(self, entry, *args):
        user_input = entry.get_text().strip()
        self.save_persistent_settings(manual_path=user_input)

    def get_saved_zen_path(self):
        config_path = os.path.expanduser(
            "~/.var/app/io.github.schwarzen.colormydesktop/config/color-my-desktop/settings.json"
        )
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                try:
                    data = json.load(f)
                    return data.get("zen_path", "")
                except json.JSONDecodeError:
                    return ""
        return ""

    def save_persistent_settings(self, manual_path):
        config_dir = os.path.expanduser(
            "~/.var/app/io.github.schwarzen.colormydesktop/config/color-my-desktop/"
        )
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "settings.json")

        # Preserve existing settings if any, only update zen_path
        data = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    pass

        data["zen_path"] = manual_path

        with open(config_path, "w") as f:
            json.dump(data, f, indent=4)


# --- 1. The Reusable Folder Section ---
@Gtk.Template(filename=f"{PYTHON_DIR}/folder_selection.ui")
class FolderSelectionBox(Gtk.Box):
    __gtype_name__ = "FolderSelectionBox"

    # Map all IDs from folder_section.blp
    vesktop_header = Gtk.Template.Child()
    vesktop_rows = Gtk.Template.Child()
    flatpak_path_label = Gtk.Template.Child()
    regular_path_label = Gtk.Template.Child()
    flatpak_copy_btn = Gtk.Template.Child()
    regular_copy_btn = Gtk.Template.Child()
    zen_header = Gtk.Template.Child()
    zen_rows = Gtk.Template.Child()
    zen_copy_btn = Gtk.Template.Child()
    zen_path_label = Gtk.Template.Child()
    standard_header = Gtk.Template.Child()
    standard_row = Gtk.Template.Child()
    standard_copy_btn = Gtk.Template.Child()
    path_entry = Gtk.Template.Child()
    warning_label = Gtk.Template.Child()
    select_btn = Gtk.Template.Child()
    selected_path_header = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


@Gtk.Template(filename=f"{PYTHON_DIR}/permission_dialog.ui")
class PermissionDialogPage(Gtk.Box):
    __gtype_name__ = "PermissionDialogPage"

    papirus_box = Gtk.Template.Child()
    instruction_label = Gtk.Template.Child()
    folders_box = Gtk.Template.Child()
    command_label = Gtk.Template.Child()
    requirements_label = Gtk.Template.Child()
    zen_warning_label = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.requirements_label.connect("activate-link", self._on_requirements_clicked)
        self.zen_warning_label.connect("activate-link", self._on_requirements_clicked)

    def _on_requirements_clicked(self, label, uri):
        from colormydesktop.broker import ContextBroker

        ContextBroker.translate_action(
            sender_id="PermissionDialogPage",
            action_type="OPEN_REQUIREMENTS_CLICKED",
            payload={
                "widget": self,  # Passes current widget for parent window detection/swapping
            },
        )
        return True

    def setup_dialog(self, title, folders, portal_data_map, broker_instance=None):
        """Dynamically populates the UI after the broker instantiates the page."""
        self.current_title = title
        self.current_folders = folders
        self.folder_rows = {}
        if broker_instance is not None:
            self.current_broker_instance = broker_instance

        from colormydesktop.lib_gui import FolderSelectionBox

        # 1. Handle Papirus specific visibility
        self.papirus_box.set_visible(title == "Papirus")

        # 2. Set instructional text
        if len(folders) == 1:
            msg = f"To save the {title} theme to <b>{folders[0]}</b>, you must grant limited portal access to the folder :"
        else:
            msg = f"To save {title} themes, you must grant limited portal access to the folders listed below :"
        self.instruction_label.set_label(msg)

        # 3. Clear existing rows if the instance is being recycled by the broker
        while child := self.folders_box.get_first_child():
            self.folders_box.remove(child)

        app_id = "io.github.schwarzen.colormydesktop"
        command_lines = []
        # 4. Generate the dynamic folder sections
        for i, folder in enumerate(folders):
            section = FolderSelectionBox()

            section.selected_path_header.set_label(f"<b>Selected Path {i + 1}:</b>")
            section.select_btn.set_label(f"Select Path {i + 1} Manually")

            # Toggle layout state based on the app
            if title == "Vesktop":
                section.vesktop_header.set_visible(True)
                section.vesktop_rows.set_visible(True)
                section.standard_header.set_visible(False)
                section.standard_row.set_visible(False)

                # 1. Define standard Vesktop config/theme directory paths
                flatpak_path = os.path.expanduser(
                    "~/.var/app/dev.vencord.Vesktop/config/vesktop/themes"
                )
                regular_path = os.path.expanduser("~/.config/vesktop/themes")

                # 2. Set label text
                section.flatpak_path_label.set_label(flatpak_path)
                section.regular_path_label.set_label(regular_path)

                # 3. Connect copy buttons to clipboard

                section.flatpak_copy_btn.connect(
                    "clicked",
                    lambda b, p=flatpak_path: broker.translate_action(
                        sender_id="flatpak_copy_btn",
                        action_type="COPY_PATH_CLICKED",
                        payload={"path": p},
                    ),
                )

                section.regular_copy_btn.connect(
                    "clicked",
                    lambda b, p=regular_path: (
                        Gdk.Display.get_default()
                        .get_clipboard()
                        .set_content(
                            Gdk.ContentProvider.new_for_value(os.path.expanduser(p))
                        )
                    ),
                )

            elif title == "Zen-browser":
                self.zen_warning_label.set_visible(True)
                self.requirements_label.set_visible(False)
                section.zen_header.set_visible(True)
                section.zen_rows.set_visible(True)
                section.standard_header.set_visible(False)
                section.standard_row.set_visible(False)

                # Retrieve the path saved from the Requirements page
                zen_path = broker_instance.manager.get_saved_zen_path()
                display_text = (
                    zen_path if zen_path else "No path configured. Check Requirements."
                )

                section.zen_path_label.set_label(display_text)

                # Hook up the copy button to the clipboard
                section.zen_copy_btn.connect(
                    "clicked", lambda b, p=display_text: b.get_clipboard().set_text(p)
                )

            else:
                section.standard_row.set_subtitle(folder)
                section.standard_copy_btn.connect(
                    "clicked",
                    lambda b, p=folder: (
                        Gdk.Display.get_default()
                        .get_clipboard()
                        .set_content(
                            Gdk.ContentProvider.new_for_value(os.path.expanduser(p))
                        )
                    ),
                )
                self.zen_warning_label.set_visible(False)
                self.requirements_label.set_visible(True)

            # Apply Persistence Logic evaluated by the broker
            existing_path = portal_data_map.get(folder)
            if existing_path:
                section.path_entry.set_text(existing_path)
                section.path_entry.add_css_class("success")

            self.folder_rows[folder] = section

            # Connect signal directly to your manager
            section.select_btn.connect(
                "clicked",
                lambda b, f=folder: broker_instance.manager.on_dialog_response(
                    None, "select", f
                ),
            )

            self.folders_box.append(section)

            # Add separator logic
            if len(folders) > 1 and i < len(folders) - 1:
                self.folders_box.append(Gtk.Separator())
            # Generate the command line for this specific folder
            expanded_folder = folder.replace("~", "$HOME")
            command_lines.append(
                f"flatpak override --user --filesystem={expanded_folder} {app_id}"
            )
        # Combine all commands using a newline character and update the label once outside the loop
        combined_command_text = "\n".join(command_lines)
        self.command_label.set_label(combined_command_text)


# }}}
# SECTION: GnomeSetupDialog {{{
@Gtk.Template(filename=f"{PYTHON_DIR}/gnome_setup_dialog.ui")
class GnomeSetupDialog(Gtk.Box):
    __gtype_name__ = "GnomeSetupDialog"

    # Bind elements we need to interact with dynamically
    status_expander = Gtk.Template.Child()
    host_path_label = Gtk.Template.Child()

    def __init__(self, parent_window=None, theme_manager=None, **kwargs):
        super().__init__(**kwargs)

        from colormydesktop.broker import ContextBroker

        self.manager = getattr(ContextBroker, "manager", None)

        # 1. Fallback for parent_window
        self.host_path = "~/.config/systemd/user"

        ContextBroker.register_page("gnome_setup_dialog", self)

        # 3. Safely execute status checks if manager exists
        self.run_status_check()

    def run_status_check(self):

        if self.manager and hasattr(self.manager, "get_safe_key"):
            safe_key = self.manager.get_safe_key(self.host_path)
        else:
            safe_key = None  # Or your default fallback value
            print("no safe key used")
        # Look for path in Memory -> then File Cache
        portal_path = getattr(self.manager, f"active_portal_{safe_key}", None)

        if not portal_path:
            portal_path = self.manager.load_cached_portal_path(self.host_path)
            if portal_path:
                setattr(self.manager, f"active_portal_{safe_key}", portal_path)

        # Accurate Status Checks
        has_access = portal_path is not None and os.path.exists(portal_path)
        path_exists = False
        service_exists = False

        if has_access:
            path_exists = os.path.isfile(
                os.path.join(portal_path, "gnome-refresher.path")
            )
            service_exists = os.path.isfile(
                os.path.join(portal_path, "gnome-refresher.service")
            )

        # Add dynamic rows to the expander
        display_path = portal_path if portal_path else "Folder Not Linked"
        self.status_expander.add_row(
            self.create_status_row(f"Portal Access: {display_path}", has_access)
        )
        self.status_expander.add_row(
            self.create_status_row("Systemd .path file found", path_exists)
        )
        self.status_expander.add_row(
            self.create_status_row("Systemd .service file found", service_exists)
        )

    def create_status_row(self, title, is_ready):
        """Helper to generate styled Adw.ActionRows for status"""
        row = Adw.ActionRow(title=title)
        icon_name = "emblem-ok-symbolic" if is_ready else "window-close-symbolic"
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.add_css_class("success" if is_ready else "error")
        row.add_prefix(icon)
        return row

    # --- UI Signal Handlers from Blueprint ---

    @Gtk.Template.Callback()
    def on_copy_path_clicked(self, *args):
        expanded_path = os.path.expanduser(self.host_path)
        Gdk.Display.get_default().get_clipboard().set_content(
            Gdk.ContentProvider.new_for_value(expanded_path)
        )
        self._show_toast("Path copied!")

    @Gtk.Template.Callback()
    def on_copy_cmd_clicked(self, *args):
        full_cmd = "systemctl --user daemon-reload && systemctl --user enable --now gnome-refresher.path"
        Gdk.Display.get_default().get_clipboard().set_content(
            Gdk.ContentProvider.new_for_value(full_cmd)
        )
        self._show_toast("Command copied!")

    @Gtk.Template.Callback()
    def on_installer_clicked(self, *args):
        # Trigger the installer function from your logic manager
        self.manager.install_gnome_host_refresher()

    def _show_toast(self, message):
        """Helper to show toast notifications via the main window's toast overlay"""
        # Assumes ThemeManager or parent_window has the toast_overlay bound
        if hasattr(self.manager, "toast_overlay"):
            self.manager.toast_overlay.add_toast(Adw.Toast.new(message))

    # }}}


# SECTION: KDESetupDialog {{{
@Gtk.Template(filename=f"{PYTHON_DIR}/kde_setup_dialog.ui")
class KDESetupDialog(Gtk.Box):
    __gtype_name__ = "KDESetupDialog"
    # Bind elements we need to interact with dynamically
    status_expander = Gtk.Template.Child()
    host_path_label = Gtk.Template.Child()

    def __init__(self, parent_window=None, theme_manager=None, **kwargs):
        super().__init__(**kwargs)

        from colormydesktop.broker import ContextBroker

        self.manager = getattr(ContextBroker, "manager", None)

        # 1. Fallback for parent_window
        self.host_path = "~/.config/systemd/user"

        ContextBroker.register_page("kde_setup_dialog", self)

        # 3. Safely execute status checks if manager exists
        self.run_status_check()

    def run_status_check(self):

        if self.manager and hasattr(self.manager, "get_safe_key"):
            safe_key = self.manager.get_safe_key(self.host_path)
        else:
            safe_key = None  # Or your default fallback value
            print("no safe key used")
        # Look for path in Memory -> then File Cache
        portal_path = getattr(self.manager, f"active_portal_{safe_key}", None)

        if not portal_path:
            portal_path = self.manager.load_cached_portal_path(self.host_path)
            if portal_path:
                setattr(self.manager, f"active_portal_{safe_key}", portal_path)

        # Accurate Status Checks
        has_access = portal_path is not None and os.path.exists(portal_path)
        path_exists = False
        service_exists = False

        if has_access:
            path_exists = os.path.isfile(
                os.path.join(portal_path, "kde-refresher.path")
            )
            service_exists = os.path.isfile(
                os.path.join(portal_path, "kde-refresher.service")
            )

        # Add dynamic rows to the expander
        display_path = portal_path if portal_path else "Folder Not Linked"
        self.status_expander.add_row(
            self.create_status_row(f"Portal Access: {display_path}", has_access)
        )
        self.status_expander.add_row(
            self.create_status_row("Systemd .path file found", path_exists)
        )
        self.status_expander.add_row(
            self.create_status_row("Systemd .service file found", service_exists)
        )

    def create_status_row(self, title, is_ready):
        """Helper to generate styled Adw.ActionRows for status"""
        row = Adw.ActionRow(title=title)
        icon_name = "emblem-ok-symbolic" if is_ready else "window-close-symbolic"
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.add_css_class("success" if is_ready else "error")
        row.add_prefix(icon)
        return row

    # --- UI Signal Handlers from Blueprint ---

    @Gtk.Template.Callback()
    def on_copy_path_clicked(self, *args):
        expanded_path = os.path.expanduser(self.host_path)
        Gdk.Display.get_default().get_clipboard().set_content(
            Gdk.ContentProvider.new_for_value(expanded_path)
        )
        self._show_toast("Path copied!")

    @Gtk.Template.Callback()
    def on_copy_cmd_clicked(self, *args):
        full_cmd = "systemctl --user daemon-reload && systemctl --user enable --now kde-refresher.path"
        Gdk.Display.get_default().get_clipboard().set_content(
            Gdk.ContentProvider.new_for_value(full_cmd)
        )
        self._show_toast("Command copied!")

    @Gtk.Template.Callback()
    def on_installer_clicked(self, *args):
        # Trigger the installer function from your logic manager
        self.manager.install_host_refresher()

    def _show_toast(self, message):
        """Helper to show toast notifications via the main window's toast overlay"""
        # Assumes ThemeManager or parent_window has the toast_overlay bound
        if hasattr(self.manager, "toast_overlay"):
            self.manager.toast_overlay.add_toast(Adw.Toast.new(message))


# }}}


# SECTION: PERMISSION SETTINGS {{{
@Gtk.Template(filename=f"{PYTHON_DIR}/permission_settings.ui")
class PermissionSettings(Gtk.Box):
    __gtype_name__ = "PermissionSettings"
    portal_cmd_label = Gtk.Template.Child()
    portal_copy_btn = Gtk.Template.Child()
    direct_cmd_label = Gtk.Template.Child()
    direct_copy_btn = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.portal_copy_btn.connect(
            "clicked",
            lambda b: b.get_clipboard().set_text(self.portal_cmd_label.get_label()),
        )
        self.direct_copy_btn.connect(
            "clicked",
            lambda b: b.get_clipboard().set_text(self.direct_cmd_label.get_label()),
        )


# }}}
# SECTION: NAUTILUS OPTIONS {{{
@Gtk.Template(filename=f"{PYTHON_DIR}/nautilus_options.ui")
class NautilusOptions(Gtk.Box):
    __gtype_name__ = "NautilusOptions"
    nautilus_primary_row = Gtk.Template.Child()
    nautilus_secondary_row = Gtk.Template.Child()
    nautilus_toggle = Gtk.Template.Child()
    nautilus_second_toggle = Gtk.Template.Child()
    from colormydesktop.functions import ThemeManager

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color_entries = {}
        self.status_labels = {}
        self.status_buttons = {}
        self.current_colors = {}
        self.home_page = self
        from colormydesktop.broker import ContextBroker

        # Synchronize toggle states dynamically from your UI switches on startup
        advanced_nautilus_configurations = [
            {
                "label": "Nautilus Primary Color",
                "hex": "#246cc5",
                "id": "nautilusprimarycolor",
            },
            {
                "label": "Nautilus Secondary Color",
                "hex": "#241f31",
                "id": "nautilussecondarycolor",
            },
        ]

        for config in advanced_nautilus_configurations:
            entry_row = ColorEntryRow(
                main_page_context=self,
                label=config["label"],
                default_hex=config["hex"],
                css_id=config["id"],
            )
            self.color_entries[config["id"]] = entry_row
            self.status_labels[config["id"]] = entry_row.status_label
            self.current_colors[config["id"]] = config["hex"]

            if config["id"] == "nautilusprimarycolor":
                self.nautilus_primary_row.add(entry_row)
            elif config["id"] == "nautilussecondarycolor":
                self.nautilus_secondary_row.add(entry_row)

            if ContextBroker.manager:
                ContextBroker.manager.update_preview(entry_row, config["id"])

        # Connect your toggle switch signals
        self.switches = {
            "nautilusprimarycolor": self.nautilus_toggle,
            "nautilussecondarycolor": self.nautilus_second_toggle,
        }

        for css_id, switch_widget in self.switches.items():
            switch_widget.connect(
                "notify::active",
                lambda sw, pspec, cid=css_id: ContextBroker.translate_action(
                    sender_id="NautilusOptions",
                    action_type="TOGGLED_FEATURE_SWITCH",
                    payload={
                        "css_id": cid,
                        "is_active": sw.get_active(),
                        "widget": sw,
                        "page": self,  # <-- Pass the GnomeOptions instance as 'self'
                    },
                ),
            )

    @property
    def manager(self):
        """
        Dynamically climbs the widget tree to find the live root window
        and extracts the active ThemeManager instance.
        """
        root_window = self.get_root()
        if root_window and hasattr(root_window, "logic"):
            return root_window.logic

        # Fallback trace: check if your main application layer holds it under self.manager
        if root_window and hasattr(root_window, "manager"):
            return root_window.manager

        print("[MOCKUP ERROR] Could not locate an active ThemeManager instance.")
        return None


#             }}}


# SECTION: KDE OPTIONS {{{
@Gtk.Template(filename=f"{PYTHON_DIR}/kde_options.ui")
class KDEOptions(Gtk.Box):
    __gtype_name__ = "KDEOptions"
    kde_refresh_row = Gtk.Template.Child()
    kde_refresh_switch = Gtk.Template.Child()
    kde_refresh_btn = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.environment_status()
        self.switches = {
            "kde_refresh_switch": self.kde_refresh_switch,
        }

        from colormydesktop.broker import ContextBroker

        ContextBroker.register_page("kde_options", self)

        for css_id, switch_widget in self.switches.items():
            switch_widget.connect(
                "notify::active",
                lambda sw, pspec, cid=css_id: ContextBroker.translate_action(
                    sender_id="KDEOptions",
                    action_type="TOGGLED_FEATURE_SWITCH",
                    payload={
                        "css_id": cid,
                        "is_active": sw.get_active(),
                        "widget": sw,
                        "page": self,  # <-- Pass the KDEOptions instance as 'self'
                    },
                ),
            )
        self.kde_refresh_btn.connect("clicked", self.on_kde_refresh_btn_clicked)

    def on_kde_refresh_btn_clicked(self, button):
        print("[UI] Setup button clicked. Transitioning via ContextBroker...")

        from colormydesktop.broker import ContextBroker
        from colormydesktop.lib_gui import KDESetupDialog

        ContextBroker.navigate(
            current_widget=self,
            target_page_class=KDESetupDialog,
            page_id="kde_setup_dialog",
        )

    def environment_status(self):
        from colormydesktop.broker import ContextBroker

        is_flatpak = os.path.exists("/.flatpak-info")

        if not is_flatpak:
            ready = True
        else:
            theme_manager = getattr(ContextBroker, "manager", None)
            if theme_manager and hasattr(theme_manager, "is_plasma_refresh_ready"):
                # Call using the actual ThemeManager instance as 'self'
                ready = theme_manager.is_plasma_refresh_ready()
            else:
                ready = False

            # Check dictionary storage or direct template child attribute
        if hasattr(self, "switches") and "kde_refresh_switch" in self.switches:
            self.switches["kde_refresh_switch"].set_active(ready)
        elif hasattr(self, "kde_refresh_switch") and self.kde_refresh_switch:
            self.kde_refresh_switch.set_active(ready)


# }}}


# SECTION: GNOME OPTIONS {{{
@Gtk.Template(filename=f"{PYTHON_DIR}/gnome_options.ui")
class GnomeOptions(Gtk.Box):
    __gtype_name__ = "GnomeOptions"
    topbar_color_row = Gtk.Template.Child()
    datemenu_color_row = Gtk.Template.Child()
    clock_color_row = Gtk.Template.Child()
    topbar_toggle = Gtk.Template.Child()
    datemenu_toggle = Gtk.Template.Child()
    clock_toggle = Gtk.Template.Child()
    refresh_row = Gtk.Template.Child()
    refresh_switch = Gtk.Template.Child()
    refresh_btn = Gtk.Template.Child()
    from colormydesktop.functions import ThemeManager

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.environment_status()
        self.color_entries = {}
        self.status_labels = {}
        self.status_buttons = {}
        self.current_colors = {}
        self.home_page = self
        from colormydesktop.broker import ContextBroker

        # Synchronize toggle states dynamically from your UI switches on startup
        advanced_gnome_configurations = [
            {
                "label": "TopBar Color",
                "hex": "#246cc5",
                "id": "topbarcolor",
            },
            {
                "label": "Datemenu Color",
                "hex": "#246cc5",
                "id": "datemenucolor",
            },
            {
                "label": "Clock Color",
                "hex": "#f9f9f9",
                "id": "clockcolor",
            },
        ]

        for config in advanced_gnome_configurations:
            entry_row = ColorEntryRow(
                main_page_context=self,
                label=config["label"],
                default_hex=config["hex"],
                css_id=config["id"],
            )
            self.color_entries[config["id"]] = entry_row
            self.status_labels[config["id"]] = entry_row.status_label
            self.current_colors[config["id"]] = config["hex"]

            if config["id"] == "topbarcolor":
                self.topbar_color_row.add(entry_row)
            elif config["id"] == "datemenucolor":
                self.datemenu_color_row.add(entry_row)
            elif config["id"] == "clockcolor":
                self.clock_color_row.add(entry_row)

            if ContextBroker.manager:
                ContextBroker.manager.update_preview(entry_row, config["id"])

        # Connect your toggle switch signals
        self.switches = {
            "topbarcolor": self.topbar_toggle,
            "datemenucolor": self.datemenu_toggle,
            "clockcolor": self.clock_toggle,
            "refresh_switch": self.refresh_switch,
        }

        for css_id, switch_widget in self.switches.items():
            switch_widget.connect(
                "notify::active",
                lambda sw, pspec, cid=css_id: ContextBroker.translate_action(
                    sender_id="GnomeOptions",
                    action_type="TOGGLED_FEATURE_SWITCH",
                    payload={
                        "css_id": cid,
                        "is_active": sw.get_active(),
                        "widget": sw,
                        "page": self,  # <-- Pass the GnomeOptions instance as 'self'
                    },
                ),
            )
        self.refresh_btn.connect("clicked", self.on_gnome_refresh_btn_clicked)

    def on_gnome_refresh_btn_clicked(self, button):
        print("[UI] Setup button clicked. Transitioning via ContextBroker...")

        from colormydesktop.broker import ContextBroker
        from colormydesktop.lib_gui import GnomeSetupDialog

        ContextBroker.navigate(
            current_widget=self,
            target_page_class=GnomeSetupDialog,
            page_id="gnome_setup_dialog",
        )

    def environment_status(self):
        from colormydesktop.broker import ContextBroker

        is_flatpak = os.path.exists("/.flatpak-info")

        if not is_flatpak:
            ready = True
        else:
            theme_manager = getattr(ContextBroker, "manager", None)
            if theme_manager and hasattr(theme_manager, "is_gnome_refresh_ready"):
                # Call using the actual ThemeManager instance as 'self'
                ready = theme_manager.is_gnome_refresh_ready()
            else:
                ready = False

            # Check dictionary storage or direct template child attribute
        if hasattr(self, "switches") and "refresh_switch" in self.switches:
            self.switches["refresh_switch"].set_active(ready)
        elif hasattr(self, "refresh_switch") and self.refresh_switch:
            self.refresh_switch.set_active(ready)

    @property
    def manager(self):
        """
        Dynamically climbs the widget tree to find the live root window
        and extracts the active ThemeManager instance.
        """
        root_window = self.get_root()
        if root_window and hasattr(root_window, "logic"):
            return root_window.logic

        # Fallback trace: check if your main application layer holds it under self.manager
        if root_window and hasattr(root_window, "manager"):
            return root_window.manager

        print("[MOCKUP ERROR] Could not locate an active ThemeManager instance.")
        return None


#             }}}
# SECTION: ADVANCED PAGE {{{
@Gtk.Template(filename=f"{PYTHON_DIR}/advanced_page.ui")
class AdvancedPage(Gtk.Box):
    __gtype_name__ = "AdvancedPage"

    gnome_options = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from colormydesktop.broker import ContextBroker

        ContextBroker.register_page("advanced_options", self)

    @Gtk.Template.Callback()
    def on_gnome_card_pressed(self, gesture, n_press, x, y):
        from colormydesktop.lib_gui import GnomeOptions
        from colormydesktop.broker import ContextBroker

        # Explicit, readable, and highly maintainable:
        # Pass 'self' (the AdvancedPage), the class blueprint, and your string identifier key.
        ContextBroker.navigate(
            current_widget=self, target_page_class=GnomeOptions, page_id="gnome_options"
        )

    @Gtk.Template.Callback()
    def on_permissions_card_pressed(self, gesture, n_press, x, y):
        from colormydesktop.lib_gui import PermissionSettings
        from colormydesktop.broker import ContextBroker

        # Pass 'self' (the AdvancedPage), the class blueprint, and your string identifier key.
        ContextBroker.navigate(
            current_widget=self,
            target_page_class=PermissionSettings,
            page_id="permissions_options",
        )

    @Gtk.Template.Callback()
    def on_kde_card_pressed(self, gesture, n_press, x, y):
        from colormydesktop.lib_gui import KDEOptions
        from colormydesktop.broker import ContextBroker

        # Pass 'self' (the AdvancedPage), the class blueprint, and your string identifier key.
        ContextBroker.navigate(
            current_widget=self,
            target_page_class=KDEOptions,
            page_id="kde_options",
        )

    @Gtk.Template.Callback()
    def on_nautilus_card_pressed(self, gesture, n_press, x, y):
        from colormydesktop.lib_gui import NautilusOptions
        from colormydesktop.broker import ContextBroker

        # Pass 'self' (the AdvancedPage), the class blueprint, and your string identifier key.
        ContextBroker.navigate(
            current_widget=self,
            target_page_class=NautilusOptions,
            page_id="nautilus_options",
        )


# }}}
# SECTION: HOME PAGE {{{
@Gtk.Template(filename=f"{PYTHON_DIR}/page_home.ui")
class PageHomeView(Adw.NavigationPage):
    __gtype_name__ = "PageHomeView"

    color_rows_group = Gtk.Template.Child()
    mockup_wrapper = Gtk.Template.Child()
    preview_holder = Gtk.Template.Child()
    show_mockup_switch = Gtk.Template.Child()
    combo_row = Gtk.Template.Child()
    name_row = Gtk.Template.Child()
    advanced_options_action_btn = Gtk.Template.Child()
    delete_profile_btn = Gtk.Template.Child()
    build_btn = Gtk.Template.Child()
    # MAIN ROWS
    gnome_row = Gtk.Template.Child()
    plasma_row = Gtk.Template.Child()
    gtk4_row = Gtk.Template.Child()
    papirus_row = Gtk.Template.Child()
    zen_row = Gtk.Template.Child()
    youtube_row = Gtk.Template.Child()
    vesktop_row = Gtk.Template.Child()
    # MAIN SWITCHES
    gnome_switch = Gtk.Template.Child()
    plasma_switch = Gtk.Template.Child()
    gtk4_switch = Gtk.Template.Child()
    papirus_switch = Gtk.Template.Child()
    zen_switch = Gtk.Template.Child()
    youtube_switch = Gtk.Template.Child()
    vesktop_switch = Gtk.Template.Child()
    # MAIN BUTTONS
    gnome_folder_btn = Gtk.Template.Child()
    plasma_folder_btn = Gtk.Template.Child()
    gtk4_folder_btn = Gtk.Template.Child()
    papirus_folder_btn = Gtk.Template.Child()
    zen_folder_btn = Gtk.Template.Child()
    ytb_folder_btn = Gtk.Template.Child()
    vesktop_folder_btn = Gtk.Template.Child()

    def __init__(self, themes_list_data=None, css_provider=None, **kwargs):
        # FIX A: Extract custom parameters before initializing the underlying GObject
        super().__init__(**kwargs)
        self.css_provider = css_provider
        # Attach the provider to the entire screen layout engine display pool.
        # This guarantees that ANY widget nested inside this page can read your dynamic CSS rules!
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # 1. Instantiate interactive view
        self.interactive_preview = InteractiveMockup()
        self.interactive_preview.set_hexpand(True)
        self.interactive_preview.set_vexpand(True)

        # 2. Inject it directly into the empty placeholder slot
        self.preview_holder.append(self.interactive_preview)

        # 2. CONNECT THE RESPONSIVE TOGGLE EVENT
        # When clicked on small viewports, it hides/reveals column B below column A
        self.show_mockup_switch.connect("notify::active", self.on_mockup_toggle_changed)

        self.themes = themes_list_data or []
        self.color_entries = {}
        self.status_labels = {}
        self.status_buttons = {}
        self.current_colors = {}

        color_configurations = [
            {
                "label": "Primary Color",
                "hex": "#e1251b",
                "id": "primary",
                "magic": False,
            },
            {
                "label": "Secondary",
                "hex": "#5e6c7d",
                "id": "secondary",
                "magic": False,
            },
            {
                "label": "Accent",
                "hex": "#f4f5f7",
                "id": "accent",
                "magic": False,
            },
            {
                "label": "Text",
                "hex": "#e1251b",
                "id": "text",
                "magic": True,
            },
        ]

        for config in color_configurations:
            color_row = ColorEntryRow(
                main_page_context=self,
                label=config["label"],
                default_hex=config["hex"],
                css_id=config["id"],
                show_magic=config["magic"],
            )

            self.color_entries[config["id"]] = color_row
            self.status_labels[config["id"]] = color_row.status_label
            self.status_buttons[config["id"]] = color_row.fix_btn
            self.current_colors[config["id"]] = config["hex"]

            self.color_rows_group.add(color_row)
        from colormydesktop.broker import ContextBroker

        self.manager = ContextBroker.manager

        for css_id, color_row in self.color_entries.items():
            color_row.manager = self.manager
            self.manager.update_preview(color_row, css_id)
            # Seed our central ContextBroker's current_colors map on startup
            self.current_colors[css_id] = color_row.get_text().strip()
        # Fire a simulated text input change event straight through the broker matrix
        ContextBroker.translate_action(
            sender_id="PageHomeView",
            action_type="CHANGED_TEXT_INPUT",
            payload={
                "entry_row": list(self.color_entries.values())[0],
                "css_id": "primary",
            },
        )
        ContextBroker.translate_action(
            sender_id="PageHomeView",
            action_type="BUILD_BUTTON_CLICKED",
            payload={},
        )
        gnome_opts = ContextBroker.gnome_options_singleton
        # 2. Extract the active boolean state
        is_active = False
        if gnome_opts:
            # If stored in your self.switches dictionary:
            if (
                hasattr(gnome_opts, "switches")
                and "refresh_switch" in gnome_opts.switches
            ):
                is_active = gnome_opts.switches["refresh_switch"].get_active()

            # Or if bound directly as a Template.Child:
            elif hasattr(gnome_opts, "refresh_switch"):
                is_active = gnome_opts.refresh_switch.get_active()
        self.manager.initial_status(self, is_active)

        # 1. Define the mapping for your feature switches
        self.feature_switches = {
            self.gnome_switch: {
                "feature_name": "GNOME",
                "folders": [
                    "~/.local/share/themes",
                ],
            },
            self.plasma_switch: {
                "feature_name": "KDEPlasma",
                "folders": [
                    "~/.local/share/plasma",
                    "~/.local/share/color-schemes",
                ],
            },
            self.gtk4_switch: {
                "feature_name": "GTK4",
                "folders": [
                    "~/.config/gtk-4.0",
                ],
            },
            self.papirus_switch: {
                "feature_name": "Papirus",
                "folders": [
                    "~/.local/share/icons",
                ],
            },
            self.zen_switch: {
                "feature_name": "Zen-browser",
                "folders": [
                    "~/.zen/*/chrome",
                ],
            },
            self.youtube_switch: {
                "feature_name": "Zen-browser",
                "folders": [
                    "~/.zen/*/chrome",
                ],
            },
            self.vesktop_switch: {
                "feature_name": "Vesktop",
                "folders": [
                    "~/.config/vesktop/themes",
                ],
            },
            # Add others here (e.g., gtk4_switch, vesktop_switch)
        }

        # 2. Iterate and dynamically connect the state-change signal
        for switch_widget, app_data in self.feature_switches.items():
            switch_widget.connect(
                "notify::active",
                # Catch the widget and param, but bind the specific dictionary to 'data'
                lambda widget, param, data=app_data: self._on_switch_toggled(
                    widget, data
                ),
            )

        # 1. Map the BUTTONS (not the switches) to the payloads
        self.app_permission_buttons = {
            self.gnome_folder_btn: {
                "title": "GNOME",
                "folders": [
                    "~/.local/share/themes",
                ],
            },
            self.plasma_folder_btn: {
                "title": "KDEPlasma",
                "folders": [
                    "~/.local/share/plasma",
                    "~/.local/share/color-schemes",
                ],
            },
            self.gtk4_folder_btn: {
                "title": "GTK4",
                "folders": [
                    "~/.config/gtk-4.0",
                ],
            },
            self.papirus_folder_btn: {
                "title": "Papirus",
                "folders": [
                    "~/.local/share/icons",
                ],
            },
            self.zen_folder_btn: {
                "title": "Zen-browser",
                "folders": [
                    "~/.zen/*/chrome",
                ],
            },
            self.ytb_folder_btn: {
                "title": "Zen-browser",
                "folders": [
                    "~/.zen/*/chrome",
                ],
            },
            self.vesktop_folder_btn: {
                "title": "Vesktop",
                "folders": [
                    "~/.config/vesktop/themes",
                ],
            },
            # Add others here
        }

        # 2. Iterate and dynamically connect the clicked signal
        for btn_widget, app_data in self.app_permission_buttons.items():
            btn_widget.connect(
                "clicked", lambda btn, data=app_data: self._on_folder_btn_clicked(data)
            )

        self.delete_profile_btn.connect(
            "clicked", lambda btn: self.manager.on_delete_clicked()
        )

    def _on_switch_toggled(self, widget, data):
        from colormydesktop.broker import ContextBroker

        ContextBroker.translate_action(
            sender_id="PageHomeView",
            action_type="SWITCH_TOGGLED",
            payload={
                "widget": widget,  # Passes the switch itself to check get_active() or set_active(False)
                "folders": data["folders"],
                "feature_name": data["feature_name"],
                "parent_widget": self,  # Passes the home view container in case navigation needs it
            },
        )

    def _on_folder_btn_clicked(self, data):

        from colormydesktop.broker import ContextBroker

        ContextBroker.translate_action(
            sender_id="PageHomeView",
            action_type="SWITCH_FOLDER_CLICKED",
            payload={
                "title": data["title"],
                "folders": data["folders"],
                "widget": self,  # The container for the Universal Routing Engine
            },
        )

    def on_mockup_toggle_changed(self, switch_row, pspec):
        """
        Manually syncs the visible state of your layout panel whenever the
        user updates the mobile/narrow viewport switch row.
        """
        is_checked = switch_row.get_active()
        self.mockup_wrapper.set_visible(is_checked)
        print(
            f"[ADAPTIVE LOGIC] Mockup visibility overridden manually to: {is_checked}"
        )

    # FIX B: Added real fallback methods to ensure the ColorEntryRow setup doesn't crash on init

    def on_generate_variants_clicked(self, button):
        pass

    def on_fix_contrast_clicked(self, button):
        pass

    def on_advanced_picker_clicked(self, gesture, n_press, x, y, target_entry):
        pass

    def on_quick_picker_clicked(self, gesture, n_press, x, y, target_entry):
        pass


# }}}
# SECTION: MAIN WINDOW {{{
@Gtk.Template(filename=f"{PYTHON_DIR}/main_window.ui")
class MyMainWindow(Adw.ApplicationWindow):
    __gtype_name__ = "MyMainWindow"

    nav_view = Gtk.Template.Child()
    close_btn = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        main_window = self
        from colormydesktop.broker import ContextBroker

        self.close_btn.connect(
            "clicked", lambda _: ContextBroker.manager.on_window_close(main_window)
        )


# }}}
