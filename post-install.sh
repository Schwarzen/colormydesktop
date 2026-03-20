#!/bin/bash
set -e # Exit immediately if a command fails

# 1. Configuration
VENV_DIR="$HOME/.local/share/color-my-desktop/.venv"
VENV_BIN="$VENV_DIR/bin"
SASS_VERSION="1.97.1"
ARCH=$(uname -m)

echo "--- Configuring Python Virtual Environment ---"
mkdir -p "$HOME/.local/share/color-my-desktop"
python3 -m venv "$VENV_DIR"
"$VENV_BIN/pip" install --upgrade pip PyGObject nodeenv

# 2. Architecture-aware Sass Selection
case "$ARCH" in
    x86_64)
        URL="https://github.com/sass/dart-sass/releases/download/1.97.1/dart-sass-1.97.1-linux-x64.tar.gz"
        EXPECTED_SHA="08867d2f63f458bc07985d0fd96bfef42ed759a4dd9b3d5e1a87b85b52b76112"
        ;;
    aarch64)
        URL="https://github.com/sass/dart-sass/releases/download/1.97.1/dart-sass-1.97.1-linux-arm64.tar.gz"
        EXPECTED_SHA="a8176dc31889977a2026895a35674dfabec01a9c3cc62f55f321fb67d9dbe971"
        ;;
    *)
        echo "Warning: Unsupported architecture ($ARCH). Skipping automatic Sass download."
        exit 0 # We exit 0 so the rest of the install doesn't fail
        ;;
esac

# 3. Check for Sass and Install
if [ ! -f "$VENV_BIN/sass" ]; then
    echo "--- Downloading Standalone Dart Sass ($ARCH) ---"
    
    # Create a temporary workspace
    TMP_BUILD=$(mktemp -d)
    curl -L -o "$TMP_BUILD/sass.tar.gz" "$URL"
    
    # Verify Integrity (Mirroring Flatpak security)
    echo "$EXPECTED_SHA  $TMP_BUILD/sass.tar.gz" | sha256sum --check
    
    # Extract
    tar -xzf "$TMP_BUILD/sass.tar.gz" -C "$TMP_BUILD/"
    
    # Move to venv (keeping your structure)
    mv "$TMP_BUILD/dart-sass/sass" "$VENV_BIN/sass"
    # Ensure the 'src' directory is moved if present, as Dart Sass needs it
    if [ -d "$TMP_BUILD/dart-sass/src" ]; then
        cp -r "$TMP_BUILD/dart-sass/src" "$VENV_BIN/"
    fi
    
    # Create symlink for compatibility
    ln -sf "$VENV_BIN/sass" "$VENV_BIN/sass-embedded"
    
    chmod +x "$VENV_BIN/sass"
    
    # Cleanup
    rm -rf "$TMP_BUILD"
    echo "Sass installation complete!"
else
    echo "Sass is already installed in the venv. Skipping download."
fi

# Refresh the desktop database so the new .desktop file is recognized
if [ -z "$DESTDIR" ]; then
    echo "Updating desktop database..."
    update-desktop-database ~/.local/share/applications
fi


echo "--- Post-install setup finished successfully ---"
