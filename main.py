#!/usr/bin/env python3
import sys
import os

# Ensure local module directory can be discovered during path resolution
sys.path.insert(0, os.path.dirname(__file__))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk, Gdk

# 1. CORE ARCHITECTURAL PIPELINES (Loaded First)
from colormydesktop.broker import ContextBroker
from colormydesktop.functions import ThemeManager

# 2. SEPARATED WINDOW LAYOUT VIEWS
from colormydesktop.lib_gui import (
    MyMainWindow,
    PageHomeView,
    GnomeOptions,
    KDEOptions,
    NautilusOptions,
)
from colormydesktop.css import BASE_STYLE_SHEET


class ColorMyDesktop(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.schwarzen.colormydesktop",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )

    def do_activate(self):
        # =========================================================================
        # PHASE 1: PRE-INITIALIZATION (Instantiate the real ThemeManager instantly)
        # =========================================================================
        # The manager registers safely into the central broker pool without a UI context yet
        function_manager = ThemeManager(ui_context=None)
        ContextBroker.manager = function_manager

        # Instantiating layout options here is now completely immune to early event loops
        # because the broker already has a valid manager reference waiting for them!
        ContextBroker.gnome_options_singleton = GnomeOptions()
        ContextBroker.kde_options_singleton = KDEOptions()
        ContextBroker.nautilus_options_singleton = NautilusOptions()

        ContextBroker.register_page(
            "gnome_options", ContextBroker.gnome_options_singleton
        )
        ContextBroker.register_page("kde_options", ContextBroker.kde_options_singleton)
        ContextBroker.register_page(
            "nautilus_options", ContextBroker.nautilus_options_singleton
        )

        # =========================================================================
        # PHASE 2: DISPLAY SURFACE & GLOBAL APPLICATION GRAPHICS SETTINGS
        # =========================================================================
        self.global_css_provider = Gtk.CssProvider.new()
        initial_styles = BASE_STYLE_SHEET.replace("__BG_COLOR__", "#181a1e")
        self.global_css_provider.load_from_string(initial_styles)

        # Secure non-None hardware display context inside the activate runtime
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self.global_css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Instantiate primary application framing window
        self.win = MyMainWindow(application=self)

        # =========================================================================
        # PHASE 3: DYNAMIC VIEW RESOLUTION & CROSS-LINKING PIPELINE
        # =========================================================================
        mock_themes = ["Default Slate", "Arch Dark", "GNOME Classic", "Nordic Winter"]

        # This executes safely, finds the real manager instance in the broker pool,
        # populates initial previews, and builds your home row layouts perfectly!
        home_page_view = PageHomeView(
            themes_list_data=mock_themes, css_provider=self.global_css_provider
        )
        ContextBroker.register_page("home_view", home_page_view)

        # CRITICAL REACTION TRIGGER: This exact property assignment activates the main functions layer
        # internal methods to cleanly attach drop-down factories, gestures, and signals.
        function_manager.ui = home_page_view
        home_page_view.manager = function_manager

        # =========================================================================
        # PHASE 4: COMPOSITION RENDER
        # =========================================================================
        self.win.nav_view.push(home_page_view)
        self.win.present()


def main():
    app = ColorMyDesktop()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
