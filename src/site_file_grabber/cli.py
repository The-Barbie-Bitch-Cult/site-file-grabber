from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import webbrowser
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Iterable

from . import __version__


DEFAULT_EXTENSIONS = (
    "mp4",
    "wav",
    "mp3",
    "jpg",
    "jpeg",
    "png",
    "doc",
    "docx",
    "csv",
    "pdf",
    "docm",
    "odt",
    "wpt",
    "ppt",
    "zip",
    "webp",
)
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
PAGE_LIKE_EXTENSIONS = {"", ".html", ".htm", ".php", ".asp", ".aspx", ".jsp", ".jspx"}
URL_RE = re.compile(r"""(?i)\bhttps?://[^\s"'<>\\)]+""")
ENCODED_URL_RE = re.compile(r"""(?i)https?(?:%3A|:)(?:%2F|/)(?:%2F|/)[^\s"'<>\\)&]+""")


BLOCK_FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10011", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
}
BLOCK_CELL = "██"
BLANK_CELL = "  "
LETTER_GAP = "  "
WORD_GAP = "      "
ANSI_PURPLE = "\033[95m"
ANSI_CYAN = "\033[96m"
ANSI_RESET = "\033[0m"
VERIFICATION_INDICATORS = (
    "/sorry/",
    "captcha",
    "recaptcha",
    "unusual traffic",
    "not a robot",
    "verify you're not a robot",
    "verify you are human",
    "about this page",
    "performing security verification",
    "security verification",
    "security service",
    "verifies you are not a bot",
    "verify you are not a bot",
    "checking your browser",
    "checking if the site connection is secure",
    "needs to review the security",
    "cloudflare",
    "ray id:",
)
SKIP_BROWSER_DOWNLOAD = object()


@dataclass
class CommonOptions:
    site: str
    extensions: set[str]
    output_dir: Path
    max_documents: int = 100
    delay: float = 1.0
    user_agent: str = DEFAULT_USER_AGENT
    timeout: float = 30.0
    max_file_bytes: int = 0


@dataclass
class LiveOptions(CommonOptions):
    max_pages: int = 100
    max_page_bytes: int = 200_000_000
    max_depth: int = 4
    respect_robots: bool = True


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if not value:
                continue
            lowered = name.lower()
            if lowered in {"href", "src", "data", "poster", "action"}:
                self.links.append(value)
            elif lowered == "srcset":
                for part in value.split(","):
                    candidate = part.strip().split(" ", 1)[0]
                    if candidate:
                        self.links.append(candidate)

    def handle_data(self, data: str) -> None:
        self.links.extend(URL_RE.findall(data))


def render_banner() -> str:
    color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    body: list[str] = []
    body.extend(colorize(render_text("BARBIE"), ANSI_PURPLE, color))
    body.extend(["", ""])
    body.extend(colorize(render_text("BITCH"), ANSI_PURPLE, color))
    body.extend(["", ""])
    body.extend(colorize(render_text("CULT"), ANSI_CYAN, color))
    width = max(78, *(visible_length(line) for line in body))
    lines = ["=" * width]
    lines.extend(body)
    lines.append("")
    lines.append(center_text("Barbie Bitch Cult - Site File Grabber", width))
    lines.append("=" * width)
    return "\n".join(lines)


def render_text(text: str) -> list[str]:
    rows = [""] * 7
    for character in text.upper():
        if character == " ":
            for row_index in range(7):
                rows[row_index] += WORD_GAP
            continue
        pattern = BLOCK_FONT.get(character)
        if pattern is None:
            continue
        for row_index, row_pattern in enumerate(pattern):
            rows[row_index] += "".join(BLOCK_CELL if cell == "1" else BLANK_CELL for cell in row_pattern)
            rows[row_index] += LETTER_GAP
    return [row.rstrip() for row in rows]


def colorize(lines: list[str], color_code: str, enabled: bool) -> list[str]:
    if not enabled:
        return lines
    return [f"{color_code}{line}{ANSI_RESET}" if line else line for line in lines]


def center_text(text: str, width: int) -> str:
    if len(text) >= width:
        return text
    return text.center(width)


def visible_length(text: str) -> int:
    return len(re.sub(r"\033\[[0-9;]*m", "", text))


def is_module_available(module_name: str) -> bool:
    try:
        __import__(module_name)
    except ImportError:
        return False
    return True


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="site-file-grabber",
        description="Interactive shell for downloading site files from live pages, Google results, and Wayback Machine indexes.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--json", action="store_true", help="Emit JSON for supported commands.")
    parser.add_argument("command", nargs="?", choices=["doctor"], help="Optional command. Omit to launch the shell.")
    args = parser.parse_args(argv)

    if args.command == "doctor":
        selenium_available = is_module_available("selenium")
        payload = {
            "ok": True,
            "version": __version__,
            "python": sys.version.split()[0],
            "network_required": True,
            "dependencies": {
                "stdlib_only": False,
                "selenium_available": selenium_available,
                "selenium_required_for_google_browser": True,
            },
            "commands": ["interactive shell", "doctor"],
        }
        print(json.dumps(payload, indent=None if args.json else 2))
        return

    if args.json:
        print(json.dumps({"ok": False, "error": "--json is only supported with doctor"}))
        raise SystemExit(2)

    run_shell()


def run_shell() -> None:
    print(render_banner())
    print("Site File Grabber interactive shell\n")

    while True:
        print("1. Scrape from the live site")
        print("2. Scrape from the live site from Google")
        print("3. Scrape from historic")
        print("4. Exit Application")
        choice = input("\nSelect an option [1-4]: ").strip()

        try:
            if choice == "1":
                run_live(prompt_live_options())
            elif choice == "2":
                run_google(prompt_common_options())
            elif choice == "3":
                run_wayback(prompt_common_options())
            elif choice == "4":
                print("Exiting Site File Grabber.")
                return
            else:
                print("Enter a number from 1 through 4.\n")
        except KeyboardInterrupt:
            print("\nOperation cancelled.\n")
        except Exception as exc:
            print(f"\nError: {exc}\n")


def common_dict(options: CommonOptions) -> dict[str, object]:
    return {
        "site": options.site,
        "extensions": options.extensions,
        "output_dir": options.output_dir,
        "max_documents": options.max_documents,
        "delay": options.delay,
        "user_agent": options.user_agent,
        "timeout": options.timeout,
        "max_file_bytes": options.max_file_bytes,
    }


def prompt_common_options() -> CommonOptions:
    launch_cwd = Path.cwd()
    site = normalize_site(prompt_text("Website or domain to crawl"))
    extensions = prompt_extensions()
    output_dir = resolve_output_dir(prompt_text("Output directory", "downloads"), launch_cwd)
    max_documents = prompt_int("Maximum amount of documents to grab", 100, minimum=1)
    delay = prompt_float("Rate limit delay in seconds", 1.0, minimum=0.0)
    timeout = prompt_float("HTTP timeout in seconds", 30.0, minimum=1.0)
    max_file_bytes = prompt_int("Maximum bytes per downloaded file, 0 for no limit", 0, minimum=0)
    user_agent = prompt_text("User-Agent", DEFAULT_USER_AGENT)
    output_dir.mkdir(parents=True, exist_ok=True)
    return CommonOptions(
        site=site,
        extensions=extensions,
        output_dir=output_dir,
        max_documents=max_documents,
        delay=delay,
        user_agent=user_agent,
        timeout=timeout,
        max_file_bytes=max_file_bytes,
    )


def prompt_live_options() -> LiveOptions:
    common = prompt_common_options()
    max_pages = prompt_int("Maximum pages to crawl", 100, minimum=1)
    max_page_bytes = prompt_int("Maximum bytes to read per page", 200_000_000, minimum=1)
    max_depth = prompt_int("Maximum crawl depth", 4, minimum=0)
    respect_robots = prompt_bool("Respect robots.txt", True)
    return LiveOptions(
        **common_dict(common),
        max_pages=max_pages,
        max_page_bytes=max_page_bytes,
        max_depth=max_depth,
        respect_robots=respect_robots,
    )


def prompt_text(label: str, default: str | None = None) -> str:
    prompt = f"{label}"
    if default is not None:
        prompt += f" [{default}]"
    prompt += ": "
    while True:
        value = input(prompt).strip()
        if value:
            return value
        if default is not None:
            return default
        print("This value is required.")


def prompt_int(label: str, default: int, minimum: int | None = None) -> int:
    while True:
        raw = input(f"{label} [{default}]: ").strip()
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            print("Enter a whole number.")
            continue
        if minimum is not None and value < minimum:
            print(f"Enter a number greater than or equal to {minimum}.")
            continue
        return value


def prompt_float(label: str, default: float, minimum: float | None = None) -> float:
    while True:
        raw = input(f"{label} [{default:g}]: ").strip()
        if not raw:
            return default
        try:
            value = float(raw)
        except ValueError:
            print("Enter a number.")
            continue
        if minimum is not None and value < minimum:
            print(f"Enter a number greater than or equal to {minimum:g}.")
            continue
        return value


def prompt_bool(label: str, default: bool) -> bool:
    suffix = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{label} [{suffix}]: ").strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes", "true", "1"}:
            return True
        if raw in {"n", "no", "false", "0"}:
            return False
        print("Enter yes or no.")


def prompt_extensions() -> set[str]:
    default = ",".join(DEFAULT_EXTENSIONS)
    return normalize_extensions(prompt_text("File extensions to look for, comma separated", default))


def normalize_extensions(raw: str | Iterable[str]) -> set[str]:
    if isinstance(raw, str):
        parts = raw.split(",")
    else:
        parts = list(raw)
    extensions = {part.strip().lower().lstrip(".") for part in parts if part.strip()}
    if not extensions:
        raise ValueError("At least one file extension is required.")
    return extensions


def normalize_site(site: str) -> str:
    site = site.strip()
    if not urllib.parse.urlparse(site).scheme:
        site = f"https://{site}"
    parsed = urllib.parse.urlparse(site)
    if not parsed.netloc:
        raise ValueError("Enter a valid website or domain.")
    path = parsed.path or "/"
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def resolve_output_dir(value: str, launch_cwd: Path) -> Path:
    path = Path(os.path.expanduser(value))
    if not path.is_absolute():
        path = launch_cwd / path
    return path.resolve()


def run_live(options: LiveOptions) -> list[Path]:
    print("\nStarting live site crawl...")
    found = crawl_live(options)
    print(f"Found {len(found)} matching file URL(s).")
    return download_urls(found, options)


def crawl_live(options: LiveOptions) -> list[str]:
    root = normalize_site(options.site)
    queue: list[tuple[str, int]] = [(root, 0)]
    visited: set[str] = set()
    found: list[str] = []
    found_seen: set[str] = set()
    robots = build_robots(root, options) if options.respect_robots else None

    while queue and len(visited) < options.max_pages and len(found) < options.max_documents:
        page_url, depth = queue.pop(0)
        page_url = strip_fragment(page_url)
        if page_url in visited or depth > options.max_depth:
            continue
        if robots and not robots.can_fetch(options.user_agent, page_url):
            print(f"Skipping blocked by robots.txt: {page_url}")
            visited.add(page_url)
            continue

        visited.add(page_url)
        print(f"Crawling [{len(visited)}/{options.max_pages}] depth {depth}: {page_url}")
        try:
            body, final_url, _headers = fetch_bytes(
                page_url,
                max_bytes=options.max_page_bytes,
                user_agent=options.user_agent,
                timeout=options.timeout,
            )
        except Exception as exc:
            print(f"  Failed: {exc}")
            sleep_between(options.delay)
            continue

        links = extract_links(final_url, body)
        for link in links:
            if has_target_extension(link, options.extensions):
                if link not in found_seen:
                    found_seen.add(link)
                    found.append(link)
                    print(f"  File: {link}")
                    if len(found) >= options.max_documents:
                        break
            elif depth < options.max_depth and should_crawl(root, link):
                normalized = strip_fragment(link)
                if normalized not in visited and all(normalized != queued[0] for queued in queue):
                    queue.append((normalized, depth + 1))
        sleep_between(options.delay)

    return found[: options.max_documents]


def run_google(options: CommonOptions) -> list[Path]:
    print("\nStarting Google result lookup...")
    found: list[str] = []
    seen: set[str] = set()
    domain = urllib.parse.urlparse(normalize_site(options.site)).netloc
    driver = create_selenium_driver(options)
    saved: list[Path] = []

    try:
        for extension in sorted(options.extensions):
            if len(found) >= options.max_documents:
                break
            query = f"site:{domain} filetype:{extension}"
            search_url = "https://www.google.com/search?" + urllib.parse.urlencode(
                {"q": query, "num": "100", "filter": "0", "hl": "en", "pws": "0"}
            )
            print(f"Searching Google: {query}")
            result_urls: list[str] = []

            if driver is not None:
                result_urls = fetch_selenium_google_results(driver, search_url, query)
            else:
                print("  Selenium is unavailable; using HTTP search fallbacks.")

            if not any(is_matching_result(url, domain, options.extensions) for url in result_urls):
                print("  Visible browser did not expose matching result links; trying search fallbacks with the same dork...")
                result_urls = fetch_search_fallback_results(query, options)

            for result_url in result_urls:
                if (
                    result_url not in seen
                    and is_matching_result(result_url, domain, options.extensions)
                ):
                    seen.add(result_url)
                    found.append(result_url)
                    print(f"  File: {result_url}")
                    if len(found) >= options.max_documents:
                        break
            sleep_between(options.delay)
        print(f"Found {len(found)} matching Google result URL(s).")
        saved = download_urls(found, options, browser_driver=driver)
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

    return saved


def is_matching_result(url: str, domain: str, extensions: set[str]) -> bool:
    return has_target_extension(url, extensions) and host_matches(domain, url)


def fetch_duckduckgo_results(query: str, options: CommonOptions) -> list[str]:
    search_url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    try:
        body, final_url, _headers = fetch_bytes(
            search_url,
            max_bytes=5_000_000,
            user_agent=options.user_agent,
            timeout=options.timeout,
        )
    except Exception as exc:
        print(f"  DuckDuckGo fallback failed: {exc}")
        return []
    return extract_google_result_urls(final_url, body)


def fetch_brave_results(query: str, options: CommonOptions) -> list[str]:
    search_url = "https://search.brave.com/search?" + urllib.parse.urlencode({"q": query, "count": "50"})
    try:
        body, final_url, _headers = fetch_bytes(
            search_url,
            max_bytes=5_000_000,
            user_agent=options.user_agent,
            timeout=options.timeout,
        )
    except Exception as exc:
        print(f"  Brave Search fallback failed: {exc}")
        return []
    return extract_google_result_urls(final_url, body)


def fetch_search_fallback_results(query: str, options: CommonOptions) -> list[str]:
    urls: list[str] = []
    urls.extend(fetch_duckduckgo_results(query, options))
    sleep_between(options.delay)
    urls.extend(fetch_brave_results(query, options))
    sleep_between(options.delay)
    urls.extend(fetch_yahoo_results(query, options))
    return dedupe_preserve_order(urls)


def fetch_yahoo_results(query: str, options: CommonOptions) -> list[str]:
    search_url = "https://search.yahoo.com/search?" + urllib.parse.urlencode({"p": query, "n": "50"})
    try:
        body, final_url, _headers = fetch_bytes(
            search_url,
            max_bytes=5_000_000,
            user_agent=options.user_agent,
            timeout=options.timeout,
        )
    except Exception as exc:
        print(f"  Yahoo fallback failed: {exc}")
        return []
    return extract_google_result_urls(final_url, body)


def create_selenium_driver(options: CommonOptions):
    try:
        from selenium import webdriver
        from selenium.common.exceptions import WebDriverException
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from selenium.webdriver.firefox.options import Options as FirefoxOptions
    except ImportError:
        print("  Selenium is not installed. Install it with: python3 -m pip install --user selenium")
        return None

    chrome_options = ChromeOptions()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument(f"--user-agent={options.user_agent}")
    chrome_options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": str(options.output_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True,
        },
    )
    chrome_binary = find_chromium_browser()
    if chrome_binary:
        chrome_options.binary_location = chrome_binary

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(max(options.timeout, 30.0))
        allow_chrome_downloads(driver, options.output_dir)
        print("  Opened visible Selenium Chrome browser for Google search.")
        return driver
    except WebDriverException as exc:
        print(f"  Could not start Selenium Chrome: {short_error(exc)}")

    firefox_options = FirefoxOptions()
    firefox_options.set_preference("general.useragent.override", options.user_agent)
    firefox_options.set_preference("browser.download.folderList", 2)
    firefox_options.set_preference("browser.download.dir", str(options.output_dir))
    firefox_options.set_preference("browser.download.useDownloadDir", True)
    firefox_options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf,application/octet-stream")
    firefox_options.set_preference("pdfjs.disabled", True)
    try:
        driver = webdriver.Firefox(options=firefox_options)
        driver.set_page_load_timeout(max(options.timeout, 30.0))
        print("  Opened visible Selenium Firefox browser for Google search.")
        return driver
    except WebDriverException as exc:
        print(f"  Could not start Selenium Firefox: {short_error(exc)}")
        return None


def allow_chrome_downloads(driver, output_dir: Path) -> None:
    try:
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": str(output_dir)},
        )
    except Exception:
        pass


def fetch_selenium_google_results(driver, search_url: str, query: str) -> list[str]:
    print(f"  Opening visible browser search: {query}")
    try:
        driver.get(search_url)
    except Exception as exc:
        print(f"  Browser navigation failed: {short_error(exc)}")
        return []
    if wait_for_captcha_if_present(driver, "Google search") == "skip":
        return []
    settle_browser_page(driver)
    urls = collect_selenium_result_urls(driver)
    print(f"  Browser exposed {len(urls)} candidate result link(s).")
    return urls


def wait_for_captcha_if_present(
    driver,
    context: str = "page",
    url: str | None = None,
    output_dir: Path | None = None,
    before: dict[Path, tuple[int, int]] | None = None,
) -> str:
    settle_browser_page(driver)
    while page_needs_human_verification(driver):
        print(f"\n  CAPTCHA/security verification detected on {context}.")
        print("  Complete it or wait for it to finish in the visible browser window.")
        if url and output_dir:
            print("  If it keeps spinning, type 'o' to open this URL in your normal browser.")
            print(f"  For manual downloads, save or move the file into: {output_dir}")
        choice = input("  Press Enter to re-check, type 's' to skip, or 'o' to open normally: ").strip().lower()
        if choice in {"s", "skip"}:
            return "skip"
        if choice in {"o", "open"} and url and output_dir:
            webbrowser.open(url)
            input("  Save or move the file into the output directory, then press Enter to continue...")
            if before is not None and newest_completed_file(output_dir, before) is not None:
                return "manual"
            print("  No new completed file was detected in the output directory.")
            retry = input("  Press Enter to re-check Selenium, or type 's' to skip this file: ").strip().lower()
            if retry in {"s", "skip"}:
                return "skip"
        settle_browser_page(driver)
    return "ok"


def page_needs_human_verification(driver) -> bool:
    try:
        current_url = driver.current_url.lower()
        source = driver.page_source.lower()
    except Exception:
        return False
    return any(indicator in current_url or indicator in source for indicator in VERIFICATION_INDICATORS)


def settle_browser_page(driver) -> None:
    time.sleep(2)
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 0);")
    except Exception:
        pass


def collect_selenium_result_urls(driver) -> list[str]:
    candidates: list[str] = []
    try:
        candidates.extend(extract_google_result_urls(driver.current_url, driver.page_source.encode("utf-8", errors="ignore")))
    except Exception:
        pass
    try:
        from selenium.webdriver.common.by import By

        for element in driver.find_elements(By.TAG_NAME, "a"):
            href = element.get_attribute("href")
            if href:
                target = unwrap_google_result_url(href)
                if target:
                    candidates.append(target)
    except Exception:
        pass
    return dedupe_preserve_order(candidates)


def find_chromium_browser() -> str | None:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "brave-browser"):
        path = shutil.which(name)
        if path:
            return path
    return None


def short_error(exc: Exception) -> str:
    text = str(exc).strip().splitlines()
    return text[0] if text else exc.__class__.__name__


def run_wayback(options: CommonOptions) -> list[Path]:
    print("\nStarting Wayback Machine CDX lookup...")
    target = normalize_site(options.site)
    cdx_url = "https://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode(
        {
            "url": f"{target}*",
            "output": "text",
            "fl": "original",
            "collapse": "urlkey",
        }
    )
    print(f"Fetching CDX index: {cdx_url}")
    body, _final_url, _headers = fetch_bytes(
        cdx_url,
        max_bytes=100_000_000,
        user_agent=options.user_agent,
        timeout=options.timeout,
    )
    originals = body.decode("utf-8", errors="ignore").splitlines()
    found = [
        url.strip()
        for url in originals
        if url.strip() and has_target_extension(url.strip(), options.extensions)
    ][: options.max_documents]
    print(f"Found {len(found)} matching archived URL(s).")

    archived_urls = [wayback_raw_url(url) for url in found]
    return download_urls(archived_urls, options, display_urls=found)


def build_robots(root: str, options: LiveOptions) -> urllib.robotparser.RobotFileParser:
    parsed = urllib.parse.urlparse(root)
    robots_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.read()
    except Exception as exc:
        print(f"Could not read robots.txt ({exc}); continuing with allow-all behavior.")
    return parser


def fetch_bytes(url: str, max_bytes: int, user_agent: str, timeout: float) -> tuple[bytes, str, object]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = response.read(min(64 * 1024, max_bytes - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total >= max_bytes:
                break
        return b"".join(chunks), response.geturl(), response.headers


def extract_links(base_url: str, body: bytes) -> list[str]:
    text = body.decode("utf-8", errors="ignore")
    parser = LinkExtractor()
    parser.feed(text)
    links: list[str] = []
    for raw in parser.links:
        for value in split_candidate_link(raw):
            absolute = absolutize_url(base_url, value)
            if absolute:
                links.append(absolute)
    return dedupe_preserve_order(links)


def split_candidate_link(raw: str) -> list[str]:
    raw = raw.strip()
    if not raw:
        return []
    return [raw]


def absolutize_url(base_url: str, value: str) -> str | None:
    value = value.strip()
    if not value or value.startswith("#"):
        return None
    if value.lower().startswith(("mailto:", "tel:", "javascript:", "data:")):
        return None
    absolute = urllib.parse.urljoin(base_url, value)
    parsed = urllib.parse.urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.params, parsed.query, ""))


def extract_google_result_urls(base_url: str, body: bytes) -> list[str]:
    results: list[str] = []
    text = normalize_google_html(body)
    candidates = extract_links(base_url, text.encode("utf-8", errors="ignore"))
    candidates.extend(URL_RE.findall(text))
    candidates.extend(decode_percent_encoded_urls(text))

    for link in candidates:
        unwrapped = unwrap_google_result_url(link)
        if unwrapped:
            results.append(unwrapped)
    return dedupe_preserve_order(results)


def normalize_google_html(body: bytes) -> str:
    text = body.decode("utf-8", errors="ignore")
    text = html.unescape(text)
    return (
        text.replace("\\u003d", "=")
        .replace("\\u0026", "&")
        .replace("\\u003c", "<")
        .replace("\\u003e", ">")
        .replace("\\/", "/")
    )


def decode_percent_encoded_urls(text: str) -> list[str]:
    decoded: list[str] = []
    for match in ENCODED_URL_RE.findall(text):
        value = match
        for _ in range(3):
            next_value = urllib.parse.unquote(value)
            if next_value == value:
                break
            value = next_value
        decoded.append(value)
    return decoded


def unwrap_google_result_url(link: str) -> str | None:
    link = html.unescape(link).strip()
    if not link:
        return None
    parsed = urllib.parse.urlparse(link)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    if is_google_host(parsed.netloc):
        query = urllib.parse.parse_qs(parsed.query)
        for key in ("url", "q", "adurl"):
            for value in query.get(key, []):
                target = normalize_result_url(value)
                if target and not is_google_host(urllib.parse.urlparse(target).netloc):
                    return target
        return None
    if is_duckduckgo_host(parsed.netloc) and parsed.path.startswith("/l/"):
        query = urllib.parse.parse_qs(parsed.query)
        for value in query.get("uddg", []):
            target = normalize_result_url(value)
            if target and not is_duckduckgo_host(urllib.parse.urlparse(target).netloc):
                return target
        return None
    if is_yahoo_redirect(parsed.netloc, parsed.path):
        match = re.search(r"/RU=([^/]+)", link)
        if match:
            target = normalize_result_url(match.group(1))
            if target and not is_yahoo_host(urllib.parse.urlparse(target).netloc):
                return target
        return None
    return normalize_result_url(link)


def normalize_result_url(link: str) -> str | None:
    link = html.unescape(link).strip()
    if not link:
        return None
    for _ in range(3):
        decoded = urllib.parse.unquote(link)
        if decoded == link:
            break
        link = decoded
    parsed = urllib.parse.urlparse(link)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.params, parsed.query, ""))


def is_google_host(host: str) -> bool:
    host = host.lower().split("@")[-1].split(":")[0]
    return host == "google.com" or host.endswith(".google.com")


def is_duckduckgo_host(host: str) -> bool:
    host = host.lower().split("@")[-1].split(":")[0]
    return host == "duckduckgo.com" or host.endswith(".duckduckgo.com")


def is_yahoo_host(host: str) -> bool:
    host = host.lower().split("@")[-1].split(":")[0]
    return host == "yahoo.com" or host.endswith(".yahoo.com")


def is_yahoo_redirect(host: str, path: str) -> bool:
    return host.lower().endswith("search.yahoo.com") and "/RU=" in path


def should_crawl(root: str, candidate: str) -> bool:
    parsed = urllib.parse.urlparse(candidate)
    suffix = PurePosixPath(urllib.parse.unquote(parsed.path)).suffix.lower()
    return host_matches(urllib.parse.urlparse(root).netloc, candidate) and suffix in PAGE_LIKE_EXTENSIONS


def host_matches(root_host: str, candidate: str) -> bool:
    host = urllib.parse.urlparse(candidate).netloc.lower().split("@")[-1].split(":")[0]
    root = root_host.lower().split("@")[-1].split(":")[0]
    return host == root or host.endswith(f".{root}")


def has_target_extension(url: str, extensions: set[str]) -> bool:
    parsed = urllib.parse.urlparse(url)
    path = urllib.parse.unquote(parsed.path).lower()
    suffix = PurePosixPath(path).suffix.lower().lstrip(".")
    return suffix in extensions


def download_urls(
    urls: list[str],
    options: CommonOptions,
    display_urls: list[str] | None = None,
    browser_driver=None,
) -> list[Path]:
    saved: list[Path] = []
    for index, url in enumerate(urls[: options.max_documents], start=1):
        label = display_urls[index - 1] if display_urls else url
        destination = unique_destination(options.output_dir, label, index)
        print(f"Downloading [{index}/{min(len(urls), options.max_documents)}]: {label}")
        browser_saved = None
        if browser_driver is not None:
            browser_saved = download_file_with_browser(browser_driver, url, destination, options)
            if browser_saved is SKIP_BROWSER_DOWNLOAD:
                sleep_between(options.delay)
                continue
            if isinstance(browser_saved, Path):
                saved.append(browser_saved)
                print(f"  Saved: {browser_saved}")
                sleep_between(options.delay)
                continue

        try:
            download_file(
                url,
                destination,
                user_agent=options.user_agent,
                timeout=options.timeout,
                max_bytes=options.max_file_bytes,
            )
            saved.append(destination)
            print(f"  Saved: {destination}")
        except urllib.error.HTTPError as exc:
            print(f"  HTTP {exc.code}: {exc.reason}")
        except Exception as exc:
            print(f"  Failed: {exc}")
        sleep_between(options.delay)
    print(f"Saved {len(saved)} file(s) to {options.output_dir}\n")
    return saved


def download_file_with_browser(driver, url: str, destination: Path, options: CommonOptions):
    downloaded = try_browser_download(driver, url, options)
    if downloaded is SKIP_BROWSER_DOWNLOAD:
        return SKIP_BROWSER_DOWNLOAD
    if downloaded is None and not page_needs_human_verification(driver):
        print("  Retrying browser download after verification/session setup...")
        downloaded = try_browser_download(driver, url, options)
    if downloaded is SKIP_BROWSER_DOWNLOAD:
        return SKIP_BROWSER_DOWNLOAD
    if downloaded is None:
        print("  Browser did not produce a completed download; falling back to HTTP downloader.")
        return None
    if options.max_file_bytes and downloaded.stat().st_size > options.max_file_bytes:
        downloaded.unlink(missing_ok=True)
        print(f"  Browser download exceeded max bytes per file ({options.max_file_bytes}).")
        return None
    if downloaded.resolve() != destination.resolve():
        destination = unique_destination_for_path(destination)
        downloaded.rename(destination)
    return destination


def try_browser_download(driver, url: str, options: CommonOptions):
    before = directory_snapshot(options.output_dir)
    try:
        driver.get(url)
    except Exception as exc:
        print(f"  Browser download navigation warning: {short_error(exc)}")
    settle_browser_page(driver)
    verification_action = wait_for_captcha_if_present(
        driver,
        urllib.parse.urlparse(url).netloc or "download page",
        url=url,
        output_dir=options.output_dir,
        before=before,
    )
    if verification_action == "skip":
        print("  Skipping this file.")
        return SKIP_BROWSER_DOWNLOAD
    if verification_action == "manual":
        manual_file = newest_completed_file(options.output_dir, before)
        if manual_file is not None:
            return manual_file
        print("  Manual download was not detected; skipping this file.")
        return SKIP_BROWSER_DOWNLOAD
    return wait_for_browser_download(options.output_dir, before, options.timeout)


def directory_snapshot(directory: Path) -> dict[Path, tuple[int, int]]:
    snapshot: dict[Path, tuple[int, int]] = {}
    for path in directory.iterdir():
        if path.is_file():
            stat = path.stat()
            snapshot[path] = (stat.st_size, stat.st_mtime_ns)
    return snapshot


def wait_for_browser_download(directory: Path, before: dict[Path, tuple[int, int]], timeout: float) -> Path | None:
    deadline = time.time() + max(timeout, 30.0)
    latest: Path | None = None
    while time.time() < deadline:
        partials = partial_downloads(directory)
        candidates = completed_download_candidates(directory, before)
        if candidates and not partials:
            newest = max(candidates, key=lambda item: item.stat().st_mtime_ns)
            if latest == newest:
                return newest
            latest = newest
        time.sleep(0.5)
    return None


def newest_completed_file(directory: Path, before: dict[Path, tuple[int, int]]) -> Path | None:
    candidates = completed_download_candidates(directory, before)
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.stat().st_mtime_ns)


def completed_download_candidates(directory: Path, before: dict[Path, tuple[int, int]]) -> list[Path]:
    candidates: list[Path] = []
    for path in directory.iterdir():
        if not path.is_file() or path.suffix.lower() in {".crdownload", ".part", ".tmp"}:
            continue
        stat = path.stat()
        old = before.get(path)
        if old is None or old != (stat.st_size, stat.st_mtime_ns):
            candidates.append(path)
    return candidates


def partial_downloads(directory: Path) -> list[Path]:
    return [
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in {".crdownload", ".part", ".tmp"}
    ]


def unique_destination_for_path(destination: Path) -> Path:
    if not destination.exists():
        return destination
    stem = destination.stem
    suffix = destination.suffix
    counter = 2
    while True:
        candidate = destination.with_name(f"{stem}-{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def download_file(url: str, destination: Path, user_agent: str, timeout: float, max_bytes: int = 0) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    total = 0
    with urllib.request.urlopen(request, timeout=timeout) as response, destination.open("wb") as handle:
        while True:
            chunk = response.read(64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if max_bytes and total > max_bytes:
                handle.close()
                destination.unlink(missing_ok=True)
                raise ValueError(f"download exceeded max bytes per file ({max_bytes})")
            handle.write(chunk)


def unique_destination(output_dir: Path, url: str, index: int) -> Path:
    parsed = urllib.parse.urlparse(url)
    name = Path(urllib.parse.unquote(parsed.path)).name or f"download-{index}"
    name = sanitize_filename(name)
    if "." not in name:
        suffix = PurePosixPath(urllib.parse.unquote(parsed.path)).suffix
        if suffix:
            name += suffix
    candidate = output_dir / name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    counter = 2
    while True:
        candidate = output_dir / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return cleaned or "download"


def wayback_raw_url(original_url: str) -> str:
    return "https://web.archive.org/web/0id_/" + original_url


def strip_fragment(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.params, parsed.query, ""))


def sleep_between(delay: float) -> None:
    if delay > 0:
        time.sleep(delay)


def dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output


if __name__ == "__main__":
    main()
