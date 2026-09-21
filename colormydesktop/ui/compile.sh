#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "🎨 Compiling Blueprint UI files..."

# 1. Main Window
blueprint-compiler compile $PWD/colormydesktop/ui/main_window.blp --output $PWD/colormydesktop/main_window.ui
echo "✓ Compiled main_window.ui"

# 2. Home Page
blueprint-compiler compile $PWD/colormydesktop/ui/page_home.blp --output $PWD/colormydesktop/page_home.ui
echo "✓ Compiled page_home.ui"

# 3. Color Row Item
blueprint-compiler compile $PWD/colormydesktop/ui/color_row_item.blp --output $PWD/colormydesktop/color_row_item.ui
echo "✓ Compiled color_row_item.ui"

blueprint-compiler compile $PWD/colormydesktop/ui/advanced_page.blp --output $PWD/colormydesktop/advanced_page.ui
echo "✓ Compiled advanced_options.ui"

blueprint-compiler compile $PWD/colormydesktop/ui/permission_settings.blp --output $PWD/colormydesktop/permission_settings.ui
echo "✓ Compiled permission_settings.ui"

blueprint-compiler compile $PWD/colormydesktop/ui/gnome_options.blp --output $PWD/colormydesktop/gnome_options.ui
echo "✓ Compiled gnome_options.ui"

blueprint-compiler compile $PWD/colormydesktop/ui/gnome_setup_dialog.blp --output $PWD/colormydesktop/gnome_setup_dialog.ui
echo "✓ Compiled gnome_setup_dialog.ui"

blueprint-compiler compile $PWD/colormydesktop/ui/kde_options.blp --output $PWD/colormydesktop/kde_options.ui
echo "✓ Compiled kde_options.ui"

blueprint-compiler compile $PWD/colormydesktop/ui/kde_setup_dialog.blp --output $PWD/colormydesktop/kde_setup_dialog.ui
echo "✓ Compiled kde_setup_dialog.ui"

blueprint-compiler compile $PWD/colormydesktop/ui/nautilus_options.blp --output $PWD/colormydesktop/nautilus_options.ui
echo "✓ Compiled nautilus_options.ui"

blueprint-compiler compile $PWD/colormydesktop/ui/permission_dialog.blp --output $PWD/colormydesktop/permission_dialog.ui
echo "✓ Compiled permission_dialog.ui"

blueprint-compiler compile $PWD/colormydesktop/ui/folder_selection.blp --output $PWD/colormydesktop/folder_selection.ui
echo "✓ Compiled folder_selection.ui"

blueprint-compiler compile $PWD/colormydesktop/ui/requirements_checklist.blp --output $PWD/colormydesktop/requirements_checklist.ui
echo "✓ Compiled requirements_checklist.ui"

echo "✨ All UI files compiled successfully!"
