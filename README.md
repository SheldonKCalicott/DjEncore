# DJ Encore

DJ Encore is a Windows desktop app for browsing and downloading chart packs from Enchor. It helps you build an artist library, filter by difficulty, and track downloaded chart files in a clean history view.

## Features

- Add and manage an artist library
- Search one or more artists in Enchor
- Filter results by difficulty
- Download matching chart files into a standard Windows Downloads folder
- Organize saved files by artist folder
- View a tracked download history grouped by artist
- Package a portable EXE for sharing with others

## Requirements

- Windows 10 or newer
- Python 3.10+
- Playwright browser support
- PyInstaller for building the shareable EXE

## Download and run the app

For most users, you do not need Python, VS Code, or an IDE. Download the latest Windows release from GitHub Releases:

- https://github.com/SheldonKCalicott/DjEncore/releases/latest

Then:

1. Download the EXE file
2. Save it somewhere easy to find, such as Desktop or Downloads
3. Double-click the EXE to launch it
4. If Windows shows a security warning, click More info and then Run anyway

## Quick start for developers

```powershell
cd S:\VSC\Projects\DjCloneHero
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install
python src/main.py
```

## Build a shareable EXE

```powershell
cd S:\VSC\Projects\DjCloneHero
.\.venv\Scripts\python.exe build_exe.py
```

This creates a standalone executable at:

- dist/DJCloneHero.exe

You can then share that single EXE with others without requiring Python or a local project checkout.

## Usage notes

- Your artist library is stored in the project data folder
- Downloaded files are saved under the standard Windows Downloads folder in a DJ Extractor subfolder
- The app keeps a JSON manifest for download tracking and history
- The project is designed as a local desktop workflow and is intended to be used responsibly in line with the Enchor site rules and copyright laws

## Project structure

```text
DJCloneHero/
├── src/
│   ├── main.py
│   ├── search_runner.py
│   └── app.ico
├── data/
│   ├── artists.json
│   └── preferred_download.json
├── tests/
├── build_exe.py
├── README.md
├── README_PACKAGING.md
├── requirements.txt
├── .gitignore
├── LICENSE
├── CHANGELOG.md
├── dist/
└── build/
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome. If you improve the downloader, UI, or packaging flow, open a pull request with a clear description of the change and the validation used.

## Disclaimer

This project automates web downloads from Enchor and should be used in accordance with the site’s terms of service and all applicable copyright laws.
