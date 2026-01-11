#!/bin/bash

TARGET_DIR="$HOME/.local/share/Color-My-Desktop/scss"
# Set your default values here
DEF_P="#3584e4"   # GNOME Blue
DEF_S="#241f31" # Dark Gray
DEF_T="#1e1e1e"  # Deep Black
DEF_TXT="#f9f9f9"      # White
main_scss="gnome-shell.scss"
temp_scss=$(mktemp --suffix=".scss")


gtk4_scss="gtk4.scss"
output_css="$HOME/.local/share/themes/Color-My-Desktop/gnome-shell/gnome-shell.css"
output_gtk4_css="$HOME/.config/gtk-4.0/gtk.css"
output_gtk4dark_css="$HOME/.config/gtk-4.0/gtk-dark.css"
SCSS_DIR="$HOME/.local/share/Color-My-Desktop/scss"
youtube_scss="$HOME/.local/share/Color-My-Desktop/scss/youtube.scss"
output_youtube="$HOME/.local/share/Color-My-Desktop/scss/youtube.css"
zen_scss="$HOME/.local/share/Color-My-Desktop/scss/zen.scss"
output_zen="$HOME/.local/share/Color-My-Desktop/scss/zen.css"
vencord_scss="$HOME/.local/share/Color-My-Desktop/scss/vencord.theme.scss"
output_vencord="$HOME/.config/vesktop/themes/vencord.theme.css"
KDEcore="$HOME/.local/share/Color-My-Desktop/KDE/Color-My-Desktop"
output_KDE="$HOME/.local/share/plasma/look-and-feel"
KDEtheme="$HOME/.local/share/Color-My-Desktop/KDE/Color-My-Desktop-Plasma"
output_KDEtheme="$HOME/.local/share/plasma/desktoptheme"
KDEcolors="$HOME/.local/share/Color-My-Desktop/KDE/Color-My-Desktop-Scheme.colors"
output_KDEcolors="$HOME/.local/share/color-schemes/Color-My-Desktop-Scheme.colors"

ZEN_BASE_MANUAL="$HOME/.zen"
ZEN_BASE_FLATPAK="$HOME/.var/app/app.zen_browser.zen/zen"

CSS_IMPORT_LINE="@import url(\"file://$HOME/.local/share/Color-My-Desktop/scss/youtube.css\");
@-moz-document domain(youtube.com) {

}"

CSS_IMPORT_LINE2="@import url(\"file://$HOME/.local/share/Color-My-Desktop/scss/zen.css\");"

DIRS=(
    "$ZEN_CHROME_DIR"
    "$HOME/.config/vesktop/theme"
)

# --- EXPLICIT ARGUMENT MAPPING ---
GUI_NAME="$1"
GUI_PRIMARY="$2"
GUI_SECONDARY="$3"
GUI_TERTIARY="$4"
GUI_TEXT="$5"
GUI_ZEN_TOGGLE="$6"
GUI_TOPBAR_TOGGLE="$7"
GUI_TOPBAR_HEX="$8"        # Check if this is truly the color
GUI_CLOCK_TOGGLE="$9"
GUI_CLOCK_HEX="${10}"      # Check if this is truly the color
GUI_TRANS_TOGGLE="${11}"
GUI_ALPHA="${12}"
GUI_ICON_SYNC="${13}"
GUI_GNOME_TOGGLE="${17}"
GUI_GTK4_TOGGLE="${18}"
GUI_KDE_TOGGLE="${19}"
GUI_YT_TOGGLE="${20}"
GUI_VESKTOP_TOGGLE="${21}"

VENV="$HOME/.local/share/Color-My-Desktop/.venv/bin"

# 1. Detect environment
if [ -f "/.flatpak-info" ]; then
    # We are in a Flatpak! Use the path in the sandbox.
    SASS="/app/bin/sass"
else
    # We are native and have a local venv!
    SASS="$VENV/sass"

fi

# 2. Safety check
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

custom_top_bar_logic() {
   
if [ -n "$PROFILE_NAME" ]; then
    # --- MODE: GUI (Python) ---
    if [ "$GUI_TRANS_TOGGLE" -eq 1 ]; then
        APPLY_TRANS=true
        alpha="${GUI_ALPHA_VAL:-0.8}"
    else
        APPLY_TRANS=false
    fi
else
    # --- MODE: TERMINAL (Manual) ---
    read -p "Apply global transparency? (y/n): " trans_choice
    if [[ "$trans_choice" =~ ^[Yy]$ ]]; then
        read -p "Enter alpha value (0.0 to 1.0, e.g., 0.5): " alpha
        APPLY_TRANS=true
    else
        APPLY_TRANS=false
    fi
fi

# Save the transparency status into a comment at the top of the partial
if [ "$APPLY_TRANS" = true ]; then
    trans_flag="// TRANSPARENT: true ($alpha)"
else
    trans_flag="// TRANSPARENT: false"
fi

if [ "$APPLY_TRANS" = true ]; then
    echo "Applying transparency ($alpha) to main stylesheet..."

    # This regex looks for $primary, $secondary, or $tertiary.
    # It uses a 'negative lookbehind' logic (simulated in sed) 
    # to ensure it doesn't match if 'rgba(' is already present.
    
    # Wrap $primary, $secondary, $tertiary if NOT already in rgba
    # We target common background variables, excluding $text
    for var in "primary" "secondary" "tertiary"; do
        # regex: replace ' $var' with ' rgba($var, alpha)' 
        # but skip if it preceded by 'rgba('
        sed -i "/BAR_TARGET/! s/\([^a(]\)\$$var/\1rgba(\$$var, $alpha)/g" "$temp_scss"
    done
    
    echo "Transparency applied."
else
    # CLEANUP: If user chose NO, revert rgba($var, x) back to $var
    for var in "primary" "secondary" "tertiary" "topbar-color" "clock-color"; do
        sed -i "s/rgba(\$$var, [0-9.]*)/\$$var/g" "$temp_scss"
    done
fi


# New prompt for Top Bar color
    # Capture arguments passed from the main script call
    # $1 was $7 (Toggle), $2 was $8 (Color Value)
    local gui_toggle="$1"
    local gui_value="$2"

    #  HANDLE THE TOGGLE (USE_CUSTOM_TOPBAR)
if [ -n "$gui_toggle" ]; then
      
        if [ "$gui_toggle" -eq 1 ]; then
    
            USE_CUSTOM_TOPBAR=true
            topbar_val="$gui_value"
        else
            USE_CUSTOM_TOPBAR=false
        fi

# --- HANDLE TOPBAR COLOR REPLACEMENT ---
if [ "$USE_CUSTOM_TOPBAR" = true ]; then
    # This finds the BAR_TARGET line and replaces ANY variable ($...) with $topbar-color
    sed -i '/BAR_TARGET/s/\$[a-zA-Z0-9_-]*/\$topbar-color/' "$temp_scss"
    echo "Top Bar set to custom variable."
else
    # This finds the BAR_TARGET line and replaces ANY variable ($...) with $primary
    sed -i '/BAR_TARGET/s/\$[a-zA-Z0-9_-]*/\$primary/' "$temp_scss"
    echo "Top Bar color reverted to default primary color."
fi
      
    else

read -p "Use a specific background color/transparency for the Top Bar (y/n): " topbar_choice

if [[ "$topbar_choice" =~ ^[Yy]$ ]]; then
    echo "-----------------------------------------------"
    echo "Select a color for the Top Bar:"
    echo "1) Primary ($primary) Default"
    echo "2) Secondary ($secondary)"
    echo "3) Tertiary ($tertiary)"
    echo "4) Text ($text)"
    echo "5) Transparent (rgba(0,0,0,0))"
    echo "6) Enter a custom value (Hex/RGBA)"
    read -p "Selection [1-6]: " topbar_sel

    case $topbar_sel in
        1) topbar_val="\$primary" ;;
        2) topbar_val="\$secondary" ;;
        3) topbar_val="\$tertiary" ;;
        4) topbar_val="\$text" ;;
        5) topbar_val="rgba(0,0,0,0)" ;;
        6) read -p "Enter custom value: " custom_input ;;
        *) echo "Invalid choice, defaulting to \$primary"; topbar_val="\$primary" ;;
    esac
    
  
    

    USE_CUSTOM_TOPBAR=true
else

    USE_CUSTOM_TOPBAR=false
fi

fi

# --- HANDLE TOPBAR COLOR REPLACEMENT ---
if [ "$USE_CUSTOM_TOPBAR" = true ]; then
    # This finds the BAR_TARGET line and replaces ANY variable ($...) with $topbar-color
    sed -i '/BAR_TARGET/s/\$[a-zA-Z0-9_-]*/\$topbar-color/' "$temp_scss"
    echo "Top Bar set to custom variable."
else
    # This finds the BAR_TARGET line and replaces ANY variable ($...) with $primary
    sed -i '/BAR_TARGET/s/\$[a-zA-Z0-9_-]*/\$primary/' "$temp_scss"
    echo "Top Bar color reverted to default primary color."
fi

# New prompt for clock color

    # Capture arguments passed from the main script call
    # $3 was 9 (Toggle), $4 was $10 (Color Value)
    local clock_toggle="$3"
    local clock_value="$4"

if [ -n "$clock_toggle" ]; then
        # ---  RUNNING FROM GUI ---
        if [ "$clock_toggle" -eq 1 ]; then
            USE_CUSTOM_CLOCK=true
            clock_val="$clock_value"
        else
            USE_CUSTOM_CLOCK=false
        fi

# --- HANDLE CLOCK COLOR REPLACEMENT ---
if [ "$USE_CUSTOM_TOPBAR" = true ]; then
    # This finds the BAR_TARGET line and replaces ANY variable ($...) with $topbar-color
    sed -i '/TIME_TARGET/s/\$[a-zA-Z0-9_-]*/\$clock-color/' "$temp_scss"
    echo "Top Bar set to custom variable."
else
    # This finds the BAR_TARGET line and replaces ANY variable ($...) with $primary
    sed -i '/TIME_TARGET/s/\$[a-zA-Z0-9_-]*/\$text/' "$temp_scss"
    echo "Top Bar color reverted to default primary color."
fi
     
    else

 
  
   
read -p "Use a specific color for the Top Bars Date and Time / icons? (y/n): " clock_choice

if [[ "$clock_choice" =~ ^[Yy]$ ]]; then
    echo "-----------------------------------------------"
    echo "Select a color for the Clock:"
    echo "1) Primary ($primary)"
    echo "2) Secondary ($secondary) Default"
    echo "3) Tertiary ($tertiary)"
    echo "4) Text ($text)"
    echo "5) Enter a custom value (Hex/RGBA)"
    read -p "Selection [1-5]: " clock_sel

    case $clock_sel in
        1) clock_val="\$primary" ;;
        2) clock_val="\$secondary" ;;
        3) clock_val="\$tertiary" ;;
        4) clock_val="\$text" ;;
        5) read -p "Enter custom value: " custom_input ;;
        *) echo "Invalid choice, defaulting to \$text"; clock_val="\$text" ;;
    esac
    

    
  
    USE_CUSTOM_CLOCK=true
else

    USE_CUSTOM_CLOCK=false
fi

fi

# --- HANDLE CLOCK COLOR REPLACEMENT ---
if [ "$USE_CUSTOM_TOPBAR" = true ]; then
    # This finds the BAR_TARGET line and replaces ANY variable ($...) with $topbar-color
    sed -i '/TIME_TARGET/s/\$[a-zA-Z0-9_-]*/\$clock-color/' "$temp_scss"
    echo "Top Bar set to custom variable."
else
    # This finds the BAR_TARGET line and replaces ANY variable ($...) with $primary
    sed -i '/TIME_TARGET/s/\$[a-zA-Z0-9_-]*/\$text/' "$temp_scss"
    echo "Top Bar color reverted to default primary color."
fi
}


configure_theme() {
    #  Capture Arguments from Python/CLI

    profile_name="$1"
    primary="$2"
    secondary="$3"
    tertiary="$4"
    text="$5"

 # Check if a profile name was provided via arguments
    if [ -n "$profile_name" ]; then
        echo "Arguments detected. Applying theme: $profile_name"
    
        CONFIRMED=true
    else
        # If no arguments, run the interactive terminal loop
        CONFIRMED=false
        while [ "$CONFIRMED" = false ]; do
            echo "--- Theme Configuration ---"
            read -p "Primary [$DEF_P]: " ip && primary=${ip:-$DEF_P}
            read -p "Secondary [$DEF_S]: " is && secondary=${is:-$DEF_S}
            read -p "Tertiary [$DEF_T]: " it && tertiary=${it:-$DEF_T}
            read -p "Text [$DEF_TXT]: " itxt && text=${itxt:-$DEF_TXT}

            echo -e "\n--- THEME SUMMARY ---"
            echo -n "Primary:   " && show_color "$primary"
            echo -n "Secondary: " && show_color "$secondary"
            echo -n "Tertiary:  " && show_color "$tertiary"
            echo -n "Text:      " && show_color "$text"
            
            read -p "Happy with these? (y/n): " c && [[ "$c" =~ ^[Yy]$ ]] && CONFIRMED=true
        done
    fi

   
    custom_top_bar_logic "$7" "$8" "$9" "${10}"

    if [ "$choice" != "1" ]; then

    #  Create partial file
    printf "%s\n\$primary: %s;\n\$secondary: %s;\n\$tertiary: %s;\n\$text: %s;\n\$tertiary-light: rgba(\$tertiary, 0.25);
     \n\$text-light: rgba(\$text, 0.25);\n\$topbar-color: %s;\n\$clock-color: %s;\n" \
	   "$trans_flag" "$primary" "$secondary" "$tertiary" "$text" "$topbar_val" "$clock_val" > "$partial_file"
  echo "CLI Mode: Saved changes to new partial file."
    else
        echo "GUI Mode: Using pre-saved partial file from ThemeManager."
    fi
}

# Create dir
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR" || { echo "Failed to enter $TARGET_DIR"; exit 1; }

cp "$main_scss" "$temp_scss"

PROFILE_NAME="$1"

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
    
    partial_file="${SCSS_DIR}/_${clean_name}.scss"
     #  Map to clean, hyphen-free Bash variables
    B_PRIMARY="${2:-#3584e4}"
    B_SECONDARY="${3:-#241f31}"
    B_TERTIARY="${4:-#1e1e1e}"
    B_TEXT="${5:-#f9f9f9}"
    B_TOPBAR="${8:-$B_PRIMARY}"  # Fallback to primary if empty
    B_CLOCK="${10:-$B_TEXT}"     # Fallback to text if empty
        # Capture the new arguments ($14 and $15)
    B_NAUTILUS="${14:-$3}" # Fallback to Primary ($2) if empty
    B_DATEMENU="${15:-$2}" # Fallback to Primary ($2) if empty
    B_NAUT_SEC="${16:-$3}"


    {
        printf '$primary: %s;\n' "$B_PRIMARY"
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
    } > "$partial_file"

    echo "Status: Theme partial updated at $partial_file"

  
    configure_theme "$@"


selected_import="$clean_name"



# --- OPTION 2: SELECT EXISTING ---


elif [ "$choice" == "2" ]; then

     

    echo "Available profiles in $SCSS_DIR:"
    # List files, removing underscore and extension for the display
    files=($(ls "$SCSS_DIR" | grep '^_.*\.scss$' | sed 's/^_//;s/\.scss$//'))
    
    if [ ${#files[@]} -eq 0 ]; then
        echo "No partials found! Exiting." && exit 1
    fi

    for i in "${!files[@]}"; do
        echo "$((i+1))) ${files[$i]}"
    done

    read -p "Select a file number: " file_num
    selected_import="${files[$((file_num-1))]}"
    
    if [ -z "$selected_import" ]; then
        echo "Invalid selection." && exit 1
    fi
    selected_import="${files[$((file_num-1))]}"
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
        
        configure_theme

	# Update selected_import in case configure_theme changed the filename
      
        selected_import=$(echo "$partial_file" | sed 's/^_//;s/\.scss$//')
    fi

   else
    echo "Invalid menu choice." && exit 1
fi

  


   
# --- Auto-Detect Transparency from Partial ---
# Look for the // TRANSPARENT: line in the chosen partial
flag_line=$(grep "TRANSPARENT:" "$partial_file")

if [[ "$flag_line" == *"true"* ]]; then
    # Extract the alpha value from the parentheses, e.g., "0.5"
    alpha=$(echo "$flag_line" | grep -oP '\(\K[0-9.]+')
    # Fallback to 0.8 if extraction fails
    alpha=${alpha:-0.8}
    APPLY_TRANS=true
    echo "Partial: Transparency Detected ($alpha)"
else
    APPLY_TRANS=false
    echo "Partial: Solid Colors Detected"
fi


for var in "primary" "secondary" "tertiary" "topbar-color" "clock-color"; do
    sed -i "s/rgba(\$$var, [0-9.]*)/\$$var/g" "$temp_scss"
done

# Re-apply only if the flag was true
if [ "$APPLY_TRANS" = true ]; then
    for var in "primary" "secondary" "tertiary" "topbar-color" "clock-color"; do
        # Skip lines with BAR_TARGET
        sed -i "/BAR_TARGET/! s/\([^a(]\)\$$var/\1rgba(\$$var, $alpha)/g" "$temp_scss"
    done
    echo "Main stylesheet synchronized with transparent partial."
else
    echo "Main stylesheet synchronized with solid partial."
fi



#  Clean existing imports and add new one
import_statement="@use '$HOME/.local/share/Color-My-Desktop/scss/$selected_import' as *;"

if [ -f "$temp_scss" ]; then
    # Delete any line that starts with @import, regardless of the filename
    sed -i '/^@use/d' "$temp_scss"
    echo "Removed previous @use statements from $temp_scss."
else
    touch "$temp_scss"
fi

if [ -f "$gtk4_scss" ]; then
    # Delete any line that starts with @import, regardless of the filename
    sed -i '/^@use/d' "$gtk4_scss"
    echo "Removed previous @use statements from $gtk4_scss."
else
    touch "$gtk4_scss"
fi

if [ -f "$youtube_scss" ]; then
    # Delete any line that starts with @import, regardless of the filename
    sed -i '/^@use/d' "$youtube_scss"
    echo "Removed previous @use statements from $youtube_scss."
else
    touch "$youtube_scss"
fi

if [ -f "$zen_scss" ]; then
    # Delete any line that starts with @import, regardless of the filename
    sed -i '/^@use/d' "$zen_scss"
    echo "Removed previous @use statements from $zen_scss."
else
    touch "$zen_scss"
fi

if [ -f "$zen_scss" ]; then
    # Delete any line that starts with @import, regardless of the filename
    sed -i '/^@use/d' "$vencord_scss"
    echo "Removed previous @use statements from $vencord_scss."
else
    touch "$vencord_scss"
fi

# Append the new import at the top of the file
echo "$import_statement" | cat - "$temp_scss" > temp && mv temp "$temp_scss"

echo "$import_statement" | cat - "$gtk4_scss" > temp && mv temp "$gtk4_scss"

echo "$import_statement" | cat - "$youtube_scss" > temp && mv temp "$youtube_scss"

echo "$import_statement" | cat - "$zen_scss" > temp && mv temp "$zen_scss"

echo "$import_statement" | cat - "$vencord_scss" > temp && mv temp "$vencord_scss"


# --- PAPIRUS RECOLOR LOGIC ---
if [ "$GUI_ICON_SYNC" == "1" ]; then
    SYSTEM_PAPIRUS="/usr/share/icons/Papirus"
    LOCAL_ICONS="$HOME/.local/share/icons"
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
    nautilus -q > /dev/null 2>&1
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
	echo "Checking for Zen Browser profiles..."
    if [ -d "$ZEN_BASE_FLATPAK" ]; then
        ZEN_BASE="$ZEN_BASE_FLATPAK"
    elif [ -d "$ZEN_BASE_MANUAL" ]; then
        ZEN_BASE="$ZEN_BASE_MANUAL"
    else
        echo "Zen Browser profile base directory not found."
        exit 1
    fi

    REL_PATH=$(grep -m 1 "^Path=" "$ZEN_BASE/profiles.ini" | cut -d= -f2)

    if [ -z "$REL_PATH" ]; then
        echo "Could not determine the active Zen profile path."
        exit 1
    fi

    #   Construct the path
    ZEN_CHROME_DIR="$ZEN_BASE/$REL_PATH/chrome"
    echo "Detected Zen Chrome Directory: $ZEN_CHROME_DIR"

    #  ADD the detected path to your DIRS array
    DIRS+=("$ZEN_CHROME_DIR")

    #   Create the folders
    for dir in "${DIRS[@]}"; do
        if [ -n "$dir" ]; then  # Extra safety check: only run if dir is not empty
            mkdir -p "$dir"
        fi
    done
    printf "%s\n" "$CSS_IMPORT_LINE2" > "$ZEN_CHROME_DIR/userChrome.css"
    printf "%s\n" "$CSS_IMPORT_LINE" > "$ZEN_CHROME_DIR/userContent.css"

    echo "Created userChrome.css and userContent.css in $ZEN_CHROME_DIR"
    echo "Compiling YouTube styles..."
    $SASS "$zen_scss" "$output_zen" --style expanded

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


	

	$SASS "$vencord_scss" "$output_vencord" --style expanded
    else
        echo "Skipping Vesktop  styles."
    fi

    #   compile Main and GTK styles


 if [ -n "$PROFILE_NAME" ]; then
    # --- GUI MODE ---
 if [ "$GUI_GNOME_TOGGLE" == "1" ]; then
     apply_gnome="y"
 else
     apply_gnome="n"
 fi

    
    else

	    read -p "Would you like to apply the theme to the gnome-shell? (y/n): " apply_gnome

    fi


    
    #  Compile GNOME CSS if user said 'y'
    if [[ "$apply_gnome" =~ ^[Yy]$ ]]; then
	
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
 if [[ "$apply_kde" =~ ^[Yy]$ ]]; then\

	
     primary_rgb = $(hex_to_rgb "$primary")

     secondary_rgb = $(hex_to_rgb "$secondary")
       tertiary_rgb = $(hex_to_rgb "$tertiary")
     
     text_rgb = $(hex_to_rgb "$text")
     
        echo "Compiling KDE theme"
	cp -r "$KDEcore" "$output_KDE"
	cp -r "$KDEtheme" "$output_KDEtheme"
	cp -r "$KDEcolors" "$output_KDEcolors"

	sed -i "s/text/$text/g; s/primary/$primary/g; s/secondary/$secondary/g; s/tertiary/$tertiary/g" "$output_KDEcolors"
	sed -i "s/text/$text/g; s/primary/$primary/g; s/secondary/$secondary/g;  s/tertiary/$tertiary/g" "$output_KDEtheme/Color-My-Desktop-Plasma/colors"
	sed '/^\(Name\|Id\)/!d' "$output_KDEtheme/Color-My-Desktop-Plasma/metadata.json"

	sed -i "s/breeze-dark/Color-My-Desktop/g" "$output_KDEtheme/Color-My-Desktop-Plasma/metadata.json"
	sed -i "s/Breeze Dark/Color-My-Desktop/g" "$output_KDEtheme/Color-My-Desktop-Plasma/metadata.json"

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

