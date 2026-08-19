#!/usr/bin/env python3
"""Extract CV styling from a reference PDF into a JSON config (scripts/cv_style.json).

The generated PDFs reuse this template so they look like the resume the user
provided during ground-truth onboarding. Detection targets the classes of layout
used by the current template (single-column, left-aligned body, tabbed dates,
bullet list, centered name); anything it cannot detect falls back to known-good
defaults so rendering always succeeds.

Usage:
    python cv_style.py /path/to/Reference_CV.pdf [--out scripts/cv_style.json]
"""
import argparse
import json
import os
import re
import statistics

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTChar, LTTextContainer, LTTextLine, LTTextLineHorizontal

MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?|Conferred \S+ \d{4}|\d{4}"
DATE_RE = re.compile(r"\b(?:\d{1,2}[ /-]\d{1,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?[ /-]\d{2,4}|Conferred \S+ \d{4})\b")
BULLET_GLYPHS = ("\u2022", "\uf0b7", "\uf04a", "\u2219")

DEFAULTS = {
    "page_size": "LETTER",
    "font_family": "Carlito",
    "colors": {"NAVY": "#1f3864", "GRAY": "#595959", "BODY": "#222222"},
    "sizes": {"name": 17, "section": 11, "body": 10, "role": 10, "tech": 9,
              "bullet": 10, "skill": 9.5, "edu_deg": 10, "edu_school": 9.5,
              "contact": 9},
    "leading": {"body": 12.2, "section": 13, "role": 11.5, "tech": 11.5,
                "bullet": 12.2, "skill": 13.1, "contact": 12.2, "name": 19},
    "margins": {"left": 45, "right": 45, "top": 45, "bottom": 45},
    "indents": {"bullet_x": 49.1, "bullet_text_x": 58.1},
    "date_tab_x": 297.1,
    "inline_dates": [],
    "source_pdf": None,
}


def _hex(color):
    if not color:
        return "#000000"
    vals = list(color)
    if len(vals) >= 3:
        r, g, b = int(vals[0] * 255 + 0.5), int(vals[1] * 255 + 0.5), int(vals[2] * 255 + 0.5)
        return "#%02x%02x%02x" % (r, g, b)
    return "#000000"


def _collect(path):
    """Return (page_w, page_h, chars, lines)."""
    chars, lines = [], []
    page_w = page_h = 0
    for page in extract_pages(path):
        if not page_w:
            page_w = float(page.width)
            page_h = float(page.height)
        for obj in page:
            if not isinstance(obj, LTTextContainer):
                continue
            for line in obj:
                if not isinstance(line, LTTextLineHorizontal):
                    continue
                text = line.get_text()
                if not text.strip():
                    continue
                cs = [c for c in line if isinstance(c, LTChar)]
                if not cs:
                    continue
                lines.append((line, text))
                chars.extend(
                    (c.get_text(), c.fontname, c.size, _hex(c.graphicstate.ncolor), c.x0, c.y0, c.x1, c.y1)
                    for c in cs)
    return page_w, page_h, chars, lines


def _font_family(fontname):
    base = fontname.split("+")[-1]
    return re.sub(r"-(Regular|BoldItalic|Bold|Italic)$", "", base)


def _tuple(c):
    return (c.get_text(), c.fontname, c.size, _hex(c.graphicstate.ncolor), c.x0, c.y0, c.x1, c.y1)


def detect(path):
    pw, ph, chars, lines = _collect(path)
    conf = json.loads(json.dumps(DEFAULTS))
    conf["source_pdf"] = path
    conf["page_size"] = "LETTER" if (abs(pw - 612) < 5 and abs(ph - 792) < 5) else "A4"

    x0 = lambda c: c[4]
    size = lambda c: c[2]
    color = lambda c: c[3]

    # ---- bullet geometry + body size (anchored on bullet glyphs) ----
    bullet_lines = []
    for line, t in lines:
        s = t.lstrip()
        if s[:1] in BULLET_GLYPHS:
            glyph_x = None
            for c in line:
                if isinstance(c, LTChar) and c.get_text() in BULLET_GLYPHS:
                    glyph_x = c.x0
                    break
            text_x = None
            for c in line:
                if isinstance(c, LTChar) and c.x0 > 60 and c.get_text() not in BULLET_GLYPHS:
                    text_x = c.x0
                    break
            bullet_lines.append((glyph_x, text_x, [_tuple(c) for c in line if isinstance(c, LTChar)]))
    if bullet_lines:
        gxs = [g for g, _, _ in bullet_lines if g]
        txs = [t for _, t, _ in bullet_lines if t]
        left = min(x0(c) for c in chars if c[4] > 30)
        body_cands = [size(c) for _, _, cs in bullet_lines for c in cs
                      if c[0] not in BULLET_GLYPHS]
        body_size = statistics.mode(body_cands) if body_cands else None
        conf["sizes"]["body"] = body_size or DEFAULTS["sizes"]["body"]
        conf["indents"] = {
            "bullet_x": round(statistics.median(gxs), 1),
            "bullet_text_x": round(statistics.median(txs), 1),
            "bullet_indent": round(statistics.median(gxs) - left, 1),
            "text_indent": round(statistics.median(txs) - left, 1),
        }

    # ---- section & name sizes ----
    caps_sizes = []
    for line, t in lines:
        ts = t.strip()
        if 3 < len(ts) < 45 and ts.isupper():
            caps_sizes.extend(c.size for c in line if isinstance(c, LTChar))
    if caps_sizes:
        conf["sizes"]["section"] = statistics.mode(caps_sizes)
    name_size = max(size(c) for c in chars)
    conf["sizes"]["name"] = name_size

    # ---- colors ----
    name_chars = [c for c in chars if size(c) == name_size]
    if name_chars:
        conf["colors"]["NAVY"] = statistics.mode(color(c) for c in name_chars)
    section_chars = [c for _, t in lines if t.strip().isupper() and 3 < len(t.strip()) < 45
                     for c in line if isinstance(c, LTChar) and c.size == conf["sizes"]["section"]]
    if section_chars:
        conf["colors"]["NAVY"] = statistics.mode(color(c) for c in section_chars)
    body_size = conf["sizes"]["body"]
    body_chars = [c for c in chars if abs(size(c) - body_size) < 0.2]
    if body_chars:
        conf["colors"]["BODY"] = statistics.mode(color(c) for c in body_chars)
    other = [color(c) for c in chars if c[3] not in (conf["colors"]["BODY"], conf["colors"]["NAVY"])]
    if other:
        conf["colors"]["GRAY"] = statistics.mode(other)

    # ---- fonts ----
    fams = [_font_family(c[1]) for c in chars]
    conf["font_family"] = statistics.mode(fams)

    # ---- margins (exclude the centered name line only) ----
    max_y1 = max(c[7] for c in chars)
    name_line_id = None
    for c in chars:
        if abs(c[7] - max_y1) < 3:
            name_line_id = c[7]
    def _is_name(c):
        return abs(c[7] - max_y1) < 3
    bodyx = [x0(c) for c in chars if x0(c) > 30 and not _is_name(c)]
    maxx = [c[6] for c in chars if not _is_name(c)]
    bodyy = [c[5] for c in chars if not _is_name(c)]
    maxy = [c[7] for c in chars if not _is_name(c)]
    conf["margins"] = {
        "left": round(min(bodyx), 1),
        "right": round(pw - max(maxx), 1),
        "top": round(ph - max(maxy), 1),
        "bottom": round(min(bodyy), 1),
    }
    left = conf["margins"]["left"]

    # ---- date tab: first date token NOT inside parentheses, grouped by column ----
    def _first_date_x(line, t):
        m = DATE_RE.search(t)
        if not m:
            return None, None
        dstart = t.find(m.group(0))
        # paren dates (role lines) are not tab anchors; skip phone/email lines
        before = t[:dstart]
        if "(" in before or ")" in before:
            return None, None
        if before.strip().startswith("+") or "@" in before:
            return None, None
        cur = ""
        for c in line:
            if isinstance(c, LTChar):
                cur += c.get_text()
                if len(cur) >= dstart + 1:
                    return c.x0, before
        return None, None

    cols = []
    inline_words = []
    for line, t in lines:
        dx, before = _first_date_x(line, t)
        if dx is None:
            continue
        if dx > 200:
            cols.append(round(dx))
        else:
            first_word = before.split()[0] if before.split() else None
            if (first_word and first_word not in inline_words
                    and len(before) < 60):
                inline_words.append(first_word)
    if cols:
        from collections import Counter
        cnt = Counter(cols)
        tab = cnt.most_common(1)[0][0]
        if cnt[tab] >= 2:
            conf["date_tab_x"] = tab
    # anything south of the tab column is an inline date on a company line
    if conf.get("date_tab_x"):
        tab = conf["date_tab_x"]
        for line, t in lines:
            dx, before = _first_date_x(line, t)
            if dx is not None and dx <= tab - 40:
                first_word = before.split()[0] if before.split() else None
                if first_word and len(before) < 60 and first_word not in inline_words:
                    inline_words.append(first_word)
    conf["inline_dates"] = sorted(inline_words)

    # ---- scale leading proportionally to body size (template tuned at 10pt -> 12.2) ----
    scale = body_size / 10.0
    for k in ("body", "section", "role", "tech", "bullet", "skill", "contact", "name"):
        conf["leading"][k] = round(conf["leading"][k] * scale, 2)

    return conf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source_pdf")
    ap.add_argument("--out", default=os.path.join(SCRIPT_DIR, "cv_style.json"))
    args = ap.parse_args()
    conf = detect(args.source_pdf)
    with open(args.out, "w") as f:
        json.dump(conf, f, indent=2)
    print("wrote:", args.out)
    print(json.dumps(conf, indent=2))


if __name__ == "__main__":
    main()