#!/usr/bin/env python3
# Copyright 2026 Schwarzen
# SPDX-License-Identifier: Apache-2.0

import gi

from gi.repository import Gtk, Adw, Gdk

class AdvancedMixin:

    def add_grid_item(self, label, default_color, css_id):
  
        # CREATE THE SETTINGS PAGE FOR THIS ITEM
        sub_page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
                # Sub-page Header
        sub_header = Adw.HeaderBar()
        sub_page_box.append(sub_header) #
        sub_pref_page = Adw.PreferencesPage()
        sub_page_box.append(sub_pref_page)


        #  CREATE THE CUSTOMIZATION GROUP (Below)
        sub_group = Adw.PreferencesGroup(title=f"{label} Customization")
        # Create the button row

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

            # Visibility Bindings 
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
        
    def show_reset_instructions(self, widget):
        app_id = "io.github.schwarzen.colormydesktop"
        
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Reset Permissions",
            body="If you want to clear permanent folder access, run this command in your terminal or use Flatseal."
        )
        
        #  Provide the command (Selectable for easy copy)
        #  Create the label
        cmd_label = Gtk.Label(selectable=True, xalign=0)
        

        cmd_label.set_markup(f"flatpak override --user --reset {app_id}")
        
 
        cmd_label.add_css_class("card")
        
        dialog.set_extra_child(cmd_label)

        #  Add the response buttons
        dialog.add_response("flatseal", "Open Flatseal")
        dialog.add_response("close", "Close")
        
        def on_response(d, response_id):
            if response_id == "flatseal":

                Gtk.show_uri(self, f"app://com.github.tchx84.Flatseal", Gdk.CURRENT_TIME)
                
        dialog.connect("response", on_response)
        dialog.present()




        

                
        
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
        
