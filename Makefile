# --- CONFIGURATION ---
# Use a stable, persistent directory for the app's environment
APP_DATA_DIR  = $(HOME)/.local/share/Color-My-Desktop
VENV_DIR      = $(APP_DATA_DIR)/.venv
VENV_PYTHON   = $(VENV_DIR)/bin/python3
VENV_BIN      = $(VENV_DIR)/bin
VENV_NPM      = $(VENV_DIR)/bin/npm
VENV_NODEENV  = $(VENV_DIR)/bin/nodeenv
SASS	      = $(VENV_DIR)/bin/sass

# Destinations
SCSS_DATA_DIR = $(APP_DATA_DIR)/scss
KDE_DIR = $(APP_DATA_DIR)/KDE
REFRESHER_DIR = $(APP_DATA_DIR)/refresher
BIN_DIR       = $(HOME)/.local/bin
DESKTOP_FILE  = $(HOME)/.local/share/applications/Color-My-Desktop.desktop

.PHONY: all build-styles install setup  clean uninstall

# --- MAIN INSTALL TARGET ---
build-styles:
	# Call the binary directly by its full path
	SASS_BIN=$(SASS) bash ./color-my-desktop.sh

install: setup
	@echo "Installing SCSS partials..."
	@mkdir -p $(SCSS_DATA_DIR)
	install -m 644 scss/*.scss $(SCSS_DATA_DIR)
	install -m 644 palettes/*.scss $(SCSS_DATA_DIR)

#	@mkdir -p $(REFRESHER_DIR)
#	install -m 644 refresher/* $(REFRESHER_DIR)

	@echo "Installing KDE data recursively..."
	mkdir -p $(KDE_DIR)
	cp -r KDE/* $(KDE_DIR)/
	# Set directories to 755 (required to enter them) and files to 644
	find $(KDE_DIR) -type d -exec chmod 755 {} +
	find $(KDE_DIR) -type f -exec chmod 644 {} +

	@echo "Installing scripts to $(BIN_DIR)..."
	@mkdir -p $(BIN_DIR)
	# 1. Install binaries
	install -d $(BIN_DIR)
	install -m 755 main.py $(BIN_DIR)/color-my-desktop
	install -m 755 color-my-desktop.sh $(BIN_DIR)/color-my-desktop-backend

	# 2. Install the subfolder package to /app/bin/
	install -d  $(BIN_DIR)/colormydesktop
	install -m 644 colormydesktop/*.py $(BIN_DIR)/colormydesktop/

	# Copy files to the stable APP_DATA_DIR so they never disappear
	cp main.py $(APP_DATA_DIR)/color-my-desktop
	mkdir -p $(APP_DATA_DIR)/colormydesktop/
	cp colormydesktop/* $(APP_DATA_DIR)/colormydesktop/


	@echo "Creating desktop launcher..."
	@echo "[Desktop Entry]" > $(DESKTOP_FILE)
	@echo "Type=Application" >> $(DESKTOP_FILE)
	@echo "Name=Color My Desktop" >> $(DESKTOP_FILE)
	@echo "Comment=GNOME Theme Manager" >> $(DESKTOP_FILE)
	# Use the full path to the python inside the venv
	@echo "Exec=$(VENV_DIR)/bin/python3 $(APP_DATA_DIR)/color-my-desktop" >> $(DESKTOP_FILE)
	# ADD THIS: Sets the working directory to where the code lives
	@echo "Path=$(APP_DATA_DIR)" >> $(DESKTOP_FILE)
	@echo "Terminal=false" >> $(DESKTOP_FILE)
	@echo "Categories=Settings;GNOME;GTK;" >> $(DESKTOP_FILE)

	@update-desktop-database $(HOME)/.local/share/applications
	@echo "Installation successful! You can now launch Color-My-Desktop from the app list."

# --- SETUP: VENV + NODE + SASS ---
setup:
	@echo "Building Virtual Environment in stable location..."
	@mkdir -p $(APP_DATA_DIR)
	# Recreate venv in the persistent path
	@python3 -m venv $(VENV_DIR)
	@$(VENV_DIR)/bin/pip install --upgrade pip PyGObject nodeenv
	@echo "Installing standalone Dart Sass to venv..."
	curl -L -o sass.tar.gz https://github.com/sass/dart-sass/releases/download/1.97.1/dart-sass-1.97.1-linux-x64.tar.gz
	tar -xzf sass.tar.gz
	mv dart-sass/sass $(VENV_BIN)/sass
	mv dart-sass/src $(VENV_DIR)/bin/
	chmod +x $(VENV_DIR)/bin/sass
	rm -rf dart-sass sass.tar.gz
	@echo "Sass installed!"





	# Copy icon to stable location



clean:
	@echo "Removing installation..."
	rm -rf $(VENV_DIR)
	rm -f $(DESKTOP_FILE)
	rm -f $(BIN_DIR)/color-my-desktop-backend
	rm -f $(BIN_DIR)/color-my-desktop
	rm -rf $(BIN_DIR)/colormydesktop

uninstall:
	@echo "Removing Color My Desktop installation..."
	# Remove the data folder (SCSS partials and local Sass)
	rm -rf $(HOME)/.local/share/Color-My-Desktop
	# Remove the scripts
	rm -f $(HOME)/.local/bin/color-my-desktop.sh
	rm -f $(HOME)/.local/bin/color-my-desktop
	# Remove the launcher
	rm -f $(HOME)/.local/share/applications/color-my-desktop.desktop
	# Update the desktop database so the icon disappears
	@update-desktop-database $(HOME)/.local/share/applications
	@echo "Uninstall complete."
