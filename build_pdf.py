"""
build_pdf.py — convert paper.md to paper.pdf via Chrome headless.
1. Convert markdown to HTML using the markdown Python module.
2. Inject the HTML into our academic template.
3. Print to PDF via Chrome headless.
"""
import sys, os, subprocess, shutil

PAPER_MD = "paper.md"
TEMPLATE = "paper_template.html"
HTML_OUT = "paper.html"
PDF_OUT = "paper.pdf"

# Find Chrome
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]
chrome = next((p for p in CHROME_CANDIDATES if os.path.isfile(p)), None)
if not chrome:
    sys.exit("Chrome not found. Install it or set CHROME env var.")

# 1. Try to import markdown; if missing, install it
try:
    import markdown
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown"])
    import markdown

# 2. Read paper.md, strip the leading # title block (we'll render that as the page title)
with open(PAPER_MD, "r", encoding="utf-8") as fh:
    md = fh.read()

# Remove leading comment block
import re
md = re.sub(r"^#.*\n>.*\n(?:>.*\n)*", "", md, count=1, flags=re.MULTILINE).strip()
md = re.sub(r"^# [^\n]+\n", "", md, count=1, flags=re.MULTILINE).strip()

# 3. Convert MD to HTML
md_converter = markdown.Markdown(
    extensions=["fenced_code", "tables", "sane_lists", "toc", "nl2br"],
    extension_configs={"toc": {"toc_depth": "2"}},
)
body_html = md_converter.convert(md)

# 4. Wrap in template
with open(TEMPLATE, "r", encoding="utf-8") as fh:
    template = fh.read()
full_html = template.replace("__BODY__", body_html)

with open(HTML_OUT, "w", encoding="utf-8") as fh:
    fh.write(full_html)

# 5. Render to PDF via Chrome headless
cmd = [
    chrome,
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    f"--print-to-pdf={os.path.abspath(PDF_OUT)}",
    "--no-pdf-header-footer",
    f"file://{os.path.abspath(HTML_OUT)}",
]
print(f"Running: {' '.join(cmd[:3])} ...")
res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
if res.returncode != 0:
    print("STDERR:", res.stderr)
    sys.exit(f"Chrome returned {res.returncode}")
print(f"Wrote {PDF_OUT}")
print(f"Size: {os.path.getsize(PDF_OUT):,} bytes")