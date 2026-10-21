# Packaging and distribution

## Build the portable Windows EXE

From the project root, run:

```powershell
.\.venv\Scripts\python.exe build_exe.py
```

This produces a single-file executable in:

- dist/DJCloneHero.exe

## Files included in the build

The packaged app includes:
- the Tkinter interface
- the Playwright browser automation logic
- the app metadata and artist storage files
- the default downloads/manifest handling for user data

## Recommended release flow

1. Test the app locally
2. Run the build script
3. Verify the exe launches on a clean Windows machine
4. Share the generated EXE directly, or wrap it in an installer if desired

## Notes for recipients

- The app stores runtime data under the user profile and the standard Windows Downloads folder
- The first launch creates any required folders automatically
- It is intended as a portable desktop app and does not require an installation step

## Optional installer

If you want a formal installer experience rather than a portable EXE, you can wrap the built file in Inno Setup or another installer tool.
