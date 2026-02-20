# Color-My-Desktop
An easy to use tool for creating, managing, and applying custom color palettes to an auto generated gnome-shell/ KDE-Plasma / GTK apps theme. With options for creating/applying Vesktop, Zen-browser, and Youtube themes with your colors,<br>
allowing for easy and uniform customization of your desktop environment.

<img src="https://github.com/user-attachments/assets/6422dd01-cafa-432b-8a62-0f71a348aa6f" width="60%"/>


## Table of Contents
* [Requirements](#requirements)
* [How to Install](#install)
* [Usage Instructions](#usage)
* [First Time Setup](#first-time-setup)
* [Features](#features)
* [Finishing Steps](#finishing-steps)
* [Screenshots](#screenshots)
  

# Requirements:

### GNOME
 * GNOME 49 (may work on older versions)
 * GNOME TWEAKS
    *  [GITHUB](https://github.com/GNOME/gnome-tweaks) 
    * Ubuntu/Debian: `sudo apt install gnome-tweaks`
 * GNOME User Themes extension
    * [GNOME Extensions](https://extensions.gnome.org/extension/19/user-themes/)
  
### KDE

 * KDE-Plasma 6

# Install:

For a permission free, fully sandboxed, flatpak version please download from flathub

<a href="https://flathub.org/en/apps/io.github.schwarzen.colormydesktop">
  <img src="https://raw.githubusercontent.com/flathub-infra/assets/refs/heads/main/buttons/template/download.svg" width="240"/>
</a>

&nbsp;


If you prefer a non-sandbox native install, download the latest stable release from github and build from source


<a href="https://github.com/Schwarzen/colormydesktop/releases/latest">
   <img src="https://img.shields.io" height="40" alt="Latest Release"/>
</a>

&nbsp;

After downloading, navigate into the unpacked folder and run

```
make install 
```

Color My Desktop installs into ~/.local/bin which may not be automatically included in the PATH of some distributions like Arch linux,<br>
please add <br>
`export PATH="$HOME/.local/bin:$PATH"`<br>
to your .bashrc and run <br>
`. ~/.bashrc`<br>
to refresh <br>

# Usage:


Open the Color-My-Desktop gui and either create a new profile, or select an existing to edit/apply. <br>


<p>
      <img width="60%" src="https://raw.githubusercontent.com/Schwarzen/colormydesktop/assets/ss0.png" />
</p>

Then select which platforms/apps you want to generate themes for and press the build and apply button.

# First time setup:


* GNOME

* KDE Plasma 

* Zen-browser themes

   * Zen-broswer requires an initial one time configuration to apply themes<br>
   * these instructions are included in the application aswell.
   
     First you will need to enable user themes for zen. In your browser enter `about:config` into the url bar and search for `toolkit.legacyUserProfileCustomizations.stylesheets` <br>
          click the arrow to set the value to "true" <br>

     Then In your browser enter `about:profiles` into your url bar, look for the profile currently in use and click the "Open Directory" button <br>
     open your "chrome" directory and copy the path to your "chrome" directory.

     Finally in the Color My Desktop app, open the zen-browser permission dialog and paste the path of your current profiles chrome directory into the box as prompted.
     You will now be able to correctly select this path in the app for exporting your custom zen themes.


# Features:

Color My Desktop currently has these features: <br>
* Picking hex color values for <br>
  * Primary (main color used on top bar, window bar, and main window elements)
  * Secondary (used for window backgrounds and some accents)
  * Tertiary (used mostly for accents and some backgrounds)
  * Text color.<br>
* Apply colors to / create themes for
  
   * <details>
        <summary>GNOME</summary>

        <p align="center">
        <img src="https://raw.githubusercontent.com/Schwarzen/Color-My-Desktop/assets/ss3.png" width="48%"/>
        <img src="https://raw.githubusercontent.com/Schwarzen/Color-My-Desktop/assets/ss4.png" width="48%"/>
        </p>

      </details>
   * KDE-Plasma
   * <details>
        <summary>Zen-browser</summary>

      * Zen-broswer requires an initial one time configuration to apply themes<br>
      * these instructions are included in the application aswell.
      
        First you will need to enable user themes for zen. In your browser enter `about:config` into the url bar and search for `toolkit.legacyUserProfileCustomizations.stylesheets` <br>
             click the arrow to set the value to "true" <br>
   
        Then In your browser enter `about:profiles` into your url bar, look for the profile currently in use and click the "Open Directory" button <br>
        open your "chrome" directory and copy the path to your "chrome" directory.
   
        Finally in the Color My Desktop app, open the zen-browser permission dialog and paste the path of your current profiles chrome directory into the box as prompted.
        You will now be able to correctly select this path in the app for exporting your custom zen themes.

       
      </details>


   * <details>
        <summary>Youtube (Zen browser only)</summary>

        <p align="center">
        <img src="https://raw.githubusercontent.com/Schwarzen/Color-My-Desktop/assets/ss6.png" width="48%"/>
        <img src="https://raw.githubusercontent.com/Schwarzen/Color-My-Desktop/assets/ss5.png" width="48%"/>
        </p>

      </details>

   * <details>
        <summary>Vesktop</summary>

        <p align="center">
        <img src="https://raw.githubusercontent.com/Schwarzen/Color-My-Desktop/assets/ss9.png" width="48%"/>
        <img src="https://raw.githubusercontent.com/Schwarzen/Color-My-Desktop/assets/ss10.png" width="48%"/>
        </p>

      </details>
   * Papirus Icons
   * <details>
        <summary>GTK4 Apps</summary>
      
        <img src="https://raw.githubusercontent.com/Schwarzen/Color-My-Desktop/assets/ss2.png" width="75%" />
      </details>










<br clear="left" />

# Finishing steps:

* GNOME
   * For regular installs auto apply/refresh is enabled by default for GNOME shell themes (requires setup in flatpak installs), if not using auto apply/refresh, you will need to set the theme manually.
   * To manually change themes, once the theme has finished compiling, open the gnome tweaks application and change your shell theme to "Color-My-Desktop"<br>
     Some apps may require logging out to refresh their colors. <br>

* KDE
   * For regular installs auto apply/refresh is enabled by default for Plasma themes (requires setup in flatpak installs), if not using auto apply/refresh, you will need to set the theme manually.
   * Once the theme has finished compiling, open the system settings, navigate to the "Colors & Themes" and change your "Colors" and "Plasma Style" to Color-My-Desktop.  <br>

* Vesktop
   * The path for Vesktops theme folder will be automatically determined regardless of its installation method (flatpak), simply go to "User Settings" > "Themes <br>
     and press the "load missing themes" button, then activate the Color-My-Desktop theme.

* Zen-browser/youtube
   * Please make sure you complete the Zen-browser/youtube initial setup, the Zen-browser themes will then autmatically refresh after the browser is closed and re-opened






Color My Desktop is still being tested, please backup any important files and use with caution. Color My Desktop only alters the files it comes with, <br>
and only creates files in the Zen-browser theme folder that reference the css files created by Color My Desktop.

## Uninstall

navigate to the directory where you cloned the files 

 ```
make uninstall
make clean
```
# Screenshots:

<p align="center">
<img width="45%" alt="Screenshot From 2025-12-28 15-07-21" src="https://github.com/user-attachments/assets/f4ddcbc8-d34d-4cd9-9354-94787883f6dd" />
<img width="45%" h alt="Screenshot From 2025-12-28 15-08-27" src="https://github.com/user-attachments/assets/ffb83776-ec5a-454d-bd59-6a097dcfc8a8" />
</p>



<img width="3839" height="2159" alt="ss1" src="https://github.com/user-attachments/assets/61e6643a-3d71-4cda-9a94-1d54a00563b8" />

<img width="3839" height="2159" alt="ss4" src="https://github.com/user-attachments/assets/6cc2f536-25cf-4737-be39-5c29e786ac6a" />
<img width="3839" height="2159" alt="ss5" src="https://github.com/user-attachments/assets/8974ce27-5f73-41b9-abfc-dfa855735854" />




