# Color-My-Desktop
A simple tool for creating, managing, and applying custom color palettes to a custom gnome-shell theme, and GTK apps theme, with options for creating/applying vesktop, Zen-browser, and youtube themes with your colors,<br>
allowing for easy and uniform customization of the shell colors and gtk/(some)non gtk - apps on GNOME

<img src="https://github.com/user-attachments/assets/6422dd01-cafa-432b-8a62-0f71a348aa6f" width="60%"/>




## Requriements:
 * GNOME 49 (may work on older versions)
 * GNOME TWEAKS
    *  [GITHUB](https://github.com/GNOME/gnome-tweaks) 
    * Ubuntu/Debian: `sudo apt install gnome-tweaks`
 * GNOME User Themes extension
    * [GNOME Extensions](https://extensions.gnome.org/extension/19/user-themes/) 

## Install:

```
git clone https://github.com/Schwarzen/Color-My-Desktop.git
cd Color-My-Desktop
make install 
```

Color My Desktop installs into ~/.local/bin which may not be automatically included in the PATH of some distributions like Arch linux,<br>
please add <br>
`export PATH="$HOME/.local/bin:$PATH"`<br>
to your .bashrc and run <br>
`. ~/.bashrc`<br>
to refresh <br>

## Usage:


Open the Color-My-Desktop gui and either create a new profile, or select an existing to edit/apply. <br>


<p>
      <img width="60%" src="https://raw.githubusercontent.com/Schwarzen/Color-My-Desktop/assets/Screenshot%20From%202026-01-06%2023-18-46.png" />
</p>
Or 

Run the command <br>

`color-my-desktop` <br>

If you prefer the cli <br>

You will then have the option to either create a new color profile or choose from an existing color profile to swap to.<br>

### Features:
Color My Desktop currently has these features: <br>
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
* Apply colors to Papirus icons (requires Papirus Icons) <br>
* Apply specific colors to nautilus elements <br>




<img src="https://github.com/user-attachments/assets/1139419e-8ea9-4ad4-b198-0d8ea54a7c5c" width="400" height="600" align="left" />


<img src="https://raw.githubusercontent.com/Schwarzen/Color-My-Desktop/assets/ss2.png" width="75%" />


<br clear="left" />

Once the theme has finished compiling, open the gnome tweaks application and change your shell theme to "Color-My-Desktop"<br>
Some apps may require logging out to refresh their colors. <br>

Color My Desktop is still being tested, please backup any important files and use with caution. Color My Desktop only alters the files it comes with, <br>
and only creates files in the Zen-browser theme folder that reference the css files created by Color My Desktop.

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



<img width="3839" height="2159" alt="ss1" src="https://github.com/user-attachments/assets/61e6643a-3d71-4cda-9a94-1d54a00563b8" />

<img width="3839" height="2159" alt="ss4" src="https://github.com/user-attachments/assets/6cc2f536-25cf-4737-be39-5c29e786ac6a" />
<img width="3839" height="2159" alt="ss5" src="https://github.com/user-attachments/assets/8974ce27-5f73-41b9-abfc-dfa855735854" />




