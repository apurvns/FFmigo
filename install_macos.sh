#!/bin/bash
# FFMigo Installer for macOS

echo "Installing FFMigo..."

# Create Applications directory if it doesn't exist
mkdir -p /Applications

# Copy the application bundle
cp -R "dist/FFMigo.app" /Applications/

# Make it executable
chmod +x /Applications/FFMigo.app/Contents/MacOS/FFMigo

echo "FFMigo has been installed to /Applications/"
echo "You can now launch FFMigo from your Applications folder!"
