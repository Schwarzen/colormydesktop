# Color-My-GNOME
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


<p>
      <img width="60%" src="https://github.com/user-attachments/assets/5e5bb232-40fd-45fc-9805-c16279d8c3d6" />
</p>
Or 

Run the command <br>

`color-my-gnome` <br>

If you prefer the cli <br>

You will then have the option to either create a new color profile or choose from an existing color profile to swap to.<br>
<p align="center">
<img width="45%" alt="Screenshot From 2025-12-28 15-07-21" src="https://github.com/user-attachments/assets/f98563d6-a557-4e3a-af27-689fccaaf776" />
<img width="45%" h alt="Screenshot From 2025-12-28 15-08-27" src="https://github.com/user-attachments/assets/ce7c7a98-9ac0-4afe-b48e-431fcf4fdecd" />
</p>

### Features:
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
* Apply colors to Papirus icons (requires Papirus Icons) <br>
* Apply specific colors to nautilus elements <br>



<img src="https://github.com/user-attachments/assets/4ae977ae-4898-43b9-aae3-29d82273a4b3" width="400" height="600" align="left" />


<img src="https://github.com/user-attachments/assets/106e2d48-8827-4515-b56f-09f522bef461" width="25%" />
<img src="https://github.com/user-attachments/assets/1deda1c4-101b-4d85-877d-c0697069a29f" width="25%"  /><br>
<img src="https://github.com/user-attachments/assets/3bc3e076-06fa-4a24-a1c6-cd011d16816a" width="25%"  />
<img src="https://github.com/user-attachments/assets/01314d65-7370-427f-bd11-0487b063ffe1" width="25%"  />


<br clear="left" />

Once the theme has finished compiling, open the gnome tweaks application and change your shell theme to "Color-My-Gnome"<br>
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



<img width="3839" height="2159" alt="ss1" src="https://github.com/user-attachments/assets/61e6643a-3d71-4cda-9a94-1d54a00563b8" />

<img width="3839" height="2159" alt="ss4" src="https://github.com/user-attachments/assets/6cc2f536-25cf-4737-be39-5c29e786ac6a" />
<img width="3839" height="2159" alt="ss5" src="https://github.com/user-attachments/assets/8974ce27-5f73-41b9-abfc-dfa855735854" />




