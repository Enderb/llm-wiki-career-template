#!/usr/bin/env python3
"""Render a compiled CV markdown (20_Wiki/Career/CV_*.md) into a styled PDF.

Styling comes from scripts/cv_style.json, which cv_style.py extracts from the
reference resume PDF added during ground-truth onboarding. Only the CV body is
rendered -- Match Summary / Application Notes / SOURCES are working documents
and are excluded.

Usage:
    python cv_pdf.py 20_Wiki/Career/CV_Maxon_Full-Stack-Developer.md
    python cv_pdf.py 20_Wiki/Career/CV_Universal-Generalist.md --out 20_Wiki/Assets/Ender_Barillas_CV_Universal_2026.pdf
    python cv_pdf.py <md> --style <json>   # override style config
"""
import argparse
import json
import os
import re
import sys

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame,
                                Paragraph, Spacer, Table, TableStyle)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(SCRIPT_DIR, "fonts")
DEFAULT_STYLE = os.path.join(SCRIPT_DIR, "cv_style.json")

VOID = {
    "page_size": "LETTER",
    "font_family": "Carlito",
    "colors": {"NAVY": "#1f3864", "GRAY": "#595959", "BODY": "#222222"},
    "sizes": {"name": 17, "section": 11, "body": 10, "role": 10, "tech": 9,
              "bullet": 10, "skill": 9.5, "edu_deg": 10, "edu_school": 9.5,
              "contact": 9},
    "leading": {"body": 12.2, "section": 13, "role": 11.5, "tech": 11.5,
                "bullet": 12.2, "skill": 13.1, "contact": 12.2, "name": 19},
    "margins": {"left": 45, "right": 45, "top": 45, "bottom": 45},
    "indents": {"bullet_x": 49.1, "bullet_text_x": 58.1,
                "bullet_indent": 4.1, "text_indent": 13.1},
    "date_tab_x": 297.1,
    "inline_dates": [],
    "source_pdf": None,
}

SEC_TITLES = {
    "SUMMARY": "Summary",
    "TECHNICAL SKILLS": "Technical Skills",
    "PROFESSIONAL EXPERIENCE": "Professional Experience",
    "RESEARCH & AI EXPERIENCE": "Research & AI Experience",
    "ADDITIONAL EXPERIENCE": "Additional Experience",
    "EDUCATION": "Education",
    "AWARDS & SELECTED PROJECTS": "Awards & Selected Projects",
}


def load_style(path):
    conf = json.loads(json.dumps(VOID))
    if path and os.path.exists(path):
        with open(path) as f:
            loaded = json.load(f)
        conf.update(loaded)
        conf.setdefault("colors", {}).update(VOID["colors"])
        for k in ("sizes", "leading", "margins", "indents"):
            conf.setdefault(k, {}).update(VOID[k])
    return conf


def register_fonts(family):
    variants = {
        "Regular": "Carlito-Regular.ttf",
        "Bold": "Carlito-Bold.ttf",
        "Italic": "Carlito-Italic.ttf",
        "BoldItalic": "Carlito-BoldItalic.ttf",
    }
    names = {}
    for variant, fname in variants.items():
        path = os.path.join(FONT_DIR, fname)
        if not os.path.exists(path):
            raise SystemExit("missing font: %s (run scripts/setup.sh)" % path)
        tag = "%s-%s" % (family, variant) if variant != "Regular" else family
        pdfmetrics.registerFont(TTFont(tag, path))
        names[variant.lower()] = tag
    registerFontFamily(family, normal=names["regular"], bold=names["bold"],
                       italic=names["italic"], boldItalic=names["bolditalic"])


class Render:
    def __init__(self, out, title, conf):
        self.conf = conf
        self.c = conf["colors"]
        self.sz = conf["sizes"]
        self.ld = conf["leading"]
        self.family = conf["font_family"]
        page = A4 if conf["page_size"].upper() == "A4" else letter
        pw, ph = page
        m = conf["margins"]
        self.left = float(m["left"])
        self.W = pw - m["left"] - m["right"]
        self.TOP = min(float(m["top"]), 45)
        self.TAB = conf.get("date_tab_x") or None
        self.inline_dates = conf.get("inline_dates") or []

        self.out = out
        self.doc = BaseDocTemplate(out, pagesize=page, title=title,
                                   author="Ender Jose Barillas Rodriguez")
        frame = Frame(self.left, m["bottom"], self.W, ph - self.TOP - m["bottom"],
                      id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.doc.addPageTemplates([PageTemplate(id="p", frames=[frame])])
        self.story = []
        self.mode = "pre"

        def ps(size, lead, **kw):
            d = dict(fontName=self.family, fontSize=size, leading=lead,
                     textColor=self.c["BODY"], spaceAfter=0, spaceBefore=0,
                     leftIndent=0, bulletIndent=0)
            d.update(kw)
            return ParagraphStyle("s", **d)

        bi = conf["indents"].get("bullet_indent", 4.1)
        ti = conf["indents"].get("text_indent", 13.1)
        self.s_name = ps(self.sz["name"], self.ld["name"], alignment=TA_CENTER, textColor=self.c["NAVY"])
        self.s_contact = ps(self.sz["contact"], self.ld["contact"], alignment=TA_CENTER, textColor=self.c["GRAY"])
        self.s_contact_navy = ps(self.sz["contact"], self.ld["contact"], alignment=TA_CENTER, textColor=self.c["NAVY"])
        self.s_section = ps(self.sz["section"], self.ld["section"], spaceBefore=10, spaceAfter=2.5, textColor=self.c["NAVY"])
        self.s_skill = ps(self.sz["skill"], self.ld["skill"])
        self.s_company = ps(self.sz["body"] + 0.5, self.ld["body"] + 1, spaceBefore=6.5, textColor=self.c["BODY"], keepWithNext=True)
        self.s_role = ps(self.sz["role"], self.ld["role"], spaceBefore=2, textColor=self.c["BODY"], keepWithNext=True)
        self.s_techL = ps(self.sz["tech"], self.ld["tech"], textColor=self.c["GRAY"], keepWithNext=True)
        self.s_bullet = ps(self.sz["bullet"], self.ld["bullet"], leftIndent=ti, bulletIndent=bi, spaceBefore=2, textColor=self.c["BODY"])
        self.s_edudeg = ps(self.sz["edu_deg"], self.ld["body"], spaceBefore=2.8, textColor=self.c["BODY"])
        self.s_edusch = ps(self.sz["edu_school"], self.ld["body"], textColor=self.c["GRAY"])

    # ------------------------------------------------------------------ flowables
    def _rule(self):
        t = Table([[""]], colWidths=[self.W])
        t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 1, colors.HexColor(self.c["NAVY"])),
                               ("TOPPADDING", (0, 0), (-1, -1), 0),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        self.story.append(t)
        self.story.append(Spacer(1, 4.5))

    def section(self, raw):
        self.story.append(Paragraph(
            "<b>%s</b>" % SEC_TITLES.get(raw.strip().upper(), raw.strip().title()).upper(),
            self.s_section))
        self._rule()
        self.mode = "section/" + raw.strip().upper()

    def name(self, title):
        self.story.append(Paragraph("<b>%s</b>" % self.inline(title), self.s_name))
        self.story.append(Spacer(1, 2))
        self.mode = "statics"
        self.pending_contact = 2

    def company(self, header):
        body = header[len("### "):]
        name, _, rest = body.partition(" \u00b7 ")
        date = rest.strip().strip("*").strip()
        tab = bool(self.TAB) and not any(w in name for w in self.inline_dates)
        gap = self.spaces_to(self.TAB, name, "Carlito-Bold", self.sz["body"] + 0.5) if tab else "&#160;&#160;"
        self.story.append(Paragraph(
            '<font name="%s" color="%s"><b>%s</b></font>'
            '<font name="%s" color="%s">%s%s</font>'
            % (self.family, self.c["BODY"], name, self.family, self.c["GRAY"], gap, date),
            self.s_company))

    def role(self, line):
        m = re.match(r"\*\*([^*]+?)\*\*", line)
        if not m:
            return
        role = m.group(1)
        dm = re.search(r"\*\(([^)]+)\)\*", line)
        if dm:
            role = "%s (%s)" % (role, dm.group(1))
        self.story.append(Paragraph(self.inline(role), self.s_role))

    def tech(self, line):
        rest = line[len("Technologies:"):].strip()
        self.story.append(Paragraph(
            '<font name="%s" color="%s">Technologies: </font>'
            '<font name="%s" color="%s">%s</font>'
            % (self.family, self.c["GRAY"], self.family, self.c["GRAY"], self.inline(rest)),
            self.s_techL))

    def bullet(self, text):
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        self.story.append(Paragraph(self.inline(text), self.s_bullet, bulletText="\u2022"))

    def skill(self, line):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            return
        cat = cells[0].strip("*")
        if cat.lower() in ("category", "---"):
            return
        val = " | ".join(cells[1:])
        self.story.append(Paragraph(
            '<font name="%s" color="%s"><b>%s</b></font>  '
            '<font name="%s" color="%s">%s</font>'
            % (self.family, self.c["NAVY"], self.inline(cat), self.family, self.c["BODY"], self.inline(val)),
            self.s_skill))

    def edu(self, line):
        left, _, right = line.partition(" \u2014 ")
        if not right:
            left, _, right = line.partition(" - ")
        dm = re.search(r"\*([^*]+?)\*, (.+)", right)
        if not dm:
            return
        date, school = dm.group(1), dm.group(2)
        plain = re.sub(r"\*\*|\*", "", left)
        self.story.append(Paragraph(
            '<font name="%s" color="%s"><b>%s</b></font>'
            '<font name="%s" color="%s">%s%s</font>'
            % (self.family, self.c["BODY"], self.inline(left),
               self.family, self.c["GRAY"],
               self.spaces_to(self.TAB, plain, "Carlito-Bold", self.sz["edu_deg"]), self.inline(date)),
            self.s_edudeg))
        self.story.append(Paragraph(self.inline(school), self.s_edusch))

    # ------------------------------------------------------------------ helpers
    def spaces_to(self, target_x, text, font, size):
        if not target_x:
            return "&#160;&#160;"
        end = self.left + pdfmetrics.stringWidth(text, font, size)
        need = target_x - end
        sw = pdfmetrics.stringWidth(" ", font, size)
        n = int(need / sw) if need > 0 else 0
        return "&#160;" * max(n, 2)

    def inline(self, md):
        xml = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        xml = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", xml)
        xml = re.sub(r"\[\[([^\]]+)\]\]", r"\1", xml)
        xml = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", xml)
        xml = re.sub(r"\*([^*]+?)\*", r"<i>\1</i>", xml)
        return xml

    # ------------------------------------------------------------------ parsing
    def line(self, text):
        raw = text.strip()
        if not raw:
            return
        if self.mode == "statics":
            after = re.sub(r"\[([^\]\|]+)\|[^]]*\]", r"\1", raw)
            after = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", after)
            if "linkedin" in after:
                self.story.append(Paragraph(self.inline(after), self.s_contact_navy))
            else:
                self.story.append(Paragraph(self.inline(after), self.s_contact))
            self.pending_contact -= 1
            if self.pending_contact <= 0:
                self.mode = "body"
            return
        if raw.startswith("## APPLICATION NOTES") or raw.startswith("## SOURCES"):
            self.mode = "done"
            return
        if raw.startswith("## "):
            self.section(raw[3:])
            return
        if raw.startswith("### "):
            self.company(raw)
            return
        if self.mode.startswith("section/EDUCATION"):
            self.edu(raw)
            return
        if self.mode.startswith("section/AWARDS"):
            if raw.startswith("- "):
                self.bullet(raw[2:])
            return
        if self.mode.startswith("section/TECHNICAL SKILLS"):
            if raw.startswith("|"):
                self.skill(raw)
            return
        if self.mode.startswith("section/") and "EXPERIENCE" in self.mode:
            if raw.startswith("- "):
                self.bullet(raw[2:])
            elif raw.startswith("Technologies:"):
                self.tech(raw)
            elif raw.startswith("**"):
                self.role(raw)
            return
        if self.mode.startswith("section/SUMMARY"):
            if raw:
                self.story.append(Paragraph(self.inline(raw), self.s_skill))
            return

    def build(self, md_path):
        started = False
        for line in open(md_path, encoding="utf-8"):
            if not started:
                if line.strip().startswith("# ENDER"):
                    started = True
                    self.name(line.strip()[2:].strip())
                continue
            if self.mode == "done":
                break
            self.line(line)
        self.doc.build(self.story)


def default_out(md_path, prefix="Ender_Barillas"):
    base = os.path.basename(md_path).replace(".md", "")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(md_path))), "Assets",
                        prefix + "_" + base + ".pdf")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("markdown")
    ap.add_argument("--out")
    ap.add_argument("--prefix", default="Ender_Barillas",
                    help="output filename prefix (default: Ender_Barillas)")
    ap.add_argument("--style", default=DEFAULT_STYLE)
    args = ap.parse_args()

    conf = load_style(args.style)
    register_fonts(conf["font_family"])
    out = args.out or default_out(args.markdown, args.prefix)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    label = os.path.basename(args.markdown)[3:-3]
    r = Render(out, "Ender Jose Barillas Rodriguez - CV (%s)" % label, conf)
    r.build(args.markdown)
    print("wrote:", out)


if __name__ == "__main__":
    main()