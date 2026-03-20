project('color-my-desktop', version: '1.0.0', meson_version: '>= 0.50.0')

# 1. Dependency Checks (Pre-flight)
python = import('python').find_installation('python3', required: true)
sass = find_program('sass', required: false) # Checks if Sass is already on system

# Define install paths
bindir = get_option('bindir')
datadir = get_option('datadir') / 'color-my-desktop'

# 2. Install Binaries
# We rename scripts during installation for a cleaner 'bin' folder
install_data('main.py', install_dir: bindir, rename: 'color-my-desktop')
install_data('color-my-desktop.sh', install_dir: bindir, rename: 'color-my-desktop-backend')

# 3. Install Directories (SCSS, KDE themes, etc.)
install_subdir('colormydesktop', install_dir: bindir)
install_subdir('scss', install_dir: datadir)
install_subdir('palettes', install_dir: datadir)
install_subdir('KDE', install_dir: datadir)

# 4. Desktop File & Icons
# In meson.build, replace the old desktop install with this:
install_data('color-my-desktop.desktop.in', 
  rename: 'io.github.schwarzen.colormydesktop.desktop',
  install_dir: get_option('datadir') / 'applications'
)

install_data('io.github.schwarzen.colormydesktop.png', 
             install_dir: get_option('datadir') / 'icons/hicolor/128x128/apps')

# 5. Post-Install Script (The "Setup" logic)
# This handles the venv creation and Sass download that Meson can't do natively
meson.add_install_script('post-install.sh')
