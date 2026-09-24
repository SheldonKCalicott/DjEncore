
import hashlib
import json
import os
import re
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def get_workspace_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def normalize_title_text(value):
    if not value:
        return ""
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s]", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def should_stop_scrolling(current_count, previous_count, stable_rounds, loading=False, bottom_reached=False, height_delta=0):
    if loading:
        return False
    if current_count is None:
        return False
    if previous_count is None:
        return False
    if current_count != previous_count:
        return False
    if not bottom_reached:
        return False
    if height_delta > 0:
        return False
    return stable_rounds >= 8


def extract_chart_artist(raw_title):
    if not raw_title:
        return ""
    title = raw_title.strip()
    for separator in [" - ", " – "]:
        if separator in title:
            return title.split(separator, 1)[0].strip()
    return title


def is_cover_title(raw_title):
    text = (raw_title or "").strip()
    if not text:
        return False
    lowered = text.lower()
    if "cover" not in lowered:
        return False

    if " - " in text:
        _, song_part = text.split(" - ", 1)
        return "cover" in song_part.lower()

    return True


def normalize_artist_folder(name):
    name = (name or "").strip() or "Unknown Artist"
    name = re.sub(r'[<>:"/\\|?*]+', "_", name)
    return name[:120] or "Unknown Artist"


def fingerprint_path(path):
    path = Path(path)
    if not path.exists():
        return ""
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    if path.is_dir():
        digest = hashlib.sha256()
        for child in sorted(path.rglob("*")):
            if child.is_file():
                digest.update(str(child.relative_to(path)).encode("utf-8"))
                digest.update(child.read_bytes())
        return digest.hexdigest()
    return ""


def title_matches_artist(raw_title, artist):
    if not raw_title or not artist:
        return False

    chart_artist = extract_chart_artist(raw_title)
    if not chart_artist:
        return False

    def split_artist_parts(value):
        raw_value = (value or "").strip()
        if not raw_value:
            return []
        parts = re.split(r"\s*(?:&|and|/|,|\+|x|feat\.?|ft\.?|with)\s*", raw_value, flags=re.IGNORECASE)
        return [normalize_title_text(part) for part in parts if normalize_title_text(part)]

    normalized_artist = normalize_title_text(artist)
    normalized_chart_artist = normalize_title_text(chart_artist)

    if not normalized_artist or not normalized_chart_artist:
        return False

    if normalized_chart_artist == normalized_artist:
        return True

    exact_token_match = bool(re.search(rf"(?<![a-z0-9]){re.escape(normalized_artist)}(?![a-z0-9])", normalized_chart_artist))
    if exact_token_match and normalized_chart_artist != normalized_artist:
        chart_parts = split_artist_parts(chart_artist)
        if normalized_artist in chart_parts:
            return True
        return False
    if exact_token_match:
        return True

    artist_parts = split_artist_parts(artist)
    chart_parts = split_artist_parts(chart_artist)

    if not artist_parts or not chart_parts:
        return False

    return any(part == normalized_artist for part in chart_parts) or any(part == normalized_chart_artist for part in artist_parts)


def get_downloads_root():
    return Path.home() / "Downloads" / "DJ Extractor"


def get_manifest_path():
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "DJ Extractor" / "downloaded_files.json"
    return Path.home() / ".djextractor" / "downloaded_files.json"


def load_download_manifest(manifest_path=None):
    path = Path(manifest_path) if manifest_path else get_manifest_path()
    try:
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def append_download_entry(manifest_path, entry, existing_manifest=None):
    path = Path(manifest_path)
    manifest = existing_manifest if existing_manifest is not None else load_download_manifest(path)
    if not isinstance(manifest, list):
        manifest = []

    artist = (entry.get("artist") or "").strip().lower()
    title = (entry.get("title") or "").strip().lower()
    sha256 = entry.get("sha256") or ""

    duplicate = any(
        (existing.get("sha256") and sha256 and existing.get("sha256") == sha256)
        or (
            ((existing.get("artist") or "").strip().lower() == artist)
            and ((existing.get("title") or "").strip().lower() == title)
            and artist
            and title
        )
        for existing in manifest
    )
    if duplicate:
        return manifest

    manifest.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def format_download_success_message(artist, title):
    return f"Downloaded {artist} - {title} (Charter)"


def format_download_skip_message(artist, title):
    return f"Skipping '{artist} - {title}' already recorded in download manifest"


def clear_download_history(manifest, manifest_path):
    manifest[:] = []
    paths = [Path(manifest_path)]
    legacy_path = get_workspace_root() / "data" / "downloaded_files.json"
    if legacy_path not in paths:
        paths.append(legacy_path)
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
    return manifest


def difficulty_matches_result(result_text, selected_difficulties):
    if not selected_difficulties:
        return True

    text = result_text or ""
    normalized_text = text.upper()
    difficulty_map = {"easy": "E", "medium": "M", "hard": "H", "expert": "X"}

    if len(selected_difficulties) == 1:
        word = selected_difficulties[0].lower()
        if word not in difficulty_map:
            return True
        return bool(re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE) or re.search(rf"\b{re.escape(difficulty_map[word])}\b", normalized_text))

    selected_letters = "".join(
        difficulty_map[name]
        for name in ["easy", "medium", "hard", "expert"]
        if name in selected_difficulties
    )
    if not selected_letters:
        return True

    return all(letter in normalized_text for letter in selected_letters)


def run_search(artists, difficulties, on_progress=None, close_browser=False, selector_test=False):
    """
    Navigate https://www.enchor.us/, search for each artist, and attempt to download charts.

    Steps implemented here (updateable):
    - Open enchor.us in a visible Chromium browser.
    - Find the site search input and enter artist name, press Enter.
    - Wait for `ce-search-result` elements to load and pick the first result.
    - Click the download button in the result, select `.zip` format if available, and confirm download.
    - Save downloaded file(s) to `downloads/` under the workspace root.

    Returns a dict summary with `artists_processed`, `artists_found` (list), and `files_downloaded`.
    """
    WORKSPACE_ROOT = get_workspace_root()
    downloads_dir = get_downloads_root()
    downloads_dir.mkdir(parents=True, exist_ok=True)
    pref_file = WORKSPACE_ROOT / "data" / "preferred_download.json"
    manifest_path = get_manifest_path()
    preferred_set = False
    zip_preference_set_this_run = False
    download_manifest = []
    try:
        if pref_file.exists():
            obj = json.loads(pref_file.read_text(encoding="utf-8"))
            preferred_set = bool(obj.get("preferred_set", False))
    except Exception:
        preferred_set = False

    download_manifest = load_download_manifest(manifest_path)

    # configure logger
    import logging
    import sys

    log_dir = WORKSPACE_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "search_runner.log"
    logger = logging.getLogger("search_runner")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        fh = logging.FileHandler(str(log_file), encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
        fh.setFormatter(fmt)
        sh.setFormatter(fmt)
        logger.addHandler(fh)
        logger.addHandler(sh)

    def report(msg, level="info"):
        if level == "debug":
            logger.debug(msg)
        elif level == "warning":
            logger.warning(msg)
        elif level == "error":
            logger.error(msg)
        else:
            logger.info(msg)
        if on_progress:
            try:
                on_progress(msg)
            except Exception:
                logger.exception("on_progress callback raised")

    def save_download_manifest():
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(download_manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_download_entry(artist, title, file_path, download_url="", repacked=False):
        nonlocal download_manifest
        path = Path(file_path)
        if not path.exists():
            return
        sha256 = fingerprint_path(path)
        entry = {
            "artist": artist,
            "title": title,
            "filename": path.name,
            "path": str(path.resolve()),
            "sha256": sha256,
            "download_url": download_url,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "repacked": repacked,
        }
        current_manifest = load_download_manifest(manifest_path)
        updated_manifest = append_download_entry(manifest_path, entry, existing_manifest=current_manifest)
        if updated_manifest != current_manifest:
            download_manifest = updated_manifest
            save_download_manifest()

    def is_downloaded_before(artist, title):
        normalized_artist = (artist or "").strip().lower()
        normalized_title = (title or "").strip().lower()
        current_manifest = load_download_manifest(manifest_path)
        return any((entry.get("artist") or "").strip().lower() == normalized_artist and (entry.get("title") or "").strip().lower() == normalized_title for entry in current_manifest)

    def load_more_results(times=100, pause_ms=1200):
        previous_count = None
        previous_height = None
        stable_rounds = 0
        for step in range(times):
            try:
                page.evaluate("""
                    const root = document.scrollingElement || document.documentElement || document.body;
                    root.scrollTop = root.scrollHeight;
                    window.scrollTo(0, document.body.scrollHeight);
                """)
            except Exception:
                pass
            try:
                page.mouse.wheel(0, 30000)
            except Exception:
                pass

            page.wait_for_timeout(pause_ms)

            try:
                page_state = page.evaluate("""
                    (() => {
                        const root = document.scrollingElement || document.documentElement || document.body;
                        const currentCount = document.querySelectorAll('ce-search-result').length;
                        const currentHeight = Math.max(
                            document.body ? document.body.scrollHeight : 0,
                            document.documentElement ? document.documentElement.scrollHeight : 0,
                            document.body ? document.body.offsetHeight : 0,
                            document.documentElement ? document.documentElement.offsetHeight : 0,
                        );
                        const previous = window.__dj_last_results_state || {count: currentCount, height: currentHeight, scrollY: root.scrollTop};
                        const atBottom = window.innerHeight + window.scrollY >= (root.scrollHeight || 0) - 300;
                        const heightDelta = currentHeight - (previous.height || 0);
                        const countChanged = currentCount !== previous.count;
                        const moved = Math.abs((previous.scrollY || 0) - root.scrollTop) > 40;
                        const changed = countChanged || heightDelta > 0 || moved;
                        window.__dj_last_results_state = {count: currentCount, height: currentHeight, scrollY: root.scrollTop};
                        return { loading: changed && atBottom, atBottom, currentCount, currentHeight, heightDelta };
                    })()
                """)
                is_loading = bool(page_state.get("loading", False)) if isinstance(page_state, dict) else False
                bottom_reached = bool(page_state.get("atBottom", False)) if isinstance(page_state, dict) else False
                height_delta = int(page_state.get("heightDelta", 0)) if isinstance(page_state, dict) else 0
            except Exception:
                is_loading = False
                bottom_reached = False
                height_delta = 0

            try:
                current_count = len(page.query_selector_all("ce-search-result"))
            except Exception:
                current_count = None

            if should_stop_scrolling(current_count, previous_count, stable_rounds, loading=is_loading, bottom_reached=bottom_reached, height_delta=height_delta):
                report(f"Reached stable result count after {step + 1} scrolls; stopping pagination.", "debug")
                break

            if current_count is not None:
                if previous_count is not None and current_count == previous_count:
                    stable_rounds += 1
                else:
                    stable_rounds = 0
                previous_count = current_count
                previous_height = page_state.get("currentHeight", previous_height) if isinstance(page_state, dict) else previous_height

    def set_search_filters_to_broadest():
        selectors = [
            'label:has-text("Expert")',
            'a:has-text("Any Difficulty")',
            'label:has-text("Lead Guitar")',
            'a:has-text("Any Instrument")',
        ]
        for selector in selectors:
            try:
                loc = page.locator(selector).first
                if loc.count() > 0:
                    loc.click(timeout=2000)
            except Exception:
                pass

    def wait_for_file_ready(path, timeout=30.0, stable_for=1.0) -> bool:
        path = Path(path)
        deadline = time.time() + timeout
        last_size = None
        stable_since = None
        while time.time() < deadline:
            if path.exists():
                size = path.stat().st_size
                if last_size is not None and size == last_size:
                    if stable_since is None:
                        stable_since = time.time()
                    elif time.time() - stable_since >= stable_for:
                        return True
                else:
                    stable_since = None
                    last_size = size
            time.sleep(0.25)
        return path.exists() and path.stat().st_size > 0

    def inspect_download_signature(path) -> str:
        p = Path(path)
        if not p.exists():
            return "missing"
        with p.open("rb") as f:
            header = f.read(8)
        if header.startswith(b"PK\x03\x04"):
            return "zip"
        if header.startswith((b"<!DO", b"<!doc", b"<html", b"<?xml")):
            return "html/xml"
        if header.startswith(b"{"):
            return "json"
        if header.startswith((b"<?", b"<")):
            return "xml"
        return "binary"

    # helper: fetch URL using Playwright's request context so cookies/auth/session are preserved
    def fetch_url_with_requests(url: str, save_path: str) -> bool:
        try:
            headers = {}
            try:
                ua = page.evaluate("() => navigator.userAgent")
            except Exception:
                ua = "Mozilla/5.0"
            headers["User-Agent"] = ua

            resp = page.context.request.get(url, headers=headers, timeout=60000)
            report(f"Playwright request status: {resp.status} for {url}", "debug")
            try:
                report(f"Playwright response content-type: {resp.headers.get('content-type')}", "debug")
            except Exception:
                pass
            if resp.status >= 400:
                raise RuntimeError(f"HTTP {resp.status}")
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as fh:
                fh.write(resp.body())

            if wait_for_file_ready(save_path):
                report(f"Fetched file size: {Path(save_path).stat().st_size} bytes", "debug")
                report(f"Fetched file signature: {inspect_download_signature(save_path)}", "debug")
            return True
        except Exception as e:
            report(f"Failed to fetch url via Playwright request context: {e}", "warning")
            return False

    # helper: finalize a saved download - move to user Downloads, repackage single .sng into folder zip
    def finalize_download(saved_path: str, suggested_name: str, destination_dir=None):
        try:
            import shutil, tempfile
            if destination_dir is None:
                destination_dir = Path.home() / "Downloads"
            else:
                destination_dir = Path(destination_dir)
            destination_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            destination_dir = downloads_dir
            destination_dir.mkdir(parents=True, exist_ok=True)

        final_path = destination_dir / suggested_name
        try:
            if not wait_for_file_ready(saved_path):
                report(f"Download file was not ready in time: {saved_path}", "warning")
                return str(final_path), False

            report(f"Download signature for {saved_path}: {inspect_download_signature(saved_path)}", "debug")
            if zipfile.is_zipfile(saved_path):
                with zipfile.ZipFile(saved_path, 'r') as z:
                    names = z.namelist()
                flat_files = [n for n in names if n and not n.endswith('/')]
                has_dirs = any('/' in n for n in names)
                if (len(flat_files) == 1 and flat_files[0].lower().endswith('.sng')) or not has_dirs:
                    base = Path(suggested_name).stem
                    tmpdir = Path(tempfile.mkdtemp())
                    with zipfile.ZipFile(saved_path, 'r') as z:
                        z.extractall(tmpdir)
                    sngs = list(tmpdir.rglob('*.sng'))
                    folder = tmpdir / base
                    folder.mkdir(exist_ok=True)
                    for s in sngs:
                        shutil.move(str(s), str(folder / s.name))
                    final_name = base + '.zip'
                    final_path = destination_dir / final_name
                    with zipfile.ZipFile(final_path, 'w', zipfile.ZIP_DEFLATED) as nz:
                        for p in folder.rglob('*'):
                            arc = str(folder.name + '/' + p.relative_to(folder).as_posix())
                            nz.write(p, arcname=arc)
                    shutil.rmtree(tmpdir)
                    return str(final_path), True
                try:
                    shutil.move(saved_path, str(final_path))
                except Exception:
                    Path(saved_path).rename(final_path)
                return str(final_path), False
            else:
                try:
                    shutil.move(saved_path, str(final_path))
                except Exception:
                    Path(saved_path).rename(final_path)
                return str(final_path), False
        except Exception as e:
            report(f"Error finalizing download {saved_path}: {e}", "warning")
            return str(final_path), False

    def extract_zip(zip_path, destination_dir=None, delete_original=False):
        zip_path = Path(zip_path)

        if not zip_path.exists():
            raise FileNotFoundError(zip_path)

        if not zipfile.is_zipfile(zip_path):
            raise ValueError(f"Not a valid zip file: {zip_path}")

        if destination_dir is None:
            destination_dir = zip_path.parent
        else:
            destination_dir = Path(destination_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)

        extract_folder = destination_dir / zip_path.stem

        if extract_folder.exists():
            if delete_original and zip_path.exists():
                try:
                    zip_path.unlink(missing_ok=True)
                except Exception:
                    pass
            return extract_folder

        extract_folder.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_folder)

        if delete_original and zip_path.exists():
            try:
                zip_path.unlink(missing_ok=True)
            except Exception:
                pass

        return extract_folder

    def process_download(artist, display_title, save_path, suggested, download_url, artist_files):
        artist_dir = downloads_dir / normalize_artist_folder(artist)
        final_path, repacked = finalize_download(save_path, suggested, destination_dir=artist_dir)

        final_path = Path(final_path)

        if not final_path.exists():
            report(f"Final download missing: {final_path}", "warning")
            return False

        record_path = final_path
        try:
            extracted_folder = extract_zip(final_path, destination_dir=artist_dir, delete_original=False)
            report(f"Extracted ZIP to {extracted_folder}", "info")
            record_path = extracted_folder
        except Exception as e:
            report(f"Extraction failed: {e}", "warning")

        if final_path.exists() and final_path.is_file() and final_path.suffix.lower() == ".zip":
            try:
                final_path.unlink(missing_ok=True)
            except Exception:
                pass

        add_download_entry(
            artist,
            display_title,
            record_path,
            download_url,
            repacked,
        )

        artist_files.append(Path(record_path).name)

        report(
            format_download_success_message(artist, Path(record_path).name),
            "info",
        )

        return True

    report("Launching browser...")

    playwright = sync_playwright().start()
    # use a persistent Chromium/Chrome profile so the site sees a normal browser session
    profile_dir = WORKSPACE_ROOT / "chromium_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    launch_error = None
    try:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            accept_downloads=True,
            channel="chrome",
        )
    except Exception as exc:
        launch_error = exc
        if "existing browser session" in str(exc).lower() or "already in use" in str(exc).lower():
            fallback_dir = WORKSPACE_ROOT / "chromium_profile" / f"run_{int(time.time())}"
            fallback_dir.mkdir(parents=True, exist_ok=True)
            report(f"Primary profile is busy; retrying with fallback profile: {fallback_dir}", "warning")
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(fallback_dir),
                headless=False,
                accept_downloads=True,
                channel="chrome",
            )
        else:
            raise
    if launch_error and "existing browser session" not in str(launch_error).lower() and "already in use" not in str(launch_error).lower():
        raise launch_error
    page = context.new_page()

    artists_found = []
    files_downloaded = 0

    # CSS selector for the search input — prefer a placeholder-based selector for stability
    search_input_selector = 'input[placeholder="What do you feel like playing today?"]'

    # Keep selectors generic and stable instead of page-position-specific paths.

    for idx, artist in enumerate(artists, start=1):
        msg = f"[{idx}/{len(artists)}] Searching for: {artist}"
        report(msg)

        try:
            report("Visiting https://www.enchor.us/ for artist: %s" % artist, "debug")
            page.goto("https://www.enchor.us/", wait_until="domcontentloaded", timeout=30000)
            # wait for the search input
            try:
                page.wait_for_selector(search_input_selector, timeout=15000)
                report("Found search input selector.", "debug")
            except PWTimeout:
                report("Search input selector not found.", "warning")

            try:
                set_search_filters_to_broadest()
                report("Reset difficulty and instrument filters to broadest options.", "debug")
            except Exception as exc:
                report(f"Could not reset search filters: {exc}", "warning")

            # focus, fill, and submit quickly without waiting for a full page render lifecycle
            try:
                search_box = page.locator(search_input_selector).first
                search_box.wait_for(timeout=15000)
                search_box.click()
                search_box.fill(artist)
                search_box.press("Enter")
                report("Filled search input and submitted.", "debug")
            except Exception as e:
                report(f"Could not fill/submit search input: {e}", "error")

            # wait for results to appear
            try:
                page.wait_for_selector("ce-search-result", timeout=10000)
                report("Search results appeared.", "debug")
            except PWTimeout:
                report("Search results did not appear in time.", "warning")

            # load additional results by scrolling to the bottom several times
            load_more_results(32)

            # collect downloads for all matching results on the page
            results = page.query_selector_all("ce-search-result")
            if not results:
                report(f"No results found for {artist}", "info")
                continue

            artist_files = []

            for r_idx, result in enumerate(results, start=1):
                try:
                    # ensure the result is scrolled into view (helps lazy-loaded content)
                    try:
                        result.evaluate("el => el.scrollIntoView({behavior:'auto', block:'center'})")
                        page.wait_for_timeout(150)
                    except Exception:
                        pass

                    # extract title for this result using the title cluster in the card itself
                    result_text = ""
                    try:
                        result_text = (result.inner_text() or "").strip()
                    except Exception:
                        result_text = ""

                    raw_title = ""
                    for line in result_text.splitlines():
                        candidate = line.strip()
                        if not candidate:
                            continue
                        if " - " in candidate:
                            raw_title = candidate
                            break
                    if not raw_title:
                        raw_title = result_text.splitlines()[0].strip() if result_text else ""
                    if not raw_title:
                        try:
                            title_el = result.query_selector("xpath=.//div[contains(@class,'text-xl') or contains(@class,'text-2xl')]")
                            if title_el:
                                raw_title = title_el.inner_text().strip()
                        except Exception:
                            raw_title = ""
                    if not raw_title:
                        try:
                            css_candidates = [".card-title", "h3", "h2", ".title", ".text-xl", ".text-2xl"]
                            for sel in css_candidates:
                                el = result.query_selector(sel)
                                if el:
                                    raw_title = el.inner_text().strip()
                                    break
                        except Exception:
                            raw_title = ""

                    report(f"Result {r_idx}: raw title: {raw_title}", "debug")

                    if is_cover_title(raw_title):
                        report(f"Skipping '{raw_title}' — title contains 'cover'", "debug")
                        continue

                    if not title_matches_artist(raw_title, artist):
                        report(
                            f"Result {r_idx}: artist '{artist}' did not match title artist '{extract_chart_artist(raw_title)}' for '{raw_title}'",
                            "debug",
                        )
                        continue

                    parts = [p.strip() for p in raw_title.split(" - ")] if " - " in raw_title else [raw_title.strip()]
                    candidate_left = parts[0] if parts else raw_title
                    song_part = " ".join(parts[1:]) if len(parts) > 1 else ""
                    display_title = f"{candidate_left} - {song_part}".strip(" -") if candidate_left else raw_title

                    report(f"Result {r_idx}: matched artist '{artist}' against title '{raw_title}'", "debug")

                    # difficulty check: use whole-word matching for a single selection and letter matching for multiple selections
                    try:
                        text_block = result.inner_text()
                    except Exception:
                        text_block = ""
                    selected_difficulties = [name for name in ["easy", "medium", "hard", "expert"] if difficulties.get(name)]
                    difficulty_ok = difficulty_matches_result(text_block, selected_difficulties)
                    report(f"Result {r_idx} difficulty selection: {selected_difficulties}; text: {text_block[:120]}", "debug")

                    if not difficulty_ok:
                        report(f"Skipping result {r_idx} '{display_title}' — difficulty text did not satisfy selected {selected_difficulties}", "debug")
                        continue

                    if is_downloaded_before(artist, display_title):
                        report(format_download_skip_message(artist, display_title), "info")
                        continue

                    # find download button inside this result
                    download_btn = result.query_selector("button.btn.btn-primary")
                    if not download_btn:
                        download_btn = result.query_selector("i.bi-download")
                        if download_btn:
                            download_btn = download_btn.evaluate_handle("node => node.closest('button')")

                    if not download_btn:
                        report(f"Result {r_idx} has no download button", "debug")
                        continue

                    # First attempt: if ZIP preference is already set this run/session, direct click should download.
                    if preferred_set or zip_preference_set_this_run:
                        try:
                            with page.expect_download(timeout=12000) as download_info:
                                try:
                                    # native element.click() tends to follow site handlers more reliably than synthetic MouseEvent
                                    download_btn.evaluate("el => el.click()")
                                except Exception:
                                    download_btn.click()

                            download = download_info.value
                            suggested = download.suggested_filename
                            save_path = str((downloads_dir / suggested).resolve())
                            download.save_as(save_path)
                            # diagnostic: log saved file size and header bytes
                            try:
                                p = Path(save_path)
                                size = p.stat().st_size
                                report(f"Saved file size: {size} bytes at {save_path}", "debug")
                                with open(save_path, "rb") as f:
                                    hdr = f.read(8)
                                report(f"Saved file header (first 8 bytes): {hdr}", "debug")
                            except Exception:
                                pass
                            try:
                                dl_url = download.url
                            except Exception:
                                dl_url = ""

                            # verify file is a zip; if not, try fetching the URL directly with requests
                            try:
                                import zipfile as _z
                                is_zip = _z.is_zipfile(save_path)
                            except Exception:
                                is_zip = False

                            if not is_zip and dl_url:
                                report(f"Result {r_idx}: direct-saved file not a zip, attempting HTTP fetch of {dl_url}", "debug")
                                try:
                                    Path(save_path).unlink(missing_ok=True)
                                except Exception:
                                    pass
                                ok = fetch_url_with_requests(dl_url, save_path)
                                if ok:
                                    try:
                                        import zipfile as _z2

                                        if _z2.is_zipfile(save_path):
                                            if process_download(
                                                artist,
                                                display_title,
                                                save_path,
                                                suggested,
                                                dl_url,
                                                artist_files,
                                            ):
                                                files_downloaded += 1
                                            continue
                                        else:
                                            report(f"Result {r_idx}: fetched file still not zip", "warning")
                                    except Exception:
                                        report(f"Result {r_idx}: error validating fetched file", "warning")
                                else:
                                    report(f"Result {r_idx}: HTTP fetch fallback failed", "warning")
                            else:
                                if process_download(
                                    artist,
                                    display_title,
                                    save_path,
                                    suggested,
                                    dl_url,
                                    artist_files,
                                ):
                                    files_downloaded += 1
                                continue
                        except PWTimeout:
                            report(f"Result {r_idx}: direct download did not start; will try popup flow", "debug")
                        except Exception as e:
                            report(f"Result {r_idx}: direct download click failed; trying popup flow: {e}", "debug")

                    # Popup flow (usually first download only): choose .zip then click popup Download.
                    try:
                        try:
                            download_btn.evaluate("el => el.click()")
                        except Exception:
                            download_btn.click()
                    except Exception as e:
                        report(f"Could not click download button for result {r_idx}: {e}", "warning")
                        continue

                    modal = None
                    try:
                        start = time.time()
                        while time.time() - start < 10:
                            candidates = page.query_selector_all("dialog, .modal-box, .modal")
                            for c in candidates:
                                try:
                                    html = c.inner_html().lower()
                                except Exception:
                                    html = ""
                                if "selecteddownloadformat" in html or ".zip" in html:
                                    modal = c
                                    break
                            if modal:
                                break
                            time.sleep(0.2)
                    except Exception:
                        modal = None

                    if not modal:
                        report(f"Result {r_idx}: no format popup found", "warning")
                        continue

                    # save popup HTML for debugging
                    try:
                        modal_html = modal.inner_html()
                        diag_file = log_dir / f"modal_{idx}_{r_idx}.html"
                        diag_file.write_text(modal_html, encoding="utf-8")
                        report(f"Wrote modal HTML to {diag_file}", "debug")
                    except Exception:
                        modal_html = ""

                    # If running in selector_test mode, return modal diagnostics and candidate selectors
                    if selector_test:
                        try:
                            labels = [l.inner_text().strip() for l in modal.query_selector_all("label")]
                        except Exception:
                            labels = []
                        try:
                            radios_info = []
                            for r in modal.query_selector_all("input[type=radio]"):
                                try:
                                    name = r.get_attribute("name")
                                except Exception:
                                    name = None
                                try:
                                    value = r.get_attribute("value")
                                except Exception:
                                    value = None
                                try:
                                    lbl = r.evaluate("n => { const l = n.closest('label'); return l? l.innerText : (n.nextElementSibling? n.nextElementSibling.innerText : ''); }")
                                except Exception:
                                    lbl = ""
                                radios_info.append({"name": name, "value": value, "label": lbl})
                        except Exception:
                            radios_info = []

                        handler_snippet = (
                            "# Selection/confirmation snippet in src/search_runner.py:\n"
                            "labels = modal.query_selector_all('label')\n"
                            "for lab in labels:\n"
                            "    if '.zip' in (lab.inner_text() or '').lower():\n"
                            "        lab.evaluate('el => el.dispatchEvent(new MouseEvent(\\\'click\\\', {bubbles:true}))')\n"
                            "        # or find input[name^=\"selectedDownloadFormat\"] and set checked + dispatch change events\n"
                        )

                        return {
                            "selector_test": True,
                            "modal_html_path": str(diag_file) if 'diag_file' in locals() else None,
                            "labels": labels,
                            "radios": radios_info,
                            "handler_snippet": handler_snippet,
                        }

                    # specifically target input[name^="selectedDownloadFormat..."] for .zip option
                    chosen = False

                    # attempt to actively select the .zip choice inside the modal using explicit selectors and text-based fallbacks
                    try:
                        js_select_zip = '''
                        (() => {
                          const root = arguments[0] || document;
                          const normalize = (value) => (value || '').toLowerCase();
                          const activate = (el) => {
                            if (!el) return false;
                            if (el.matches && el.matches('input[type=radio], [role="radio"]')) {
                              el.checked = true;
                              el.dispatchEvent(new Event('input', {bubbles:true}));
                              el.dispatchEvent(new Event('change', {bubbles:true}));
                            }
                            const label = el.closest('label') || el.parentElement;
                            if (label && label.matches && label.matches('label')) {
                              label.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window}));
                            } else {
                              el.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window}));
                            }
                            return true;
                          };

                          const directSelectors = [
                            'a:has-text(".zip")',
                            'a:has-text("zip")',
                            'label:has-text(".zip")',
                            'label:has-text("zip")',
                            'button:has-text(".zip")',
                            'button:has-text("zip")',
                            'input[value*="zip"]',
                            'input[name*="zip"]',
                            '[data-download-format*="zip"]',
                            '[data-format*="zip"]',
                          ];

                          for (const selector of directSelectors) {
                            const matches = Array.from(root.querySelectorAll(selector));
                            for (const el of matches) {
                              if (activate(el)) return true;
                            }
                          }

                          const candidates = Array.from(root.querySelectorAll('input[type=radio], [role="radio"], label, a, button, .option, .choice'));
                          for (const el of candidates) {
                            const text = [el.innerText, el.textContent, el.getAttribute('aria-label'), el.getAttribute('title'), el.getAttribute('data-value'), el.getAttribute('value')]
                              .filter(Boolean)
                              .join(' ');
                            if (normalize(text).includes('.zip') || normalize(text).includes('zip') || normalize(text).includes('archive')) {
                              if (activate(el)) return true;
                            }
                          }
                          return false;
                        })()
                        '''
                        try:
                            chosen = modal.evaluate(js_select_zip, modal)
                        except Exception:
                            chosen = modal.evaluate(js_select_zip)
                        report(f"Result {r_idx}: attempted to select .zip option in modal: {chosen}", "debug")
                    except Exception:
                        chosen = False

                    # click popup Download button
                    confirm_btn = modal.query_selector("button.btn.btn-primary")
                    if not confirm_btn:
                        report(f"Result {r_idx}: popup Download button not found", "warning")
                        continue

                    try:
                        # if framework did not remove disabled yet, force-enable and then click
                        confirm_btn.evaluate("b => { if (b.disabled) { b.disabled = false; b.removeAttribute('disabled'); } }")
                    except Exception:
                        pass

                    try:
                        with page.expect_download(timeout=30000) as download_info:
                            try:
                                confirm_btn.evaluate("b => b.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window}))")
                            except Exception:
                                confirm_btn.click()
                        download = download_info.value
                        suggested = download.suggested_filename
                        save_path = str((downloads_dir / suggested).resolve())
                        download.save_as(save_path)
                        # diagnostic: log saved file size and header bytes
                        try:
                            p = Path(save_path)
                            size = p.stat().st_size
                            report(f"Saved file size: {size} bytes at {save_path}", "debug")
                            with open(save_path, "rb") as f:
                                hdr = f.read(8)
                            report(f"Saved file header (first 8 bytes): {hdr}", "debug")
                        except Exception:
                            pass
                        try:
                            dl_url = download.url
                        except Exception:
                            dl_url = ""

                        # verify file is zip; if not, try HTTP fetch via requests
                        try:
                            import zipfile as _z
                            is_zip = _z.is_zipfile(save_path)
                        except Exception:
                            is_zip = False

                        if not is_zip and dl_url:
                            report(f"Result {r_idx}: popup-saved file not a zip, attempting HTTP fetch of {dl_url}", "debug")
                            try:
                                Path(save_path).unlink(missing_ok=True)
                            except Exception:
                                pass
                            ok = fetch_url_with_requests(dl_url, save_path)
                            if ok:
                                try:
                                    import zipfile as _z2

                                    if _z2.is_zipfile(save_path):
                                        if process_download(
                                            artist,
                                            display_title,
                                            save_path,
                                            suggested,
                                            dl_url,
                                            artist_files,
                                        ):
                                            files_downloaded += 1
                                    else:
                                        report(f"Result {r_idx}: fetched file still not zip", "warning")
                                except Exception:
                                    report(f"Result {r_idx}: error validating fetched file", "warning")
                            else:
                                report(f"Result {r_idx}: HTTP fetch fallback failed", "warning")
                        else:
                            if process_download(
                                artist,
                                display_title,
                                save_path,
                                suggested,
                                dl_url,
                                artist_files,
                            ):
                                files_downloaded += 1

                        zip_preference_set_this_run = True
                        if not preferred_set:
                            try:
                                pref_file.parent.mkdir(parents=True, exist_ok=True)
                                pref_file.write_text(json.dumps({"preferred_set": True}), encoding="utf-8")
                                preferred_set = True
                                report("Preferred download type recorded; subsequent downloads use direct button click.", "info")
                            except Exception as e:
                                report(f"Could not persist preferred download flag: {e}", "warning")
                    except PWTimeout:
                        report(f"Result {r_idx}: download did not start in time", "warning")
                    except Exception as e:
                        report(f"Result {r_idx}: download error: {e}", "error")

                    # try to close modal so we can continue
                    try:
                        # common close buttons
                        close_btn = page.locator("dialog.modal .btn.btn-ghost, .modal-box .btn.btn-ghost, .modal .btn.btn-ghost, button.btn-close, button.close").first
                        if close_btn and close_btn.count() > 0:
                            try:
                                close_btn.click()
                                report(f"Result {r_idx}: closed modal via close button", "debug")
                            except Exception:
                                try:
                                    page.keyboard.press("Escape")
                                except Exception:
                                    pass
                        else:
                            try:
                                page.keyboard.press("Escape")
                                report(f"Result {r_idx}: closed modal via Escape", "debug")
                            except Exception:
                                pass
                    except Exception:
                        pass

                except Exception as e:
                    report(f"Unhandled error processing result {r_idx}: {e}", "error")

            # record artist-level summary
            if artist_files:
                artists_found.append({"artist": artist, "title": None, "downloaded": len(artist_files), "files": artist_files})
            else:
                artists_found.append({"artist": artist, "title": None, "downloaded": 0})

            # small delay between artists
            time.sleep(0.5)

        except Exception as e:
            report(f"Error searching for {artist}: {e}", "error")
            artists_found.append({"artist": artist, "title": None, "downloaded": 0})

    # Optionally close browser and stop playwright; otherwise leave open for inspection
    if close_browser:
        try:
            context.close()
        except Exception:
            pass
        try:
            playwright.stop()
        except Exception:
            pass

    report("Done.")

    summary = {
        "artists_processed": len(artists),
        "artists_found": artists_found,
        "files_downloaded": files_downloaded,
    }

    return summary
