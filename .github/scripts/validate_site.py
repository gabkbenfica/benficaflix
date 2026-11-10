"""Check local HTML and CSS file references in the Pages artifact."""

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(
            (self.getpos()[0], value)
            for name, value in attrs
            if name in {"href", "src", "poster"} and value
        )


def check_reference(root, source, value, files):
    if value.startswith("//"):
        return None
    url = urlsplit(value)
    if url.scheme or not url.path:
        return None
    if url.path.startswith("/"):
        return "use a relative path for GitHub Pages"

    target = (source.parent / unquote(url.path)).resolve()
    if not target.is_relative_to(root):
        return "path points outside the site"
    if target.is_dir():
        target /= "index.html"
    if target.relative_to(root).as_posix() not in files:
        return "file missing or capitalization differs"
    return None


def main(root):
    if not (root / "index.html").is_file():
        print("Missing index.html", file=sys.stderr)
        return 1

    paths = sorted(path for path in root.rglob("*") if path.is_file())
    files = {path.relative_to(root).as_posix() for path in paths}
    errors = []
    count = 0
    for source in paths:
        if source.suffix == ".html":
            parser = References()
            parser.feed(source.read_text(encoding="utf-8-sig"))
            parser.close()
            links = parser.links
        elif source.suffix == ".css":
            css = source.read_text(encoding="utf-8-sig")
            css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
            urls = re.findall(r"url\(([^)]*)\)", css, re.I)
            links = [(None, value.strip().strip("\"'")) for value in urls]
        else:
            continue

        for line, value in links:
            count += 1
            if error := check_reference(root, source, value, files):
                location = source.relative_to(root).as_posix()
                if line:
                    location += f":{line}"
                errors.append(f"{location}: {value}: {error}")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Checked {count} HTML/CSS references.")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve()))
