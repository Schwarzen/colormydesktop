Public API Declaration (SemVer 2.0.0)
As of Version 0.9.0, Color My Desktop defines its Public API through its Command Line Interface (CLI) and its Configuration Schema. Changes to these elements will dictate version increments.
1. Command Line Interface (The "Script Contract")
The CLI is the primary way third-party scripts and the Python GUI interact with the backend. The positional argument order is considered stable within a minor version.
<pre>
The CLI Argument Specification (v0.9.0)

Index   Argument          Format      Default/Fallback      Description
$1      Profile Name      String      Required              Name of the theme (e.g., dracula).
$2      Primary           Hex         #3584e4               The main system color, use on topbars and outer panels.
$3      Secondary         Hex         #241f31               Backgrounds for window content and accents.
$4      Tertiary          Hex         #1e1e1e               Surfaces and accents.
$5      Text              Hex         #f9f9f9               Primary font and icon color.
$6      Zen Toggle        0 or 1      0                     Applies theme to Zen Browser/YouTube.
$7      Topbar Toggle     0 or 1      0                     Enables custom top bar color overrides.
$8      Topbar Hex        Hex         $2                    Custom color value for top bar.
$9      Clock Toggle      0 or 1      0                     Enables custom clock/date menu color.
$10     Clock Hex         Hex         $5                    Custom color for the Shell clock text.
$11     Trans Toggle      0 or 1      0                     Enables global background transparency.
$12     Alpha Value       Float       0.8                   Opacity level for transparent elements.
$13     Icon Sync         0 or 1      0                     Deep-recolors Papirus icon set via SVG.
$14     Nautilus Main     Hex         $2                    Nautilus sidebar and header color.
$15     DateMenu          Hex         $2                    Background of the Shell calendar popover.
$16     Nautilus Sec      Hex         $3                    Nautilus main file view background.
</pre>




3. Configuration Schema (The "Partial Contract")
The structure of the .scss files stored in ~/.local/share/Color-My-Desktop/scss/ is part of the Public API.

    Stable Variables: $primary, $secondary, $tertiary, $text, $topbar-color, $clock-color, $nautilus-main, $nautilus-secondary.
    Stability Guarantee: Renaming these variables is considered a breaking change. Adding new variables to the partial file is considered a backward-compatible addition.

4. Developer Hooks (Internal API)
The interaction between lib_gui.py and color-my-desktop.sh is considered an Internal API. While it is comprehensive, it is subject to change without notice in the 0.x.x phase to facilitate rapid development.
