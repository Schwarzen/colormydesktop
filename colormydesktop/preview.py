      # --- MORE OPTIONS EXPANDER ------------------------------------
        self.more_group = Adw.PreferencesGroup()
        self.more_group.set_title("Additional Settings")
        self.page.add(self.more_group)

        # 1. Create the expander row
        self.more_expander = Adw.ExpanderRow(title="More Options")

        self.placeholder_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.placeholder_box.set_margin_top(12)

        # 2. Build the main container for everything inside the expander
        # We use a Box and apply margins here
        self.expander_content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        # Set margins for the entire content box
        self.expander_content_box.set_margin_top(20)
        self.expander_content_box.set_margin_bottom(20)
        self.expander_content_box.set_margin_start(20)
        self.expander_content_box.set_margin_end(20)

        # --- MOCKUP WINDOW PREVIEW (Detailed) ---

        # Main container for the mini "window" simulation
        self.preview_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.preview_container.set_name("mockup-preview-area")
        self.preview_container.set_size_request(300, 180)  # Set a reasonable default size

        # Mock Titlebar (HeaderBar)
        self.mock_header = Gtk.HeaderBar()
        self.mock_header.set_name("mock-headerbar")  # Use this name for CSS targeting
        self.preview_container.append(self.mock_header)

        # Main content area below the titlebar (Sidebar + Main View)
        self.main_content_area = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_content_area.set_vexpand(True)
        self.preview_container.append(self.main_content_area)

        # Mock Sidebar
        self.mock_sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.mock_sidebar.set_name("mock-sidebar")  # Target this for sidebar color
        self.mock_sidebar.set_size_request(80, -1)  # Make sidebar narrow
        self.main_content_area.set_start_child(self.mock_sidebar)

        # Add some dummy items to the sidebar
        for name in ["Home", "Documents", "Pictures"]:
            label = Gtk.Label(label=name, xalign=0)
            label.set_margin_start(10)
            self.mock_sidebar.append(label)

        # Mock Main Content View
        self.mock_main_view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.mock_main_view.set_name("mock-window-content")  # Target this for main background color
        self.main_content_area.set_end_child(self.mock_main_view)

        # Add a fake file icon
        file_icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic")
        file_icon.set_pixel_size(32)
        file_icon.set_margin_top(20)
        file_icon.set_margin_bottom(20)
        file_icon.set_margin_start(20)
        file_icon.set_margin_end(20)
        self.mock_main_view.append(file_icon)

        # --- ADD THE MOCKUP TO THE EXPANDER CONTENT ---
        self.expander_content_box.append(self.preview_container)

        # Add the previously defined taskbar mockup as well
        # self.expander_content_box.append(self.mock_taskbar) # (assuming taskbar code is present)

        # 3. FIX: Add the content box to the ExpanderRow using the correct method
        self.more_expander.add_row(self.expander_content_box)

        # 4. Now add the expander to the group
        self.more_group.add(self.more_expander)

        # Optional: keep the placeholder hidden when collapsed
        def on_expanded_changed(row, pspec):
            self.placeholder_box.set_visible(row.get_expanded())

        self.more_expander.connect("notify::expanded", on_expanded_changed)
