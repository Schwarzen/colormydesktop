#!/usr/bin/env python3
# Copyright 2026 Schwarzen
# SPDX-License-Identifier: Apache-2.0

import os
import re
import subprocess
import threading
import sys
import shutil
import json



import gi

from gi.repository import Gtk, Adw, Gdk, GLib, Gio, GObject



from .dialogs import DialogMixin
from .advancedpref import AdvancedMixin
# --- CONFIGURATION ---




if os.environ.get("FLATPAK_ID"):
    # Inside Flatpak, the script is at /app/bin/
    BASH_SCRIPT = "/app/bin/color-my-desktop-backend"
    SCSS_DIR = os.path.expanduser("~/.var/app/io.github.schwarzen.colormydesktop/data/scss")
    PYTHON_DIR = "/app/bin/colormydesktop"
else:
    # Native install location
    BASH_SCRIPT = os.path.expanduser("~/.local/bin/color-my-desktop-backend")
    SCSS_DIR = os.path.expanduser("~/.local/share/Color-My-Desktop/scss")
    PYTHON_DIR = os.path.expanduser("colormydesktop")


class ThemeManager(Adw.ApplicationWindow, DialogMixin, AdvancedMixin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.portal_widgets = {}
        self.color_entries = {}
        self.setup_css_providers()
        self.last_manually_enterd_zen_path = ""
        self.load_persistent_settings()
        self.setup_user_data()
        self.load_all_cached_portals()
        self.is_plasma_refresh_ready()
        self.is_gnome_refresh_ready()
        
        


        if os.path.exists(SCSS_DIR):
            raw_themes = [f[1:-5] for f in os.listdir(SCSS_DIR) if f.startswith('_') and f.endswith('.scss')]
            raw_themes.sort()
            self.themes = ["Default"] + raw_themes
        else:
            print("CRITICAL: SCSS_DIR missing even after setup_user_data")
            self.themes = ["Default"]



        self.current_colors = {} 
        self.status_labels = {}
    
        self.nautilus_active = False
        self.nautilus_hex_var = ""
        self.datemenu_active = False
        self.datemenu_hex_var = ""
     
        self.set_title("Color My Desktop")
        self.set_default_size(1200, 800)

   
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
        self.load_group.set_name("load-group-id")
        self.page.add(self.load_group)

        # CREATE DROPDOWN WIDGETS - EXISTING 
        self.theme_list = Gtk.StringList.new(self.themes)
        self.combo_row = Adw.ComboRow(title="Load Existing Profile")
        self.combo_row.set_model(self.theme_list)
        self.combo_row.set_selected(0) # Force "Default" selection
        self.combo_row.connect("notify::selected", self.on_theme_select)

                # --- NEW PROFILE BUTTON ---
        new_profile_btn = Gtk.Button.new_from_icon_name("list-add-symbolic")
        new_profile_btn.set_valign(Gtk.Align.CENTER)
        new_profile_btn.add_css_class("flat")
        new_profile_btn.set_tooltip_text("Start New Profile")
        
        # --- DELETE PROFILE BUTTON ---
        self.delete_profile_btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        self.delete_profile_btn.set_valign(Gtk.Align.CENTER)
        self.delete_profile_btn.add_css_class("flat")
        self.delete_profile_btn.add_css_class("error") # Makes it red on hover in some themes
        self.delete_profile_btn.set_tooltip_text("Delete Selected Profile")
        self.delete_profile_btn.set_visible(False)
        
        # Hides the built-in arrow so only your button is visible


        

        # Connect the logic
        def on_new_profile_clicked(button):
            self.on_window_width_changed()
            self.combo_row.set_selected(0) 
            self.name_row.set_text("New Profile")
            
            # FIX: Reveal the ROW, not just the button inside it
            self.bash_trigger_row.set_visible(True)


        def on_delete_clicked(button):
            selected_index = self.combo_row.get_selected()
            selected_theme = self.theme_list.get_string(selected_index)

            if selected_index == 0 or selected_theme == "Default":
                # Don't delete the factory default
                return

            # Create a confirmation dialog
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading=f"Delete Profile?",
                body=f"Are you sure you want to permanently delete '{selected_theme}'?"
            )
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("delete", "Delete")
            dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.set_default_response("cancel")

            dialog.connect("response", self.on_delete_confirm, selected_theme)
            dialog.present()

        # Clicking this button triggers the row's internal dropdown

        new_profile_btn.set_margin_end(4)
        self.delete_profile_btn.set_margin_end(10) # Larger margin for the last button
        new_profile_btn.connect("clicked", on_new_profile_clicked)
        self.combo_row.add_suffix(new_profile_btn)
        self.delete_profile_btn.connect("clicked", on_delete_clicked)
        self.combo_row.add_suffix(self.delete_profile_btn)
        self.combo_row.set_activatable_widget(self.combo_row)

        


        self.load_group.add(self.combo_row)



        # CONNECT SIGNALS LAST
        self.combo_row.connect("notify::selected", self.on_theme_select)
        




        # COLOR GROUP (The Hex Entries) ---
        self.color_group = Adw.PreferencesGroup()
        self.color_group.set_title("Theme Colors")
        
        
        self.name_row = Adw.EntryRow(
            title="Profile Name", 
            text="Default"
        )
        
        self.color_group.add(self.name_row)
        # Name sanitize
        def on_name_insert_text(editable, new_text, length, position):
            # Added a space inside the brackets [ ]
            if not re.match(r'^[a-zA-Z0-9_ -]*$', new_text):
                editable.stop_emission_by_name("insert-text")

        self.name_row.get_delegate().connect("insert-text", on_name_insert_text)


        

        self.primary_row = self.create_color_entry("Primary", "#246cc5", "primary", show_magic=True)
        self.color_group.add(self.primary_row)
        self.secondary_row = self.create_color_entry("Secondary", "#241f31", "secondary")
        self.color_group.add(self.secondary_row)
        self.tertiary_row = self.create_color_entry("Accent Color", "#1e1e1e", "tertiary")
        self.color_group.add(self.tertiary_row)

        # --- 1. MAIN TEXT ROW ---
        self.text_row = self.create_color_entry("Text Color", "#f9f9f9", "text")
        self.color_group.add(self.text_row)


        self.setup_color_watchdog()
        # --- 2. CLICKABLE CONTRAST ROW ---
        self.contrast_info_row = Adw.ActionRow(title="Contrast Check")
        self.contrast_info_row.set_subtitle("Contrast: 21.0:1 — ✅ Perfect")
        self.contrast_info_row.set_activatable(True) # Makes the whole row clickable
        self.contrast_info_row.add_css_class("contrast-sub-row") # For the CSS trick later

        # Add a "details" arrow icon to the end
        self.contrast_info_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))

        # Connect the click to open the "Fix" Dialog
        self.contrast_info_row.connect("activated", self.on_show_contrast_dialog)

        self.color_group.add(self.contrast_info_row)



        # --- HIDDEN BASH TRIGGER ROW ---
        # Using an ActionRow makes it look like a standard part of the list
        self.bash_trigger_row = Adw.ActionRow(title="Save new color profile")
        self.bash_trigger_row.set_subtitle("Save these custom hex colors to a new file")
        self.bash_trigger_row.set_visible(False) # Hidden by default

        self.bash_trigger_btn = Gtk.Button(label="Save")
        self.bash_trigger_btn.set_valign(Gtk.Align.CENTER)
        self.bash_trigger_btn.add_css_class("suggested-action")

        # Connect to your bash function
        self.bash_trigger_btn.connect("clicked", self.on_configure_clicked)

        self.bash_trigger_row.add_suffix(self.bash_trigger_btn)
        self.color_group.add(self.bash_trigger_row)

        # Connect to the selection change signal
        self.combo_row.connect("notify::selected", self.on_theme_select)
        # --- PREVIEW TOGGLE ROW ---
        self.preview_switch_row = Adw.SwitchRow(title="Show Live Preview")
        self.preview_switch_row.set_subtitle("Visualize theme changes on a mockup")
        self.preview_switch_row.set_active(False) 

        # Connect the toggle logic
        self.preview_switch_row.connect("notify::active", self.on_preview_toggled)

        self.color_group.add(self.preview_switch_row)
        

        
        self.preview_group = Adw.PreferencesGroup()
        self.preview_group.set_title("Preview")
        


        # --- MOCKUP WRAPPER ---
        self.mockup_wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.mockup_wrapper.set_name("mockup-wrapper")
        self.mockup_wrapper.set_size_request(425, 100)
        self.mockup_wrapper.set_overflow(Gtk.Overflow.HIDDEN) 


 

        # --- MOCKUP IMAGE ---
        svg_file = Gio.File.new_for_path(f"{PYTHON_DIR}/preview-symbolic.svg")
        # Set the paintable size to match what you want to see
        self.mockup_paintable = Gtk.IconPaintable.new_for_file(svg_file, 1200, -1)

        self.mockup_image = Gtk.Image.new_from_paintable(self.mockup_paintable)
        # Ensure pixel_size matches the paintable 
        self.mockup_image.set_pixel_size(425)
        self.mockup_image.set_hexpand(True)

                # Remove spacing between children in the box
        self.mockup_wrapper.set_spacing(0)

        # Ensure the image has no internal margins
      
       

        # Optional: If the PreferencesGroup is adding space at the top


        self.mockup_image.set_name("mockup-preview-image")

        self.mockup_wrapper.append(self.mockup_image)
        self.preview_group.set_visible(False)
        self.preview_group.add(self.mockup_wrapper)
        
        
        # --- ADAPTIVE CONTAINER ---
        self.adaptive_group = Adw.PreferencesGroup()
        self.page.add(self.adaptive_group)

        #  The main horizontal split (only used in wide mode)
        self.split_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        self.adaptive_group.add(self.split_container)

        # LEFT SIDE: Settings + the Bottom Slot
        self.settings_side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.settings_side.set_size_request(400, -1)
        self.settings_side.append(self.color_group)

        # This is where the preview goes when the window is NARROW
        self.bottom_preview_slot = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.settings_side.append(self.bottom_preview_slot)

        #  RIGHT SIDE: The Side Slot
        #  create a box to hold the preview on the right
        self.side_preview_slot = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.side_preview_slot.set_name("preview-side-id")
        self.side_preview_slot.set_hexpand(True)

        # Initially place the preview in the Side Slot (Wide mode default)
        self.side_preview_slot.append(self.preview_group)

        # Pack everything into the main split
        self.split_container.append(self.settings_side)
        self.split_container.append(self.side_preview_slot)



        # Connect width monitor for the re-parenting logic
    
        self.is_currently_wide = None # Track state to prevent redundant runs
        self.connect("notify::width", lambda *args: self.on_window_width_changed())

        self.connect("notify::default-width", lambda *args: self.on_window_width_changed())
        
        self.connect("notify::maximized", lambda *args: self.on_window_width_changed())
        self.connect("notify::width", lambda *args: self.scale_mockup())

        self.connect("notify::default-width", lambda *args: self.scale_mockup())
        
        self.connect("notify::maximized", lambda *args: self.scale_mockup())


        
        
        # Global Options Group
      
        self.group.set_title("Select themes to generate/apply")
        self.page.add(self.group)
        


        # --- GNOME SHELL TOGGLE ---
        self.gnome_switch = Adw.SwitchRow()
        self.gnome_switch.set_title("gnome-shell")
        self.gnome_switch.set_subtitle("Refresh")
        self.gnome_switch.set_active(False)
        
        # Add it to the group IMMEDIATELY to keep its position at the top
        self.group.add(self.gnome_switch)

        # --- THE INVISIBLE CLICK LOGIC ---
        # We use a gesture instead of an overlay to avoid breaking the UI layout
        click_gesture = Gtk.GestureClick.new()
        
        def on_subtitle_clicked(gesture, n_press, x, y):
            # Check if the click is in the bottom-left area (the subtitle area)
            # Row height is usually ~60px, so y > 30 is the bottom half
            if y > 30 and 120 < x < 300:
                self.show_gnome_setup_dialog()

        click_gesture.connect("released", on_subtitle_clicked)
        self.gnome_switch.add_controller(click_gesture)
                # Add this after the gesture code
        cursor_controller = Gtk.EventControllerMotion.new()
        def on_motion(controller, x, y):
            if y > 30 and 120 < x < 300:
                self.gnome_switch.set_cursor(Gdk.Cursor.new_from_name("pointer", None))
            else:
                self.gnome_switch.set_cursor(None)
        
        cursor_controller.connect("motion", on_motion)
        self.gnome_switch.add_controller(cursor_controller)


        # 6. Add the OVERLAY to your group, not the switch
        
              
        # Connect the signal to a handler that checks the specific folder
        self.gnome_handler_id = self.gnome_switch.connect(
            "notify::active", 
            lambda widget, pspec: self.on_feature_toggled(widget, pspec, ["~/.local/share/themes"], "GNOME")
        )
        self.add_folder_action(self.gnome_switch, "GNOME", ["~/.local/share/themes"])
         # For GNOME path arg
        self.gnome_path = self.get_path_argument("~/.local/share/themes")
        
  
        

        # --- KDE PLASMA TOGGLE ---
        self.plasma_switch = Adw.SwitchRow()
        self.plasma_switch.set_title("KDE Plasma")
        self.plasma_switch.set_subtitle("Refresh")
        self.plasma_switch.set_active(False)
        
        # Add it to the group
        self.group.add(self.plasma_switch)

        # --- THE INVISIBLE CLICK LOGIC (PLASMA) ---
        plasma_click_gesture = Gtk.GestureClick.new()
        
        def on_plasma_subtitle_clicked(gesture, n_press, x, y):
            # Adjusted x range (120 to 350) for the longer KDE text
            if y > 30 and 120 < x < 350:
                # Assuming this navigates or shows the KDE setup
                self.show_plasma_setup_dialog()

        plasma_click_gesture.connect("released", on_plasma_subtitle_clicked)
        self.plasma_switch.add_controller(plasma_click_gesture)

        # --- CURSOR LOGIC (PLASMA) ---
        plasma_cursor_controller = Gtk.EventControllerMotion.new()
        def on_plasma_motion(controller, x, y):
            if y > 30 and 120 < x < 350:
                self.plasma_switch.set_cursor(Gdk.Cursor.new_from_name("pointer", None))
            else:
                self.plasma_switch.set_cursor(None)
        
        plasma_cursor_controller.connect("motion", on_plasma_motion)
        self.plasma_switch.add_controller(plasma_cursor_controller)

        # Connect the signal to a handler that checks the specific folder
        plasma_folders = ["~/.local/share/plasma", "~/.local/share/color-schemes"]

        #  Use the list in the toggle connection
        self.plasma_handler_id = self.plasma_switch.connect(
            "notify::active", 
            lambda widget, pspec: self.on_feature_toggled(
                widget, 
                pspec, 
                plasma_folders, 
                "KDE Plasma"
            )
        )

        #  Use the SAME list in the folder action helper
        # This ensures the dialog shows both "Path 1" and "Path 2"
        self.add_folder_action(self.plasma_switch, "KDE Plasma", plasma_folders)
        # For Plasma path arg
        self.plasma_path = self.get_path_argument("~/.local/share/plasma")
        self.schemes_path = self.get_path_argument("~/.local/share/color-schemes")
        self.group.add(self.plasma_switch)
        
        # --- GTK4 TOGGLE ---
        self.gtk4_switch = Adw.SwitchRow()
        self.gtk4_switch.set_title("GTK4 apps")
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
        current_zen_path = getattr(self, "last_manually_entered_zen_path", "~/.zen/*/chrome")
        self.zen_switch = Adw.SwitchRow()
        self.zen_switch.set_title("Zen Browser")
        self.zen_switch.set_active(False)
                # Connect the signal to a handler that checks the specific folder
        self.zen_handler_id = self.zen_switch.connect(
            "notify::active", 
            lambda widget, pspec: self.on_feature_toggled(
                widget, 
                pspec, 
                [getattr(self, "last_manually_entered_zen_path", "~/.zen/*/chrome")],  
                "Zen"
            )
        )
        self.add_folder_action(self.zen_switch, "Zen" , [current_zen_path])
         # For zen path arg
        self.zen_path = self.get_path_argument(current_zen_path)
        self.group.add(self.zen_switch)


        
        # --- YOUTUBE TOGGLE ---
        self.youtube_switch = Adw.SwitchRow()
        self.youtube_switch.set_title("YouTube (Zen Browser)")
        self.youtube_switch.set_active(False)
        self.youtube_handler_id = self.youtube_switch.connect(
            "notify::active", 
            lambda widget, pspec: self.on_feature_toggled(
                widget, 
                pspec, 
                [getattr(self, "last_manually_entered_zen_path", "~/.zen/*/chrome")],  
                "Zen"
            )
        )
        self.add_folder_action(self.youtube_switch, "Zen" , [current_zen_path])
         # For zen path arg
        self.zen_path = self.get_path_argument(current_zen_path)
        self.group.add(self.youtube_switch)


        # --- VESKTOP TOGGLE ---
        self.vesktop_switch = Adw.SwitchRow()
        self.vesktop_switch.set_title("Vesktop")
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
        self.advanced_link.connect("activated", self.open_advanced_options)

        
        
        
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
        self.add_grid_item("KDE", "#bd93f9", "KDE_custom")
        
        

        # Wrap it in a NavigationPage
        self.adv_nav_page = Adw.NavigationPage.new(self.adv_page_content, "Advanced")
        self.nav_view.add(self.adv_nav_page)
        
        initial_css = ""
        for cid, hcolor in self.current_colors.items():
            initial_css += f"#{cid}-preview {{ background-color: {hcolor}; border-radius: 6px; min-width: 24px; min-height: 24px; }}\n"
        self.dynamic_color_provider.load_from_string(initial_css)
        
        # --- AT THE END OF YOUR __init__ ---

        # 1. Fill the current_colors registry with the default values from the entries
        if not hasattr(self, 'current_colors'):
            self.current_colors = {}

        for css_id, entry_widget in self.color_entries.items():
            # Get the text currently in the box (the default hex you passed)
            hex_val = entry_widget.get_text().strip()
            if hex_val:
                # Ensure it has a #
                clean_hex = hex_val if hex_val.startswith('#') else f"#{hex_val}"
                self.current_colors[css_id] = clean_hex

        # 2. Now call the refresh. It will find the colors in self.current_colors
        self.update_mockup_css()
        self.on_window_width_changed()
        self.check_gnome_refresh_status()
        self.initial_status()

        

        
        
        self.nav_view.push(self.main_nav_page)
        # Connect to the 'popped' signal of the NavigationView
        self.nav_view.connect("popped", self.on_nav_popped)

        self.on_window_width_changed()

    def setup_subtitle_links(self):
        # 1. Use your search function to find the label
        gnome_label = self.find_label_by_text(self.gnome_switch, "Refresh")
        
        if gnome_label:
            # 2. Create a 'Gesture' to catch clicks anywhere on that label
            click_gesture = Gtk.GestureClick.new()
            # 3. Connect the gesture to your function
            click_gesture.connect("released", lambda gesture, n, x, y: self.show_gnome_setup_dialog())
            # 4. Add the gesture to the label
            gnome_label.add_controller(click_gesture)
            
            # 5. Make the label look like a link manually
            gnome_label.set_markup("<span color='blue' underline='single'>Click to Install</span>")

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
   

    def scale_mockup(self):
        # 1. Get the current window width
        width = self.get_width()
        
        # 2. Logic for large screens
        if width >= 1200:
            
            self.mockup_image.set_pixel_size(600)
            
            # 2. SIZE AUTHORITY: Tell the image widget to only 'occupy' 100px
            # This is the "Magic" line that lets the wrapper shrink.
            
            
            
           
            self.mockup_image.set_margin_top(-120)
            
            self.mockup_wrapper.set_size_request(600, 100)
            
            
            
      



            
        # 3. Logic for smaller screens 
        else:
            self.mockup_wrapper.set_size_request(425, 100)
            self.mockup_image.set_pixel_size(425)
            self.mockup_image.set_margin_top(-70)
            self.mockup_image.set_margin_bottom(-60)

    def initial_status(self):
        accent_blue = "#3584e4"
        
        if hasattr(self, 'refresh_switch'):
            toggled = self.refresh_switch.get_active()
        else:
            toggled = False
            
        # ADD THE 'f' HERE -----------------------------------------vv
        switch_text = "Auto refresh active" if toggled else f"Auto refresh inactive - (<span color='{accent_blue}' underline='single'>See advanced GNOME options</span>)"
        self.gnome_switch.set_subtitle(switch_text)
        self.gnome_switch.set_use_markup(True)
        
        if hasattr(self, 'plasma_refresh_switch'):
            toggled = self.plasma_refresh_switch.get_active()
        else:
            toggled = False
            
        # ADD THE 'f' HERE ------------------------------------------------vv
        plasma_switch_text = "Auto refresh active" if toggled else f"Auto refresh inactive - (<span color='{accent_blue}' underline='single'>See advanced KDE options</span>)"
        self.plasma_switch.set_subtitle(plasma_switch_text)
        self.plasma_switch.set_use_markup(True)

            

    def on_nav_popped(self, nav_view, page):
        
        
        if page == self.adv_nav_page:
            print("Left Advanced page, syncing status...")
            
            accent_blue = "#3584e4"
            
            if hasattr(self, 'refresh_switch'):
                toggled = self.refresh_switch.get_active()
            else:
                toggled = False
                
            # ADD THE 'f' HERE -----------------------------------------vv
            switch_text = "Auto refresh active" if toggled else f"Auto refresh inactive - (<span color='{accent_blue}' underline='single'>See advanced GNOME options</span>)"
            self.gnome_switch.set_subtitle(switch_text)
            self.gnome_switch.set_use_markup(True)
            
            if hasattr(self, 'plasma_refresh_switch'):
                toggled = self.plasma_refresh_switch.get_active()
            else:
                toggled = False
                
            # ADD THE 'f' HERE ------------------------------------------------vv
            plasma_switch_text = "Auto refresh active" if toggled else f"Auto refresh inactive - (<span color='{accent_blue}' underline='single'>See advanced KDE options</span>)"
            self.plasma_switch.set_subtitle(plasma_switch_text)
            self.plasma_switch.set_use_markup(True)


        
    def open_advanced_options(self, row):
        # Trigger the sync for both GNOME and Plasma
        # This ensures the subtitles and switches are accurate
        

        self.nav_view.push(self.adv_nav_page)

        
    def check_gnome_refresh_status(self):
        is_flatpak = os.path.exists('/.flatpak-info')
        
        if not is_flatpak:
            ready = True
            status_text = "Status: Active (Native Mode)"
        else:
            ready = self.is_gnome_refresh_ready()
            status_text = "Ready" if ready else "Not Setup - Requires one time install"

        if hasattr(self, 'gnome_refresh_row'):
            self.gnome_refresh_row.set_subtitle(status_text)
            
        if hasattr(self, 'refresh_switch') and hasattr(self, 'gnome_handler_id'):
            self.refresh_switch.handler_block(self.gnome_handler_id)
            self.refresh_switch.set_active(ready)
            self.refresh_switch.handler_unblock(self.gnome_handler_id)
                
        return ready

    def check_plasma_refresh_status(self):
        # 1. DETECT ENVIRONMENT
        is_flatpak = os.path.exists('/.flatpak-info')
        
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
        if hasattr(self, 'plasma_refresh_row'):
            self.plasma_refresh_row.set_subtitle(status_text)
            
        # 4. UPDATE THE SWITCH
        # Use the specific Plasma switch and handler ID
        if hasattr(self, 'plasma_refresh_switch') and hasattr(self, 'plasma_handler_id'):
            self.plasma_refresh_switch.handler_block(self.plasma_handler_id)
            self.plasma_refresh_switch.set_active(ready)
            self.plasma_refresh_switch.handler_unblock(self.plasma_handler_id)
            
            print(f"DEBUG: Plasma Row updated to {status_text} (Flatpak: {is_flatpak})")
                
        return ready





        
    def is_gnome_refresh_ready(self):
        # 1. Check Systemd Portal Path
        host_path = "~/.config/systemd/user"
        portal_path = getattr(self, f"active_portal_{self.get_safe_key(host_path)}", None)
        if not portal_path:
            portal_path = self.load_cached_portal_path(host_path)
        
        if not portal_path or not os.path.exists(portal_path):
            return False

        # 2. Check for the two GNOME refresher files
        path_exists = os.path.isfile(os.path.join(portal_path, "gnome-refresher.path"))
        service_exists = os.path.isfile(os.path.join(portal_path, "gnome-refresher.service"))
        if not (path_exists and service_exists):
            return False

        # 3. Check App Data Trigger
        # For GNOME, we look in the persistent data folder defined in the .path unit
        trigger_file = os.path.expanduser("~/.var/app/io.github.schwarzen.colormydesktop/data/colormydesktop/refresh.trigger")
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
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        
        # Start the chooser in the home config dir to help the user find it
        chooser.set_current_folder(Gio.File.new_for_path(os.path.expanduser("~/.config/systemd/user")))

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

                        with open(src, 'rb') as f_src:
                            content = f_src.read()
                        
                        g_file_dst = Gio.File.new_for_path(dst)
                        g_file_dst.replace_contents(
                            content, None, False, 
                            Gio.FileCreateFlags.REPLACE_DESTINATION, None
                        )

                    trigger_path = os.path.expanduser("~/.var/app/io.github.schwarzen.colormydesktop/data/colormydesktop/refresh.trigger")
                    
                    # Ensure the directory structure exists
                    os.makedirs(os.path.dirname(trigger_path), exist_ok=True)
                    
                    # Create the file if it doesn't exist
                    if not os.path.exists(trigger_path):
                        with open(trigger_path, 'w') as f:
                            f.write("trigger") # Initial content
                        print(f"Trigger file created at: {trigger_path}")
                    # 2. PERSISTENCE: Link host path to the portal path
                    self.save_portal_path(host_config_path, sandboxed_path)
                    
                    # 3. SESSION DATA: Update the safe_key attribute
                    safe_key = self.get_safe_key(host_config_path)
                    setattr(self, f"active_portal_{safe_key}", sandboxed_path)


                    # 4. REFRESH UI: Update the GNOME setup dialog
                    self.show_gnome_setup_dialog()
                    self.toast_overlay.add_toast(Adw.Toast.new("GNOME Installer Successful!"))
                    
                except Exception as e:
                    print(f"Failed to copy GNOME files: {e}")
                    self.toast_overlay.add_toast(Adw.Toast.new("Installation Failed! Check console."))
            
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
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        
        chooser.set_current_folder(Gio.File.new_for_path(os.path.expanduser("~/.config/systemd/user")))

        def on_response(dialog, response_id):
            if response_id == Gtk.ResponseType.ACCEPT:
                target_folder_file = dialog.get_file()
                sandboxed_path = target_folder_file.get_path() 

                try:
                    # 1. Copy the files using your Gio logic
                    for filename in files_to_copy:
                        src = os.path.join(internal_path, filename)
                        dst = os.path.join(sandboxed_path, filename)
                        
                        with open(src, 'rb') as f_src:
                            content = f_src.read()
                        
                        g_file_dst = Gio.File.new_for_path(dst)
                        g_file_dst.replace_contents(
                            content, None, False, 
                            Gio.FileCreateFlags.REPLACE_DESTINATION, None
                        )

                    trigger_path = os.path.expanduser("~/.var/app/io.github.schwarzen.colormydesktop/data/colormydesktop/plasma-refresh.trigger")
                    
                    # Ensure the directory structure exists
                    os.makedirs(os.path.dirname(trigger_path), exist_ok=True)
                    
                    # Create the file if it doesn't exist
                    if not os.path.exists(trigger_path):
                        with open(trigger_path, 'w') as f:
                            f.write("trigger") # Initial content
                        print(f"Trigger file created at: {trigger_path}")
                    # 2. PERSISTENCE: Save the link between the host path and portal path
                    # This ensures the status boxes turn green after restart
                    self.save_portal_path(host_config_path, sandboxed_path)
                    
                    # 3. SESSION DATA: Update the safe_key attribute
                    safe_key = self.get_safe_key(host_config_path)
                    setattr(self, f"active_portal_{safe_key}", sandboxed_path)

                    # 4. REFRESH UI: Re-run the setup dialog to update icons to green
                    self.show_plasma_setup_dialog()
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
            text="Units Installed Successfully"
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
            dialog.set_secondary_text("Command copied to clipboard! You can now paste it into your terminal.")
            dialog.run()

        dialog.destroy()






    def trigger_refresh(self):
        # 1. Check if the feature is even enabled in the UI
        # This prevents accidental triggers from other parts of the code
        if not hasattr(self, 'plasma_refresh_switch') or not self.plasma_refresh_switch.get_active():
            return

        
        # 1. Check for the Flatpak sandbox marker
        is_flatpak = os.path.exists('/.flatpak-info')

        if is_flatpak:
            # --- FLATPAK LOGIC: Touch the trigger file ---
            trigger_path = os.path.expanduser("~/.var/app/io.github.schwarzen.colormydesktop/data/colormydesktop/plasma-refresh.trigger")
            try:
                os.makedirs(os.path.dirname(trigger_path), exist_ok=True)
                with open(trigger_path, 'a'):
                    os.utime(trigger_path, None)
                print(f"Flatpak: Refresh signal sent to {trigger_path}")
            except Exception as e:
                print(f"Flatpak Trigger Error: {e}")
        else:
            # --- NATIVE LOGIC: Run the command directly ---
            try:
                # We use the same logic from your systemd service for consistency
                cmd = "/usr/bin/bash -c '/usr/bin/plasma-apply-colorscheme BreezeDark && sleep 0.5 && /usr/bin/plasma-apply-colorscheme Color-My-Desktop-Scheme'"
                subprocess.Popen(cmd, shell=True)
                print("Native: Direct Plasma refresh command executed.")
            except Exception as e:
                print(f"Native Refresh Error: {e}")















        

    def get_host_script_uri(self):
        # 1. Get the actual username from the environment
        # Inside Flatpak, 'USER' is usually passed through
        user = os.environ.get("USER") or os.path.basename(os.path.expanduser("~"))
        
        # 2. Construct the path as the HOST sees it
        # Flatpak's internal XDG_DATA_HOME (~/.local/share) maps to this on the host:
        app_id = "io.github.schwarzen.colormydesktop"
        host_path = f"/home/{user}/.var/app/{app_id}/data/setup_refresh.sh"
        
        # 3. Convert to a proper URI
        return f"file://{host_path}"
        
    def on_setup_clicked(self, button=None):
        # 1. Use the INTERNAL path (sandbox-local)
        # The portal handles the mapping to the host automatically via the File Descriptor
        xdg_data = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        internal_path = os.path.join(xdg_data, "setup_refresh.sh")
        
        print(f"Opening local file via portal: {internal_path}")

        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        proxy = Gio.DBusProxy.new_sync(
            bus, Gio.DBusProxyFlags.NONE, None,
            "org.freedesktop.portal.Desktop",
            "/org/freedesktop/portal/desktop",
            "org.freedesktop.portal.OpenURI", # Interface remains the same
            None
        )

        try:
            # 2. Open the file to get a File Descriptor
            # 'O_RDONLY' is enough to run/execute
            f = os.open(internal_path, os.O_RDONLY)
            
            # 3. Use the 'OpenFile' method instead of 'OpenURI'
            # Signature: (parent_window 's', file_descriptor 'h', options 'a{sv}')
            proxy.call_sync(
                "OpenFile",
                GLib.Variant('(sha{sv})', ("", f, GLib.Variant('a{sv}', {}))),
                Gio.DBusCallFlags.NONE, -1, None
            )
            
            # Always close your local FD handle after the D-Bus call
            os.close(f)
            print("OpenFile request sent successfully.")
            
        except Exception as e:
            print(f"Portal failed to open file: {e}")






        





    def save_portal_path(self, folder_path, portal_path):
        # Use the app's specific config directory to ensure it's writable
        config_dir = GLib.get_user_data_dir()
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            
        config_file = os.path.join(config_dir, "portal_cache.json")
        cache = {}
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    cache = json.load(f)
            except Exception:
                cache = {}
        
        cache[folder_path] = portal_path
        with open(config_file, 'w') as f:
            json.dump(cache, f)

    def load_cached_portal_path(self, folder_path):
        config_file = os.path.expanduser("~/.config/portal_cache.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
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
            with open(config_file, 'r') as f:
                cache = json.load(f)
                for host_path, portal_path in cache.items():
                    safe_key = self.get_safe_key(host_path)
                    setattr(self, f"active_portal_{safe_key}", portal_path)


    def on_plasma_refresh_toggled(self, switch, pspec):
        is_active = switch.get_active()
        is_flatpak = os.path.exists('/.flatpak-info')

        # 1. ONLY perform the 'Installation' check if we are in a Flatpak
        if is_flatpak:
            if is_active and not self.check_plasma_refresh_status():
                # Not installed in Flatpak: Reset switch and show setup
                switch.set_active(False)
                self.show_plasma_setup_dialog()
            elif not is_active:
                print("Plasma Auto-Reload Disabled (Flatpak mode)")
        
        # 2. NATIVE MODE: If it's active, we just assume it works 
        # (since we trigger commands directly on the host)
        else:
            if is_active:
                print("Plasma Auto-Reload Enabled (Native mode - direct commands)")





        
    def on_gnome_refresh_toggled(self, switch, pspec):
        is_active = switch.get_active()
        is_flatpak = os.path.exists('/.flatpak-info')

        # ONLY perform the 'Installation' check if we are in a Flatpak
        if is_flatpak:
            if is_active and not self.check_gnome_refresh_status():
                # Not installed in Flatpak: Reset switch and show setup
                switch.set_active(False)
                self.show_gnome_setup_dialog()
            elif not is_active:
                print("GNOME Auto-Reload Disabled (Flatpak mode)")
        
        # NATIVE MODE: If it's active, we just assume it works 
        # (since we trigger commands directly on the host)
        else:
            if is_active:
                print("GNOME Auto-Reload Enabled (Native mode - direct commands)")



    def trigger_shell_refresh(self):
        if not hasattr(self, 'refresh_switch') or not self.refresh_switch.get_active():
            return

        is_flatpak = os.path.exists('/.flatpak-info')

        if is_flatpak:
            # --- FLATPAK LOGIC: Touch the trigger file ---
            trigger_path = os.path.expanduser("~/.var/app/io.github.schwarzen.colormydesktop/data/colormydesktop/refresh.trigger")
            try:
                os.makedirs(os.path.dirname(trigger_path), exist_ok=True)
                with open(trigger_path, 'a'):
                    os.utime(trigger_path, None)
                print("Flatpak: GNOME refresh signal sent.")
            except Exception as e:
                print(f"Flatpak Trigger Error: {e}")
        else:
            # --- NATIVE LOGIC: Run dconf commands directly ---
            try:
                # We toggle the theme to empty then back to your theme to force a refresh
                cmd = (
                    "/usr/bin/bash -c "
                    "'dconf write /org/gnome/shell/extensions/user-theme/name \"\\'\\' \"; "
                    "sleep 0.2; "
                    "dconf write /org/gnome/shell/extensions/user-theme/name \"\\'Color-My-Desktop\\'\"'"
                )
                subprocess.Popen(cmd, shell=True)
                print("Native: Direct GNOME refresh executed via dconf.")
            except Exception as e:
                print(f"Native Refresh Error: {e}")

            




        
    def on_show_contrast_dialog(self, row):
        p_hex = self.primary_row.get_text()
        txt_hex = self.text_row.get_text()
        ratio = self.get_contrast_ratio(p_hex, txt_hex)

        # Create a MessageDialog
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Accessibility Details",
            body=f"Current Ratio: {ratio:.1f}:1\n\nWCAG standards recommend at least 4.5:1 for readable text. Poor contrast can make your theme difficult to use."
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
                int(new_rgba.blue * 255)
            )

        #  Apply to Secondary and Tertiary rows
        # Secondary is slightly shifted, Tertiary is shifted more
        secondary_hex = adjust_color(rgba, offset)
        tertiary_hex = adjust_color(rgba, offset * 2)
        
        self.secondary_row.set_text(secondary_hex)
        self.tertiary_row.set_text(tertiary_hex)
        
        # Trigger UI sync
        self.update_mockup_css()



        
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
                    self.combo_row.set_selected(0)
                    
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
        
        
    def on_preview_toggled(self, switch_row, pspec):
        # Just call the width check logic, it already handles the switch state!
        self.on_window_width_changed()

        


    def update_mockup_css(self):
        print("DEBUG: update_mockup_css triggered!")
        # --- SAFETY CHECK 1: Ensure UI is built ---
        # If the contrast row or color entries aren't ready, exit early to prevent crash
        if not hasattr(self, 'contrast_info_row') or not hasattr(self, 'color_entries'):
            return

        # 1. Gather current hex codes safely
        # Use .strip() and fall back to a safe color if empty to prevent CSS syntax errors
        def get_safe_hex(row_attr, fallback="#ffffff"):
            row = getattr(self, row_attr, None)
            if row:
                val = row.get_text().strip()
                return val if val else fallback
            return fallback

        p = get_safe_hex("primary_row", "#246cc5")
        s = get_safe_hex("secondary_row", "#1a4d8c")
        t = get_safe_hex("tertiary_row", "#102f54")
        txt = get_safe_hex("text_row", "#ffffff")
        rgba_p = Gdk.RGBA()
        rgba_p.parse(p)
        
                #  CALCULATE LUMINANCE (0.0 to 1.0)
        luminance = (rgba_p.red * 0.299) + (rgba_p.green * 0.587) + (rgba_p.blue * 0.114)

        #  Define a "Floor" color (The darkest the background can ever be)
        # Deep Charcoal with a hint of blue/grey (standard for Pro apps)
        floor_r, floor_g, floor_b = 24, 26, 30 

        #  Dynamic Factor based on Luminance
        if luminance > 0.4:
            # For bright colors: We want a 15% tint of the primary color over the floor
            mix = 0.15
        else:
            # For dark colors: We want a 30% "glow" of the primary color
            mix = 0.30

        #  LERP Calculation: (Primary * mix) + (Floor * (1 - mix))
        bg_r = int((rgba_p.red * 255 * mix) + (floor_r * (1 - mix)))
        bg_g = int((rgba_p.green * 255 * mix) + (floor_g * (1 - mix)))
        bg_b = int((rgba_p.blue * 255 * mix) + (floor_b * (1 - mix)))

        bg_color = "#{:02x}{:02x}{:02x}".format(
            max(0, min(255, bg_r)), 
            max(0, min(255, bg_g)), 
            max(0, min(255, bg_b))
        )

        
        # --- CONTRAST CHECK ---
        try:
            # Only run if we have a contrast ratio helper
            if hasattr(self, 'get_contrast_ratio'):
                ratio = self.get_contrast_ratio(p, txt)
                
                if ratio >= 4.5:
                    status = "✅ Perfect"
                    self.contrast_info_row.remove_css_class("error")
                else:
                    status = "⚠️ Poor Contrast"
                    self.contrast_info_row.add_css_class("error")
                    
                self.contrast_info_row.set_subtitle(f"Contrast: {ratio:.1f}:1 — {status}")
        except Exception:
            self.contrast_info_row.set_subtitle("Contrast: --")
        

        #  Build the CSS String
        combined_css = f"""
        .color-preview-dot {{
            border-radius: 6px;
            border: 1px solid rgba(0,0,0,0.3);
            transition: all 0.2s ease-in-out;
            min-width: 26px;
            min-height: 26px;
        }}

        .preview-dropper-icon {{
            transition: opacity 0.2s ease;
            opacity: 0.5;
        }}

        /* --- 2. ROW-LEVEL TRIGGERS --- */
        /* Trigger when the whole row is hovered OR when typing inside it */
        row:hover .color-preview-dot,
        row:focus-within .color-preview-dot {{
            transform: scale(1.18);
            box-shadow: 0 0 12px rgba(255,255,255,0.25);
            border-color: rgba(255,255,255,0.6);
        }}

        row:hover .preview-dropper-icon,
        row:focus-within .preview-dropper-icon {{
            opacity: 1.0;
        }}

        /* Active click effect remains on the container for tactile feel */
        .color-preview-container:active .color-preview-dot {{
            transform: scale(0.92);
            transition: transform 0.05s;
        }}
        """

        #  Dynamic loop for Dots and Icons
        if hasattr(self, 'current_colors'):
            for cid, hcolor in self.current_colors.items():
                # Apply background to the dot
                combined_css += f"#{cid}-preview {{ background-color: {hcolor}; }}\n"
                
                # Apply contrast color to the icon ID
                if hasattr(self, 'icon_colors') and cid in self.icon_colors:
                    icolor = self.icon_colors[cid]
                    combined_css += f"#{cid}-icon {{ color: {icolor}; }}\n"

        #  Add the Mockup Palette
        combined_css += f"""
        #mockup-preview-image {{
            -gtk-icon-palette: success {p}, warning {s}, info {t}, error {txt};
            color: {t};

            margin-top: -80px;
            margin-bottom: -60px;
            padding: 0px;
            
            /* 2. Remove the negative transform/margin if it's cutting off the edges */
            /* Instead of transform, we use object-fit or centered layout */
            filter: drop-shadow(0 0 1.5px {p}88) 
                    drop-shadow(0 2px 4px rgba(0,0,0,0.4));
        }}

        #mockup-wrapper {{
            border-radius: 12px;
            background: linear-gradient(165deg, {bg_color} 0%, #080808 100%);
            
            /* 3. Reduce padding to 0 or very small (e.g. 4px) to let the image hit the edges */
            padding: 0px; 
            min-height: 10px;
            
             
        }}
        """
        
        if hasattr(self, 'dynamic_color_provider'):
            self.dynamic_color_provider.load_from_string(combined_css)
        
    def on_fix_contrast_clicked(self, button):
        p_hex = self.primary_row.get_text()
        rgba = Gdk.RGBA()
        if not rgba.parse(p_hex): return

        # Calculate primary luminance
        def get_lum(c):
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        lum = 0.2126 * get_lum(rgba.red) + 0.7152 * get_lum(rgba.green) + 0.0722 * get_lum(rgba.blue)

        # If background is dark, use White. If light, use Black.
        new_text = "#ffffff" if lum < 0.5 else "#000000"
        self.text_row.set_text(new_text)
        
        # Trigger refresh
        self.update_mockup_css()
        
    def on_window_width_changed(self):
        width = self.get_width()
        self.scale_mockup()
        # Fallback for startup
        if width <= 0: width = 900 

        is_switch_on = self.preview_switch_row.get_active()
        THRESHOLD = 1000

        if width >= THRESHOLD:
            # --- WIDE MODE ---
            if self.preview_group.get_parent() != self.side_preview_slot:
                self.preview_group.unparent()
                self.side_preview_slot.append(self.preview_group)
            
            #  Lock settings to 400px
            self.settings_side.set_size_request(400, -1)
            #  Restore the mockup to its full size
            self.mockup_image.set_size_request(300, -1) 
            
            self.side_preview_slot.set_visible(True)
            self.bottom_preview_slot.set_visible(False)
            self.preview_group.set_visible(True)
            self.preview_switch_row.set_visible(False)
        else:
            # --- NARROW MODE ---
            if self.preview_group.get_parent() != self.bottom_preview_slot:
                self.preview_group.unparent()
                self.bottom_preview_slot.append(self.preview_group)
            
            # Remove all width constraints so the window can shrink
            self.settings_side.set_size_request(-1, -1)
            self.side_preview_slot.set_size_request(0, -1)
            
            # Tell the mockup image itself to stop asking for 300px
            
            self.mockup_image.set_size_request(0, -1) 
            
            self.side_preview_slot.set_visible(False)
            self.preview_switch_row.set_visible(True)
            self.bottom_preview_slot.set_visible(is_switch_on)
            self.preview_group.set_visible(is_switch_on)





        

    def is_valid_hex(self, color):
        # Strip whitespace to avoid simple input errors
        color = color.strip()
        
        # Matches SCSS variables (e.g., $primary-color)
        if re.match(r'^\$[A-Za-z0-9_-]+$', color):
            return True
        

        if re.match(r'^#?([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', color):
            return True

        # Fallback to Gdk.RGBA.parse (Handles rgba(0,0,0,0), hsl, names, etc.)
        rgba = Gdk.RGBA()
        return rgba.parse(color)
        
    def setup_color_watchdog(self):
        # List of all rows we want to monitor
        rows_to_watch = [
            self.primary_row, 
            self.secondary_row, 
            self.tertiary_row, 
            self.text_row
        ]
        
        for row in rows_to_watch:
            if row is not None:
                # Gtk.Editable 'changed' signal is the universal way to catch typing
                # We use a lambda to discard the widget argument and just run our refresh
                row.get_delegate().connect("changed", lambda *args: self.update_mockup_css())

    
    def create_color_entry(self, label, default_hex, css_id, use_subtitle=False, show_magic=False):
        if not hasattr(self, 'color_entries'):
            self.color_entries = {}
            
        def create_slick_btn(icon_name, click_handler, target):
            container = Gtk.Overlay()
            container.set_valign(Gtk.Align.CENTER)
            container.set_size_request(26, 26)
            container.set_cursor(Gdk.Cursor.new_from_name("pointer", None))
            container.add_css_class("color-preview-container")

            # The Background Box (The colored/tinted part)
            bg_box = Gtk.Label()
            bg_box.set_size_request(26, 26)
            # Use the same ID for both so they both show the row's color
            bg_box.set_name(f"{css_id}-preview")
            bg_box.add_css_class("color-preview-dot")
            container.set_child(bg_box)

            # The Icon (The dropper or palette)
            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.add_css_class("preview-dropper-icon")
            icon.set_name(f"{css_id}-icon") # For the dynamic contrast logic
            container.add_overlay(icon)

            

            # Gesture
            gesture = Gtk.GestureClick.new()
            gesture.connect("pressed", click_handler, target)
            container.add_controller(gesture)
            
            return container



        #  CREATE THE ROW (This defines the 'row' variable)
        if use_subtitle:
            row = Adw.ActionRow(title=label)
            entry = Gtk.Entry()
            entry.set_text(default_hex)
            entry.set_valign(Gtk.Align.CENTER)
            entry.add_css_class("flat")
            
            # This is the widget the picker will update
            target_widget = entry
            
            # Connect live updates
            entry.connect("changed", lambda *args: self.update_mockup_css())
            entry.connect("changed", lambda e: self.update_preview(e, css_id))
            
            if show_magic:
                btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
                btn.add_css_class("flat")
                btn.connect("clicked", self.on_generate_variants_clicked)
                entry.set_suffix_widget(btn)

            row.add_suffix(entry)
            self.color_entries[css_id] = entry
        else:
            row = Adw.EntryRow(title=label)
            row.set_text(default_hex)
            
            # In an EntryRow, the row itself is the target
            target_widget = row
            
            # Connect live updates
            row.connect("notify::text", lambda *args: self.update_mockup_css())
            row.connect("notify::text", lambda r, pspec: self.update_preview(r, css_id))
            
            if show_magic:
                btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
                btn.add_css_class("flat")
                btn.connect("clicked", self.on_generate_variants_clicked)
                row.add_suffix(btn)
                
            self.color_entries[css_id] = row

        # --- ADD THE TWO PREFIX BUTTONS ---
        #  The Advanced Picker (Dropper Icon)
        advanced_btn = create_slick_btn("color-select-symbolic", self.on_advanced_picker_clicked, target_widget)
        
        # The Quick Picker (Palette/Grid Icon)
        quick_btn = create_slick_btn("applications-graphics-symbolic", self.on_quick_picker_clicked, target_widget)

        # Add them both as prefixes (they will sit side-by-side)
        row.add_prefix(advanced_btn)
        row.add_prefix(quick_btn)
        #  ATTACH PICKER GESTURE TO OVERLAY
        click_gesture = Gtk.GestureClick.new()
        click_gesture.connect("pressed", self.on_advanced_picker_clicked, target_widget)





        # SETUP CONTRAST LABELS & BUTTONS
        status_label = Gtk.Label()
        status_label.add_css_class("caption")
        status_label.set_margin_end(6)
        
        if not hasattr(self, "status_labels"):
            self.status_labels = {}
        self.status_labels[css_id] = status_label

        fix_btn = Gtk.Button()
        fix_btn.add_css_class("flat")
        fix_btn.set_valign(Gtk.Align.CENTER)
        fix_btn.set_visible(False)
        fix_btn.connect("clicked", self.on_fix_contrast_clicked)
        
        if not hasattr(self, "status_buttons"):
            self.status_buttons = {}
        self.status_buttons[css_id] = fix_btn

        # Add them to the row suffix
        row.add_suffix(status_label)
        row.add_suffix(fix_btn)

        return row

        




        row.default_val = default_hex
        self.current_colors[css_id] = default_hex
        
            #  Create the CLICKABLE button instead of a Gtk.Image
        # Using new_from_icon_name is the cleanest way to make an icon-button
        preview_btn = Gtk.Button.new_from_icon_name("applications-graphics-symbolic")
        preview_btn.set_name(f"{css_id}-preview")
        preview_btn.add_css_class("flat")           # Keeps it integrated with the row
        preview_btn.add_css_class("color-preview-box") # For your background-color CSS
        preview_btn.set_valign(Gtk.Align.CENTER)
        
            #  Setup the Color Dialog (GTK 4.10+)
        # Note: Use self.win or self as the parent window
        color_dialog = Gtk.ColorDialog.new()
        color_dialog.set_title(f"Choose {label}")

        # Connect the signal (Ensuring 'row' is passed to update the text later)
        preview_btn.connect("clicked", self.on_eye_dropper_clicked, color_dialog, row)
        
        #  Add the BUTTON to the row suffix
        row.add_suffix(preview_btn)

        # Setup Preview Box as before

        preview = Gtk.Image.new_from_icon_name("color-select-symbolic")
        preview.set_pixel_size(24)
        preview.add_css_class("color-preview-box")
        preview.set_name(f"{css_id}-preview")
        row.add_suffix(preview)
                        # Connect a gesture or click handler to the preview box itself
        click_gesture = Gtk.GestureClick()
        click_gesture.connect("released", self.on_advanced_picker_clicked, row)
        preview.add_controller(click_gesture)
        

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
    def update_preview(self, entry, css_id):
        #  Get the current text
        try:
            hex_code = entry.get_text().strip()
        except AttributeError:
            # This happens if 'entry' is actually a GParamSpec
            return
        
        #  Validation
        rgba = Gdk.RGBA()
        if rgba.parse(hex_code) or (hex_code.startswith('#') and len(hex_code) in [4, 7, 9]):
                    # --- NEW: BRIGHTNESS CHECK FOR ICON CONTRAST ---
            # Standard perceived luminance formula
            brightness = (rgba.red * 0.299) + (rgba.green * 0.587) + (rgba.blue * 0.114)
            
            # If brightness > 0.6, the background is light, so use a dark icon
            icon_color = "rgba(0,0,0,0.7)" if brightness > 0.6 else "rgba(255,255,255,0.8)"
            
            # Store this in your color registry so the CSS builder can see it
            if not hasattr(self, 'icon_colors'):
                self.icon_colors = {}
            self.icon_colors[css_id] = icon_color
            clean_hex = hex_code if hex_code.startswith('#') else f"#{hex_code}"
            
            if not hasattr(self, 'current_colors'):
                self.current_colors = {}
            self.current_colors[css_id] = clean_hex
            self.update_mockup_css()
            
            #  Rebuild the CSS string
            full_css = ""
            for cid, hcolor in self.current_colors.items():
                # Update dots
                full_css += f"#{cid}-preview {{ background-color: {hcolor}; border-radius: 6px; min-width: 24px; min-height: 24px; }}\n"
                
                # Update Mockup logic
                if cid == "primary":
                    full_css += f"#mock-headerbar {{ background-color: {hcolor}; }}\n"
                elif cid == "secondary":
                    full_css += f"#mock-sidebar {{ background-color: {hcolor}; }}\n"

            # Apply CSS
            if hasattr(self, 'dynamic_color_provider'):
                self.dynamic_color_provider.load_from_string(full_css)

            # --- DYNAMIC CONTRAST LOGIC ---
            # Now we use the dictionaries created in create_color_entry
            if hasattr(self, "status_labels") and css_id in self.status_labels:
                label = self.status_labels[css_id]
                # You can add your contrast checking logic here
                # label.set_markup("<span foreground='green'>✔ Pass</span>")

        
    def on_advanced_picker_clicked(self, gesture, n_press, x, y, entry_row):
        # Create the dialog
        dialog = Gtk.ColorChooserDialog(title="Advanced Color Editor", transient_for=self)
        
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
        if rgba.parse(current_text if current_text.startswith('#') else f"#{current_text}"):
            dialog.set_rgba(rgba)

        # Use existing response handler to save the color back to the row
        dialog.connect("response", self.on_advanced_response, entry_row)
        dialog.present()


    def on_advanced_response(self, dialog, response_id, entry_row):
        if response_id == Gtk.ResponseType.OK:
            rgba = dialog.get_rgba()
            hex_color = "#{:02x}{:02x}{:02x}".format(
                int(rgba.red * 255), 
                int(rgba.green * 255), 
                int(rgba.blue * 255)
            )
            entry_row.set_text(hex_color)
            self.update_mockup_css()
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
                    int(rgba.red * 255), 
                    int(rgba.green * 255), 
                    int(rgba.blue * 255)
                )
                # Update the entry row - this triggers your live preview automatically!
                entry_row.set_text(hex_color)
                self.update_mockup_css()
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
        self.on_window_width_changed()
        is_default = (combo_row.get_selected() == 0)
        self.delete_profile_btn.set_visible(not is_default)
        selected_index = combo_row.get_selected()
        
        #  Guard: Ignore index 0 ('Default') or errors
        if selected_index <= 0:
            print("Resetting to Default theme values...")
            self.name_row.set_text("Default")
            self.primary_row.set_text("#246cc5")
            self.secondary_row.set_text("#241f31")
            self.tertiary_row.set_text("#1e1e1e")
            self.text_row.set_text("#f9f9f9")
            self.topbar_row.set_text("#246cc5") 
            self.topbar_switch.set_active(False)
            self.clock_row.set_text("#246cc5") 
            self.clock_switch.set_active(False)
            self.update_mockup_css()
            return
            
                # ---  RESET TO DEFAULT CASE ---
        if is_default:
            print("Resetting to Default theme values...")
            self.name_row.set_text("Default")
            self.primary_row.set_text("#246cc5")
            self.secondary_row.set_text("#241f31")
            self.tertiary_row.set_text("#1e1e1e")
            self.text_row.set_text("#f9f9f9")
            # Refresh mockup for default values
            self.update_mockup_css()
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
                self.topbar_row.set_text(self.get_scss_value(selected_theme, "primary")) 
                self.topbar_switch.set_active(False)
            clock_val = self.get_scss_value(selected_theme, "clock-color")
            if clock_val:
                self.clock_row.set_text(clock_val)
                self.clock_switch.set_active(True)
            else:
                # If the file doesn't have it, reset to a safe default but don't clear it!
                self.clock_row.set_text(self.get_scss_value(selected_theme, "text")) 
                self.clock_switch.set_active(False)
                
            self.update_mockup_css()
                
            # If you have the switch: self.topbar_switch.set_active(True)
    # Assuming 'selected' is the string from your dropdown/ComboRow

        
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
        newly_saved_name = self.name_row.get_text()

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
                self.combo_row.set_selected(index)
                break
                
        print(f"Refreshed dropdown. Selected: {newly_saved_name}")


        
    def on_run_build_clicked(self, button):

        self.active_build_button = button 
        self.active_build_button.set_sensitive(False)
    # Get primary hex and ensure it is a string
        primary_color = str(self.primary_row.get_text() or "#246cc5")
        secondary_color = str(self.secondary_row.get_text() or "#246cc5")
        text_color = str(self.text_row.get_text() or "#f9f9f9")
        plasma_path = self.get_path_argument("~/.local/share/plasma")
        schemes_path = self.get_path_argument("~/.local/share/color-schemes")
        gnome_path = self.get_path_argument("~/.local/share/themes")
        #  Dynamic Zen path
        # Get the actual path string first (falling back to the default glob if not set)
        current_zen_val = getattr(self, "last_manually_entered_zen_path", "~/.zen/*/chrome")

        # Pass that VALUE to get_path_argument
        zen_path = self.get_path_argument(current_zen_val)
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
            "#246cc5",  # $15 (Datemenu fallback)
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
        self.win = None
        
    def do_startup(self):
        Adw.Application.do_startup(self)



    def do_activate(self):
        #initialize window
        if not self.win:
            # Pass 'self' as the application
            self.win = ThemeManager(application=self)
            
            #  Connect the close signal to the WINDOW (ThemeManager)
            self.win.connect("close-request", self.on_window_close)
        
        self.win.present()
        
    def on_window_close(self, window):
        print("Shutting down cleanly...")
        
        # Clean up the subprocess if it is running
    
        if hasattr(window, 'current_process') and window.current_process:
            print("Terminating active build process...")
            window.current_process.terminate()
            
     
        # Calling quit() ensures all background threads are signaled to stop.
        self.quit() 
        return False 

if __name__ == "__main__":

    app = ColorMyDesktopApp()

    sys.exit(app.run([]))
