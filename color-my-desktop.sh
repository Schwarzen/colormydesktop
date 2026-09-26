#!/bin/bash
# Copyright 2026 Schwarzen
# SPDX-License-Identifier: Apache-2.0

# default values
DEF_P="#3584e4"   # GNOME Blue
DEF_S="#241f31"   # Dark Gray
DEF_T="#1e1e1e"   # Deep Black
DEF_TXT="#f9f9f9" # White

# --- EXPLICIT ARGUMENT MAPPING ---
GUI_NAME="$1"
GUI_PRIMARY="$2"
GUI_SECONDARY="$3"
GUI_TERTIARY="$4"
GUI_TEXT="$5"
GUI_ZEN_TOGGLE="$6"
GUI_TOPBAR_TOGGLE="$7"
GUI_TOPBAR_HEX="$8"
GUI_CLOCK_TOGGLE="$9"
GUI_CLOCK_HEX="${10}"
GUI_TRANS_TOGGLE="${11}"
GUI_ALPHA="${12}"
GUI_ICON_SYNC="${13}"
GUI_GNOME_TOGGLE="${17}"
GUI_GTK4_TOGGLE="${18}"
GUI_KDE_TOGGLE="${19}"
GUI_YT_TOGGLE="${20}"
GUI_VESKTOP_TOGGLE="${21}"
GUI_GNOME_MENU_TOGGLE="${34}"

#Global

main_scss="gnome-shell.scss"
temp_scss=$(mktemp --suffix=".scss")
gtk4_scss="gtk4.scss"

#  Detect environment
if [ -f "/.flatpak-info" ]; then
  # We are in a Flatpak! Use the path in the sandbox.
  SASS="/app/lib/dart-sass/sass"
  TARGET_DIR="$XDG_DATA_HOME/scss"
  SCSS_DIR="$XDG_DATA_HOME/scss"
  KDEcore="/app/share/color-my-desktop/KDE/Color-My-Desktop"
  KDEtheme="/app/share/color-my-desktop/KDE/Color-My-Desktop-Plasma"
  KDEcolors="/app/share/color-my-desktop/KDE/Color-My-Desktop-Scheme.colors"

  youtube_scss="$XDG_DATA_HOME/scss/youtube.scss"
  zen_scss="$XDG_DATA_HOME/scss/zen.scss"
  vencord_scss="$XDG_DATA_HOME/scss/Color-My-Desktop.scss"

  CSS_IMPORT_LINE="@import url(\"youtube.css\");
@-moz-document domain(youtube.com) {

}"

  CSS_IMPORT_LINE2="@import url(\"zen.css\");"

  # OUTPUTS
  output_KDE="${23}/look-and-feel"
  output_KDEtheme="${22}/desktoptheme"
  output_KDEcolors="${23}/Color-My-Desktop-Scheme.colors"

  output_css="${24}/Color-My-Desktop/gnome-shell/gnome-shell.css"
  output_gtk4_css="${27}/gtk.css"
  output_gtk4dark_css="${27}/gtk-dark.css"
  output_vencord="${26}/Color-My-Desktop.css"
  output_zen="${25}/zen.css"
  output_youtube="${25}/youtube.css"

else
  # We are native and have a local venv!
  VENV="$HOME/.local/share/color-my-desktop/.venv/bin"
  SASS="$VENV/sass"
  TARGET_DIR="$HOME/.local/share/color-my-desktop/scss"
  SCSS_DIR="$HOME/.local/share/color-my-desktop/scss"
  KDEcore="$HOME/.local/share/color-my-desktop/KDE/Color-My-Desktop"
  KDEtheme="$HOME/.local/share/color-my-desktop/KDE/Color-My-Desktop-Plasma"
  KDEcolors="$HOME/.local/share/color-my-desktop/KDE/Color-My-Desktop-Scheme.colors"

  youtube_scss="$HOME/.local/share/color-my-desktop/scss/youtube.scss"
  zen_scss="$HOME/.local/share/color-my-desktop/scss/zen.scss"
  vencord_scss="$HOME/.local/share/color-my-desktop/scss/Color-My-Desktop.scss"

  # OUTPUTS
  output_KDE="$HOME/.local/share/plasma/look-and-feel"
  output_KDEtheme="$HOME/.local/share/plasma/desktoptheme"
  output_KDEcolors="$HOME/.local/share/color-schemes/Color-My-Desktop-Scheme.colors"
  output_css="$HOME/.local/share/themes/Color-My-Desktop/gnome-shell/gnome-shell.css"
  output_gtk4_css="$HOME/.config/gtk-4.0/gtk.css"
  output_gtk4dark_css="$HOME/.config/gtk-4.0/gtk-dark.css"
  output_vencord="$HOME/.config/vesktop/themes/Color-My-Desktop.css"
  output_zen="${25}/zen.css"
  output_youtube="${25}/youtube.css"

  CSS_IMPORT_LINE="@import url(\"youtube.css\");
@-moz-document domain(youtube.com) {

}"

  CSS_IMPORT_LINE2="@import url(\"zen.css\");"

fi

#  Safety check
if [ ! -x "$SASS" ]; then
  echo "Error: Sass compiler not found at $SASS"
  exit 1
fi

# --- METADATA (For the Partial File) ---
if [ "$APPLY_TRANS" = true ]; then
  trans_flag="// TRANSPARENT: true ($alpha)"
else
  trans_flag="// TRANSPARENT: false"
fi

# --------------------- Functions

get_val() {
  # Looks for "$variable: value;" and returns just the value
  grep "\$$1:" "$partial_file" | sed "s/.*\$$1: \(.*\);/\1/"
}

show_color() {
  local hex=${1#\#} # Remove the '#' if present
  # Extract R, G, and B from hex and convert to decimal
  local r=$((16#${hex:0:2}))
  local g=$((16#${hex:2:2}))
  local b=$((16#${hex:4:2}))

  # Print a colored block using background escape sequence \e[48;2;R;G;Bm
  printf "\e[48;2;%d;%d;%dm  \e[0m #%s\n" "$r" "$g" "$b" "$hex"
}

compile_themes() {
  #  Clean existing imports and add new one
  import_statement="@use '$SCSS_DIR/$selected_import' as *;"

  # Append the new import at the top of the file

  # --- PAPIRUS RECOLOR LOGIC ---
  if [ "$GUI_ICON_SYNC" == "1" ]; then
    SYSTEM_PAPIRUS="${28}/Papirus"
    LOCAL_ICONS="${28}"
    CUSTOM_THEME="Papirus-Custom"
    LOCAL_PAPIRUS="$LOCAL_ICONS/$CUSTOM_THEME"

    echo "Status: Syncing Papirus icons to theme colors..."

    #  Ensure local copy exists
    if [ ! -d "$LOCAL_PAPIRUS" ]; then
      mkdir -p "$LOCAL_ICONS"
      cp -r "$SYSTEM_PAPIRUS" "$LOCAL_PAPIRUS"
      sed -i "s/Name=Papirus/Name=$CUSTOM_THEME/" "$LOCAL_PAPIRUS/index.theme"
    fi

    #  CLEANUP: Delete any accidental multi-extension files before starting
    find "$LOCAL_PAPIRUS" -name "*.svg.svg*" -delete

    echo "Syncing Papirus Icons (Targeting blue icons)..."

    #  THE LOOP
    #  exclude any files already containing 'cmg' to prevent recursion
    find "$LOCAL_PAPIRUS" -type f -name "*blue*.svg" ! -name "*cmg*" | while read -r blue_file; do

      # Precise replacement: only replace 'blue' at the end of the filename, not in paths
      # This prevents the .svg.svg.svg issue
      cmg_file="${blue_file%-blue.svg}-cmg.svg"

      # If the file hasn't changed, don't waste time copying

      cp -f "$blue_file" "$cmg_file"

      # THE MEGA-SED (Scoped to the new CMG file)
      sed -i \
        "s/#5294e2/$primary/gI; s/fill:#5294e2/fill:$primary/gI; s/stop-color:#5294e2/stop-color:$primary/gI; \
         s/#84afea/$text/gI; s/fill:#84afea/fill:$text/gI; s/stop-color:#84afea/stop-color:$text/gI; \
         s/#2e6bb4/$secondary/gI; s/fill:#2e6bb4/fill:$secondary/gI; s/stop-color:#2e6bb4/stop-color:$secondary/gI; \
         s/#4877b1/$primary/gI; s/fill:#4877b1/fill:$primary/gI; s/stop-color:#4877b1/stop-color:$primary/gI" \
        "$cmg_file"

      #  SYMLINK
      #  get the directory and the base name without the extension
      dir_name=$(dirname "$blue_file")
      # Get filename without '-blue.svg'
      base_name=$(basename "$blue_file" "-blue.svg")

      # Redirect the generic symlink (e.g. folder.svg) to our custom file (e.g. folder-cmg.svg)
      # This must be done inside the directory to avoid path errors
      (cd "$dir_name" && ln -sf "${base_name}-cmg.svg" "${base_name}.svg")

    done

    echo "Icon sync complete. Refreshing icon cache..."
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/Papirus-Custom" 2>/dev/null || true
    # Force Nautilus to reload the new symlink targets
    nautilus -q >/dev/null 2>&1
    echo "Status: Icons synced successfully with custom profile."
  fi

  #  Compile SCSS to CSS

  #  Determine zen toggle
  if [ -n "$PROFILE_NAME" ]; then
    # --- GUI MODE ---
    if [ "$GUI_ZEN_TOGGLE" == "1" ]; then
      apply_zen="y"
    else
      apply_zen="n"
    fi
  else

    read -p "Would you like to apply the Zen Browser (y/n): " apply_zen

  fi

  #  Compile YouTube CSS if user said 'y'
  if [[ "$apply_zen" =~ ^[Yy]$ ]]; then

    if [ -f "$zen_scss" ]; then
      # Delete any line that starts with @import, regardless of the filename
      sed -i '/^@use/d' "$zen_scss"
      echo "Removed previous @use statements from $zen_scss."
    else
      touch "$zen_scss"
    fi

    echo "$import_statement" | cat - "$zen_scss" >temp && mv temp "$zen_scss"

    printf "%s\n" "$CSS_IMPORT_LINE2" >"${25}/userChrome.css"

    echo "Compiling Zen styles to ${25}/userChrome.css..."
    $SASS "$zen_scss" "$output_zen" --style expanded
  else
    echo "Skip Zen"
  fi

  if [ -n "$PROFILE_NAME" ]; then
    # --- GUI MODE ---
    if [ "$GUI_YT_TOGGLE" == "1" ]; then
      apply_yt="y"
    else
      apply_yt="n"
    fi
  else

    read -p "Would you like to apply the colors to the Youtube webpage (Zen only) (y/n): " apply_yt

  fi

  if [[ "$apply_yt" =~ ^[Yy]$ ]]; then

    if [ -f "$youtube_scss" ]; then
      # Delete any line that starts with @import, regardless of the filename
      sed -i '/^@use/d' "$youtube_scss"
      echo "Removed previous @use statements from $youtube_scss."
    else
      touch "$youtube_scss"
    fi

    echo "$import_statement" | cat - "$youtube_scss" >temp && mv temp "$youtube_scss"

    printf "%s\n" "$CSS_IMPORT_LINE" >"${25}/userContent.css"

    $SASS "$youtube_scss" "$output_youtube" --style expanded

  else
    echo "Skipping youtube"

  fi

  if [ -n "$PROFILE_NAME" ]; then
    # --- GUI MODE ---
    if [ "$GUI_VESKTOP_TOGGLE" == "1" ]; then
      apply_vesktop="y"
    else
      apply_vesktop="n"
    fi

  else

    read -p "Would you like to apply the colors to Vesktop/Vencord (y/n): " apply_vesktop

  fi

  if [[ "$apply_vesktop" =~ ^[Yy]$ ]]; then

    if [ -f "$vencord_scss" ]; then
      # Delete any line that starts with @import, regardless of the filename
      sed -i '/^@use/d' "$vencord_scss"
      echo "Removed previous @use statements from $vencord_scss."
    else
      touch "$vencord_scss"
    fi

    echo "$import_statement" | cat - "$vencord_scss" >temp && mv temp "$vencord_scss"

    echo "Compiling Vesktop"

    $SASS "$vencord_scss" "$output_vencord" --style expanded
  else
    echo "Skipping Vesktop  styles."
  fi

  #   compile Main and GTK styles

  # --- GUI MODE ---
  if [ "$GUI_GNOME_TOGGLE" == "1" ]; then
    apply_gnome="y"
  else
    apply_gnome="n"
  fi

  #  Compile GNOME CSS if user said 'y'
  if [[ "$apply_gnome" =~ ^[Yy]$ ]]; then

    # Create dir
    mkdir -p "$TARGET_DIR"
    cd "$TARGET_DIR" || {
      echo "Failed to enter $TARGET_DIR"
      exit 1
    }

    cp "$main_scss" "$temp_scss"

    # clean imports

    if [ -f "$temp_scss" ]; then
      # Delete any line that starts with @import, regardless of the filename
      sed -i '/^@use/d' "$temp_scss"
      echo "Removed previous @use statements from $temp_scss."
    else
      touch "$temp_scss"
    fi
    echo "$import_statement" | cat - "$temp_scss" >temp && mv temp "$temp_scss"

    echo "Compiling $temp_scss to $output_css..."
    $SASS "$temp_scss" "$output_css" --style expanded

  else
    echo "Skipping gnome-shell"

  fi

  if [ -n "$PROFILE_NAME" ]; then
    # --- GUI MODE ---
    if [ "$GUI_KDE_TOGGLE" == "1" ]; then
      apply_kde="y"
    else
      apply_kde="n"
    fi

  else

    read -p "Would you like to apply the theme to KDE ? (y/n): " apply_kde

  fi

  #  Compile KDE if user said 'y'
  if [[ "$apply_kde" =~ ^[Yy]$ ]]; then

    echo "Compiling KDE theme"
    cp -r "$KDEcore" "$output_KDE"
    cp -r "$KDEtheme" "$output_KDEtheme"
    cp -r "$KDEcolors" "$output_KDEcolors"

    sed -i "s/text/$text/g; s/primary/$primary/g; s/secondary/$secondary/g; s/tertiary/$tertiary/g" "$output_KDEcolors"
    sed -i "s/text/$text/g; s/primary/$primary/g; s/secondary/$secondary/g;  s/tertiary/$tertiary/g" "$output_KDEtheme/Color-My-Desktop-Plasma/colors"

  else
    echo "Skipping KDE"

  fi

  if [ -n "$PROFILE_NAME" ]; then
    # --- GUI MODE ---
    if [ "$GUI_GTK4_TOGGLE" == "1" ]; then
      apply_gtk4="y"
    else
      apply_gtk4="n"
    fi

  else

    read -p "Would you like to apply the theme to GTK4 apps? (y/n): " apply_gtk4

  fi

  #  Compile GTK4 CSS if user said 'y'
  if [[ "$apply_gtk4" =~ ^[Yy]$ ]]; then

    # Create dir
    mkdir -p "$TARGET_DIR"
    cd "$TARGET_DIR" || {
      echo "Failed to enter $TARGET_DIR"
      exit 1
    }

    if [ -f "$gtk4_scss" ]; then
      # Delete any line that starts with @import, regardless of the filename
      sed -i '/^@use/d' "$gtk4_scss"
      echo "Removed previous @use statements from $gtk4_scss."
    else
      touch "$gtk4_scss"
    fi

    echo "$import_statement" | cat - "$gtk4_scss" >temp && mv temp "$gtk4_scss"

    echo "Compiling to $output_gtk4_css..."
    $SASS "$gtk4_scss" "$output_gtk4_css" --style expanded

    echo "Compiling to $output_gtk4dark_css..."
    $SASS "$gtk4_scss" "$output_gtk4dark_css" --style expanded

  else
    echo "Skipping GTK4 apps"

  fi

  echo "DEBUG: Name=$1, Primary=$2, TopbarHex=$8, ClockHex=${10}"

  # Remove temp file
  rm "$temp_scss"
}
PROFILE_NAME="$1"

APP_ID="io.github.schwarzen.colormydesktop"

#  Check if the specific app is installed
if flatpak info "$APP_ID" &>/dev/null; then
  flatpak_status="y"
else
  flatpak_status="n"
fi

# --- Option 1: CREATE NEW ---
if [ -z "$PROFILE_NAME" ]; then
  echo "Select an option:"
  echo "1) Create a NEW color profile"
  echo "2) Use an EXISTING profile"
  read -p "Selection [1-2]: " choice
else

  choice="1"

fi

if [ "$choice" == "1" ]; then
  # 1. Determine the filename (from $1 or terminal prompt)
  if [ -n "$1" ]; then
    clean_name=$(echo "$1" | sed 's/^_//;s/\.scss$//')
  else
    read -p "Enter Profile Name: " filename
    clean_name=$(echo "$filename" | sed 's/^_//;s/\.scss$//')
  fi

  # SECTION: UPDATE PARTIAL AND COMPILE
  partial_file="${SCSS_DIR}/_${clean_name}.scss"
  B_PRIMARY="${2:-#3584e4}"
  B_PRIMARY_GRADIENT="${29:-$2}"
  B_TOPBAR_START="${30:-$2}"
  B_TOPBAR_END="${31:-$2}"
  B_GNOME_MENU_START="${32:-$2}"
  B_GNOME_MENU_END="${33:-$2}"
  B_SECONDARY="${3:-#241f31}"
  B_TERTIARY="${4:-#1e1e1e}"
  B_TEXT="${5:-#f9f9f9}"
  B_TOPBAR="${8:-$B_PRIMARY}" # Fallback to primary if empty
  B_CLOCK="${10:-$B_TEXT}"    # Fallback to text if empty
  # Capture the new arguments ($14 and $15)
  B_NAUTILUS="${14:-$3}" # Fallback to Primary ($2) if empty
  B_DATEMENU="${15:-$2}" # Fallback to Primary ($2) if empty
  B_NAUT_SEC="${16:-$3}"
  B_NAUTILUS_START="${35:-$2}"
  B_NAUTILUS_END="${36:-$2}"
  GUI_NAUTILUS_MAINTOGGLE="${37}"
  GUI_NAUTILUS_SECONDTOGGLE="${38}"
  PARTIAL_ONLY_FLAG="${39}"
  SAVE_PALETTE_FLAG="${40}"

  # Check if our gradient variable has a comma separating colors
  if [[ "$B_PRIMARY_GRADIENT" == *","* ]]; then
    CUSTOM_GRAD="yes"

    # Extract the first color before the comma
    GRAD_START=$(echo "$B_PRIMARY_GRADIENT" | cut -d',' -f1 | xargs)
    # Extract the second color after the comma
    GRAD_END=$(echo "$B_PRIMARY_GRADIENT" | cut -d',' -f2 | xargs)
  else
    # Fallback to the same solid color if no comma is present
    GRAD_START="$B_PRIMARY"
    GRAD_END="$B_PRIMARY"
    CUSTOM_GRAD="no"
  fi

  if [[ "$GUI_TOPBAR_TOGGLE" == 1 ]]; then
    CUSTOM_TOPBAR="yes"
  else
    CUSTOM_TOPBAR="no"
  fi
  if [[ "$GUI_CLOCK_TOGGLE" == 1 ]]; then
    CUSTOM_CLOCK="yes"
  else
    CUSTOM_CLOCK="no"
  fi
  if [[ "$GUI_GNOME_MENU_TOGGLE" == 1 ]]; then
    CUSTOM_GNOME_MENU="yes"
  else
    CUSTOM_GNOME_MENU="no"
  fi

  if [[ "$GUI_NAUTILUS_MAINTOGGLE" == 1 ]]; then
    CUSTOM_NAUTILUS_MAIN="yes"
  else
    CUSTOM_NAUTILUS_MAIN="no"
  fi

  if [[ "$GUI_NAUTILUS_SECONDTOGGLE" == 1 ]]; then
    CUSTOM_NAUTILUS_SECOND="yes"
  else
    CUSTOM_NAUTILUS_SECOND="no"
  fi

  {
    printf '$primary: %s;\n' "$B_PRIMARY"
    printf '$panel-grad-start: %s;\n' "$GRAD_START"
    printf '$panel-grad-end: %s;\n' "$GRAD_END"
    printf '$topbar-start: %s;\n' "$B_TOPBAR_START"
    printf '$topbar-end: %s;\n' "$B_TOPBAR_END"
    printf '$gnome-menu-start: %s;\n' "$B_GNOME_MENU_START"
    printf '$gnome-menu-end: %s;\n' "$B_GNOME_MENU_END"
    printf '$nautilus-start: %s;\n' "$B_NAUTILUS_START"
    printf '$nautilus-end: %s;\n' "$B_NAUTILUS_END"
    printf '$secondary: %s;\n' "$B_SECONDARY"
    printf '$tertiary: %s;\n' "$B_TERTIARY"
    printf '$tertiary-light: %s;\n' "rgba(\$tertiary, 0.25)"
    printf '$text: %s;\n' "$B_TEXT"
    printf '$text-light: %s;\n' "rgba(\$text, 0.25)"
    printf '$topbar-color: %s;\n' "$B_TOPBAR"
    printf '$clock-color: %s;\n' "$B_CLOCK"
    printf '$nautilus-main: %s;\n' "$B_NAUTILUS"
    printf '$nautilus-secondary: %s;\n' "$B_NAUT_SEC"
    printf '$system-datemenu: %s;\n' "$B_DATEMENU"
    printf '/*%s;\n'
    printf 'CUSTOM_TOPBAR:%s;\n' "$CUSTOM_TOPBAR"
    printf 'CUSTOM_GNOME_MENU:%s;\n' "$CUSTOM_GNOME_MENU"
    printf 'CUSTOM_NAUTILUS_MAIN:%s;\n' "$CUSTOM_NAUTILUS_MAIN"
    printf 'CUSTOM_NAUTILUS_SECOND:%s;\n' "$CUSTOM_NAUTILUS_SECOND"
    printf 'CUSTOM_CLOCK:%s;\n' "$CUSTOM_CLOCK"
    printf 'CUSTOM_GRAD:%s;\n' "$CUSTOM_GRAD"
    printf '*/%s;\n'
  } >"$partial_file"

  echo "Status: Theme partial updated at $partial_file"

  # =========================================================
  # CONDITIONAL COMPILATION EVALUATION
  # =========================================================

  if [ "$PARTIAL_ONLY_FLAG" = "1" ]; then
    echo "Partial mode detected. Bypassing asset builds."
    if [ "$SAVE_PALETTE_FLAG" = "1" ]; then
      clean_name=$(echo "$1" | sed 's/^_//;s/\.scss$//')
      original_name=$(echo "${41}" | sed 's/^_//;s/\.scss$//')
      echo "renaming $original_name to $clean_name"
      mv -f "$SCSS_DIR/_${original_name}.scss" "$SCSS_DIR/_${clean_name}.scss"
    fi

    selected_import="$clean_name"
    exit 0
  else

    selected_import="$clean_name"
    # Only run full platform asset compiling when flag is NOT 1
    compile_themes
  fi

# --- OPTION 2: SELECT EXISTING ---

elif [ "$choice" == "2" ]; then

  echo "Available profiles in $SCSS_DIR:"
  # List files, removing underscore and extension for the display
  files=($(ls "$SCSS_DIR" | grep '^_.*\.scss$' | sed 's/^_//;s/\.scss$//'))

  if [ ${#files[@]} -eq 0 ]; then
    echo "No partials found! Exiting." && exit 1
  fi

  for i in "${!files[@]}"; do
    echo "$((i + 1))) ${files[$i]}"
  done

  read -p "Select a file number: " file_num
  selected_import="${files[$((file_num - 1))]}"

  if [ -z "$selected_import" ]; then
    echo "Invalid selection." && exit 1
  fi
  selected_import="${files[$((file_num - 1))]}"
  partial_file="_${selected_import}.scss"

  read -p "Would you like to edit '$selected_import' before applying? (y/n): " edit_choice
  if [[ "$edit_choice" =~ ^[Yy]$ ]]; then
    # Extract current values to use as new defaults
    DEF_P=$(get_val "primary")
    DEF_S=$(get_val "secondary")
    DEF_T=$(get_val "tertiary")
    DEF_TXT=$(get_val "text")

    # Load transparency defaults from the header
    flag_line=$(grep "TRANSPARENT:" "$partial_file")
    if [[ "$flag_line" == *"true"* ]]; then
      DEF_TRANS="y"
      DEF_ALPHA=$(echo "$flag_line" | sed 's/.*(\([0-9.]*\)).*/\1/')
    fi

    selected_import=$(echo "$partial_file" | sed 's/^_//;s/\.scss$//')
    compile_themes
  fi

else
  echo "Invalid menu choice." && exit 1
fi
