import gi
import colorsys

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gtk


class InteractiveMockup(Gtk.Box):
    """
    A GTK4 Mockup utilizing a 3x3 Grid of Overlays.
    Ensures elements stay centered and scale, but statically sized windows
    freely overlap if the layout shrinks too much.
    """

    def __init__(self, raw_svg_template=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_hexpand(True)
        self.set_vexpand(True)

        self.update_colors({})

        #  TOPBAR (CenterBox ensures the clock is always dead center)
        topbar = Gtk.CenterBox()
        topbar.add_css_class("topbar")
        topbar.set_margin_top(10)
        # --- Attach Click Controller to Topbar ---
        topbar_click = Gtk.GestureClick()
        topbar_click.connect(
            "pressed",
            lambda gesture, n_press, x, y: self.on_element_clicked(None, "topbar"),
        )
        topbar.add_controller(topbar_click)

        # --- Clock / Date Menu (Center) built as a Gtk.Box ---
        self.clock = Gtk.Box()
        self.clock.add_css_class("mockup-btn")

        # Add a label inside the box for the text
        clock_label = Gtk.Label(label="Oct 24 10:45 AM")
        self.clock.append(clock_label)

        # Since Gtk.Box doesn't have a 'clicked' signal, use GestureClick
        clock_click = Gtk.GestureClick()
        clock_click.connect(
            "pressed",
            lambda gesture, n_press, x, y: self.on_element_clicked(None, "datemenu"),
        )
        self.clock.add_controller(clock_click)

        topbar.set_center_widget(self.clock)

        self.powermenu = Gtk.Button(icon_name="system-shutdown-symbolic")
        self.powermenu.add_css_class("mockup-btn")
        self.powermenu.connect("clicked", self.on_element_clicked, "powermenu")

        right_box = Gtk.Box(halign=Gtk.Align.END)
        right_box.append(self.powermenu)
        topbar.set_end_widget(right_box)
        self.append(topbar)

        #  DESKTOP AREA (3x3 Grid)
        desktop_grid = Gtk.Grid()
        desktop_grid.add_css_class("desktop-area")
        desktop_grid.set_hexpand(True)
        desktop_grid.set_vexpand(True)
        desktop_grid.set_column_homogeneous(True)  # Forces equal width columns
        desktop_grid.set_row_homogeneous(True)  # Forces equal height rows

        # Helper Function: Creates a cell that lets its content overflow
        def create_overlay_cell():
            cell = Gtk.Overlay()
            # The base is an empty box. This tells GTK "I can shrink to 0 pixels!"
            base = Gtk.Box()
            base.set_hexpand(True)
            base.set_vexpand(True)
            cell.set_child(base)

            # Allow contents to bleed outside the grid cell boundaries
            cell.set_overflow(Gtk.Overflow.VISIBLE)
            return cell

        #  FILL GRID WITH OVERLAY CELLS
        # We store them in a dictionary so we can easily inject windows into specific coordinates
        self.grid_cells = {}
        for col in range(3):
            for row in range(3):
                cell = create_overlay_cell()
                desktop_grid.attach(cell, column=col, row=row, width=1, height=1)
                self.grid_cells[(col, row)] = cell

        #  WINDOW 1: Center under the clock (Col 1, Row 0)
        self.app_window1 = Gtk.Box()
        self.app_window1.add_css_class("app-window")
        self.app_window1.set_size_request(170, 180)  # Static Size
        self.app_window1.set_halign(Gtk.Align.CENTER)
        self.app_window1.set_valign(Gtk.Align.START)
        self.app_window1.set_margin_top(10)
        # --- Make app_window1 trigger the topbar action on click ---
        window1_click = Gtk.GestureClick()
        window1_click.connect(
            "pressed",
            lambda gesture, n_press, x, y: self.on_element_clicked(None, "topbar"),
        )
        self.app_window1.add_controller(window1_click)

        # Inject as a floating overlay into the Top-Center cell
        self.grid_cells[(1, 0)].add_overlay(self.app_window1)

        #  WINDOW 2: Bottom Right (Col 2, Row 1)
        self.app_window2 = Gtk.Box()
        self.app_window2.add_css_class("nautilus-window")
        self.app_window2.set_size_request(240, 150)  # Static Size
        self.app_window2.set_halign(Gtk.Align.CENTER)
        self.app_window2.set_valign(Gtk.Align.CENTER)
        self.app_window2.set_margin_top(60)
        self.app_window2_1 = Gtk.Box()
        self.app_window2_1.add_css_class("nautilus-window2")
        self.app_window2_1.set_size_request(220, 125)  # Static Size
        self.app_window2_1.set_halign(Gtk.Align.CENTER)
        self.app_window2_1.set_valign(Gtk.Align.CENTER)
        self.app_window2_1.set_margin_top(10)
        self.app_window2_1.set_margin_start(40)
        self.app_window2_1.set_margin_end(7)
        self.app_window2.append(self.app_window2_1)

        # Shift it slightly to force dramatic overlapping during resizes
        self.app_window2.set_margin_start(100)

        # Inject as a floating overlay into the Bottom-Right cell
        self.grid_cells[(0, 1)].add_overlay(self.app_window2)

        window2_click = Gtk.GestureClick()
        window2_click.connect(
            "pressed",
            lambda gesture, n_press, x, y: self.on_element_clicked(
                None, "nautilus-window"
            ),
        )
        self.app_window2.add_controller(window2_click)
        # ... (Window 1 and Window 2 setup code) ...

        # To force Window 2's cell to the absolute top of the Z-index stack:
        cell_to_bring_forward = self.grid_cells[(0, 1)]

        #  Remove it from the grid
        desktop_grid.remove(cell_to_bring_forward)

        #  Re-attach it at the exact same coordinates
        # Because it is the newest addition, GTK draws it on top of all other cells!
        desktop_grid.attach(cell_to_bring_forward, column=0, row=1, width=1, height=1)

        self.append(desktop_grid)

    def on_element_clicked(self, button, element_id):
        print(f"[MOCKUP INTERACTION] Target item clicked: {element_id}")
        from colormydesktop.broker import ContextBroker

        ContextBroker.translate_action(
            sender_id="InteractiveMockup",
            action_type="CLICKED_MOCKUP_ELEMENT",
            payload={"element_id": element_id},
        )

    def update_colors(self, color_data_map):
        from colormydesktop.config import (
            get_default_color_map,
            update_runtime_color_map,
        )
        import colorsys
        import json

        final_colors = get_default_color_map()

        final_colors.update(color_data_map)
        update_runtime_color_map(color_data_map)
        # --- DEBUG PRINT BLOCK ---
        # print("\n=== [DEBUG] SAVING LIVE PALETTE SELECTION ===")
        # print(json.dumps(final_colors, indent=4))
        # print("============================================\n")

        def parse_css_background(input_value, fallback_hex):
            """
            Checks if the user input contains multiple comma-separated hex codes.
            Returns a clean string block of CSS properties for background rendering.
            """
            val = str(input_value).strip()
            if not val:
                val = fallback_hex

            if "," in val:
                # Clean up individual components (e.g., "#6E5245 , #75361c")
                colors = [c.strip() for c in val.split(",") if c.strip()]
                color_string = ", ".join(colors)
                # clear background-color to let GTK render the gradient canvas reliably
                return f"background-image: linear-gradient(to bottom right, {color_string}); background-color: transparent;"
            else:
                # Standard solid color color rule
                return f"background-color: {val}; background-image: none;"

        def tint_desktop_from_primary(primary_input):
            """Takes a hex color or gradient input, extracts the primary/first hue, and darkens it."""
            # If primary is a gradient list, grab the first hex color to build the desktop tint background
            if "," in str(primary_input):
                colors = [c.strip() for c in str(primary_input).split(",") if c.strip()]
                primary_hex = colors[0].lstrip("#") if colors else "1a4d8c"
            else:
                primary_hex = str(primary_input).lstrip("#")

            if len(primary_hex) != 6:
                return "background-color: #0a1f38; background-image: none;"  # Fallback

            try:
                # 1. Convert hex to RGB floats (0.0 to 1.0)
                r = int(primary_hex[0:2], 16) / 255.0
                g = int(primary_hex[2:4], 16) / 255.0
                b = int(primary_hex[4:6], 16) / 255.0

                # 2. Convert RGB to HLS
                h, l, s = colorsys.rgb_to_hls(r, g, b)

                # 3. Create a dark theme background maintaining the primary hue
                new_lightness = 0.11
                new_saturation = min(s, 0.35)

                # 4. Convert back to RGB and then to Hex
                nr, ng, nb = colorsys.hls_to_rgb(h, new_lightness, new_saturation)
                dark_hex = f"#{int(nr * 255):02x}{int(ng * 255):02x}{int(nb * 255):02x}"
                return f"background-color: {dark_hex}; background-image: none;"
            except Exception:
                return "background-color: #0a1f38; background-image: none;"

        # Generate custom layout snippets using the parser
        topbar_style = parse_css_background(final_colors.get("topbarcolor"), "#1a4d8c")
        topbar_hover_style = parse_css_background(final_colors.get("accent"), "#133863")
        clock_style = final_colors.get("clockcolor", "#f9f9f9")
        nautilus_style = parse_css_background(
            final_colors.get("nautilusprimarycolor"), "#1a4d8c"
        )
        nautilus_secondary_style = parse_css_background(
            final_colors.get("nautilussecondarycolor"), "#1a4d8c"
        )

        desktop_style = tint_desktop_from_primary(
            final_colors.get("primary", "#1a4d8c")
        )

        datemenu_style = parse_css_background(
            final_colors.get("datemenucolor"), "#102f54"
        )
        datemenu_hover_style = parse_css_background(
            final_colors.get("accent"), "#133863"
        )

        primary_style = parse_css_background(final_colors.get("primary"), "#102f54")
        secondary_style = parse_css_background(final_colors.get("secondary"), "#102f54")

        css_data = f"""
        .topbar {{
            {topbar_style}
            padding: 6px;
        }}
        /* Darkens the topbar when hovered */
        .topbar:hover {{
            {topbar_hover_style}
        }}
        .desktop-area {{
            {desktop_style}
        }}
        .app-window {{
            {datemenu_style}
            border-radius: 8px;
            box-shadow: 0px 8px 24px rgba(0,0,0,0.6);
        }}
        .app-window:hover {{
            {datemenu_hover_style}
        }}
        .nautilus-window {{
            {nautilus_style}
            border-radius: 8px;
            box-shadow: 0px 8px 24px rgba(0,0,0,0.6);
        }}
        .nautilus-window:hover {{
            {topbar_hover_style}
        }}
        .nautilus-window2 {{
            {nautilus_secondary_style}
            border-radius: 8px;
        }}
        .mockup-btn, .mockup-btn label {{
            background: transparent;
            color: {clock_style};
            padding: 4px 12px;
            font-weight: bold;
        }}
        
        .mockup-btn:hover {{
            background-color: rgba(255, 255, 255, 0.15);
            border-radius: 6px;
        }}
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css_data.encode("utf-8"))
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
