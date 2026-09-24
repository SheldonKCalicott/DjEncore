# Packaging DJ Clone Hero

## Build a Windows executable

From the project root, run:

```powershell
s:/VSC/Projects/DjCloneHero/.venv/Scripts/python.exe build_exe.py
```

This creates a single-file executable at:

- dist/DJCloneHero.exe

## What gets packaged

The build includes:
- the Tkinter app interface
- the Playwright-based downloader logic
- the data folder used for artist storage and history

## Notes for recipients

After installation, the app should be launched from the generated executable. The first run will create the runtime folders it needs for downloads and history.

## Optional installer

If you want a true installer (.exe) instead of just a portable executable, the next step is to wrap the generated executable in an Inno Setup installer. That is a separate step beyond the standalone build.
