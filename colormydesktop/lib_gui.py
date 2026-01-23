#!/usr/bin/env python3
# Copyright 2026 Schwarzen
# SPDX-License-Identifier: Apache-2.0

import os
import re
import subprocess
import threading
import sys
import shutil



import gi

from gi.repository import Gtk, Adw, Gdk, GLib, Gio, GObject

from .dialogs import DialogMixin
from .advancedpref import AdvancedMixin
# --- CONFIGURATION ---




if os.environ.get("FLATPAK_ID"):
    # Inside Flatpak, the script is at /app/bin/
    BASH_SCRIPT = "/app/bin/color-my-desktop-backend"
    SCSS_DIR = os.path.expanduser("~/.var/app/io.github.schwarzen.colormydesktop/data/scss")
else:
    # Native install location
    BASH_SCRIPT = os.path.expanduser("~/.local/bin/color-my-desktop-backend")
    SCSS_DIR = os.path.expanduser("~/.local/share/Color-My-Desktop/scss")


class ThemeManager(Adw.ApplicationWindow, DialogMixin, AdvancedMixin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.portal_widgets = {}
        self.setup_css_providers()
        self.setup_user_data()
        self.last_manually_enterd_zen_path = ""
        self.load_persistent_settings()


        if os.path.exists(SCSS_DIR):
            raw_themes = [f[1:-5] for f in os.listdir(SCSS_DIR) if f.startswith('_') and f.endswith('.scss')]
            raw_themes.sort()
            self.themes = ["Default"] + raw_themes
        else:
            print("CRITICAL: SCSS_DIR missing even after setup_user_data()")
            self.themes = ["Default"]



        self.current_colors = {} 
        self.status_labels = {}
    
        self.nautilus_active = False
        self.nautilus_hex_var = "#88c0d0"
        self.datemenu_active = False
        self.datemenu_hex_var = "#88c0d0"
     
        self.set_title("Color My Desktop")
        self.set_default_size(400, 600)

   
        self.toast_overlay = Adw.ToastOverlay()
        self.nav_view = Adw.NavigationView()
        self.main_page_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

    
        self.set_content(self.toast_overlay)           
        self.toast_overlay.set_child(self.nav_view)   

        #  BUILD THE MAIN PAGE CONTENT
        self.header = Adw.HeaderBar()
        self.main_page_content.append(self.header)

        self.page = Adw.PreferencesPage()
        self.main_page_content.append(self.page)     

        self.group = Adw.PreferencesGroup()
        self.group.set_title("Theme Configuration")
     
        # SETUP GROUPS
        self.load_group = Adw.PreferencesGroup(title="Profile Management")
        self.page.add(self.load_group)

        # CREATE DROPDOWN WIDGETS - EXISTING 
        self.theme_list = Gtk.StringList.new(self.themes)
        self.combo_row = Adw.ComboRow(title="Load Existing Profile")
        self.combo_row.set_model(self.theme_list)
        self.combo_row.set_selected(0) # Force "Default" selection
        

        self.load_group.add(self.combo_row)

        # CONNECT SIGNALS LAST
        self.combo_row.connect("notify::selected", self.on_theme_select)

        # COLOR GROUP (The Hex Entries) ---
        self.color_group = Adw.PreferencesGroup()
        self.color_group.set_title("Theme Colors")
        self.page.add(self.color_group)
        
        self.name_row = Adw.EntryRow(title="Profile Name")
        self.color_group.add(self.name_row)

        self.primary_row = self.create_color_entry("Primary Color", "#3584e4","primary")
        self.color_group.add(self.primary_row)
        self.secondary_row = self.create_color_entry("Secondary Hex", "#241f31", "secondary")
        self.color_group.add(self.secondary_row)
        self.tertiary_row = self.create_color_entry("Tertiary Hex", "#1e1e1e", "tertiary")
        self.color_group.add(self.tertiary_row)
        self.text_row = self.create_color_entry("Text Hex", "#f9f9f9", "text")
        self.color_group.add(self.text_row)      

        # Connect to the selection change signal
        self.combo_row.connect("notify::selected", self.on_theme_select)

        
        # Global Options Group
      
        self.group.set_title("Global Options")
        self.page.add(self.group)
        
        
        # --- GNOME SHELL TOGGLE ---
        self.gnome_switch = Adw.SwitchRow()
        self.gnome_switch.set_title("Apply to gnome-shell")
        self.gnome_switch.set_active(False)
              
        # Connect the signal to a handler that checks the specific folder
        self.gnome_handler_id = self.gnome_switch.connect(
            "notify::active", 
            lambda widget, pspec: self.on_feature_toggled(widget, pspec, ["~/.local/share/themes"], "GNOME")
        )
        self.add_folder_action(self.gnome_switch, "GNOME", ["~/.local/share/themes"])
         # For GNOME path arg
        self.gnome_path = self.get_path_argument("~/.local/share/themes")
        self.group.add(self.gnome_switch) 
        
        # --- KDE PLASMA TOGGLE ---
        self.plasma_switch = Adw.SwitchRow()
        self.plasma_switch.set_title("Apply to KDE Plasma")
        self.plasma_switch.set_subtitle("Required for KDE Plasma style/colorscheme themes")
        self.plasma_switch.set_active(False)

        # Connect the signal to a handler that checks the specific folder
        plasma_folders = ["~/.local/share/plasma", "~/.local/share/color-schemes"]

        # 2. Use the list in the toggle connection
        self.plasma_handler_id = self.plasma_switch.connect(
            "notify::active", 
            lambda widget, pspec: self.on_feature_toggled(
                widget, 
                pspec, 
                plasma_folders, 
                "KDE Plasma"
            )
        )

        # 3. Use the SAME list in the folder action helper
        # This ensures the dialog shows both "Path 1" and "Path 2"
        self.add_folder_action(self.plasma_switch, "KDE Plasma", plasma_folders)
        # For Plasma path arg
        self.plasma_path = self.get_path_argument("~/.local/share/plasma")
        self.schemes_path = self.get_path_argument("~/.local/share/color-schemes")
        self.group.add(self.plasma_switch)
        
        # --- GTK4 TOGGLE ---
        self.gtk4_switch = Adw.SwitchRow()
        self.gtk4_switch.set_title("Apply to GTK4 apps")
        self.gtk4_switch.set_active(False)
                # Connect the signal to a handler that checks the specific folder
        self.gtk4_handler_id = self.gtk4_switch.connect(
            "notify::active", 
            lambda widget, pspec: self.on_feature_toggled(widget, pspec, ["~/.config/gtk-4.0"], "GTK4")
        )
        self.add_folder_action(self.gtk4_switch, "GTK4", ["~/.config/gtk-4.0"])
         # For GTK path arg
        self.gtk4_path = self.get_path_argument("~/.config/gtk-4.0")
        self.group.add(self.gtk4_switch) 
        
        
        # --- ZEN BROWSER TOGGLE ---
        self.zen_switch = Adw.SwitchRow()
        self.zen_switch.set_title("Apply to Zen Browser")
        self.zen_switch.set_active(False)
                # Connect the signal to a handler that checks the specific folder
        self.zen_handler_id = self.zen_switch.connect(
            "notify::active", 
            lambda widget, pspec: self.on_feature_toggled(
                widget, 
                pspec, 
                [getattr(self, "last_manually_entered_zen_path", "")], 
                "Zen"
            )
        )
        self.add_folder_action(self.zen_switch, "Zen" , ["~/.zen/*/chrome"])
         # For zen path arg
        self.zen_path = self.get_path_argument("last_manually_entered_zen_path")
        self.group.add(self.zen_switch)


        
        # --- YOUTUBE TOGGLE ---
        self.youtube_switch = Adw.SwitchRow()
        self.youtube_switch.set_title("Apply to YouTube (Zen Browser)")
        self.youtube_switch.set_active(False)
        self.youtube_handler_id = self.youtube_switch.connect(
            "notify::active", 
            lambda widget, pspec: self.on_feature_toggled(
                widget, 
                pspec, 
                [getattr(self, "last_manually_entered_zen_path", "")], 
                "Zen"
            )
        )
        self.add_folder_action(self.youtube_switch, "Zen" , ["~/.zen/*/chrome"])
         # For zen path arg
        self.zen_path = self.get_path_argument("last_manually_entered_zen_path")
        self.group.add(self.youtube_switch)


        # --- VESKTOP TOGGLE ---
        self.vesktop_switch = Adw.SwitchRow()
        self.vesktop_switch.set_title("Apply to Vesktop")
        self.vesktop_switch.set_active(False)
        self.vesktop_handler_id = self.vesktop_switch.connect(
            "notify::active", 
            lambda widget, pspec: self.on_feature_toggled(widget, pspec, ["~/.config/vesktop/themes"], "Vesktop")
        )
        self.add_folder_action(self.vesktop_switch, "Vesktop" , ["~/.config/vesktop/themes"])
         # For vesktop path arg
        self.vesktop_path = self.get_path_argument("~/.config/vesktop/themes")
        self.group.add(self.vesktop_switch)



        # --- PAPIRUS ICON SYNC TOGGLE ---
        self.papirus_switch = Adw.SwitchRow()
        self.papirus_switch.set_title("Sync Papirus Icons with Theme")
        self.papirus_switch.set_active(False) # Default off
                # Connect the signal to a handler that checks the specific folder
        self.papirus_handler_id = self.papirus_switch.connect(
            "notify::active", 
            lambda widget, pspec: self.on_feature_toggled(widget, pspec, ["~/.local/share/icons"], "Papirus")
        )
        self.add_folder_action(self.papirus_switch, "Papirus", ["~/.local/share/icons"])
         # For Papirus path arg
        self.papirus_path = self.get_path_argument("~/.local/share/icons")
        self.group.add(self.papirus_switch)


        #  ADVANCED OPTIONS SWAP BUTTON (ActionRow) ---
        # This is a row that looks like a button but fits in a PreferencesGroup
        self.advanced_link = Adw.ActionRow(title="Advanced Options", selectable=False)
        self.advanced_link.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        self.advanced_link.set_activatable(True)
        self.group.add(self.advanced_link)
        # Connect the click event
        self.advanced_link.connect("activated", lambda row: self.nav_view.push(self.adv_nav_page))

        
        
        
        # BUILD BUTTON
        self.build_btn = Gtk.Button(label="Build and Apply Theme")
        self.build_btn.add_css_class("suggested-action") # color
        self.build_btn.set_margin_top(24)
        self.build_btn.set_margin_bottom(24)
        
        self.log_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.log_container.set_visible(False) # Hidden until build starts
        self.main_page_content.append(self.log_container)

        #  Add a progress bar for visual feedback
        self.progress_bar = Gtk.ProgressBar()
        self.log_container.append(self.progress_bar)

        # Create the scrollable terminal area
        self.scrolled_window = Gtk.ScrolledWindow(min_content_height=150)
        self.scrolled_window.add_css_class("card") # Adds a nice border/background

        self.log_view = Gtk.TextView(editable=False, monospace=True)
        self.scrolled_window.set_child(self.log_view)
        self.log_container.append(self.scrolled_window)
        
        # Connect the signal to the method above
        self.build_btn.connect("clicked", self.on_run_build_clicked)
        
        # button to mainbox
        self.main_page_content.append(self.build_btn)
        
        self.main_nav_page = Adw.NavigationPage.new(self.main_page_content, "Color My Desktop")
        self.nav_view.add(self.main_nav_page)
        



        # --- ADVANCED PAGE SETUP ---
        self.adv_page_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Add a HeaderBar so users can go back (NavigationView handles the back button)
        self.adv_header = Adw.HeaderBar()
        self.adv_page_content.append(self.adv_header)

        self.adv_pref_page = Adw.PreferencesPage(
            title="Advanced",
            icon_name="preferences-system-symbolic"
        )
        self.adv_page_content.append(self.adv_pref_page)
        # CREATE A MAINTENANCE GROUP (At the top)
        maintenance_group = Adw.PreferencesGroup()
        self.adv_pref_page.add(maintenance_group)

        # Create and add the Reset Button to that group
        self.reset_btn = Adw.ActionRow()
        self.reset_btn.set_title("Reset App Permissions")
        self.reset_btn.set_subtitle("Remove all manual folder access and overrides")
        self.reset_btn.set_activatable(True)
        self.reset_btn.connect("activated", self.show_reset_instructions)
        
        maintenance_group.add(self.reset_btn)
        
        self.grid_group = Adw.PreferencesGroup()
        #  Add the group to the page
        self.adv_pref_page.add(self.grid_group)
        #  Create the FlowBox (The Grid)
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(3) # Forces 3 columns
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_homogeneous(True) # Makes all boxes the same size
        


        # Add the grid to the group
        self.grid_group.add(self.flowbox)
        
        def is_writable(path):
            # Expands XDG paths like xdg-data/plasma to full host paths
            # Note: Inside Flatpak, these are usually mounted at /run/host/... or standard ~/.local/share
            full_path = os.path.expanduser(path)
            return os.access(full_path, os.W_OK)


        #  Add items to your grid
        self.add_grid_item("Nautilus", "#88c0d0", "nautilus_custom")
        self.add_grid_item("Gnome-shell", "#bd93f9", "system_custom")
        

        # Wrap it in a NavigationPage
        self.adv_nav_page = Adw.NavigationPage.new(self.adv_page_content, "Advanced")
        self.nav_view.add(self.adv_nav_page)
        
        initial_css = ""
        for cid, hcolor in self.current_colors.items():
            initial_css += f"#{cid}-preview {{ background-color: {hcolor}; border-radius: 6px; min-width: 24px; min-height: 24px; }}\n"
        self.dynamic_color_provider.load_from_string(initial_css)
        
        GLib.idle_add(self.setup_user_data)
        self.nav_view.push(self.main_nav_page)
        
        
    def load_persistent_settings(self):
        config_path = os.path.expanduser("~/.var/app/io.github.schwarzen.colormydesktop/config/color-my-desktop/settings.json")
        if os.path.exists(config_path):
            try:
                import json
                with open(config_path, "r") as f:
                    data = json.load(f)
                    self.last_manually_entered_zen_path = data.get("zen_path", "")
                    print(f"DEBUG: Loaded Zen Path: {self.last_manually_entered_zen_path}")
            except Exception as e:
                print(f"DEBUG: Failed to load settings: {e}")
                self.last_manually_entered_zen_path = ""
        

  
    

    def is_valid_hex(self, color):
        # Strip whitespace to avoid simple input errors
        color = color.strip()
        
        # Matches SCSS variables (e.g., $primary-color)
        if re.match(r'^\$[A-Za-z0-9_-]+$', color):
            return True
        
        # 2. Matches your original Hex requirements (#RRGGBB or RRGGBB)
        # Note: Gdk.RGBA.parse also handles #hex, but your original regex 
        # handles hex without the '#' prefix, which Gdk does not.
        if re.match(r'^#?([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', color):
            return True

        # Fallback to Gdk.RGBA.parse (Handles rgba(0,0,0,0), hsl, names, etc.)
        rgba = Gdk.RGBA()
        return rgba.parse(color)
        
    
    def create_color_entry(self, label, default_hex, css_id):
        row = Adw.EntryRow(title=label)
        row.set_text(default_hex)
        row.default_val = default_hex
        self.current_colors[css_id] = default_hex

        # Setup Preview Box as before
        preview = Gtk.Image.new_from_icon_name("color-select-symbolic")
        preview.set_pixel_size(24)
        preview.add_css_class("color-preview-box")
        preview.set_name(f"{css_id}-preview")
        row.add_suffix(preview)

        # VISUAL VALIDATION ONLY (On Leave)
        def on_leave(controller):
            current_text = row.get_text().strip()
            if not self.is_valid_hex(current_text):
                # Mark it red so the user knows it's wrong, but don't delete it
                row.add_css_class("error")
            else:
                row.remove_css_class("error")
                
                # Standardize hex if it's a plain hex string
                if re.match(r'^([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', current_text):
                    row.set_text(f"#{current_text}")
                    
        focus_ctrl = Gtk.EventControllerFocus()
        focus_ctrl.connect("leave", on_leave)
        row.add_controller(focus_ctrl)

        # LOGIC PROTECTION (In Preview Update)
        def update_preview(entry, pspec):
            hex_code = entry.get_text().strip()
            
            # check if GTK can actually DRAW this color (No $ variables allowed for preview)
            rgba = Gdk.RGBA()
            if rgba.parse(hex_code) or (hex_code.startswith('#') and len(hex_code) in [4, 7, 9]):
                
                # Only if it's a "drawable" color, update the background registry
                clean_hex = hex_code if hex_code.startswith('#') else f"#{hex_code}"
                self.current_colors[css_id] = clean_hex
                
                # Rebuild the CSS string
                full_css = ""
                for cid, hcolor in self.current_colors.items():
                    # Only add to CSS if it's not a $ variable
                    if not hcolor.startswith('$'):
                        full_css += f"#{cid}-preview {{ background-color: {hcolor}; border-radius: 6px; min-width: 24px; min-height: 24px; }}\n"
                
                self.dynamic_color_provider.load_from_string(full_css)
            else:
                pass


        row.connect("notify::text", update_preview)
        return row
        
        
    def setup_css_providers(self):
        display = Gdk.Display.get_default()
        
        #  Attach them to 'self' so they persist as instance attributes
        self.preview_css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            display, self.preview_css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.dynamic_color_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            display, self.dynamic_color_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Update the loading logic to use 'self.'
        initial_css = "/* your initial css */"
        self.dynamic_color_provider.load_from_string(initial_css) # Added self.



        # --- DATA EXTRACTION LOGIC ---
    def get_scss_value(self, filename, variable):
        path = os.path.join(SCSS_DIR, f"_{filename}.scss")
        if not os.path.exists(path): return ""
        with open(path, 'r') as f:
            content = f.read()
            match = re.search(fr"\${variable}:\s*([^;]+);", content)
            return match.group(1).strip() if match else ""

    
    def on_theme_select(self, combo_row, gparamspec):
        selected_index = combo_row.get_selected()
        
        #  Guard: Ignore index 0 ('Default') or errors
        if selected_index <= 0:
            return
                
        selected_theme = self.theme_list.get_string(selected_index)
        if not selected_theme or selected_theme == "Default":
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
            self.name_row.set_text(selected_theme)
            
            # Update EACH color row specifically
            # Using existing get_scss_value logic
            self.primary_row.set_text(self.get_scss_value(selected_theme, "primary"))
            self.secondary_row.set_text(self.get_scss_value(selected_theme, "secondary"))
            self.tertiary_row.set_text(self.get_scss_value(selected_theme, "tertiary"))
            self.text_row.set_text(self.get_scss_value(selected_theme, "text"))
            

            
            tb_val = self.get_scss_value(selected_theme, "topbar-color")
            if tb_val:
                self.topbar_row.set_text(tb_val)
                self.topbar_switch.set_active(True)
            else:
                # If the file doesn't have it, reset to a safe default but don't clear it!
                self.topbar_row.set_text("#3584e4") 
                self.topbar_switch.set_active(False)
            clock_val = self.get_scss_value(selected_theme, "clock-color")
            if clock_val:
                self.clock_row.set_text(clock_val)
                self.clock_switch.set_active(True)
            else:
                # If the file doesn't have it, reset to a safe default but don't clear it!
                self.clock_row.set_text("#3584e4") 
                self.clock_switch.set_active(False)
            # If you have the switch: self.topbar_switch.set_active(True)
    # Assuming 'selected' is the string from your dropdown/ComboRow

        
        # --- RUN BASH SCRIPT ---

        
    def on_run_build_clicked(self, button):
        self.active_build_button = button 
        self.active_build_button.set_sensitive(False)
    # Get primary hex and ensure it is a string
        primary_color = str(self.primary_row.get_text() or "#3584e4")
        secondary_color = str(self.secondary_row.get_text() or "#3584e4")
        text_color = str(self.text_row.get_text() or "#f9f9f9")
        plasma_path = self.get_path_argument("~/.local/share/plasma")
        schemes_path = self.get_path_argument("~/.local/share/color-schemes")
        gnome_path = self.get_path_argument("~/.local/share/themes")
        zen_path = self.get_path_argument("~/.zen/*/chrome")
        vesktop_path = self.get_path_argument("~/.config/vesktop/themes")
        gtk4_path = self.get_path_argument("~/.config/gtk-4.0")
        papirus_path = self.get_path_argument("~/.local/share/icons")

     
        if self.topbar_switch.get_active():
            topbar_val = str(self.topbar_row.get_text())
        else:
            topbar_val = primary_color

        if self.clock_switch.get_active():
            clock_val = str(self.clock_row.get_text())
        else:
            clock_val = text_color
            
            #  Logic for Nautilus Main
        # If the advanced toggle is OFF, fallback to Primary
        n_main_sw = getattr(self, "nautilus_custom_switch")
        n_naut_row = getattr(self, "nautilus_custom_entry")
        
        n_sec_sw = getattr(self, "nautilus_custom_sec_switch")
        n_naut_row_sec = getattr(self, "nautilus_custom_naut_row_sec")

        # Get values: If active, take entry text. If not, take primary.
        n_main_val = n_naut_row.get_text() if n_main_sw.get_active() else primary_color
        n_sec_val = n_naut_row_sec.get_text() if n_sec_sw.get_active() else secondary_color

     
        if not topbar_val.strip(): topbar_val = primary_color
        if not clock_val.strip(): clock_val = text_color
           
        args = [
            self.name_row.get_text(),
            self.primary_row.get_text(),
            self.secondary_row.get_text(),
            self.tertiary_row.get_text(),
            self.text_row.get_text(),
            "1" if self.zen_switch.get_active() else "0",
            "1" if self.topbar_switch.get_active() else "0",
            topbar_val,
            "1" if self.clock_switch.get_active() else "0",
            clock_val,
            "1" if self.trans_switch.get_active() else "0",
            "0.8",
            "1" if self.papirus_switch.get_active() else "0",  # ${13}
            n_main_val, # $14
            "#3584e4",  # $15 (Datemenu fallback)
            n_sec_val,  # $16
            "1" if self.gnome_switch.get_active() else "0", # $17
            "1" if self.gtk4_switch.get_active() else "0", # $18
            "1" if self.plasma_switch.get_active() else "0", # $19
            "1" if self.youtube_switch.get_active() else "0", # 20
            "1" if self.vesktop_switch.get_active() else "0", # 21
            plasma_path,  # $22
            schemes_path, # $23
            gnome_path,
            zen_path,
            vesktop_path,
            gtk4_path,
            papirus_path,
            
        ]   
        
        self.log_container.set_visible(True)
        self.log_view.get_buffer().set_text("") 
        self.progress_bar.set_fraction(0.1)

        # Start the build in a background thread
        thread = threading.Thread(target=self.execute_build, args=(args,))
        thread.daemon = True # Closes thread if you exit the app
        thread.start()
        
        button.set_sensitive(False)
        
        
        
        

    def execute_build(self, args):
        try:
            # Use 'stdbuf -oL' to force Bash to send output line-by-line immediately
            # universal_newlines=True ensures text is handled as strings, not bytes
            process = subprocess.Popen(
                ["stdbuf", "-oL", BASH_SCRIPT] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Read output in real-time
            for line in iter(process.stdout.readline, ""):
                if line:
                    # Use idle_add to update the UI from the background thread safely
                    GLib.idle_add(self.append_log, line)

            process.wait()
        except Exception as e:
            GLib.idle_add(self.append_log, f"Error: {str(e)}\n")
        finally:
            GLib.idle_add(self.build_finished)

    def append_log(self, text):
        buffer = self.log_view.get_buffer()
        buffer.insert(buffer.get_end_iter(), text)
        
        # Auto-scroll to the bottom of the log
        adj = self.scrolled_window.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())
        
        self.progress_bar.pulse() # Makes the progress bar move
        return False
        
    def build_finished(self):
        self.progress_bar.set_fraction(1.0)
        self.toast_overlay.add_toast(Adw.Toast.new("Theme Applied Successfully!"))
        GLib.timeout_add(3000, self.auto_hide_logs)


    def auto_hide_logs(self):
        # Hide the terminal box and re-enable the build button
        self.log_container.set_visible(False)
        # self.build_button.set_sensitive(True) # Re-enable if you disabled it
        if hasattr(self, "active_build_button"):
            self.active_build_button.set_sensitive(True)
        
        # Optional: Show a final success toast
        self.toast_overlay.add_toast(Adw.Toast.new("Build Complete!"))
    
        return False # CRITICAL: Tells GLib to only run this once


    def show_success_toast(self, theme_name, button):
        """UI update logic."""
        toast = Adw.Toast.new(f"Theme '{theme_name}' applied!")
        self.toast_overlay.add_toast(toast)
        button.set_sensitive(True) 




    def show_error_dialog(self, message):
        """ replacement for Adw.MessageDialog."""
     #  Create the AlertDialog
        dialog = Adw.AlertDialog.new(
            "Error",       
            message         
        )
        
        # 'OK' button (response ID, label)
        dialog.add_response("ok", "OK")
        
    #    Set the default (accented) response
        dialog.set_default_response("ok")
   
        dialog.choose(self, None, lambda *args: None)


class ColorMyDesktopApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(
            application_id="io.github.schwarzen.colormydesktop",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,  
            **kwargs
        )
        
    def do_startup(self):
        Adw.Application.do_startup(self)



    def do_activate(self):
        # Store window as a class attribute to prevent garbage collection
        if not hasattr(self, 'win') or self.win is None:
            self.win = ThemeManager(application=self)
        self.win.present()

if __name__ == "__main__":
    # Use the class we defined above
    app = MyApp()
    # app.run returns the exit status which we pass to sys.exit
    sys.exit(app.run(sys.argv))
