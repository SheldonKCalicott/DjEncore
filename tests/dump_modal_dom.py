from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
log_dir = WORKSPACE_ROOT / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

ARTIST = "Daft Punk"
SEARCH_INPUT = 'input[placeholder="What do you feel like playing today?"]'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    print(f"Visiting enchor.us and searching for '{ARTIST}'")
    page.goto("https://www.enchor.us/", timeout=30000)
    try:
        page.wait_for_selector(SEARCH_INPUT, timeout=10000)
        page.fill(SEARCH_INPUT, ARTIST)
        page.press(SEARCH_INPUT, "Enter")
    except PWTimeout:
        print("Search input not found")

    try:
        page.wait_for_selector("ce-search-result", timeout=10000)
    except PWTimeout:
        print("No search results")

    results = page.query_selector_all("ce-search-result")
    print(f"Found {len(results)} results")

    # dump full page
    full_html = page.content()
    full_file = log_dir / "fullpage_dump.html"
    full_file.write_text(full_html, encoding="utf-8")
    print(f"Wrote full page HTML to {full_file}")

    # inspect first result if present
    if results:
        first = results[0]
        try:
            first_html = first.inner_html()
        except Exception:
            first_html = ""
        first_file = log_dir / "result_1_dump.html"
        first_file.write_text(first_html, encoding="utf-8")
        print(f"Wrote first result HTML to {first_file}")

        # list all buttons on the page with index and text
        buttons = page.query_selector_all("button")
        print(f"Total buttons on page: {len(buttons)}")
        for i, b in enumerate(buttons, start=1):
            try:
                text = b.inner_text()
            except Exception:
                text = ""
            try:
                outer = b.evaluate("e => e.outerHTML")
            except Exception:
                outer = ""
            print(f"Button {i}: text='{text}' len_outer={len(outer)}")

        # find elements whose text contains 'zip' (case-insensitive)
        xpath = "xpath=//*[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'zip')]"
        zip_nodes = page.query_selector_all(xpath)
        print(f"Nodes containing 'zip': {len(zip_nodes)}")
        for i, n in enumerate(zip_nodes, start=1):
            try:
                txt = n.inner_text()
            except Exception:
                txt = ""
            try:
                outer = n.evaluate("e => e.outerHTML")
            except Exception:
                outer = ""
            snippet_file = log_dir / f"zip_node_{i}.html"
            snippet_file.write_text(outer, encoding="utf-8")
            print(f"Zip node {i}: text='{txt}' saved to {snippet_file}")

        # attempt to click the download button in first result using JS click to avoid interception
        try:
            dl = first.query_selector("button.btn.btn-primary")
            if not dl:
                dl = first.query_selector("button")
            if dl:
                print("Attempting JS click on download button")
                try:
                    dl.evaluate("el => el.click()")
                except Exception as e:
                    print(f"JS click failed: {e}")
            else:
                print("No button found inside first result to click")
        except Exception as e:
            print(f"Error locating download button: {e}")

        try:
            page.wait_for_selector("dialog.modal, .modal-box", timeout=8000)
            modal_html = page.locator("dialog.modal, .modal-box").first.inner_html()
            modal_file = log_dir / "modal_dump.html"
            modal_file.write_text(modal_html, encoding="utf-8")
            print(f"Wrote modal HTML to {modal_file}")
        except PWTimeout:
            print("Modal did not appear after clicking")

    browser.close()
    print("Done")
