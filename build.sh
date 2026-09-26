#!/bin/bash

set -e

flatpak-builder --user --install --force-clean build-dir localtest.yaml
flatpak build-bundle ~/.local/share/flatpak/repo colormydesktop.flatpak io.github.schwarzen.colormydesktop
flatpak run io.github.schwarzen.colormydesktop
