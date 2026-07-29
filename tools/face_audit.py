"""Assert every @font-face's declared weight matches its file's usWeightClass.

Reads the declaration rather than pattern-matching filenames, so it catches the
whole class: ExtraLight in the 400 slot, a Light 300, or a correct file simply
declared at the wrong weight. Nothing here is specific to the ExtraLight bug.

    python face_audit.py <repo-root> [...]

Exit 1 if any declared face disagrees with its file.

Two things this gets wrong if written naively, both found by running it:

* A relative src does NOT always resolve against the stylesheet's own directory.
  An HTML template rendered by WeasyPrint resolves against the base_url it is
  handed, so `url('fonts/x.woff2')` inside app/templates/ points at assets/.
  Resolving as css.parent/ref reported 8 false mismatches on a verified-clean
  repo. So: try css.parent first, then fall back to a basename lookup across
  the repo, and only report MISSING when the basename exists nowhere.
* Vendored dependency trees carry hundreds of unrelated @font-face rules
  (renv/library, site-packages, node_modules). Scanning them returned 931
  "mismatches" from R packages. They must be excluded by path, not filtered
  after the fact.
"""

import re
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

# Build output, caches, and vendored dependency trees. Anything whose fonts are
# not ours to fix and whose declarations are not ours to trust.
SKIP = {
    "_freeze",
    ".quarto",
    "node_modules",
    "dist",
    "build",
    "_site",
    ".open-next",
    "out",
    ".next",
    "worktrees",
    ".git",
    "renv",
    "site-packages",
    "vendor",
    ".venv",
    "venv",
    "packrat",
    "__pycache__",
    ".cache",
    "htmlwidgets",
}
FACE = re.compile(r"@font-face\s*\{(.*?)\}", re.S)
WEIGHT = re.compile(r"font-weight\s*:\s*(\d{3})")
FAMILY = re.compile(r"font-family\s*:\s*['\"]?([^;'\"]+)")
URL = re.compile(r"url\(\s*['\"]?([^)'\"]+?)['\"]?\s*\)")


def sources(root):
    for p in root.rglob("*"):
        if SKIP & set(p.parts):
            continue
        if p.is_file() and p.suffix.lower() in {".css", ".scss", ".html"}:
            yield p


def index_fonts(root):
    """basename -> [paths]. The fallback when a relative src does not resolve."""
    idx = {}
    for p in root.rglob("*"):
        if SKIP & set(p.parts):
            continue
        if p.is_file() and p.suffix.lower() in {".woff2", ".woff", ".ttf", ".otf"}:
            idx.setdefault(p.name, []).append(p)
    return idx


def audit(root):
    root = Path(root).resolve()
    fonts = index_fonts(root)
    checked, findings = 0, []

    for css in sources(root):
        try:
            text = css.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for block in FACE.findall(text):
            w, fam, url = WEIGHT.search(block), FAMILY.search(block), URL.search(block)
            if not (w and url):
                continue
            declared = int(w.group(1))
            family = fam.group(1).strip() if fam else "?"
            ref = url.group(1).split("?")[0].split("#")[0]
            if ref.startswith(("http://", "https://", "data:", "//")):
                continue

            path = css.parent / ref
            if not path.is_file():
                candidates = fonts.get(Path(ref).name, [])
                if len(candidates) == 1:
                    path = candidates[0]
                elif candidates:
                    # Ambiguous basename: prefer one under an assets/ dir.
                    preferred = [c for c in candidates if "assets" in c.parts]
                    path = (preferred or candidates)[0]
                else:
                    findings.append((css, family, declared, ref, "file not found in repo"))
                    continue
            try:
                actual = TTFont(path, fontNumber=0)["OS/2"].usWeightClass
            except Exception as exc:
                findings.append((css, family, declared, ref, f"unreadable ({exc})"))
                continue
            checked += 1
            if actual != declared:
                findings.append((css, family, declared, ref, f"file is {actual}"))
    return checked, findings


def main(targets):
    ok = True
    for t in targets:
        checked, findings = audit(t)
        name = Path(t).name
        if not checked and not findings:
            print(f"  {name:<44} no local @font-face declarations")
            continue
        print(
            f"  {name:<44} {checked:>3} faces   "
            f"{'OK' if not findings else str(len(findings)) + ' PROBLEM'}"
        )
        for css, family, declared, ref, why in findings:
            ok = False
            print(f"       {family} declared {declared} -> {ref}: {why}")
            print(f"         {css.relative_to(Path(t).resolve())}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
