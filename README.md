# Color-My-GNOME
A simple tool for creating custom colored gnome-shell, and GTK app themes, with options for creating vesktop, Zen-browser, and youtube themes with your colors!<br>
Allowing for easy and uniform customization of the shell colors and gtk apps on GNOME

<img src="https://github.com/user-attachments/assets/6422dd01-cafa-432b-8a62-0f71a348aa6f" width="50%"/>




## Requriements:
 * GNOME 49 (may work on older versions)
 * GNOME TWEAKS
    *  [GITHUB](https://github.com/GNOME/gnome-tweaks) 
    * Ubuntu/Debian: `sudo apt install gnome-tweaks`
 * GNOME User Themes extension
    * [GNOME Extensions](https://extensions.gnome.org/extension/19/user-themes/) 
## Dependencies:
 * NPM
 * Sass

## Install:

```
git clone https://github.com/Schwarzen/Color-My-Gnome.git
cd Color-My-Gnome
make install 
```

Color My GNOME installs into ~/.local/bin which may not be automatically included in the PATH of some distributions like Arch linux,<br>
please add <br>
`export PATH="$HOME/.local/bin:$PATH"`<br>
to your .bashrc and run <br>
`. ~/.bashrc`<br>
to refresh <br>

## Usage:

Open the Color-My-Gnome gui and either create a new profile, or select an existing to edit/apply. <br>

<img width="35%" alt="image" src="https://github.com/user-attachments/assets/b264b047-a5d1-4c03-8eeb-70a8fe99a6d7" /> <br>

Or 

Run the command <br>

`color-my-gnome` <br>

If you prefer the cli <br>

You will then have the option to either create a new color profile or choose from an existing color profile to swap to.<br>
<p align="center">
<img width="45%" alt="Screenshot From 2025-12-28 15-07-21" src="https://github.com/user-attachments/assets/f98563d6-a557-4e3a-af27-689fccaaf776" />
<img width="45%" h alt="Screenshot From 2025-12-28 15-08-27" src="https://github.com/user-attachments/assets/ce7c7a98-9ac0-4afe-b48e-431fcf4fdecd" />
</p>

Color My GNOME currently has these features: <br>
* Picking hex color values for <br>
  * Primary (main color used on top bar, window bar, and main window elements)
  * Secondary (used for window backgrounds and some accents)
  * Tertiary (used mostly for accents and some backgrounds)
  * Text color.<br>
* Option to pick a specific color for: 
  * the Date/Time
  * the top bar icons
  * the top bar background
* Transparent top bar background
* Apply colors to Zen browser, Youtube, and vesktop <br>

Once the theme has finished compiling open the gnome tweaks application, and change your shell theme to "Color-My-Gnome" and enjoy!<br>
Some apps may require logging out to refresh their colors. <br>

Color my GNOME is still being tested, please backup any important files and use with caution. Color my GNOME only alters the files it comes with, <br>
and only creates files in the Zen-browser theme folder that reference the css files created by Color my GNOME.

## Uninstall

navigate to the directory where you cloned the files 

 ```
make uninstall
make clean
```
## Screenshots:

<p align="center">
<img width="45%" alt="Screenshot From 2025-12-28 15-07-21" src="https://github.com/user-attachments/assets/f4ddcbc8-d34d-4cd9-9354-94787883f6dd" />
<img width="45%" h alt="Screenshot From 2025-12-28 15-08-27" src="https://github.com/user-attachments/assets/ffb83776-ec5a-454d-bd59-6a097dcfc8a8" />
</p>




<img width="3829" height="2159" alt="Screenshot From 2025-12-26 03-28-56" src="https://github.com/user-attachments/assets/806b1c99-3115-4ee7-868c-cdaf90a2a204" />

