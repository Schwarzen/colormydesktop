# /home/Warzen/Color-My-Desktop/colormydesktop/config.py

#  mapping options rows to their respective toggle switches
SWITCH_REVEAL_MAP = {
    "topbarcolor": "topbar_toggle",
    "datemenucolor": "datemenu_toggle",
    "clockcolor": "clock_toggle",
    "nautilusprimarycolor": "nautilus_toggle",
    "nautilussecondarycolor": "nautilus_second_toggle",
    # add future custom features here
}

# Live memory storage container tracking toggle values (True = custom active, False = inherit/primary)
FEATURE_SWITCH_STATES = {
    "topbarcolor": False,
    "datemenucolor": False,
    "clockcolor": False,
    "nautilusprimarycolor": False,
    "nautilussecondarycolor": False,
}
# Maps your unique 'css_id' fields straight to their exact matching SVG __TOKENS__
COLOR_REGISTRY_MAP = {
    # Home Page Rows
    "primary": "__PRIMARY__",
    "secondary": "__SECONDARY__",
    "accent": "__ACCENT__",
    "text": "__TEXT__",
    # Advanced GNOME Options Rows (Add new custom rows right here!)
    "topbarcolor": "__TOPBAR__",
    "datemenucolor": "__DATEMENU__",  # Example: Simply add lines here to expand your app!
    "panelcolor": "__PANEL__",  # Example
}

LAST_SELECTED_THEME = {"last_theme": "none"}


_RUNTIME_CACHE = {"custom_colors": {}}


def get_default_color_map():
    # Your baseline default configuration parameters
    defaults = {
        "primary": "#3584e4",
        "secondary": "#241f31",
        "topbarcolor": "#1a4d8c",
        "accent": "#133863",
        "text": "#f9f9f9",
        "datemenucolor": "#102f54",
        "clockcolor": "#f9f9f9",
        "nautilusprimarycolor": "#f9f9f9",
        "nautilussecondarycolor": "#f9f9f9",
    }
    # Layer your active dynamic adjustments cleanly on top
    defaults.update(_RUNTIME_CACHE["custom_colors"])
    return defaults


def update_runtime_color_map(new_colors):
    """Safely preserves values in global module memory storage."""
    if isinstance(new_colors, dict):
        _RUNTIME_CACHE["custom_colors"].update(new_colors)
