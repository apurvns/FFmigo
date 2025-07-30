# FFMigo Release Guide

This guide explains how to use GitHub Actions to automatically build and release FFMigo for Windows and macOS.

## How It Works

The GitHub Actions workflow (`.github/workflows/release.yml`) automatically:

1. **Builds for Windows**: Creates a single executable file (`FFMigo.exe`)
2. **Builds for macOS**: Creates a DMG file (`FFMigo.dmg`) with the application
3. **Creates installer scripts**: Generates installation scripts for both platforms
4. **Attaches files to releases**: Automatically uploads all files to GitHub releases

## Creating a Release

### Step 1: Prepare Your Release

1. Make sure all your changes are committed and pushed to the main branch
2. Update version numbers if needed
3. Test your application locally

### Step 2: Create a GitHub Release

1. Go to your GitHub repository
2. Click on "Releases" in the right sidebar
3. Click "Create a new release" or "Draft a new release"
4. Fill in the release information:
   - **Tag version**: e.g., `v1.0.0`
   - **Release title**: e.g., "FFMigo v1.0.0"
   - **Description**: Add release notes, features, bug fixes, etc.
5. Click "Publish release"

### Step 3: Wait for Build Completion

The GitHub Actions workflow will automatically:
- Build the Windows executable
- Build the macOS DMG
- Create installer scripts
- Attach all files to your release

You can monitor the progress in the "Actions" tab of your repository.

## What Gets Created

### Windows Release Files
- `FFMigo.exe` - The main executable
- `install_windows.bat` - Automatic installer script
- `DISTRIBUTION_README_Windows.md` - Installation instructions

### macOS Release Files
- `FFMigo.dmg` - Disk image with the application
- `install_macos.sh` - Automatic installer script
- `DISTRIBUTION_README_macOS.md` - Installation instructions

## Manual Release Process (Alternative)

If you prefer to build locally and upload manually:

### Windows Build
```bash
# Install dependencies
pip install -r requirements.txt

# Build executable
python -m PyInstaller --onefile --windowed --icon=ui/resources/icons/app_logo.png --name=FFMigo --add-data=style.qss;. --add-data=ui/resources/icons;ui/resources/icons --add-data=backend;backend --add-data=ui;ui main.py

# The executable will be in dist/FFMigo.exe
```

### macOS Build
```bash
# Install dependencies
pip install -r requirements.txt

# Build application
python -m PyInstaller --onedir --windowed --icon=ui/resources/icons/app_logo.png --name=FFMigo --add-data=style.qss:. --add-data=ui/resources/icons:ui/resources/icons --add-data=backend:backend --add-data=ui:ui main.py

# Create DMG (requires create-dmg)
brew install create-dmg
create-dmg --volname "FFMigo" --volicon "ui/resources/icons/app_logo.png" --window-pos 200 120 --window-size 600 400 --icon-size 100 --icon "FFMigo.app" 175 120 --hide-extension "FFMigo.app" --app-drop-link 425 120 "FFMigo.dmg" "dist/"
```

## Troubleshooting

### Build Failures
- Check that all dependencies are in `requirements.txt`
- Ensure all required files are included in the PyInstaller command
- Verify that the icon file exists at `ui/resources/icons/app_logo.png`

### Release Issues
- Make sure the GitHub Actions workflow file is in `.github/workflows/release.yml`
- Check that the repository has the necessary permissions for releases
- Verify that the `GITHUB_TOKEN` secret is available (it should be automatic)

### File Size Issues
- Large executables are normal for PyQt applications
- Consider using `--onedir` instead of `--onefile` for faster startup
- The DMG file will be larger than the executable due to the disk image format

## Customization

### Modifying the Workflow
Edit `.github/workflows/release.yml` to:
- Change Python version
- Add additional dependencies
- Modify build parameters
- Add code signing
- Include additional files

### Adding Code Signing
For production releases, you may want to add code signing:

```yaml
# For macOS
- name: Sign macOS app
  run: |
    codesign --force --deep --sign "Developer ID Application: Your Name" dist/FFMigo/FFMigo

# For Windows
- name: Sign Windows exe
  run: |
    # Add Windows code signing commands
```

## Best Practices

1. **Version Management**: Use semantic versioning (e.g., v1.0.0, v1.1.0)
2. **Release Notes**: Always include detailed release notes
3. **Testing**: Test the built executables before releasing
4. **Dependencies**: Keep `requirements.txt` updated
5. **Icons**: Ensure your app icon is high quality and properly sized

## Support

If you encounter issues:
1. Check the GitHub Actions logs for error messages
2. Verify all file paths and dependencies
3. Test the build process locally first
4. Check GitHub's documentation for Actions and Releases 