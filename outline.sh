#!/bin/sh
gst=/usr/share/gnome-shell/gnome-shell-theme.gresource
workdir=${HOME}/shell-theme-outline

mkdir -p "$workdir"

for r in $(gresource list "$gst"); do
    # Remove the prefix to maintain folder structure
    target_path="${r#/org/gnome/shell/theme/}"
    
    # Create subdirectories if they exist in the resource path
    mkdir -p "$workdir/$(dirname "$target_path")"
    
    # Extract the file
    gresource extract "$gst" "$r" > "$workdir/$target_path"
done

