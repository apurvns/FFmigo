#!/bin/bash
# FFMigo Installer for macOS

echo "Installing FFMigo..."

# Create Applications directory if it doesn't exist
mkdir -p /Applications

# Copy the application
cp -R "dist/FFMigo" /Applications/

# Make it executable
chmod +x /Applications/FFMigo/FFMigo

echo "FFMigo has been installed to /Applications/"
echo "You can now launch FFMigo from your Applications folder!"
