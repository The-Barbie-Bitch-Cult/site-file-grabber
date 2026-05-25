# The Barbie Bitch Cult presents: The Site File Grabber

Tired of TTI programs scrubbing their sins from the internet like a bad spray tan? This script is your glitter-covered crowbar. Point it at any domain and watch it dig up PDFs, Word docs, spreadsheets, images, videos - whatever file types you tell it to hunt - straight from the live site, from pages Google knows about but the main navigation doesn’t, and from the sweet, rotting archives of the Internet Archive where deleted pages go to die (but never actually disappear). It’s the cyber equivalent of dumpster-diving behind a residential treatment center at 3 a.m., except you don’t have to touch anything questionable with your bare hands.

For those of us digging into the Troubled Teen Industry, this kind of forensic scraping is pure gold. Old intake forms, staff manuals, parent contracts, “success story” PDFs that got memory-holed, incriminating photos from long-dead websites. These are the receipts that survive even when the program rebrands for the third time and pretends it was never called “Cross Creek Manor.” When survivors, journalists, or pissed-off parents need evidence, this tool turns vague memories into downloadable, timestamped proof.

# Legal & Ethical Reminder (because we’re chaotic, not stupid):
Use this responsibly and only in ways that are 100% legal in your jurisdiction. Respect robots.txt where it actually matters, don’t DDoS anyone, and don’t be a creep. This is for legitimate research, investigative journalism, and holding abusive institutions accountable, not for stalking, harassment, or any other clown shit that gets you visited by people with badges. Barbie Bitch Cult is not responsible for you doing something terminally online and getting yourself canceled or arrested. Play smart or stay out of the sandbox.

Now go forth and resurrect the receipts they thought they buried.


# Site File Grabber

Site File Grabber is an interactive command-line tool for finding and downloading files from websites.

It can:

- Crawl a live website and download linked files.
- Search Google for files on a website using `site:` and `filetype:` searches.
- Search old archived URLs from the Wayback Machine.

When you run it, you will see a menu:

```text
1. Scrape from the live site
2. Scrape from the live site from Google
3. Scrape from historic
4. Exit Application
```

Use this tool only on sites and files you are authorized to access and download.

## What You Need

You need these installed:

- Python 3.10 or newer
- Google Chrome, Chromium, or Firefox
- Internet access
- This project folder

Option 2 uses Selenium to open a real browser window. Selenium is installed by the setup steps below.

## Windows Setup

These steps assume you are using Windows 10 or Windows 11.

### 1. Install Python

1. Open [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/).
2. Download the latest Python 3 installer.
3. Run the installer.
4. Very important: check the box that says **Add python.exe to PATH**.
5. Click **Install Now**.
6. Open PowerShell.
7. Check Python:

```powershell
python --version
```

If that does not work, try:

```powershell
py --version
```

### 2. Install a Browser

Install one of these:

- Google Chrome: [https://www.google.com/chrome/](https://www.google.com/chrome/)
- Firefox: [https://www.mozilla.org/firefox/](https://www.mozilla.org/firefox/)

Chrome is recommended.

### 3. Open PowerShell in the Project Folder

1. Open File Explorer.
2. Go to the `Document-Grabber` folder.
3. Click the address bar.
4. Type `powershell`.
5. Press Enter.

PowerShell should open inside the project folder.

### 4. Create a Virtual Environment

Run:

```powershell
python -m venv .venv
```

If `python` does not work, run:

```powershell
py -m venv .venv
```

### 5. Activate the Virtual Environment

Run:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell says scripts are disabled, run this once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

You should see `(.venv)` at the beginning of your PowerShell prompt.

### 6. Install the Tool

Run:

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

### 7. Run the Tool

Run:

```powershell
site-file-grabber
```

If that command does not work, run:

```powershell
python -m site_file_grabber.cli
```

## macOS Setup

These steps assume you are using Terminal on macOS.

### 1. Install Python

The easiest beginner option is the official Python installer:

1. Open [https://www.python.org/downloads/macos/](https://www.python.org/downloads/macos/).
2. Download the latest Python 3 installer.
3. Run the installer.
4. Open Terminal.
5. Check Python:

```bash
python3 --version
```

### 2. Install a Browser

Install one of these:

- Google Chrome: [https://www.google.com/chrome/](https://www.google.com/chrome/)
- Firefox: [https://www.mozilla.org/firefox/](https://www.mozilla.org/firefox/)

Chrome is recommended.

### 3. Open Terminal in the Project Folder

If the project folder is in Downloads, this might look like:

```bash
cd ~/Downloads/Document-Grabber
```

If it is somewhere else, type `cd `, drag the folder into Terminal, then press Enter.

### 4. Create a Virtual Environment

Run:

```bash
python3 -m venv .venv
```

### 5. Activate the Virtual Environment

Run:

```bash
source .venv/bin/activate
```

You should see `(.venv)` at the beginning of your Terminal prompt.

### 6. Install the Tool

Run:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

### 7. Run the Tool

Run:

```bash
site-file-grabber
```

If that command does not work, run:

```bash
python -m site_file_grabber.cli
```

## Linux Setup

These steps are for Ubuntu, Debian, Linux Mint, Pop!_OS, and similar Linux systems.

### 1. Install Python and Basic Tools

Open Terminal and run:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip make
```

Check Python:

```bash
python3 --version
```

### 2. Install a Browser

Chrome is recommended.

To install Chromium:

```bash
sudo apt install -y chromium-browser
```

On some systems the package is called `chromium`:

```bash
sudo apt install -y chromium
```

You can also install Google Chrome from:

[https://www.google.com/chrome/](https://www.google.com/chrome/)

Firefox usually comes preinstalled. If not:

```bash
sudo apt install -y firefox
```

### 3. Open Terminal in the Project Folder

Example:

```bash
cd ~/Documents/Document-Grabber
```

### 4. Install the Tool

On Linux, the easiest install is:

```bash
make install-local
```

This creates a `.venv` folder, installs dependencies, and installs the command at:

```text
~/.local/bin/site-file-grabber
```

### 5. Make Sure `~/.local/bin` Is on PATH

Check:

```bash
command -v site-file-grabber
```

If nothing prints, run:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Then check again:

```bash
command -v site-file-grabber
```

### 6. Run the Tool

Run:

```bash
site-file-grabber
```

If that command does not work, run:

```bash
source .venv/bin/activate
python -m site_file_grabber.cli
```

## How to Use the Tool

### Option 1: Scrape from the live site

Use this when you want the tool to crawl pages on a live website and look for linked files.

You will be asked for:

- Website or domain
- File extensions, such as `pdf,docx,jpg`
- Output directory
- Maximum pages to crawl
- Maximum bytes to read per page
- Maximum crawl depth
- Maximum documents to download
- Whether to respect `robots.txt`
- Delay between requests

### Option 2: Scrape from the live site from Google

Use this when Google can find files on a site better than the site crawler can.

The tool searches Google using this kind of query:

```text
site:example.com filetype:pdf
```

This option opens a real browser window. Do not close that browser window while the tool is running.

If Google or the target website shows a CAPTCHA, Cloudflare page, or other security verification:

1. Complete it or wait for it in the visible browser.
2. Return to the terminal.
3. Press Enter.

If a target-site verification page spins forever:

1. Type `o` at the terminal prompt.
2. The tool will open the PDF URL in your normal browser.
3. Manually save or move the file into the output directory.
4. Return to the terminal.
5. Press Enter.

To skip a stuck file, type:

```text
s
```

### Option 3: Scrape from historic

Use this when you want to search old URLs saved by the Wayback Machine.

The tool queries:

```text
https://web.archive.org/cdx/search/cdx?url=<YOUR-SITE>*&output=text&fl=original&collapse=urlkey
```

It filters those archived URLs by file extension, then downloads matching files.

## Common File Extensions

Examples:

```text
pdf,doc,docx,csv,ppt,zip,jpg,jpeg,png,webp,mp3,mp4,wav
```

You can enter one extension:

```text
pdf
```

Or many extensions:

```text
pdf,docx,csv,zip
```

Do not include spaces unless you want to. Both of these are fine:

```text
pdf,docx,csv
pdf, docx, csv
```

## Output Directory

If you enter:

```text
downloads
```

the tool creates a folder named `downloads` inside the folder where you launched the tool.

If you enter a full path, the tool uses that full path.

Windows example:

```text
C:\Users\YourName\Downloads\grabbed-files
```

macOS or Linux example:

```text
/Users/yourname/Downloads/grabbed-files
```

## Check the Installation

Run:

```bash
site-file-grabber --json doctor
```

Example output:

```json
{
  "ok": true,
  "version": "0.1.0",
  "python": "3.12.3",
  "network_required": true,
  "dependencies": {
    "stdlib_only": false,
    "selenium_available": true,
    "selenium_required_for_google_browser": true
  },
  "commands": ["interactive shell", "doctor"]
}
```

If `selenium_available` is `false`, activate your virtual environment and reinstall:

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

macOS or Linux:

```bash
source .venv/bin/activate
python -m pip install -e .
```

## Troubleshooting

### `site-file-grabber` command is not found

Use the Python module command instead:

```bash
python -m site_file_grabber.cli
```

On macOS or Linux, you may need:

```bash
python3 -m site_file_grabber.cli
```

### PowerShell says scripts are disabled

Run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate the virtual environment again:

```powershell
.\.venv\Scripts\Activate.ps1
```

### The browser opens but does not download a PDF

Some websites block automated browsers. If the terminal says a verification was detected:

- Solve it in the browser and press Enter.
- If it spins forever, type `o`, open the file in your normal browser, manually save it into the output folder, then press Enter.
- If you do not care about that file, type `s` to skip it.

### The tool downloads fewer files than Google shows

Search engines personalize and rate-limit results. Try:

- Running the search again later.
- Increasing the maximum documents value.
- Using option 1 or option 3 as a second pass.

### The site returns HTTP 403

`HTTP 403` means the website refused the request. Option 2 tries to work around this by using a visible browser download. If that still fails, use the manual browser handoff with `o`.

## Developer Commands

Run tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Install locally on Linux:

```bash
make install-local
```
