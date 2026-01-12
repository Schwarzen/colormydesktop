#!/usr/bin/env python3
import os
import re
import subprocess
import threading
import shutil
import sys

BUNDLED_DATA = "/app/share/color-my-desktop"
HOST_DATA = os.path.expanduser("~/.local/share/Color-My-Desktop")



# Run this BEFORE any gi.repository imports


import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, GLib, Gio

# --- CONFIGURATION ---
SCSS_DIR = os.path.expanduser("~/.local/share/Color-My-Desktop/scss")
if os.environ.get("FLATPAK_ID"):
    # Inside Flatpak, the script is at /app/bin/
    BASH_SCRIPT = "/app/bin/color-my-desktop-backend"
else:
    # Native install location
    BASH_SCRIPT = os.path.expanduser("~/.local/bin/color-my-desktop")


preview_css_provider = Gtk.CssProvider()
Gtk.StyleContext.add_provider_for_display(
    Gdk.Display.get_default(),
    preview_css_provider,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
)

dynamic_color_provider = Gtk.CssProvider()
Gtk.StyleContext.add_provider_for_display(
    Gdk.Display.get_default(),
    dynamic_color_provider,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
)






class ThemeManager(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sync_flatpak_data()
            # sorting for default theme
        raw_themes = [f[1:-5] for f in os.listdir(SCSS_DIR) if f.startswith('_') and f.endswith('.scss')]
        raw_themes.sort()
        themes = ["Default"] + raw_themes
        
    def sync_flatpak_data(self):
        """Copies bundled templates from /app to the user's writable ~/.local"""
        import shutil
                    # Standard paths in a 2026 Flatpak environment
        SCSS_SOURCE = "/app/share/color-my-desktop/scss"
        SCSS_TARGET = os.path.expanduser("~/.local/share/Color-My-Desktop/scss")
        KDE_SOURCE = "/app/share/color-my-desktop/KDE"
        KDE_TARGET = os.path.expanduser("~/.local/share/Color-My-Desktop/KDE")
        
        os.makedirs(SCSS_TARGET, exist_ok=True)
        os.makedirs(KDE_TARGET, exist_ok=True)
        # Sync SCSS Folder
        
        if os.path.exists(SCSS_SOURCE):
            os.makedirs(SCSS_TARGET, exist_ok=True)
            for file in os.listdir(SCSS_SOURCE):
                shutil.copy(os.path.join(SCSS_SOURCE, file), SCSS_TARGET)

        # Sync KDE Folder
        if os.path.exists(KDE_SOURCE):
            os.makedirs(KDE_TARGET, exist_ok=True)
            # dirs_exist_ok=True is essential for 2026 updates
            shutil.copytree(KDE_SOURCE, KDE_TARGET, dirs_exist_ok=True)

        themes = [f[1:-5] for f in os.listdir(SCSS_DIR) if f.startswith('_') and f.endswith('.scss')]
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
     
    #    SETUP GROUPS
        self.load_group = Adw.PreferencesGroup(title="Profile Management")
        self.page.add(self.load_group)

        # CREATE DROPDOWN WIDGETS - EXISTING 
        self.theme_list = Gtk.StringList.new(themes)
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
        self.group.add(self.gnome_switch)        
        
                # --- KDE PLASMA TOGGLE ---
        self.plasma_switch = Adw.SwitchRow()
        self.plasma_switch.set_title("Apply to KDE Plasma")
        self.plasma_switch.set_active(False)
        self.group.add(self.plasma_switch)    
        
        # --- GTK4 TOGGLE ---
        self.gtk4_switch = Adw.SwitchRow()
        self.gtk4_switch.set_title("Apply to GTK4 apps")
        self.gtk4_switch.set_active(False)
        self.group.add(self.gtk4_switch) 
        
        
        # --- ZEN BROWSER TOGGLE ---
        self.zen_switch = Adw.SwitchRow()
        self.zen_switch.set_title("Apply to Zen Browser &amp; YouTube")
        self.zen_switch.set_active(False)
        self.group.add(self.zen_switch)
        
                # --- YOUTUBE TOGGLE ---
        self.youtube_switch = Adw.SwitchRow()
        self.youtube_switch.set_title("Apply to YouTube")
        self.youtube_switch.set_active(False)
        self.group.add(self.youtube_switch)
        
                # --- VESKTOP TOGGLE ---
        self.vesktop_switch = Adw.SwitchRow()
        self.vesktop_switch.set_title("Apply to Vesktop")
        self.vesktop_switch.set_active(False)
        self.group.add(self.vesktop_switch)





        
        # --- PAPIRUS ICON SYNC TOGGLE ---
        self.icon_sync_switch = Adw.SwitchRow()
        self.icon_sync_switch.set_title("Sync Papirus Icons with Theme")
        self.icon_sync_switch.set_active(False) # Default off
        self.group.add(self.icon_sync_switch)

                #  SWAP BUTTON (ActionRow) ---
        # This is a row that looks like a button but fits in a PreferencesGroup
        self.advanced_link = Adw.ActionRow(title="Advanced Options", selectable=False)
        self.advanced_link.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        self.advanced_link.set_activatable(True)
        self.group.add(self.advanced_link)
        # Connect the click event
        self.advanced_link.connect("activated", lambda row: self.nav_view.push(self.adv_nav_page))

        
        
        
                # Button             # Create the build button
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

                        # Helper to create a "Box" Button
        def add_grid_item(label, default_color, css_id):
      
            # CREATE THE SETTINGS PAGE FOR THIS ITEM
            sub_page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            
            # Sub-page Header
            sub_header = Adw.HeaderBar()
            sub_page_box.append(sub_header)
            
            # Sub-page Settings Group
            sub_pref_page = Adw.PreferencesPage()
            sub_page_box.append(sub_pref_page)
            sub_group = Adw.PreferencesGroup(title=f"{label} Customization")
            sub_page_box.append(sub_group)
            sub_pref_page.add(sub_group)
            
            #  SPECIFIC FOR GNOME-SHELL ONLY
            if css_id == "system_custom":
                # Create a special toggle, e.g., for Blur effect or Panel transparency
     
                # --- TOP BAR SECTION ---
                self.topbar_switch = Adw.SwitchRow(title="Custom Topbar Color")
                
                sub_group.add(self.topbar_switch)

                self.topbar_row = self.create_color_entry("Top Bar Color", "#3584e4","topbar-color")
                
                self.topbar_row.set_visible(False) # Hidden initially
                sub_group.add(self.topbar_row)

                # This links the toggle to the row's visibility
                self.topbar_switch.bind_property("active", self.topbar_row, "visible", 0)
                
                    
                # Save a reference to it on 'self' for your theme-building logic
                # setattr(self, "shell_blur_switch", shell_special_row)
                
                                # --- CLOCK SECTION ---
                self.clock_switch = Adw.SwitchRow(title="Custom Clock Color")
                sub_group.add(self.clock_switch)

                self.clock_row = self.create_color_entry("Clock Color", "#f9f9f9","clock-color")
               
                self.clock_row.set_visible(False) # Hidden initially
                sub_group.add(self.clock_row)

                # This links the toggle to the row's visibility
                self.clock_switch.bind_property("active", self.clock_row, "visible", 0)
                
                                # --- TRANSPARENCY TOGGLE ---
                self.trans_switch = Adw.SwitchRow()
                self.trans_switch.set_title("Enable Global Transparency")
                self.trans_switch.set_active(False) # Default solid
                sub_group.add(self.trans_switch)
        
            # SPECIFIC FOR NAUTILUS/FILES 
            if css_id == "nautilus_custom":
                #  ADD THE CONTROLS (Live-Syncing)
                # Main Toggle
                naut_switch = Adw.SwitchRow(title="Use Custom Main Color")
                sub_group.add(naut_switch)
                # Set the class variable directly to the widget for easy access
                setattr(self, f"{css_id}_switch", naut_switch)
                
                naut_row = self.create_color_entry("Main Hex", default_color, f"{css_id}-main")
                sub_group.add(naut_row)
                setattr(self, f"{css_id}_entry", naut_row)
                
                # Secondary Toggle
                naut_switch_sec = Adw.SwitchRow(title="Use Custom Secondary Color")
                sub_group.add(naut_switch_sec)
                setattr(self, f"{css_id}_sec_switch", naut_switch_sec)
                
                naut_row_sec = self.create_color_entry("Secondary Hex", default_color, f"{css_id}-sec")
                sub_group.add(naut_row_sec)
                setattr(self, f"{css_id}_naut_row_sec", naut_row_sec)

                # Visibility Bindings (The "Topbar Logic")
                naut_switch.bind_property("active", naut_row, "visible", 0)
                naut_switch_sec.bind_property("active", naut_row_sec, "visible", 0)

            # WRAP IN NAV PAGE
            sub_nav_page = Adw.NavigationPage.new(sub_page_box, label)
            self.nav_view.add(sub_nav_page)

            #  CREATE THE GRID BOX BUTTON
            box_button = Gtk.Button(width_request=140, height_request=140)
            box_button.add_css_class("flat")
            
            btn_layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            btn_layout.set_margin_top(10); btn_layout.set_margin_bottom(10)
            btn_layout.set_margin_start(10); btn_layout.set_margin_end(10)
            
            btn_layout.append(Gtk.Label(label=label, css_classes=["heading"]))
            status_label = Gtk.Label(label="Default", css_classes=["caption"])
            btn_layout.append(status_label)
            
            # Update status label live when switches change
            def update_status(*args):
                # Try to get the switches from 'self' using the dynamic names you set earlier
                main_sw = getattr(self, f"{css_id}_switch", None)
                sec_sw = getattr(self, f"{css_id}_sec_switch", None)
                
                # Check if they exist AND if they are active
                is_main_active = main_sw.get_active() if main_sw else False
                is_sec_active = sec_sw.get_active() if sec_sw else False
                
                # Update label
                status_label.set_label("Custom" if (is_main_active or is_sec_active) else "Default")
            
                        # Inside add_grid_item, after the conditional 'if' block
            if getattr(self, f"{css_id}_switch", None):
                self.__dict__[f"{css_id}_switch"].connect("notify::active", update_status)

            if getattr(self, f"{css_id}_sec_switch", None):
                self.__dict__[f"{css_id}_sec_switch"].connect("notify::active", update_status)

            # Run once initially to set the correct label on load
            update_status()


            box_button.set_child(btn_layout)
            box_button.connect("clicked", lambda b: self.nav_view.push(sub_nav_page))
            self.flowbox.append(box_button)
            
            # Store these as attributes if you need to access them for building
            # Example: self.adv_toggles[css_id] = toggle

        #  Add items to your grid
        add_grid_item("Nautilus", "#88c0d0", "nautilus_custom")
        add_grid_item("Gnome-shell", "#bd93f9", "system_custom")
        

        # Wrap it in a NavigationPage
        self.adv_nav_page = Adw.NavigationPage.new(self.adv_page_content, "Advanced")
        self.nav_view.add(self.adv_nav_page)
        
        initial_css = ""
        for cid, hcolor in self.current_colors.items():
            initial_css += f"#{cid}-preview {{ background-color: {hcolor}; border-radius: 6px; min-width: 24px; min-height: 24px; }}\n"
        dynamic_color_provider.load_from_string(initial_css)
        
        self.nav_view.push(self.main_nav_page)
        
        
    def open_small_window(self, title, default_color, css_id): 
        # Create the sub-window
        popup = Adw.Window(transient_for=self)
        popup.set_default_size(320, 250)
        popup.set_title(title)
        
        #  Layout container
        # Using a Box with margins for a clean Libadwaita look
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_top(18)
        content_box.set_margin_bottom(18)
        content_box.set_margin_start(18)
        content_box.set_margin_end(18)
        
  
    

    def is_valid_hex(self, color):
        # Strip whitespace to avoid simple input errors
        color = color.strip()
        
        # 1. Matches SCSS variables (e.g., $primary-color)
        if re.match(r'^\$[A-Za-z0-9_-]+$', color):
            return True
        
        # 2. Matches your original Hex requirements (#RRGGBB or RRGGBB)
        # Note: Gdk.RGBA.parse also handles #hex, but your original regex 
        # handles hex without the '#' prefix, which Gdk does not.
        if re.match(r'^#?([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', color):
            return True

        # 3. Fallback to Gdk.RGBA.parse (Handles rgba(0,0,0,0), hsl, names, etc.)
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

        # 1. VISUAL VALIDATION ONLY (On Leave)
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
                
                dynamic_color_provider.load_from_string(full_css)
            else:
                pass


        row.connect("notify::text", update_preview)
        return row


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
            "1" if self.icon_sync_switch.get_active() else "0",  # ${13}
            n_main_val, # $14
            "#3584e4",  # $15 (Datemenu fallback)
            n_sec_val,  # $16
            "1" if self.gnome_switch.get_active() else "0", # $17
            "1" if self.gtk4_switch.get_active() else "0", # $18
            "1" if self.plasma_switch.get_active() else "0", # $19
            "1" if self.youtube_switch.get_active() else "0", # 20
            "1" if self.vesktop_switch.get_active() else "0", # 21
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


class MyApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.github.schwarzen.colormydesktop",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
    
    def do_startup(self):
        Adw.Application.do_startup(self)

        # SOURCE: Bundle inside the Flatpak
        BUNDLED_DATA = "/app/share/color-my-desktop"
        
        # DESTINATION: The shared host folder mapped via --filesystem=xdg-data/Color-My-Desktop:create
        # In a Flatpak, XDG_DATA_HOME is the reliable way to reach ~/.local/share
        xdg_data = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        HOST_DATA = os.path.join(xdg_data, "Color-My-Desktop")

        # Create sub-paths to verify
        src_scss = os.path.join(BUNDLED_DATA, "scss")
        dest_scss = os.path.join(HOST_DATA, "scss")
        src_kde = os.path.join(BUNDLED_DATA, "KDE")
        dest_kde = os.path.join(HOST_DATA, "KDE")

        # Check if internal bundle exists
        if not os.path.exists(src_scss):
            print(f"Error: Bundled source {src_scss} not found in Flatpak.")
            return

        # Perform the copy if the host folder is missing
        if not os.path.exists(dest_scss):
            try:
                # Ensure parent HOST_DATA exists (Flatpak should create it, but let's be safe)
                os.makedirs(HOST_DATA, exist_ok=True)
                
                # Copy directories
                shutil.copytree(src_scss, dest_scss, dirs_exist_ok=True)
                shutil.copytree(src_kde, dest_kde, dirs_exist_ok=True)
                print(f"Success: Copied assets to {HOST_DATA}")
            except Exception as e:
                print(f"Failed to copy files: {e}")

                # We continue anyway to try and open the window, 
                # or you can sys.exit(1) here if it's strictly required

    def do_activate(self):
        # 3. This is where your GUI logic starts
        # ThemeManager must be your Gtk.Window / Adw.Window subclass
        self.win = ThemeManager(application=self)
        self.win.present()

if __name__ == "__main__":
    # Use the class we defined above
    app = MyApp()
    # app.run returns the exit status which we pass to sys.exit
    sys.exit(app.run(sys.argv))
