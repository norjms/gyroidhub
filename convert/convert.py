#!/usr/bin/env python3
"""Turn a GyroidVault release into gyroidhub: OpenPrintHQ's model library.

    python3 convert/convert.py <GyroidVault source tree>

The same steps run for every release, with no judgement involved:

1. Base path. GyroidVault expects to be the root of its own address. OpenPrintHQ serves it under the hub's
   name at a path (/apps/models/), with the proxy stripping that path, so every absolute URL the browser
   is given (pages, scripts, API calls, file links) is made relative to the page, and redirects from the
   server get the path in front (server/ahi.js, AHI_BASE_PATH).
2. Sign-in. Settings are seeded from the environment at every start (AHI_SETTING_<KEY>=value), which is how
   the installer turns on OIDC with Authelia, turns off local registration and requires a sign-in. With
   AHI_SSO=1 the login dialog sends people straight to Authelia, so someone signed in to the hub is signed
   in here without seeing a second sign-in.
3. Look. OpenPrintHQ's glass theme (public/css/ahi-theme.css) is loaded after GyroidVault's own stylesheet,
   the theme and accent pickers are fixed to it, and the brand reads OpenPrintHQ. The update check and the
   donation links of the upstream project are taken out; its name, licence and source stay in the footer and
   the About panel, as the AGPL asks.

Every exact edit names text that must appear a set number of times. When a release changes that text, the
script stops and says which edit failed, rather than guessing; fix the anchor here and run it again.
A final check fails if any absolute URL is left in the browser's files.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DISPLAY = "OpenPrintHQ Models"
SOURCE = "https://github.com/norjms/gyroidhub"
UPSTREAM = "https://github.com/TeeCodeDev/GyroidVault"

# What the browser fetches by absolute path, made relative to the page.
ROOTS = ("ahi-config.js", "api", "uploads", "library-files", "js", "css", "img", "fonts", "favicon.png", "favicon.ico", "icon.png")
ABSOLUTE = re.compile(r"""(?P<q>['"`(=])/(?P<p>(?:%s)(?=[/?'"`)\s]|$))""" % "|".join(re.escape(r) for r in ROOTS))
# Where the server writes a file or thumbnail URL into its answers, and how many times.
SERVER_URLS = {"server/utils/modelHelpers.js": 4, "server/routes/projects.js": 1, "server/routes/browse.js": 2}
SERVER_URL = re.compile(r"(?P<q>['`])/(?P<p>(?:library-files|uploads)/)")
BROWSER_FILES = ("public/index.html", "public/js/api.js", "public/js/app.js", "public/js/components.js",
                 "public/js/viewer.js")


class ConvertError(SystemExit):
    pass


def edit(root: Path, rel: str, old: str, new: str, count: int = 1) -> None:
    path = root / rel
    text = path.read_text(encoding="utf-8")
    found = text.count(old)
    if found != count:
        raise ConvertError(f"convert: {rel}: expected {count} of {old[:80]!r}, found {found}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def sub(root: Path, rel: str, pattern: str, new: str, count: int = 1, flags: int = re.S) -> None:
    path = root / rel
    text = path.read_text(encoding="utf-8")
    out, n = re.subn(pattern, new, text, flags=flags)
    if n != count:
        raise ConvertError(f"convert: {rel}: expected {count} match of /{pattern[:80]}/, found {n}")
    path.write_text(out, encoding="utf-8")


def relative_urls(root: Path) -> None:
    for rel in BROWSER_FILES:
        path = root / rel
        text = path.read_text(encoding="utf-8")
        path.write_text(ABSOLUTE.sub(lambda m: m.group("q") + m.group("p"), text), encoding="utf-8")
    # The stylesheet is under /css/, so its fonts are one folder up.
    css = root / "public/css/style.css"
    text, n = re.subn(r"url\((['\"]?)/fonts/", r"url(\1../fonts/", css.read_text(encoding="utf-8"))
    if n == 0:
        raise ConvertError("convert: public/css/style.css: no font URL to make relative")
    css.write_text(text, encoding="utf-8")
    # The file and thumbnail URLs the server builds for the browser (its routes stay at the root).
    for rel, count in SERVER_URLS.items():
        sub(root, rel, SERVER_URL.pattern, r"\g<q>\g<p>", count=count)


def server(root: Path) -> None:
    shutil.copy(HERE / "files/server/ahi.js", root / "server/ahi.js")
    shutil.copy(HERE / "files/ahi-start.sh", root / "ahi-start.sh")
    (root / "ahi-start.sh").chmod(0o755)
    edit(root, "server/index.js", "app.use(cookieParser());", "app.use(cookieParser());\nrequire('./ahi').routes(app);")
    edit(root, "server/index.js", "await initDatabase();", "await initDatabase();\n  require('./ahi').start();")
    # One way to authenticate to the token endpoint: the Basic header GyroidVault also sends. Authelia refuses
    # a client that authenticates twice, with the secret in the body as well.
    edit(root, "server/routes/auth.js", "tokenParams.set('client_secret', config.oidc_client_secret);",
         "/* gyroidhub: the secret goes in the Basic header only */")
    # Releases are taken by the build (upstream.env), never by the running app.
    edit(root, "server/routes/settings.js", "router.get('/system/updates', async (req, res) => {",
         "router.get('/system/updates', async (req, res) => {\n"
         "  if (process.env.AHI_SSO) return res.json({ hasUpdate: false, latestVersion: require('../../package.json').version, currentVersion: require('../../package.json').version, changelog: '', url: '' });")


def page(root: Path) -> None:
    html = "public/index.html"
    # One theme: OpenPrintHQ's, whatever the browser had saved.
    edit(root, html, "const t = localStorage.getItem('gv_theme') || 'glass';", "const t = 'glass';")
    edit(root, html, "const a = localStorage.getItem('gv_accent') || 'blue';", "const a = 'blue';")
    sub(root, html, r'<meta name="description" content="[^"]*">',
        f'<meta name="description" content="{DISPLAY}">')
    edit(root, html, "<title>GyroidVault</title>", f"<title>{DISPLAY}</title>")
    sub(root, html, r'(<link rel="stylesheet" href="/css/style\.css[^"]*">)',
        r'\1\n  <link rel="stylesheet" href="/css/ahi-theme.css">')
    # Fonts are named, never downloaded: an installation may have no internet.
    sub(root, html, r'\s*<link href="https://fonts\.googleapis\.com/[^"]*" rel="stylesheet">', "")
    sub(root, html, r'(<script src="/js/api\.js[^"]*"></script>)', r'<script src="/ahi-config.js"></script>\n  \1')
    # The brand: the OpenPrintHQ mark (openprinthq-ui's "mark" icon) and name in place of the logo.
    sub(root, html, r'<div class="nav-logo"[^>]*>\s*<img[^>]*>\s*</div>\s*<span class="nav-title"[^>]*>GyroidVault</span>',
        '<span class="ahi-tile" aria-hidden="true"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 2.5 20.5 7.3v9.4L12 21.5l-8.5-4.8V7.3z"/><path d="M8 16h8M9.5 12.8h5M11 9.6h2"/></svg></span>\n'
        '          <span class="nav-title ahi-brand"><b>OpenPrintHQ</b><small>Models</small></span>')
    sub(root, html, r'\s*<!-- Support on Ko-fi -->\s*<a href="https://ko-fi\.com/[^"]*"[^>]*>.*?</a>', "")
    # The footer names what this is built on, with its licence and both sources (AGPL section 13).
    sub(root, html, r'<div class="footer-content">.*?</div>\s*</div>\s*</footer>',
        '<div class="footer-content">\n'
        f'          <div class="footer-left">{DISPLAY} <span id="app-version"></span></div>\n'
        '          <div class="footer-right">\n'
        f'            <span class="footer-link">Based on <a href="{UPSTREAM}" target="_blank" rel="noopener noreferrer">GyroidVault</a>, AGPL-3.0</span>\n'
        f'            <a href="{SOURCE}" target="_blank" rel="noopener noreferrer" class="footer-link"><span>Source</span></a>\n'
        '          </div>\n'
        '        </div>\n'
        '      </footer>')
    shutil.copy(HERE / "files/public/css/ahi-theme.css", root / "public/css/ahi-theme.css")


def script(root: Path) -> None:
    app = "public/js/app.js"
    comp = "public/js/components.js"
    # Signed in through Authelia: no second sign-in screen.
    edit(root, app, "showLogin() { ",
         "showLogin() { if (window.AHI && window.AHI.sso) { window.location.href = '/api/auth/oidc/login'; return; } ")
    # The upstream project's release announcements are not OpenPrintHQ's: never opened on its own.
    edit(root, app, "checkWhatsNew() {", "checkWhatsNew() {\n    return;")
    # The name people read where the app names itself. GyroidVault's About panel keeps its name: it says what
    # this is built on.
    sub(root, app, r"<h1 style=\"margin-bottom:20px\">GyroidVault</h1>",
        f'<h1 style="margin-bottom:20px">{DISPLAY}</h1>')
    sub(root, app, r"Login to Access GyroidVault", "Sign in")
    edit(root, app, "Configure and personalize your GyroidVault instance", "Settings for the model library")
    edit(root, comp, "print history from GyroidVault.", "print history from the library.")
    edit(root, comp, "</strong> from GyroidVault?", "</strong> from the library?")


def check(root: Path) -> None:
    left = []
    for rel in BROWSER_FILES:
        for n, line in enumerate((root / rel).read_text(encoding="utf-8").splitlines(), 1):
            if ABSOLUTE.search(line):
                left.append(f"{rel}:{n}: {line.strip()[:120]}")
    if left:
        raise ConvertError("convert: absolute URLs left:\n" + "\n".join(left))
    for rel in SERVER_URLS:
        for n, line in enumerate((root / rel).read_text(encoding="utf-8").splitlines(), 1):
            if SERVER_URL.search(line):
                left.append(f"{rel}:{n}: {line.strip()[:120]}")
    if left:
        raise ConvertError("convert: absolute file URLs left on the server:\n" + "\n".join(left))
    if "/fonts/" in re.sub(r"\.\./fonts/", "", (root / "public/css/style.css").read_text(encoding="utf-8")):
        raise ConvertError("convert: public/css/style.css: an absolute font URL is left")


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        raise SystemExit(__doc__.splitlines()[2].strip())
    root = Path(argv[1]).resolve()
    if not (root / "server/index.js").is_file():
        raise ConvertError(f"convert: {root} is not a GyroidVault source tree")
    # Brand, scripts and pages first, while their anchors still have their absolute URLs.
    server(root)
    page(root)
    script(root)
    relative_urls(root)
    check(root)
    print(f"converted {root}")


if __name__ == "__main__":
    main(sys.argv)
