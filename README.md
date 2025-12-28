# Color-My-GNOME
A simple cli tool for changing the colors of the gnome-shell and gtk apps on GNOME

<img src="https://github.com/user-attachments/assets/c8d13075-4571-4e77-8eb8-7a46b6ff5945" width="50%"/>


## Requriements:
 * GNOME 49 (may work on older versions)
 * GNOME TWEAKS - [GITHUB](https://github.com/GNOME/gnome-tweaks) 
    * Ubuntu/Debian: `sudo apt install gnome-tweaks`
## Dependencies:
 * NPM
 * Sass

## Install:

```
git clone https://github.com/Schwarzen/Color-My-Gnome.git
cd /Color-My-Gnome
make install 
```

Color My GNOME installs into ~/.local/bin which may not be automatically included in the PATH of some distrobutions like Arch linux,<br>
please add `export PATH="$HOME/.local/bin:$PATH"`<br>
to your .bashrc and run <br>
`. ~/.bashrc`<br>
to refresh <br>

## Usage:

Run the command <br>
`color-my-gnome` <br>
You will then have the option to either create a new color profile or choose from an existing color profile to swap to.<br>
<p align="center">
<img width="45%" alt="Screenshot From 2025-12-28 15-07-21" src="https://github.com/user-attachments/assets/f98563d6-a557-4e3a-af27-689fccaaf776" />
<img width="45%" h alt="Screenshot From 2025-12-28 15-08-27" src="https://github.com/user-attachments/assets/ce7c7a98-9ac0-4afe-b48e-431fcf4fdecd" />
</p>

Color My Gnome currently supports picking hex color values for four different elements:<br>
Primary, Secondary, Tertiary, as well as a Text color.<br>
There is also an option to pick a specific color for the Date/Time, the top bar icons, and the top bar background, as well as the option to make the top bar background completely transparent.<br>

## Screenshots:

<img width="3834" height="2159" alt="Screenshot From 2025-12-26 02-16-51" src="https://github.com/user-attachments/assets/f4ddcbc8-d34d-4cd9-9354-94787883f6dd" />

<img width="3829" height="2159" alt="Screenshot From 2025-12-26 03-22-47" src="https://github.com/user-attachments/assets/ffb83776-ec5a-454d-bd59-6a097dcfc8a8" />

<img width="3829" height="2159" alt="Screenshot From 2025-12-26 03-28-18" src="https://github.com/user-attachments/assets/37e2c4c3-f1dc-414f-934e-4eb374c090ae" />

<img width="3829" height="2159" alt="Screenshot From 2025-12-26 03-28-56" src="https://github.com/user-attachments/assets/806b1c99-3115-4ee7-868c-cdaf90a2a204" />

