#!/usr/bin/env python3
# Copyright 2026 Schwarzen
# SPDX-License-Identifier: Apache-2.0

from gi.repository import Gtk, Adw, Gdk, Gio, GLib, GObject
import glob
import os
import re
import json
import shutil
import hashlib

class DialogMixin:

    def is_running_in_flatpak(self):
        #  Check for the physical metadata file 
        if os.path.exists('/.flatpak-info'):
            return True
        
        # Check the 'container' env var (Commonly set by Flatpak/Podman)
        if os.environ.get('container') == 'flatpak':
            return True
        
        # Check for FLATPAK_ID but double-check it's not a leaked value
        # If FLATPAK_ID exists but /app does not, it's likely a leaked variable
        if os.environ.get('FLATPAK_ID') and os.path.exists('/app'):
            return True
            
        return False


    def setup_user_data(self):
        bundled_scss = "/app/share/color-my-desktop/scss"
        bundled_palettes = "/app/share/color-my-desktop/palettes"
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
                        shutil.copy2(os.path.join(root, file), os.path.join(dest_path, file))
                print(f"Synced SCSS to: {user_scss_dir}")
            except Exception as e:
                print(f"Error updating SCSS: {e}")
                   

        if os.path.exists(bundled_palettes):
            os.makedirs(user_scss_dir, exist_ok=True)
            try:
                for file in os.listdir(bundled_palettes):
                    src_file = os.path.join(bundled_palettes, file)
                    dest_file = os.path.join(user_scss_dir, file) # Placed in root
                    
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
        portal_path = getattr(self, f"active_portal_{self.get_safe_key(host_path)}", None)
        if not portal_path:
            portal_path = self.load_cached_portal_path(host_path)
        
        if not portal_path or not os.path.exists(portal_path):
            return False

        #  Check for the two refresher files
        path_exists = os.path.isfile(os.path.join(portal_path, "gnome-refresher.path"))
        service_exists = os.path.isfile(os.path.join(portal_path, "gnome-refresher.service"))
        if not (path_exists and service_exists):
            return False
            
        return True
        
    # GNOME REFRESH DIALOG
    def show_gnome_setup_dialog(self, button=None):
        # --- Close existing dialog if it's already open ---
        if hasattr(self, 'gnome_dialog') and self.gnome_dialog:
            self.gnome_dialog.destroy()
            self.gnome_dialog = None

        app_id = self.get_application().get_application_id()
        self.gnome_dialog = Adw.MessageDialog(transient_for=self, heading="GNOME Shell Refresh Setup")
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # --- STATUS LOGIC ---
        host_path = "~/.config/systemd/user"
        
        # Look for path in Memory -> then File Cache
        portal_path = getattr(self, f"active_portal_{self.get_safe_key(host_path)}", None)
        if not portal_path:
            portal_path = self.load_cached_portal_path(host_path)
            if portal_path:
                setattr(self, f"active_portal_{self.get_safe_key(host_path)}", portal_path)

        # Accurate Status Checks
        has_access = portal_path is not None and os.path.exists(portal_path)
        path_exists = False
        service_exists = False
        if has_access:
            path_exists = os.path.isfile(os.path.join(portal_path, "gnome-refresher.path"))
            service_exists = os.path.isfile(os.path.join(portal_path, "gnome-refresher.service"))

        # --- STATUS EXPANDER ---
        status_expander = Adw.ExpanderRow(title="System Status Check", subtitle="Expand to see setup details")
        status_expander.add_css_class("card")
        
        def create_status_row(title, is_ready):
            row = Adw.ActionRow(title=title)
            icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic" if is_ready else "window-close-symbolic")
            icon.add_css_class("success" if is_ready else "error")
            row.add_prefix(icon)
            return row

        display_path = portal_path if portal_path else "Folder Not Linked"
        status_expander.add_row(create_status_row(f"Portal Access: {display_path}", has_access))
        status_expander.add_row(create_status_row("Systemd .path file found", path_exists))
        status_expander.add_row(create_status_row("Systemd .service file found", service_exists))
        main_box.append(status_expander)

        # --- INSTRUCTIONS ---
        instruction_text = (
            "<b>To setup auto refresh:</b>\n"
            "• Copy the path below\n"
            "• Click the <b>Automated Installer</b> button\n"
            "• Paste the path into the folder selection dialog"
        )
        main_box.append(Gtk.Label(label=instruction_text, use_markup=True, xalign=0, wrap=True))

        # --- PATH COPY SECTION ---
        path_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        path_box.add_css_class("card")
        path_box.set_margin_start(12)
        
        path_display = Gtk.Label(label=host_path, xalign=0, hexpand=True, selectable=True)
        path_display.add_css_class("dim-label")
        
        copy_path_btn = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
        copy_path_btn.add_css_class("flat")
        copy_path_btn.set_tooltip_text("Copy path to clipboard")
        copy_path_btn.connect("clicked", lambda b: Gdk.Display.get_default().get_clipboard().set_content(
            # Use os.path.expanduser here to turn ~ into /home/User
            Gdk.ContentProvider.new_for_value(os.path.expanduser(host_path))
        ))
        copy_path_btn.connect("clicked", lambda b: self.toast_overlay.add_toast(Adw.Toast.new("Path copied!")))

        path_box.append(path_display)
        path_box.append(copy_path_btn)
        main_box.append(path_box)

        # --- ACTION BUTTONS ---
        setup_btn = Gtk.Button(label="Run Automated Installer")
        setup_btn.add_css_class("suggested-action")
        # Link to the function we wrote earlier for GNOME
        setup_btn.connect("clicked", lambda b: self.install_gnome_host_refresher())
        main_box.append(setup_btn)
                # WARNING EXPANDER
        warning_expander = Adw.ExpanderRow(title="WARNING", subtitle="Security information")
        warning_expander.add_css_class("card")
        
        warning_text = (
           
            "<span size='large' weight='bold'>Security &amp; Background Service</span>\n\n"
            "This setup installs a <b>systemd user unit</b> on your host system. "
            "This is a secure way to allow the sandbox to request a theme refresh "
            "without giving the app full control over your computer.\n\n"
            "<b>How it works:</b>\n"
            "• The app 'touches' a trigger file inside its sandbox.\n"
            "• Your host system detects this change and runs the refresh command.\n"
            "• You can inspect the exact command inside <b>gnome-refresher.service</b>.\n\n"
            "<span color='#999999' size='small'>Use with caution: This allows code execution "
            "on the host triggered by the sandbox.</span>"
        )

        warning_label = Gtk.Label(label=warning_text, use_markup=True, xalign=0, wrap=True)
        warning_label.set_margin_bottom(12)

        warning_expander.add_row(warning_label) # Add the widget you already created
        main_box.append(warning_expander)

        # --- COMMAND SECTION ---
        cmd_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        cmd_box.append(Gtk.Label(label="<b>Then run this command and restart the app</b>", use_markup=True, xalign=0))
        
        full_cmd = "systemctl --user daemon-reload && systemctl --user enable --now gnome-refresher.path"
        
        entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        cmd_label = Gtk.Label(label=full_cmd, selectable=True, wrap=True, hexpand=True, xalign=0)
        cmd_label.add_css_class("card")
        
        copy_cmd_btn = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
        copy_cmd_btn.add_css_class("flat")
        copy_cmd_btn.connect("clicked", lambda b: Gdk.Display.get_default().get_clipboard().set_content(
            Gdk.ContentProvider.new_for_value(full_cmd)
        ))
        copy_cmd_btn.connect("clicked", lambda b: self.toast_overlay.add_toast(Adw.Toast.new("Command copied!")))

        entry_box.append(cmd_label)
        entry_box.append(copy_cmd_btn)
        cmd_box.append(entry_box)
        main_box.append(cmd_box)

        # --- DIALOG FINALIZATION ---
        self.gnome_dialog.connect("destroy", self._on_gnome_dialog_destroyed)
        self.gnome_dialog.set_extra_child(main_box)
        self.gnome_dialog.add_response("close", "Close")
        self.gnome_dialog.present()

    def _on_gnome_dialog_destroyed(self, dialog):
        self.gnome_dialog = None
        # Refresh the UI switch state when user closes dialog
        self.check_gnome_refresh_status()
        self.initial_status()



        
    # PLAMSA REFRESH SETUP WINDOW
    def show_plasma_setup_dialog(self, button=None):
     # ---  Close existing dialog if it's already open ---
        if hasattr(self, 'plasma_dialog') and self.plasma_dialog:
            self.plasma_dialog.destroy()
            self.plasma_dialog = None

        app_id = self.get_application().get_application_id()
        # Store the reference on self
        self.plasma_dialog = Adw.MessageDialog(transient_for=self, heading="KDE Plasma Refresh Setup")
        
        app_id = self.get_application().get_application_id()
        dialog = Adw.MessageDialog(transient_for=self, heading="KDE Plasma Refresh Setup")
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # ---STATUS LOGIC ---
        host_path = "~/.config/systemd/user"
        
        # Look for path in Memory -> then File Cache
        portal_path = getattr(self, f"active_portal_{self.get_safe_key(host_path)}", None)
        if not portal_path:
            portal_path = self.load_cached_portal_path(host_path)
            if portal_path:
                setattr(self, f"active_portal_{self.get_safe_key(host_path)}", portal_path)

        # Accurate Status Checks
        has_access = portal_path is not None and os.path.exists(portal_path)
        
        path_exists = False
        service_exists = False
        if has_access:
            path_exists = os.path.isfile(os.path.join(portal_path, "plasma-refresher.path"))
            service_exists = os.path.isfile(os.path.join(portal_path, "plasma-refresher.service"))

        runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "")
        trigger_file = os.path.join(runtime_dir, "plasma-refresher.trigger")
        # Ensure it's a real file and not just a ghost directory
        has_trigger = os.path.isfile(trigger_file)

        # --- STATUS EXPANDER ---
        status_expander = Adw.ExpanderRow(title="System Status Check", subtitle="Expand to see setup details")
        status_expander.add_css_class("card")
        
        def create_status_row(title, is_ready):
            row = Adw.ActionRow(title=title)
            icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic" if is_ready else "window-close-symbolic")
            icon.add_css_class("success" if is_ready else "error")
            row.add_prefix(icon)
            return row

        display_path = portal_path if portal_path else "Folder Not Linked"
        status_expander.add_row(create_status_row(f"Portal Access: {display_path}", has_access))
        status_expander.add_row(create_status_row("Systemd .path file found", path_exists))
        status_expander.add_row(create_status_row("Systemd .service file found", service_exists))
        main_box.append(status_expander)
                # --- IMPORTANT: Clear the reference when the dialog is closed/destroyed ---
        self.plasma_dialog.connect("destroy", self._on_plasma_dialog_destroyed)
        
        self.plasma_dialog.set_extra_child(main_box)
        self.plasma_dialog.add_response("close", "Close")

        self.plasma_dialog.present()

        # ---  THE SETUP COMMANDS ---
        cmd_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        cmd_box.append(Gtk.Label(label="<b>Required Setup Command:</b>", use_markup=True, xalign=0))
        
        full_cmd = (
            f"flatpak override --user --filesystem=xdg-run/plasma-refresher.trigger:create {app_id} && "
            "systemctl --user daemon-reload && "
            "systemctl --user enable --now plasma-refresher.path"
        )
        
        entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        cmd_label = Gtk.Label(label=full_cmd, selectable=True, wrap=True, hexpand=True, xalign=0)
        cmd_label.add_css_class("card")
        
        copy_btn = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
        copy_btn.add_css_class("flat")
        copy_btn.connect("clicked", lambda b: Gdk.Display.get_default().get_clipboard().set_content(
            Gdk.ContentProvider.new_for_value(full_cmd)
        ))
        #  Instruction Label (Updated with Newlines)
        instruction_text = (
            "<b>To setup auto refresh:</b>\n"
            "• Copy the path below\n"
            "• Click the <b>Automated Installer</b> button\n"
            "• Paste the path into the folder selection dialog"
        )
        main_box.append(Gtk.Label(label=instruction_text, use_markup=True, xalign=0, wrap=True))
        

        #  Copy Path Section
        path_to_copy = "~/.config/systemd/user"
        
        path_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        path_box.add_css_class("card") # Optional: adds a nice background frame if your CSS supports it
        path_box.set_margin_start(12)
        
        # Display the path in a selectable label
        path_display = Gtk.Label(label=path_to_copy, xalign=0, hexpand=True, selectable=True)
        path_display.add_css_class("dim-label") # Makes it look like a secondary technical path
        
        # Copy Button
        copy_path_btn = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
        copy_path_btn.add_css_class("flat")
        copy_path_btn.set_tooltip_text("Copy path to clipboard")
        copy_path_btn.connect("clicked", lambda b: Gdk.Display.get_default().get_clipboard().set_content(
            # Use os.path.expanduser here to turn ~ into /home/User
            Gdk.ContentProvider.new_for_value(os.path.expanduser(host_path))
        ))
        #  Add a toast confirmation when clicked
        copy_path_btn.connect("clicked", lambda b: self.toast_overlay.add_toast(Adw.Toast.new("Path copied!")))

        path_box.append(path_display)
        path_box.append(copy_path_btn)
        main_box.append(path_box)
        # --- THE ACTION BUTTONS ---
        setup_btn = Gtk.Button(label="Run Automated Installer")
        setup_btn.add_css_class("suggested-action")
        setup_btn.connect("clicked", self.install_host_refresher)
        main_box.append(setup_btn)
        # WARNING EXPANDER
        warning_expander = Adw.ExpanderRow(title="WARNING", subtitle="Security information")
        warning_expander.add_css_class("card")
        
        warning_text = (
            "<span size='large' weight='bold'>Security &amp; Background Service</span>\n\n"
            "This setup installs a <b>systemd user unit</b> on your host system. "
            "This is a secure way to allow the sandbox to request a theme refresh "
            "without giving the app full control over your computer.\n\n"
            "<b>How it works:</b>\n"
            "• The app 'touches' a trigger file inside its sandbox.\n"
            "• Your host system detects this change and runs the refresh command.\n"
            "• You can inspect the exact command inside <b>plasma-refresher.service</b>.\n\n"
            "<span color='#999999' size='small'>Use with caution: This allows code execution "
            "on the host triggered by the sandbox.</span>"
        )

        warning_label = Gtk.Label(label=warning_text, use_markup=True, xalign=0, wrap=True)
        warning_label.set_margin_bottom(12)

        warning_expander.add_row(warning_label) # Add the widget you already created
        main_box.append(warning_expander)
        # --- COMMAND SECTION ---
        cmd_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        cmd_box.append(Gtk.Label(label="<b>Then run this command and restart the app</b>", use_markup=True, xalign=0))
        
        full_cmd = "systemctl --user daemon-reload && systemctl --user enable --now plasma-refresher.path"
        
        entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        cmd_label = Gtk.Label(label=full_cmd, selectable=True, wrap=True, hexpand=True, xalign=0)
        cmd_label.add_css_class("card")
        
        copy_cmd_btn = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
        copy_cmd_btn.add_css_class("flat")
        copy_cmd_btn.connect("clicked", lambda b: Gdk.Display.get_default().get_clipboard().set_content(
            Gdk.ContentProvider.new_for_value(full_cmd)
        ))
        copy_cmd_btn.connect("clicked", lambda b: self.toast_overlay.add_toast(Adw.Toast.new("Command copied!")))

        entry_box.append(cmd_label)
        entry_box.append(copy_cmd_btn)
        cmd_box.append(entry_box)
        main_box.append(cmd_box)

    def _on_plasma_dialog_destroyed(self, dialog):
        self.plasma_dialog = None
        # Refresh the UI switch state when user closes dialog
        self.check_plasma_refresh_status()
        self.initial_status()

    def is_plasma_refresh_ready(self):
        # Check Systemd Portal Path
        host_path = "~/.config/systemd/user"
        portal_path = getattr(self, f"active_portal_{self.get_safe_key(host_path)}", None)
        if not portal_path:
            portal_path = self.load_cached_portal_path(host_path)
        
        if not portal_path or not os.path.exists(portal_path):
            return False

        # Check for the two PLASMA refresher files
        path_exists = os.path.isfile(os.path.join(portal_path, "plasma-refresher.path"))
        service_exists = os.path.isfile(os.path.join(portal_path, "plasma-refresher.service"))
        if not (path_exists and service_exists):
            return False


        return True



    #MAIN PERMISSION WINDOW
    def show_permission_dialog(self, title, folders):
        # Ensure folders is always a list for consistent looping
        if isinstance(folders, str):
            folders = [folders]
            
        self.portal_widgets = {} 
        app_id = self.get_application().get_application_id()
        dialog = Adw.MessageDialog(transient_for=self, heading=f"Permissions for {title} Required")
        
        # Vertical container for the content
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        if title == "Papirus":
            papirus_msg = f"Please ensure papirus is installed locally, to install papirus locally use this command :"
            papirus_label = Gtk.Label(label=papirus_msg, wrap=True, xalign=0)
            main_box.append(papirus_label)

            command_papirus = f'wget -qO- https://git.io/papirus-icon-theme-install | DESTDIR="$HOME/.local/share/icons" sh'
            papirus_command_label = Gtk.Label(label=f"{command_papirus}", 
            selectable=True, use_markup=True, wrap=True)
            papirus_command_label.add_css_class("card")
            main_box.append(papirus_command_label)

            #  Main instructional text at the top
        if len(folders) == 1:
            msg = f"To save the {title} theme to <b>{folders[0]}</b>, you must grant temporary access to the folder (does not persist through restart) :"
        else:
            msg = f"To save {title} themes, you must grant access to the folders listed below (does not persist through restart):"
        
        instruction_label = Gtk.Label(
            label=msg, 
            use_markup=True, 
            wrap=True, 
            xalign=0
        )
        main_box.append(instruction_label)

        for i, folder in enumerate(folders):
            # Create a section for each folder
            section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            
            #  Folder specific label
            short_folder = folder.replace("~/.local/share/", "xdg-data/").replace("~/.config/", "xdg-config/")
            #  Create the descriptive label (Not selectable)
            if title == "Vesktop":
                #  Main Header for the section
                header_label = Gtk.Label(label=f"<b>Required Path {i+1} (Select either):</b>", use_markup=True, xalign=0)
                section_box.append(header_label)

                # Helper to build a "Path + Copy" row
                def create_path_row(display_name, actual_path):
                    row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                    row_box.set_margin_start(12) # Indent the specific paths
                    
                    # Display label (e.g., "Flatpak:")
                    type_label = Gtk.Label(label=f"<b>{display_name}:</b>", use_markup=True)
                    
                    # Path label
                    p_label = Gtk.Label(label=actual_path, selectable=True, xalign=0, hexpand=True)
                    p_label.add_css_class("dim-label") # Make it look like a secondary path

                    # Copy button for THIS specific path
                    c_btn = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
                    c_btn.add_css_class("flat")
                    c_btn.connect("clicked", lambda b, p=actual_path: b.get_clipboard().set_content(
                        Gdk.ContentProvider.new_for_value(os.path.expanduser(p))
                    ))
                    
                    row_box.append(type_label)
                    row_box.append(p_label)
                    row_box.append(c_btn)
                    return row_box

                # Add the Flatpak Row
                section_box.append(create_path_row("Flatpak", "~/.var/app/dev.vencord.Vesktop/config/vesktop/themes"))
                # Add the Regular Row
                section_box.append(create_path_row("Regular", "~/.config/vesktop/themes"))

            else:
                # --- Standard logic for all other apps ---

                label = Gtk.Label(label=f"<b>Required Path {i+1}:</b>", use_markup=True, xalign=0)
                section_box.append(label)

                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                path_label = Gtk.Label(label=folder, selectable=True, xalign=0, hexpand=True)

                copy_btn = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
                copy_btn.add_css_class("flat")
                copy_btn.connect("clicked", lambda b, f=folder: b.get_clipboard().set_content(
                    Gdk.ContentProvider.new_for_value(os.path.expanduser(f))
                ))

                
                box.append(path_label)
                box.append(copy_btn)
                section_box.append(box)
                

        


            
                        # Entry to show current path
            selected_label = Gtk.Label(label=f"<b>Selected Path {i+1}:</b>", use_markup=True, xalign=0)
            section_box.append(selected_label)
            path_entry = Gtk.Entry(editable=False, can_focus=False)
                # THE PERSISTENCE LOGIC
            # Check if we already have a saved portal path for this specific folder
            safe_key = self.get_safe_key(folder)
            existing_path = getattr(self, f"active_portal_{safe_key}", None)
            if existing_path:
                # If a path exists, set it in the entry so the user sees it immediately
                path_entry.set_text(existing_path)
                path_entry.add_css_class("success") 
            else:
                # Standard placeholder for new selections
                path_entry.set_placeholder_text("No folder selected yet...")
            section_box.append(path_entry)
            
            # Warning label (hidden by default)
            warning_label = Gtk.Label(use_markup=True, xalign=0)
            warning_label.set_visible(False)
            warning_label.add_css_class("error") # Libadwaita red text style
            section_box.append(warning_label)

            # Store references indexed by the original folder string
            self.portal_widgets[folder] = {
                "entry": path_entry,
                "warning": warning_label
            }
            
                        #  Individual "Select Folder" button for this specific path
            # We use a standard Gtk.Button here instead of the dialog response
            select_btn = Gtk.Button(label=f"Select Path {i+1} Manually")
            select_btn.add_css_class("suggested-action")
            # Connect to your portal logic, passing the specific folder
            select_btn.connect("clicked", lambda b, f=folder: self.on_dialog_response(dialog, "select", f))
            section_box.append(select_btn)

            #  Copy Command
            labelcopy = Gtk.Label(label=f"Or use this command for permanent access", use_markup=True, xalign=0)
            command_text = f"flatpak override --user {app_id} --filesystem={short_folder}:create"
            command_label = Gtk.Label(label=f"{command_text}", 
                                      selectable=True, use_markup=True, wrap=True)
            command_label.add_css_class("card")
            section_box.append(labelcopy)
            section_box.append(command_label)



            main_box.append(section_box)
            
            # Add a separator if there are multiple sections
            if len(folders) > 1 and i < len(folders) - 1:
                main_box.append(Gtk.Separator())

        # Add the final restart note
        bottom_text = Gtk.Label(label="<b>Note: If using commands, you must restart the app to apply permissions.</b>", 
                                use_markup=True, wrap=True, xalign=0)
        bottom_text.set_margin_top(10)
        main_box.append(bottom_text)

        dialog.set_extra_child(main_box)
        dialog.add_response("ok", "Close") # Standard close button
        dialog.present()

    def zen_permission_dialog(self, title, folders):
        if isinstance(folders, str):
            folders = [folders]
            
        self.portal_widgets = {} 
        app_id = self.get_application().get_application_id()
        dialog = Adw.MessageDialog(transient_for=self, heading=f"Special Setup: {title}")

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)

        #  Top Informational Text
        instruction_text = (
            f"<big><b>{title} First Time Configuration Required</b></big>\n\n"
            "To sync styles correctly, follow these steps to find your profile:\n\n"
            "• Open Zen browser and type <tt>about:profiles</tt> in the URL bar.\n"
            "• Locate your <b>ACTIVE</b> profile and open the <b>Root Directory</b>.\n"
            "• Navigate into the <b>chrome</b> folder.\n"
            "• Copy the path from your file manager's navigation bar."
        )
        info_label = Gtk.Label(label=instruction_text, use_markup=True, wrap=True, xalign=0)
        main_box.append(info_label)

        #  folder logic 
        for i, folder in enumerate(folders):
            section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            # Now 'folder' is defined for the safe_key logic
            safe_key = self.get_safe_key(folder)
            
            # Create the entry BEFORE calling methods on it
            path_entry = Gtk.Entry(editable=False, can_focus=False)
            
            #  Create the Label (We will update its text dynamically)
            selected_label = Gtk.Label(use_markup=True, xalign=0)
            
            
            #  Create the Editable Entry where user pastes the path
            user_path_entry = Gtk.Entry()
            user_path_entry.set_placeholder_text("Paste your /.zen/profile/chrome path here...")
                        # Create the Command Label
            command_label = Gtk.Label(selectable=True, use_markup=True, wrap=True)
            command_label.add_css_class("card")
                        # THE DYNAMIC UPDATE FUNCTION
            def update_ui(entry, label_widget, cmd_widget, original_pattern):
                user_input = entry.get_text().strip()
                # Save the input to the class instance permanently
                self.last_manually_entered_zen_path = user_input
                self.save_persistent_settings(manual_path=user_input)
                
                # Update UI labels as we did before
                display_text = user_input if user_input else "No path provided"
                label_widget.set_markup(f"<b>Target Path:</b> <tt>{display_text}</tt>")
                
                # Update the Command
                path_for_cmd = user_input if user_input else "[PASTE_PATH_HERE]"
                safe_cmd_path = GLib.markup_escape_text(path_for_cmd)
                full_cmd = f"flatpak override --user {app_id} --filesystem=\"{safe_cmd_path}\":create"
                cmd_widget.set_markup(f"<tt>{full_cmd}</tt>")
                
            user_path_entry.connect("changed", update_ui, selected_label, command_label, folder)
            saved_path = getattr(self, "last_manually_entered_zen_path", "")
            if saved_path:
                user_path_entry.set_text(saved_path)
            else:
                update_ui(user_path_entry, selected_label, command_label, folder)
            section_box.append(Gtk.Label(label="<b>Initial setup: Paste your unique Chrome path</b>", use_markup=True, xalign=0))
            section_box.append(user_path_entry)
            section_box.append(selected_label)

    


                

            
                #  PERSISTENCE LOGIC
            # Check if we already have a saved portal path for this specific folder
      
            existing_path = getattr(self, f"active_portal_{safe_key}", None)
            if existing_path:
                # If a path exists, set it in the entry so the user sees it immediately
                path_entry.set_text(existing_path)
                path_entry.add_css_class("success") 
            else:
                # Standard placeholder for new selections
                section_box.append(Gtk.Label(label="<b>Step 2: Select your unique Chrome path</b>", use_markup=True, xalign=0))
                path_entry.set_placeholder_text("No folder selected yet...")
            section_box.append(path_entry)
            
            # Warning label (hidden by default)
            warning_label = Gtk.Label(use_markup=True, xalign=0)
            warning_label.set_visible(False)
            warning_label.add_css_class("error") # Libadwaita red text style
            section_box.append(warning_label)

            # Store references indexed by the original folder string
            self.portal_widgets[folder] = {
                "entry": path_entry,
                "warning": warning_label
            }

            # Select Button (Captured correctly via lambda)
            select_btn = Gtk.Button(label=f"Select Path {i+1}")
            select_btn.add_css_class("suggested-action")
            select_btn.connect("clicked", lambda b, f=folder: self.on_dialog_response(dialog, "select", f))
            section_box.append(select_btn)


            

            #  Create the label for the dynamic command
            command_label = Gtk.Label(selectable=True, use_markup=True, wrap=True)
            command_label.add_css_class("card")
            command_label.add_css_class("monospace")
            section_box.append(Gtk.Label(label="<b>Or Paste the command in your terminal for permanent access</b>", use_markup=True, xalign=0))
            section_box.append(command_label)

            #  Helper function to update the command live
            def update_command(entry):
                user_input = entry.get_text().strip()
                # Default to a placeholder if empty
                path_to_show = user_input if user_input else "[PASTE_PATH_HERE]"
                
                # ESCAPE the user input so characters like '(' or ' ' don't break the XML
                safe_path = GLib.markup_escape_text(path_to_show)
                
  
                full_cmd = f"flatpak override --user {app_id} --filesystem=\"{safe_path}\":create"
                
      
                command_label.set_markup(f"<tt>{full_cmd}</tt>")

        # Connect the listener (Runs every time the user types or pastes)
        user_path_entry.connect("changed", update_ui, selected_label, command_label, folder)
        
        # Initial call to set default state
        update_ui(user_path_entry, selected_label, command_label, folder)

        main_box.append(section_box)

        dialog.set_extra_child(main_box)
        dialog.add_response("ok", "Close")
        dialog.present()
        
    def save_persistent_settings(self, manual_path=None):
        # Use the passed path if available; otherwise fallback to the instance variable
        path_to_save = manual_path if manual_path is not None else getattr(self, "last_manually_entered_zen_path", "")
        
        config_dir = os.path.expanduser("~/.var/app/io.github.schwarzen.colormydesktop/config/color-my-desktop/")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "settings.json")
        
        data = {
            "zen_path": path_to_save
        }
        
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
            self.check_gnome_refresh_status()
            # Pass the folder to the callback so we know which Entry to update
            portal.select_folder(self, None, 
                lambda dialog, result: self.on_portal_folder_selected(dialog, result, target_folder))
                



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
                selected_folder_name = os.path.basename(os.path.normpath(sandboxed_path))
                expected_folder_name = os.path.basename(os.path.normpath(target_folder))
                
                if not hasattr(self, 'portal_access_list'):
                    self.portal_access_list = []
                
                if sandboxed_path not in self.portal_access_list:
                    self.portal_access_list.append(sandboxed_path)
                
                widgets = self.portal_widgets.get(target_folder)
                if widgets:
                    widgets["entry"].set_text(sandboxed_path)
                    if selected_folder_name != expected_folder_name:
                        msg = f"⚠️ <b>Warning:</b> You selected '{selected_folder_name}', but we expected '{expected_folder_name}'."
                        widgets["warning"].set_label(msg)
                        widgets["warning"].set_visible(True)
                        widgets["entry"].add_css_class("error")
                    else:
                        widgets["warning"].set_visible(False)
                        widgets["entry"].remove_css_class("error")
                        widgets["entry"].add_css_class("success")

                # 3. SPECIAL HANDLING: If this was the Plasma systemd folder, refresh the setup dialog
                if "systemd/user" in target_folder:
                    # This forces the status icons (the 4 boxes) to update to green immediately
                    self.show_plasma_setup_dialog()

            # Existing switch reactivation logic
            target_switch = getattr(self, 'last_toggled_switch', None)
            if target_switch:
                handler_id = None
                if target_switch == getattr(self, 'gnome_switch', None):
                    handler_id = getattr(self, 'gnome_handler_id', None)
                elif target_switch == getattr(self, 'plasma_refresh_switch', None):
                    handler_id = getattr(self, 'plasma_handler_id', None)

                if handler_id:
                    target_switch.handler_block(handler_id)
                    target_switch.set_active(True)
                    target_switch.handler_unblock(handler_id)
                else:
                    target_switch.set_active(True)
                    
            if self.is_plasma_refresh_ready():
                    # Block the signal so we don't trigger a recursive call or toast
                    self.plasma_refresh_switch.handler_block(self.plasma_handler_id)
                    self.plasma_refresh_switch.set_active(True)
                    self.plasma_refresh_switch.handler_unblock(self.plasma_handler_id)
                
        except Exception as e:
            print(f"Portal Error: {e}")

            
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
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', raw_key).lower()
        
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
        
            
    

    def on_feature_toggled(self, widget, pspec, folders, feature_name):
        if widget.get_active():
            if isinstance(folders, str):
                folders = [folders]
                
            missing_permission = False

            for folder_pattern in folders:
                has_access = False
                
                # --- NEW: MANUAL ZEN PATH CHECK  ---
                # If we're checking Zen/YouTube, prioritize the path the user just pasted
                if feature_name in ["Zen", "YouTube"]:
                    manual_path = getattr(self, "last_manually_entered_zen_path", None)
                    if manual_path:
                        expanded_manual = os.path.expanduser(manual_path)
                        # We check the literal path directly (bypasses glob issues)
                        if os.access(expanded_manual, os.W_OK):
                            has_access = True

                # --- EXISTING PORTAL CHECK ---
                if not has_access:
                    safe_key = self.get_safe_key(folder_pattern)
                    portal_path = getattr(self, f"active_portal_{safe_key}", None)
                    if portal_path and os.access(portal_path, os.W_OK):
                        has_access = True

                # ---  UPDATED HOST FALLBACK (WITH WILDCARDS) ---
                if not has_access:
                    expanded_pattern = os.path.expanduser(folder_pattern)
                    # iglob handles '*' 
                    matches = list(glob.iglob(expanded_pattern))
                    
                    # If matches were found, check if any are writable
                    if matches and any(os.access(m, os.W_OK) for m in matches):
                        has_access = True
                    # Final raw access check (for paths without wildcards)
                    elif os.access(expanded_pattern, os.W_OK):
                        has_access = True

                # If after all checks we still have no access, this folder fails
                if not has_access:
                    missing_permission = True
                    break
            
            # --- ROUTING & DIALOG LOGIC ---
            if missing_permission:
                self.clear_specific_portal_cache(folder_pattern)
                self.last_toggled_switch = widget
                if feature_name in ["Zen", "YouTube"]:
                    self.zen_permission_dialog(feature_name, folders)
                else:
                    self.show_permission_dialog(feature_name, folders)
                widget.set_active(False)
                
    def clear_specific_portal_cache(self, target_folder):
        # 1. Clear from memory immediately
        safe_key = self.get_safe_key(target_folder)
        attr_name = f"active_portal_{safe_key}"
        if hasattr(self, attr_name):
            delattr(self, attr_name)

        # 2. Remove only the specific entry from the JSON file
        data_dir = GLib.get_user_data_dir()
        config_file = os.path.join(data_dir, "portal_cache.json")
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    cache = json.load(f)
                
                if target_folder in cache:
                    del cache[target_folder]
                    # Rewrite the file with the remaining valid paths
                    with open(config_file, 'w') as f:
                        json.dump(cache, f, indent=4)
                    print(f"Cleared {target_folder} from cache. Others preserved.")
            except Exception as e:
                print(f"Error updating cache: {e}")

        # 3. Update the UI Entry if it's currently visible
        if hasattr(self, 'portal_widgets') and target_folder in self.portal_widgets:
            w = self.portal_widgets[target_folder]
            w["entry"].set_text("")
            w["entry"].remove_css_class("success")
            w["entry"].set_placeholder_text("Permission lost, please re-select...")

        
                
                
    def add_folder_action(self, switch_row, feature_name, folders):
        # Create a uniform button
        folder_button = Gtk.Button.new_from_icon_name("folder-open-symbolic")
        folder_button.add_css_class("flat")
        folder_button.set_valign(Gtk.Align.CENTER)
        folder_button.set_tooltip_text(f"Manage {feature_name} folders")

        #  Connect the click to the permission dialog
        # We use a lambda to pass the specific feature info
        folder_button.connect("clicked", lambda b: 
            self.zen_permission_dialog(feature_name, folders) 
            if feature_name in ["Zen", "YouTube"] 
            else self.show_permission_dialog(feature_name, folders)
        )


        #  Add to the row
        switch_row.add_suffix(folder_button)

        #  Bind visibility so it only shows when the switch is ON
        switch_row.bind_property(
            "active", 
            folder_button, 
            "visible", 
            GObject.BindingFlags.SYNC_CREATE
        )
        
        return folder_button
