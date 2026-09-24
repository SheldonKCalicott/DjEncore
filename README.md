Python setup for this workspace

Quick steps to get started on Windows:

1. Install Python (3.10+ recommended)
   - Download from https://www.python.org/downloads/ and run the installer.
   - Make sure to check "Add Python to PATH" in the installer.

2. Install VS Code extensions
   - Install the **Python** extension (ms-python.python) and **Pylance** (ms-python.vscode-pylance).

3. Select interpreter in VS Code
   - Open Command Palette (Ctrl+Shift+P) → `Python: Select Interpreter` and choose your Python installation or virtual environment.

4. Create and activate a virtual environment (PowerShell example)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install
```

5. Run examples

Run the Tkinter demo:

```powershell
python src/main.py
```

Run the Playwright example:

```powershell
python tests/playwright_test.py
```

Notes
- Tkinter is included with the standard CPython installers on Windows. If you installed Python from the Microsoft Store or python.org, tkinter should be available.
- If VS Code does not show Python as a language option when creating a new file, installing the Python extension and selecting an interpreter will enable full Python support. You can also create a file with a `.py` extension manually.