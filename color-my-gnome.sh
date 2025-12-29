#!/bin/bash

TARGET_DIR="$HOME/.local/share/Color-My-Gnome/scss"

# Create it if it doesn't exist yet, then move inside
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR" || { echo "Failed to enter $TARGET_DIR"; exit 1; }


show_color() {
    local hex=${1#\#} # Remove the '#' if present
    # Extract R, G, and B from hex and convert to decimal
    local r=$((16#${hex:0:2}))
    local g=$((16#${hex:2:2}))
    local b=$((16#${hex:4:2}))
    
    # Print a colored block using background escape sequence \e[48;2;R;G;Bm
    printf "\e[48;2;%d;%d;%dm  \e[0m #%s\n" "$r" "$g" "$b" "$hex"
}



main_scss="gnome-shell.scss"
gtk4_scss="gtk4.scss"
output_css="$HOME/.local/share/themes/Color-My-Gnome/gnome-shell/gnome-shell.css"
output_gtk4_css="$HOME/.config/gtk-4.0/gtk.css"
output_gtk4dark_css="$HOME/.config/gtk-4.0/gtk-dark.css"
SCSS_DIR="$HOME/.local/share/Color-My-Gnome/scss"

# Set your default values here
DEF_PRIMARY="#3584e4"   # GNOME Blue
DEF_SECONDARY="#241f31" # Dark Gray
DEF_TERTIARY="#1e1e1e"  # Deep Black
DEF_TEXT="#f9f9f9"      # White
# ---------------------

echo "Select an option:"
echo "1) Create a NEW color profile"
echo "2) Use an EXISTING profile"
read -p "Selection [1-2]: " choice


if [ "$choice" == "1" ]; then

#  Prompt for names
read -p "Enter NEW color profile name (e.g., light blue): " filename


#  Format partial filename
clean_name=$(echo "$filename" | sed 's/^_//;s/\.scss$//')
partial_file="_${clean_name}.scss"



#  Prompt for variables
CONFIRMED=false

while [ "$CONFIRMED" = false ]; do
echo "-----------------------------------------------"
printf "set primary color or leave blank for default #3584e4 - GNOME Blue %s\n"
read -p "\$primary: " primary
primary=${primary:-$DEF_PRIMARY}
printf "set secondary color or leave blank for default #241f31 - Dark Gray %s\n"
read -p "\$secondary: " secondary
secondary=${secondary:-$DEF_SECONDARY}
printf "set tertiary color or leave blank for default #1e1e1e - Deep Black %s\n"
read -p "\$tertiary: " tertiary
tertiary=${tertiary:-$DEF_TERTIARY}
printf "set text color or leave blank for default #f9f9f9 - White %s\n"
read -p "\$text: " text
text=${text:-$DEF_TEXT}

echo "-----------------------------------------------"
echo "Theme Summary:"
echo -n "Primary:   " && show_color "$primary"
echo -n "Secondary: " && show_color "$secondary"
echo -n "Tertiary:  " && show_color "$tertiary"
echo -n "Text:      " && show_color "$text"
echo "-----------------------------------------------"

read -p "Are you happy with these colors? (y/n): " confirm_choice
    
    if [[ "$confirm_choice" =~ ^[Yy]$ ]]; then
        CONFIRMED=true
    else
        echo -e "\nStarting over..."
        # Optional: clear the screen to keep it clean
        # clear 
    fi
done

read -p "Apply global transparency to background elements? (y/n): " trans_choice

if [[ "$trans_choice" =~ ^[Yy]$ ]]; then
    read -p "Enter alpha value (0.0 to 1.0, e.g., 0.5): " alpha
    APPLY_TRANS=true
else
    APPLY_TRANS=false
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
        sed -i "/BAR_TARGET/! s/\([^a(]\)\$$var/\1rgba(\$$var, $alpha)/g" "$main_scss"
    done
    
    echo "Transparency applied."
else
    # CLEANUP: If user chose NO, we should revert rgba($var, x) back to $var
    for var in "primary" "secondary" "tertiary" "topbar-color" "clock-color"; do
        sed -i "s/rgba(\$$var, [0-9.]*)/\$$var/g" "$main_scss"
    done
fi


# New prompt for Top Bar color
topbar_val="\$primary"
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

#  Handle TOPBAR Color Replacement in main.scss
if [ "$USE_CUSTOM_TOPBAR" = true ]; then
    # Replace $text with $topbar-color on the line containing the BAR_TARGET comment
    sed -i '/BAR_TARGET/s/\$primary/\$topbar-color/' "$main_scss"
    echo "Top Bar set to custom variable."
else
    # Revert to $text if user chose 'no'
    sed -i '/BAR_TARGET/s/\$topbar-color/\$primary/' "$main_scss"
    echo "Top Bar color reverted to default secondary color."
fi

# New prompt for clock color
clock_val="\$secondary"
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
        *) echo "Invalid choice, defaulting to \$text"; clock_val="\$secondary" ;;
    esac
    

    
  
    USE_CUSTOM_CLOCK=true
else

    USE_CUSTOM_CLOCK=false
fi

#  Handle Clock Color Replacement in main.scss
if [ "$USE_CUSTOM_CLOCK" = true ]; then
    # Replace $text with $clock-color on the line containing the TIME_TARGET comment
    sed -i '/TIME_TARGET/s/\$secondary/\$clock-color/' "$main_scss"
    echo "Clock color set to custom variable."
else
    # Revert to $text if user chose 'no'
    sed -i '/TIME_TARGET/s/\$clock-color/\$secondary/' "$main_scss"
    echo "Clock color reverted to default secondary color."
fi




#  Create partial file
printf "%s\n\$primary: %s;\n\$secondary: %s;\n\$tertiary: %s;\n\$text: %s;\n\$tertiary-light: rgba(\$tertiary, 0.25);\n\$text-light: rgba(\$text, 0.25);\n\$topbar-color: %s;\n\$clock-color: %s;\n" \
    "$trans_flag" "$primary" "$secondary" "$tertiary" "$text" "$topbar_val" "$clock_val" > "$partial_file"


selected_import="$clean_name"

elif [ "$choice" == "2" ]; then




    # --- OPTION 2: SELECT EXISTING ---
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
else
    echo "Invalid choice." && exit 1
fi

   partial_file="_${selected_import}.scss" 

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

#  ALWAYS Cleanup first to avoid double-wrapping
for var in "primary" "secondary" "tertiary" "topbar-color" "clock-color"; do
    sed -i "s/rgba(\$$var, [0-9.]*)/\$$var/g" "$main_scss"
done

# 2. Re-apply only if the flag was true
if [ "$APPLY_TRANS" = true ]; then
    for var in "primary" "secondary" "tertiary" "topbar-color" "clock-color"; do
        # Skip lines with BAR_TARGET
        sed -i "/BAR_TARGET/! s/\([^a(]\)\$$var/\1rgba(\$$var, $alpha)/g" "$main_scss"
    done
    echo "Main stylesheet synchronized with transparent partial."
else
    echo "Main stylesheet synchronized with solid partial."
fi



#  Clean existing imports and add new one
import_statement="@use '$HOME/.local/share/Color-My-Gnome/scss/$selected_import' as *;"

if [ -f "$main_scss" ]; then
    # Delete any line that starts with @import, regardless of the filename
    sed -i '/^@use/d' "$main_scss"
    echo "Removed previous @use statements from $main_scss."
else
    touch "$main_scss"
fi

if [ -f "$gtk4_scss" ]; then
    # Delete any line that starts with @import, regardless of the filename
    sed -i '/^@use/d' "$gtk4_scss"
    echo "Removed previous @use statements from $gtk4_scss."
else
    touch "$gtk4_scss"
fi

# Append the new import at the top of the file
echo "$import_statement" | cat - "$main_scss" > temp && mv temp "$main_scss"

echo "$import_statement" | cat - "$gtk4_scss" > temp && mv temp "$gtk4_scss"

#  Compile SCSS to CSS
echo "-----------------------------------------------"
if command -v npx sass &> /dev/null; then
    echo "Compiling $main_scss to $output_css..."
    npx sass "$main_scss" "$output_css" --style expanded
    echo "Compiling to $output_gtk4_css"
    npx sass "$gtk4_scss" "$output_gtk4_css" --style expanded
       echo "Compiling to $output_gtk4dark_css"
       npx sass "$gtk4_scss" "$output_gtk4dark_css" --style expanded
       
else
    echo "Error: 'sass' compiler not found. Install with: npm install -g sass"
fi


