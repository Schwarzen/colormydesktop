import gi
import os
import re
import subprocess
import threading

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

# --- CONFIGURATION ---
SCSS_DIR = os.path.expanduser("~/.local/share/Color-My-Gnome/scss")
BASH_SCRIPT = os.path.expanduser("~/.local/bin/color-my-gnome")
themes = [f[1:-5] for f in os.listdir(SCSS_DIR) if f.startswith('_') and f.endswith('.scss')]

class ThemeManager(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        


        
        self.set_title("Color My Gnome")
        self.set_default_size(400, 500)

        # 1. Main Layout Container
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(self.main_box)
        self.set_content(self.toast_overlay)
        self.set_content(self.main_box)
        
                # 2. Add a Header Bar
        self.header = Adw.HeaderBar()
        self.main_box.append(self.header)
        
        
        
        self.page = Adw.PreferencesPage()
        self.group = Adw.PreferencesGroup()
        self.group.set_title("Theme Configuration")
        
        self.page.add(self.group)
        self.main_box.append(self.page)
        


        # Create the model
        self.theme_list = Gtk.StringList.new(themes)

        # Create the ComboRow and link the model
        self.combo_row = Adw.ComboRow()
        self.combo_row.set_title("Load Existing Profile")
        self.combo_row.set_model(self.theme_list)
        self.group.add(self.combo_row)

        self.name_row = Adw.EntryRow(title="Profile Name")
        self.primary_row = Adw.EntryRow(title="Primary Hex")
        self.secondary_row = Adw.EntryRow(title="Secondary Hex")
        self.tertiary_row = Adw.EntryRow(title="Tertiary Hex")
        self.text_row = Adw.EntryRow(title="Text Hex")
        # Connect to the selection change signal
        self.combo_row.connect("notify::selected", self.on_theme_select)


        
       
# 4. CRITICAL: You must append the rows to the group!
        self.group.add(self.name_row)
        self.group.add(self.primary_row) 
        self.group.add(self.secondary_row) 
        self.group.add(self.tertiary_row) 
        self.group.add(self.text_row) 

        # Button
        
                # Create the build button
        self.build_btn = Gtk.Button(label="Build and Apply Theme")
        self.build_btn.add_css_class("suggested-action") # Native blue color
        self.build_btn.set_margin_top(24)
        self.build_btn.set_margin_bottom(24)
        
        # Connect the signal to the method above
        self.build_btn.connect("clicked", self.on_run_build_clicked)
        
        # Add it to your layout (e.g., inside a Gtk.Box)
        self.main_box.append(self.build_btn)

    
        
        self.main_box.append(self.page)
                # 3. Create your Rows

      
        


        self.group.add(self.name_row)
        self.group.add(self.primary_row)
        self.group.set_title("Global Options")
        self.page.add(self.group)
        
        # --- TOP BAR SECTION ---
        self.topbar_switch = Adw.SwitchRow(title="Custom Topbar Color")
        self.group.add(self.topbar_switch)

        self.topbar_row = Adw.EntryRow(title="Topbar Hex")
        self.topbar_row.set_text("")
        self.topbar_row.set_visible(False) # Hidden initially
        self.group.add(self.topbar_row)

        # MAGIC BINDING: This links the toggle to the row's visibility
        self.topbar_switch.bind_property("active", self.topbar_row, "visible", 0)

        # --- CLOCK SECTION ---
        self.clock_switch = Adw.SwitchRow(title="Custom Clock Color")
        self.group.add(self.clock_switch)

        self.clock_row = Adw.EntryRow(title="Clock Hex")
        self.clock_row.set_text("")
        self.clock_row.set_visible(False) # Hidden initially
        self.group.add(self.clock_row)

        # MAGIC BINDING: This links the toggle to the row's visibility
        self.clock_switch.bind_property("active", self.clock_row, "visible", 0)

        # --- ZEN BROWSER TOGGLE ---
        self.zen_switch = Adw.SwitchRow()
        self.zen_switch.set_title("Apply to Zen Browser &amp; YouTube")
        self.zen_switch.set_active(True)
        self.group.add(self.zen_switch)
        # --- TRANSPARENCY TOGGLE ---
        self.trans_switch = Adw.SwitchRow()
        self.trans_switch.set_title("Enable Global Transparency")
        self.trans_switch.set_active(False) # Default solid
        self.group.add(self.trans_switch)

        # --- DATA EXTRACTION LOGIC ---
    def get_scss_value(self, filename, variable):
        path = os.path.join(SCSS_DIR, f"_{filename}.scss")
        if not os.path.exists(path): return ""
        with open(path, 'r') as f:
            content = f.read()
            match = re.search(fr"\${variable}:\s*([^;]+);", content)
            return match.group(1).strip() if match else ""

    
    def on_theme_select(self, combo_row, gparamspec):
        # 1. Get the current selected string
        selected_index = combo_row.get_selected()
        selected_theme = self.theme_list.get_string(selected_index)
        
        if not selected_theme:
            return

        # 2. Update the Name field
        self.name_row.set_text(selected_theme)
        
        # 3. Update EACH color row specifically
        # Using your existing get_scss_value logic
        self.primary_row.set_text(self.get_scss_value(selected_theme, "primary"))
        self.secondary_row.set_text(self.get_scss_value(selected_theme, "secondary"))
        self.tertiary_row.set_text(self.get_scss_value(selected_theme, "tertiary"))
        self.text_row.set_text(self.get_scss_value(selected_theme, "text"))
        
        tb_val = self.get_scss_value(selected_theme, "topbar-color")
        if tb_val:
            self.topbar_row.set_text(tb_val)
        clock_val = self.get_scss_value(selected_theme, "clock-color")
        if clock_val:
            self.clock_row.set_text(clock_val)
        # If you have the switch: self.topbar_switch.set_active(True)
    # Assuming 'selected' is the string from your dropdown/ComboRow
    def update_gui_from_file(self, selected):
        # 1. Auto-fill standard color rows
        # In PyGObject, we store rows in a dictionary: self.color_rows = {"primary": row_object, ...}
        for var, row in self.color_rows.items():
            val = self.get_scss_value(selected, var)
            if val:
                row.set_text(val)  # Replaces delete(0, tk.END) and insert(0, val)

        # 2. Check for Topbar Color
        tb_val = self.get_scss_value(selected, "topbar-color")
        
        if tb_val:
            self.topbar_row.set_text(tb_val) # Set the hex code
            self.topbar_switch.set_active(True) # Turn the toggle ON
            self.topbar_row.set_visible(True)   # Show the row (replaces toggle_topbar)
        else:
            self.topbar_switch.set_active(False) # Turn the toggle OFF
            self.topbar_row.set_visible(False)   # Hide the row

        


        cl_val = self.get_scss_value(selected, "clock-color")

        if cl_val:
            # Set the text in the Adw.EntryRow
            self.clock_row.set_text(cl_val)
            
            # Toggle the SwitchRow to "On"
            self.clock_switch.set_active(True)
            
            # Show the row (GTK4 handles the layout animation automatically)
            self.clock_row.set_visible(True)
        else:
            # Toggle the SwitchRow to "Off"
            self.clock_switch.set_active(False)
            
            # Hide the row
            self.clock_row.set_visible(False)
        # --- Top Bar Section ---
        # 1. The Toggle Switch
        self.topbar_switch = Adw.SwitchRow()
        self.topbar_switch.set_title("Custom Topbar")
        self.topbar_switch.set_active(False) # Default to 0
        self.group.add(self.topbar_switch)

        # 2. The Color Entry Row
        self.topbar_row = Adw.EntryRow()
        self.topbar_row.set_title("Topbar Color")
        self.topbar_row.set_text("#3584e4") # Default value
        self.group.add(self.topbar_row)

        # 3. THE "MAGIC" CONNECTION (Replaces toggle_topbar function)
        # This binds the 'visible' property of the entry row to 
        # the 'active' property of the switch.
        self.topbar_switch.bind_property(
            "active", 
            self.topbar_row, 
            "visible", 
            GObject.BindingFlags.SYNC_CREATE
        )


        # --- Clock Section ---
        # 1. The Toggle Switch (Standard GNOME styling)
        self.clock_switch = Adw.SwitchRow()
        self.clock_switch.set_title("Custom Clock Color")
        self.clock_switch.set_active(False) # Default to 0/False
        self.group.add(self.clock_switch)

        # 2. The Color Entry Row
        self.clock_row = Adw.EntryRow()
        self.clock_row.set_title("Clock Color Hex")
        self.clock_row.set_text("#3584e4") # Default value
        self.group.add(self.clock_row)

        # 3. THE MAGIC CONNECTION (Property Binding)
        # This replaces the entire 'toggle_clock' function logic.
        # It binds the 'active' state of the switch to the 'visible' state of the row.
        self.clock_switch.bind_property(
            "active", 
            self.clock_row, 
            "visible", 
            GObject.BindingFlags.SYNC_CREATE
        )

        # --- 1. THE DROPDOWN (ComboRow) ---
        # Create the dropdown row
        self.combo_row = Adw.ComboRow()
        self.combo_row.set_title("Load Existing Profile")

        # Scan SCSS_DIR for files (Identical logic to your Tkinter version)
        themes = [f[1:-5] for f in os.listdir(SCSS_DIR) if f.startswith('_') and f.endswith('.scss')]

        # GTK4 uses a StringList to hold the dropdown items
        self.theme_list = Gtk.StringList.new(themes)
        self.combo_row.set_model(self.theme_list)

        # Connect the selection event (Replaces <<ComboboxSelected>>)
        # 'notify::selected' triggers whenever the user picks a new item
        self.combo_row.connect("notify::selected", self.on_theme_select)
        self.group.add(self.combo_row)

        # --- 2. THE ENTRY ROWS ---
        self.color_rows = {} # To store our rows for later access

        # Define the fields (Matching your labels and variables)
        fields = [("New Name", "name"), ("Primary", "primary"), 
                  ("Secondary", "secondary"), ("Tertiary", "tertiary"), ("Text", "text")]

        for label, var in fields:
            row = Adw.EntryRow()
            row.set_title(label)
            
            # Store references so we can pull text later
            if var == "name":
                self.name_row = row
            else:
                self.color_rows[var] = row
                
            self.group.add(row)
        # --- RUN BASH SCRIPT ---
        # --- RUN BASH SCRIPT ---
        # This is now a method inside your ThemeManager(Adw.ApplicationWindow) class
    def on_run_build_clicked(self, button):
        # 1. Collect values
        args = [
            self.name_row.get_text(),
            self.primary_row.get_text(),
            self.secondary_row.get_text(),
            self.tertiary_row.get_text(),
            self.text_row.get_text(),
            "1" if self.zen_switch.get_active() else "0",
            "1" if self.topbar_switch.get_active() else "0",
            self.topbar_row.get_text(),
            "1" if self.clock_switch.get_active() else "0",
            self.clock_row.get_text(),
            "1" if self.trans_switch.get_active() else "0",
            "0.8"
        ]
        
        button.set_sensitive(False)
        
        def worker():
            try:
                import subprocess
                subprocess.run(["bash", BASH_SCRIPT] + args, check=True)
                from gi.repository import GLib
                # args[0] is the theme name
                GLib.idle_add(self.show_success_toast, args[0], button)
            except Exception as e:
                from gi.repository import GLib
                GLib.idle_add(self.show_error_dialog, f"Build failed: {e}")
                GLib.idle_add(button.set_sensitive, True)
                
        # --- FIXED INDENTATION BELOW ---
        thread = threading.Thread(target=worker)
        thread.start()


    def show_success_toast(self, theme_name, button):
        """Standard 2025 UI update logic."""
        toast = Adw.Toast.new(f"Theme '{theme_name}' applied!")
        self.toast_overlay.add_toast(toast)
        button.set_sensitive(True) # Re-enable the button




    def show_error_dialog(self, message):
        """Modern 2025 replacement for Adw.MessageDialog."""
        # 1. Create the AlertDialog
        dialog = Adw.AlertDialog.new(
            "Error",        # Heading
            message         # Body text
        )
        
        # 2. Add the 'OK' button (response ID, label)
        dialog.add_response("ok", "OK")
        
        # 3. Set the default (accented) response
        dialog.set_default_response("ok")
        
        # 4. In 2025, we use choose() instead of present() for better async handling
        # The lambda just closes the dialog when the button is clicked
        dialog.choose(self, None, lambda *args: None)
# Boilerplate to run the App
# Boilerplate to run the App
class MyApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.user.ColorMyGnome")
        # EXPLICITLY connect the signal
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        # Create and present the window
        # Ensure 'application=app' is passed so it's linked correctly
        self.win = ThemeManager(application=app)
        self.win.present()


# --- THE FIX IS HERE ---
import sys

if __name__ == "__main__":
    app = MyApp()
    # Pass sys.argv to ensure the application loop starts with system context
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)
