# colormydesktop/gnomeoptions.py
#
class GnomeThemeConfig:
    def __init__(self, broker):
        # Store a reference to the central broker
        self.broker = broker

    def get_color_value(self, color_name, primary_color):
        gnome_options = self.broker.get_page("gnome_options")

        switch = gnome_options.switches.get(color_name)
        if switch and switch.get_active():
            return str(gnome_options.color_entries[color_name].get_text())

        return primary_color

    def get_switch_string(self, color_name):
        gnome_options = self.broker.get_page("gnome_options")

        switch = gnome_options.switches.get(color_name)
        return "1" if switch and switch.get_active() else "0"
