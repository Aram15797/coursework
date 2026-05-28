# -*- coding: utf-8 -*-
"""Generate the coursework PDF, mirroring the original ``Portal for Doctors``
layout (Sylfaen 12pt body, 14pt headings, letter page size, 1-inch margins,
top-right page numbers, table of contents with dotted leaders).

The generator does not depend on the original PDF — it produces a new
PDF from scratch using ReportLab and the embedded Sylfaen font.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import List, Tuple

# Add the src/ dir to the path so we can import content.py when running directly.
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.colors import black

import content as C


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PAGE_W, PAGE_H = LETTER  # 612 x 792

LEFT_MARGIN = 72.0     # 1 inch
RIGHT_MARGIN = 72.0
TOP_MARGIN = 72.0
BOTTOM_MARGIN = 72.0   # leaves room for ~33pt of bottom space

USABLE_W = PAGE_W - LEFT_MARGIN - RIGHT_MARGIN  # 468

# Text sizes
BODY_SIZE = 12
SMALL_SIZE = 11
HEADING_SIZE = 14
SUB_SIZE = 12
TITLE_SIZE = 24
TITLE_HEAD_SIZE = 14
TITLE_BIG_SUB = 14
CODE_SIZE = 10
PAGE_NUM_SIZE = 12

# Line spacing (leading) - 1.15 line spacing typical for Word docs
LINE_HEIGHT = 14.5
HEADING_LEADING = 17.0
CODE_LEADING = 12.0
PARA_SPACE = 6.0  # extra space between paragraphs

REGULAR = "Sylfaen"
BOLD = "Sylfaen-Bold"  # registered as regular too (faux-bold via stroke)
MONO = "CourierNew"

FONT_DIR = os.path.join(os.path.dirname(HERE), "fonts")


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont(REGULAR, os.path.join(FONT_DIR, "sylfaen.ttf")))
    # Faux bold: use same TTF; reportlab will simulate bold via stroke when we
    # set canvas.setLineWidth and use textRenderMode 2 (fill+stroke).  We
    # keep the "bold" alias pointing to the same TTF so width metrics match.
    pdfmetrics.registerFont(TTFont(BOLD, os.path.join(FONT_DIR, "sylfaen.ttf")))
    # Courier New for code – fall back to ReportLab's built-in Courier if not
    # available as a TTF.  Courier is one of the 14 PDF base fonts and is
    # always available.
    # (We just reuse "Courier" base font.)


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------
@dataclass
class LayoutState:
    page: int = 1
    y: float = PAGE_H - TOP_MARGIN  # cursor (top of next line baseline)
    toc_entries: List[Tuple[str, int, int]] = field(default_factory=list)
    # (label, level, page_number)
    # level: 0 = main heading, 1 = sub heading


def _string_width(text: str, font: str, size: float) -> float:
    return pdfmetrics.stringWidth(text, font, size)


def _wrap_text(text: str, font: str, size: float, max_w: float) -> List[str]:
    """Word-wrap *text* to lines no wider than *max_w*."""
    words = text.split(" ")
    lines: List[str] = []
    cur = ""
    for w in words:
        # handle embedded newlines inside a word fragment (paragraphs do not
        # contain newlines, but be safe)
        if "\n" in w:
            parts = w.split("\n")
            for j, part in enumerate(parts):
                if j == 0:
                    candidate = (cur + (" " if cur else "") + part).strip()
                    if _string_width(candidate, font, size) <= max_w:
                        cur = candidate
                    else:
                        if cur:
                            lines.append(cur)
                        cur = part
                else:
                    lines.append(cur)
                    cur = part
            continue

        candidate = (cur + (" " if cur else "") + w).strip()
        if _string_width(candidate, font, size) <= max_w:
            cur = candidate
        else:
            if cur:
                lines.append(cur)
            # if word itself is too long, hard-break it
            if _string_width(w, font, size) > max_w:
                chunk = ""
                for ch in w:
                    if _string_width(chunk + ch, font, size) > max_w and chunk:
                        lines.append(chunk)
                        chunk = ch
                    else:
                        chunk += ch
                cur = chunk
            else:
                cur = w
    if cur:
        lines.append(cur)
    return lines


def _draw_page_number(c: canvas.Canvas, page_num: int, show: bool = True) -> None:
    """Draw the page number in the top-right corner (skip page 1 & 2)."""
    if not show:
        return
    c.setFont(REGULAR, PAGE_NUM_SIZE)
    text = str(page_num)
    w = _string_width(text, REGULAR, PAGE_NUM_SIZE)
    c.drawString(PAGE_W - RIGHT_MARGIN - w + 18, PAGE_H - 50, text)


def _new_page(c: canvas.Canvas, st: LayoutState, show_number: bool = True) -> None:
    c.showPage()
    st.page += 1
    st.y = PAGE_H - TOP_MARGIN
    _draw_page_number(c, st.page, show=show_number)


def _ensure_space(c: canvas.Canvas, st: LayoutState, needed: float) -> None:
    """Start a new page if *needed* points won't fit on the current page."""
    if st.y - needed < BOTTOM_MARGIN:
        _new_page(c, st)


def _draw_justified_line(
    c: canvas.Canvas,
    line: str,
    x: float,
    y: float,
    max_w: float,
    font: str,
    size: float,
) -> None:
    """Draw *line* justified to *max_w* by stretching spaces."""
    words = line.split(" ")
    if len(words) <= 1:
        c.setFont(font, size)
        c.drawString(x, y, line)
        return
    text_width = sum(_string_width(w, font, size) for w in words)
    space_count = len(words) - 1
    extra = max_w - text_width
    space_w = extra / space_count if space_count else 0
    c.setFont(font, size)
    cur_x = x
    for i, w in enumerate(words):
        c.drawString(cur_x, y, w)
        if i < len(words) - 1:
            cur_x += _string_width(w, font, size) + space_w


# ---------------------------------------------------------------------------
# Block writers
# ---------------------------------------------------------------------------
def write_paragraph(
    c: canvas.Canvas,
    st: LayoutState,
    text: str,
    *,
    font: str = REGULAR,
    size: float = BODY_SIZE,
    leading: float = LINE_HEIGHT,
    indent: float = 0.0,
    justify: bool = True,
    align_center: bool = False,
    space_after: float = PARA_SPACE,
) -> None:
    lines = _wrap_text(text, font, size, USABLE_W - indent)
    for i, line in enumerate(lines):
        _ensure_space(c, st, leading)
        st.y -= leading
        x = LEFT_MARGIN + indent
        if align_center:
            w = _string_width(line, font, size)
            x = (PAGE_W - w) / 2
            c.setFont(font, size)
            c.drawString(x, st.y, line)
        elif justify and i < len(lines) - 1:
            _draw_justified_line(c, line, x, st.y, USABLE_W - indent, font, size)
        else:
            c.setFont(font, size)
            c.drawString(x, st.y, line)
    st.y -= space_after


def _draw_bold_string(
    c: canvas.Canvas,
    x: float,
    y: float,
    text: str,
    font: str,
    size: float,
    stroke_w: float = 0.4,
) -> None:
    """Draw *text* with a faux-bold effect (fill + stroke) using a text object.

    Canvas.drawString does not expose setTextRenderMode directly, but text
    objects returned by Canvas.beginText() do. Render mode 2 = fill + stroke,
    which simulates bold for fonts that have no dedicated bold variant.
    """
    c.setStrokeColor(black)
    c.setFillColor(black)
    c.setLineWidth(stroke_w)
    tobj = c.beginText(x, y)
    tobj.setFont(font, size)
    tobj.setTextRenderMode(2)
    tobj.textOut(text)
    c.drawText(tobj)


def write_heading(
    c: canvas.Canvas,
    st: LayoutState,
    text: str,
    *,
    add_to_toc: bool = True,
) -> None:
    # Headings always start on a roomy area, but never on a fresh page on their
    # own.  Leave at least one line of room before the heading.
    _ensure_space(c, st, HEADING_LEADING * 2)
    # extra space before heading
    st.y -= 8

    lines = _wrap_text(text, REGULAR, HEADING_SIZE, USABLE_W)
    if add_to_toc:
        # record this heading for the TOC
        st.toc_entries.append((text, 0, st.page))
    for line in lines:
        _ensure_space(c, st, HEADING_LEADING)
        st.y -= HEADING_LEADING
        # Sylfaen has no real bold variant, so emulate it with a slight stroke
        # on top of the regular fill.
        _draw_bold_string(c, LEFT_MARGIN, st.y, line, REGULAR, HEADING_SIZE,
                          stroke_w=0.4)
    st.y -= 4


def write_subheading(
    c: canvas.Canvas,
    st: LayoutState,
    text: str,
    *,
    add_to_toc: bool = True,
) -> None:
    _ensure_space(c, st, LINE_HEIGHT * 2)
    st.y -= 4
    lines = _wrap_text(text, REGULAR, SUB_SIZE, USABLE_W)
    if add_to_toc:
        st.toc_entries.append((text, 1, st.page))
    for line in lines:
        _ensure_space(c, st, LINE_HEIGHT)
        st.y -= LINE_HEIGHT
        _draw_bold_string(c, LEFT_MARGIN, st.y, line, REGULAR, SUB_SIZE,
                          stroke_w=0.35)
    st.y -= 2


def write_bullets(
    c: canvas.Canvas,
    st: LayoutState,
    items: List[str],
    *,
    bullet: str = "•",
    indent: float = 16.0,
) -> None:
    bullet_w = _string_width(bullet + "  ", REGULAR, BODY_SIZE)
    for item in items:
        lines = _wrap_text(item, REGULAR, BODY_SIZE, USABLE_W - indent)
        for i, line in enumerate(lines):
            _ensure_space(c, st, LINE_HEIGHT)
            st.y -= LINE_HEIGHT
            c.setFont(REGULAR, BODY_SIZE)
            if i == 0:
                c.drawString(LEFT_MARGIN + indent - bullet_w, st.y, bullet)
            c.drawString(LEFT_MARGIN + indent, st.y, line)
        st.y -= 2
    st.y -= PARA_SPACE


def write_numbered(c: canvas.Canvas, st: LayoutState, items: List[str]) -> None:
    indent = 22.0
    for n, item in enumerate(items, start=1):
        prefix = f"{n}. "
        lines = _wrap_text(item, REGULAR, BODY_SIZE, USABLE_W - indent)
        for i, line in enumerate(lines):
            _ensure_space(c, st, LINE_HEIGHT)
            st.y -= LINE_HEIGHT
            c.setFont(REGULAR, BODY_SIZE)
            if i == 0:
                c.drawString(LEFT_MARGIN, st.y, prefix)
            c.drawString(LEFT_MARGIN + indent, st.y, line)
        st.y -= 2
    st.y -= PARA_SPACE


def write_code(
    c: canvas.Canvas,
    st: LayoutState,
    code: str,
    *,
    size: float = CODE_SIZE,
    leading: float = CODE_LEADING,
) -> None:
    """Write a monospace code block.  Long lines are *not* wrapped (typical
    for code listings) but the canvas font is set to Courier."""
    # Add a little top space
    st.y -= 4
    for raw_line in code.split("\n"):
        _ensure_space(c, st, leading)
        st.y -= leading
        c.setFont("Courier", size)
        c.drawString(LEFT_MARGIN + 6, st.y, raw_line)
    st.y -= PARA_SPACE


# ---------------------------------------------------------------------------
# Title page (page 1)
# ---------------------------------------------------------------------------
def draw_title_page(c: canvas.Canvas, st: LayoutState) -> None:
    """Render the first page (cover sheet)."""
    def centered(text: str, y: float, size: float = BODY_SIZE, font: str = REGULAR):
        w = _string_width(text, font, size)
        c.setFont(font, size)
        c.drawString((PAGE_W - w) / 2, y, text)

    def centered_wrapped(text: str, y: float, size: float, font: str = REGULAR,
                         line_gap: float = 4.0) -> float:
        """Centered text that wraps to multiple lines.  Returns the new y."""
        lines = _wrap_text(text, font, size, USABLE_W)
        cy = y
        for line in lines:
            w = _string_width(line, font, size)
            c.setFont(font, size)
            c.drawString((PAGE_W - w) / 2, cy, line)
            cy -= size + line_gap
        return cy

    # ---- top: ministry / university / branch
    y = PAGE_H - 56
    y = centered_wrapped(
        "ՀԱՅԱՍՏԱՆԻ ՀԱՆՐԱՊԵՏՈՒԹՅԱՆ ԿՐԹՈՒԹՅԱՆ, ԳԻՏՈՒԹՅԱՆ, "
        "ՄՇԱԿՈՒՅԹԻ ԵՎ ՍՊՈՐՏԻ ՆԱԽԱՐԱՐՈՒԹՅՈՒՆ",
        y, BODY_SIZE,
    )
    y -= 4
    y = centered_wrapped(
        "ՀԱՅԱՍՏԱՆԻ ԱԶԳԱՅԻՆ ՊՈԼԻՏԵԽՆԻԿԱԿԱՆ ՀԱՄԱԼՍԱՐԱՆ (ՀԻՄՆԱԴՐԱՄ)",
        y, BODY_SIZE,
    )
    y -= 6
    centered("ՎԱՆԱՁՈՐԻ ՄԱՍՆԱՃՅՈՒՂ", y, BODY_SIZE)
    y -= 30

    # ---- chair / spec / subject (left aligned with label)
    def labeled(label: str, value: str, ly: float) -> float:
        c.setFont(REGULAR, TITLE_HEAD_SIZE)
        c.drawString(LEFT_MARGIN, ly, label)
        c.setFont(REGULAR, TITLE_HEAD_SIZE)
        c.drawString(LEFT_MARGIN + _string_width(label + " ", REGULAR, TITLE_HEAD_SIZE),
                     ly, value)
        return ly - TITLE_HEAD_SIZE - 6

    c.setFont(REGULAR, TITLE_HEAD_SIZE)
    c.drawString(LEFT_MARGIN, y, "Ամբիոն՝")
    y -= TITLE_HEAD_SIZE + 4
    c.setFont(REGULAR, TITLE_HEAD_SIZE)
    c.drawString(LEFT_MARGIN, y, "Մաթեմատիկա և ծրագրային ճարտարագիտություն")
    y -= 22

    c.setFont(REGULAR, TITLE_HEAD_SIZE)
    c.drawString(LEFT_MARGIN, y, "Մասնագիտություն՝   Ծրագրային ճարտարագիտություն")
    y -= 22

    c.setFont(REGULAR, TITLE_HEAD_SIZE)
    c.drawString(LEFT_MARGIN, y, "Առարկա՝")
    y -= TITLE_HEAD_SIZE + 4
    c.setFont(REGULAR, TITLE_HEAD_SIZE)
    c.drawString(LEFT_MARGIN, y, "Տվյալների հենքերի նախագծում")
    y -= 36

    # ---- BIG title (bold)
    title = "ՀԱՇՎԵԲԱՑԱՏՐԱԳԻՐ"
    w = _string_width(title, REGULAR, TITLE_SIZE)
    _draw_bold_string(c, (PAGE_W - w) / 2, y, title, REGULAR, TITLE_SIZE,
                      stroke_w=0.6)
    y -= 28

    sub = "կուրսային աշխատանքի/նախագծի/հետազոտական աշխատանքի"
    w = _string_width(sub, REGULAR, TITLE_BIG_SUB)
    c.setFont(REGULAR, TITLE_BIG_SUB)
    c.drawString((PAGE_W - w) / 2, y, sub)
    y -= 28

    # ---- topic
    c.setFont(REGULAR, TITLE_HEAD_SIZE)
    label = "Թեմա՝ "
    c.drawString(LEFT_MARGIN, y, label)
    # Wrap the long topic so it lines up below the label
    label_w = _string_width(label, REGULAR, TITLE_HEAD_SIZE)
    topic_lines = _wrap_text(C.TOPIC + "։",
                             REGULAR, TITLE_HEAD_SIZE,
                             USABLE_W - label_w)
    c.setFont(REGULAR, TITLE_HEAD_SIZE)
    c.drawString(LEFT_MARGIN + label_w, y, topic_lines[0])
    y -= TITLE_HEAD_SIZE + 4
    for line in topic_lines[1:]:
        c.drawString(LEFT_MARGIN, y, line)
        y -= TITLE_HEAD_SIZE + 4
    y -= 20

    # ---- group + student
    c.setFont(REGULAR, TITLE_HEAD_SIZE)
    c.drawString(LEFT_MARGIN, y, "Ակադեմիական խումբ   " + C.GROUP)
    y -= 26

    c.setFont(REGULAR, TITLE_HEAD_SIZE)
    c.drawString(LEFT_MARGIN, y, "Ուսանող՝")
    y -= 30

    # student signature line + name
    c.setFont(REGULAR, TITLE_HEAD_SIZE)
    c.drawString(LEFT_MARGIN, y, "/  " + C.STUDENT_NAME + "  /")
    # underline label like the original
    y -= 14
    c.setFont(REGULAR, SMALL_SIZE)
    c.drawString(LEFT_MARGIN, y, "(ստորագրություն)")
    c.drawString(LEFT_MARGIN + 200, y, "(ազգանուն, անուն, հայրանուն)")
    y -= 26

    # ---- supervisor
    c.setFont(REGULAR, TITLE_HEAD_SIZE)
    c.drawString(LEFT_MARGIN, y, "Ղեկավար՝")
    y -= 22
    c.setFont(REGULAR, TITLE_HEAD_SIZE)
    c.drawString(LEFT_MARGIN, y, "/  " + C.SUPERVISOR + "  /")
    y -= 14
    c.setFont(REGULAR, SMALL_SIZE)
    c.drawString(LEFT_MARGIN, y, "(ստորագրություն)")
    c.drawString(LEFT_MARGIN + 200, y, "(ազգանուն, անուն, հայրանուն)")
    y -= 26

    c.setFont(REGULAR, TITLE_HEAD_SIZE)
    c.drawString(LEFT_MARGIN, y, "Ամբիոնի վարիչի պ/կ՝")
    y -= 22
    c.setFont(REGULAR, TITLE_HEAD_SIZE)
    c.drawString(LEFT_MARGIN, y, "/  " + C.SUPERVISOR + "  /")
    y -= 14
    c.setFont(REGULAR, SMALL_SIZE)
    c.drawString(LEFT_MARGIN, y, "(ստորագրություն)")
    c.drawString(LEFT_MARGIN + 200, y, "(ազգանուն, անուն, հայրանուն)")

    # ---- bottom: city/year
    c.setFont(REGULAR, BODY_SIZE)
    w = _string_width(C.YEAR, REGULAR, BODY_SIZE)
    c.drawString((PAGE_W - w) / 2, 50, C.YEAR)


# ---------------------------------------------------------------------------
# Assignment / brief (page 2)
# ---------------------------------------------------------------------------
def draw_assignment_page(c: canvas.Canvas, st: LayoutState) -> None:
    """Render page 2 (the «ԱՌԱՋԱԴՐԱՆՔ» brief)."""
    def centered(text: str, y: float, size: float = BODY_SIZE) -> None:
        w = _string_width(text, REGULAR, size)
        c.setFont(REGULAR, size)
        c.drawString((PAGE_W - w) / 2, y, text)

    y = PAGE_H - 60
    centered("ՀԱՅԱՍՏԱՆԻ ԱԶԳԱՅԻՆ ՊՈԼԻՏԵԽՆԻԿԱԿԱՆ ՀԱՄԱԼՍԱՐԱՆ", y, BODY_SIZE)
    y -= 16
    centered("(ՀԻՄՆԱԴՐԱՄ)", y, BODY_SIZE)
    y -= 28
    centered("Մաթեմատիկա և ծրագրային ճարտարագիտություն", y, BODY_SIZE)
    y -= 14
    centered(" ամբիոն", y, BODY_SIZE)
    y -= 12
    centered("(ամբիոնի անվանումը)", y, SMALL_SIZE)
    y -= 22

    centered("Ծրագրային ճարտարագիտություն", y, BODY_SIZE)
    y -= 14
    centered(" մասնագիտություն", y, BODY_SIZE)
    y -= 12
    centered("(մասնագիտության անվանումը)", y, SMALL_SIZE)
    y -= 22

    centered(C.GROUP, y, BODY_SIZE)
    y -= 14
    centered(" ակադեմիական խումբ", y, BODY_SIZE)
    y -= 30

    # heading (bold)
    head = "ԿՈՒՐՍԱՅԻՆ ՆԱԽԱԳԾԻ/ԱՇԽԱՏԱՆՔԻ/ՀԵՏԱԶՈՏԱԿԱՆ ԱՇԽԱՏԱՆՔԻ"
    w = _string_width(head, REGULAR, TITLE_HEAD_SIZE)
    _draw_bold_string(c, (PAGE_W - w) / 2, y, head, REGULAR, TITLE_HEAD_SIZE,
                      stroke_w=0.4)
    y -= 18
    head2 = "ԱՌԱՋԱԴՐԱՆՔ"
    w = _string_width(head2, REGULAR, TITLE_HEAD_SIZE)
    _draw_bold_string(c, (PAGE_W - w) / 2, y, head2, REGULAR, TITLE_HEAD_SIZE,
                      stroke_w=0.4)
    y -= 26

    centered("Տվյալների հենքերի նախագծում", y, BODY_SIZE)
    y -= 12
    centered("(առարկայի անվանումը)", y, SMALL_SIZE)
    y -= 24

    centered(C.STUDENT_NAME, y, BODY_SIZE)
    y -= 12
    centered("(ուսանողի ազգանուն, անուն, հայրանուն)", y, SMALL_SIZE)
    y -= 22

    # numbered task brief
    c.setFont(REGULAR, BODY_SIZE)
    body_w = USABLE_W
    items = [
        ("1. Աշխատանքի թեման  ", C.TOPIC + "։"),
        ("2. Աշխատանքի նախնական տվյալները  ", "Տարբերակ № 14"),
        ("3. Հաշվեբացատրագրի բովանդակությունը՝", ""),
    ]
    for prefix, value in items:
        text = (prefix + value).strip()
        lines = _wrap_text(text, REGULAR, BODY_SIZE, body_w)
        for line in lines:
            c.setFont(REGULAR, BODY_SIZE)
            c.drawString(LEFT_MARGIN, y, line)
            y -= 16
        y -= 4

    # sub-items 3.1 .. 3.5
    for label, text in [
        ("3.1.", "Բովանդակություն"),
        ("3.2.", "Ներածություն"),
        ("3.3.", "Հիմնական մաս (գլուխ, բաժին, ենթաբաժին)"),
        ("3.4.", "Եզրակացություն"),
        ("3.5.", "Օգտագործված գրականության ցանկ"),
    ]:
        c.setFont(REGULAR, BODY_SIZE)
        c.drawString(LEFT_MARGIN + 20, y, label)
        c.drawString(LEFT_MARGIN + 60, y, text)
        y -= 16

    y -= 6
    for label in [
        "4. Գրաֆիկական մասի ծավալ",
        "5. Կատարման ժամանակացույցը",
    ]:
        c.setFont(REGULAR, BODY_SIZE)
        c.drawString(LEFT_MARGIN, y, label)
        y -= 22

    # supervisor signatures (same as title page)
    c.setFont(REGULAR, BODY_SIZE)
    c.drawString(LEFT_MARGIN, y, "6. Աշխատանքի ղեկավար")
    y -= 16
    c.drawString(LEFT_MARGIN + 20, y, "/  " + C.SUPERVISOR + "  /")
    y -= 12
    c.setFont(REGULAR, SMALL_SIZE)
    c.drawString(LEFT_MARGIN + 20, y, "(ստորագրություն)")
    c.drawString(LEFT_MARGIN + 200, y, "(ազգանուն, անուն, հայրանուն)")
    y -= 22

    c.setFont(REGULAR, BODY_SIZE)
    c.drawString(LEFT_MARGIN, y, "7. Ամբիոնի վարիչի պ/կ")
    y -= 16
    c.drawString(LEFT_MARGIN + 20, y, "/  " + C.SUPERVISOR + "  /")
    y -= 12
    c.setFont(REGULAR, SMALL_SIZE)
    c.drawString(LEFT_MARGIN + 20, y, "(ստորագրություն)")
    c.drawString(LEFT_MARGIN + 200, y, "(ազգանուն, անուն, հայրանուն)")
    y -= 22

    c.setFont(REGULAR, BODY_SIZE)
    c.drawString(LEFT_MARGIN, y, "8. Ուսանող")
    y -= 14
    c.setFont(REGULAR, SMALL_SIZE)
    c.drawString(LEFT_MARGIN + 20, y, "(ամսաթիվ, ուսանողի ստորագրություն)")


# ---------------------------------------------------------------------------
# TOC (we lay it out AFTER the body so we know real page numbers).
# To keep the implementation simple we render the document in two passes:
#   pass 1: render to /dev/null counting pages and recording TOC entries
#   pass 2: render the real document with the TOC inserted before the body.
# ---------------------------------------------------------------------------
def _render_body(c: canvas.Canvas, st: LayoutState) -> None:
    """Render all body content onto *c*, starting from the current page/y."""
    # Sections (mixed types)
    for block in C.SECTIONS:
        kind = block[0]
        if kind == "h":
            write_heading(c, st, block[1])
        elif kind == "sh":
            write_subheading(c, st, block[1])
        elif kind == "p":
            write_paragraph(c, st, block[1])
        elif kind == "bul":
            write_bullets(c, st, block[1])
        elif kind == "num":
            write_numbered(c, st, block[1])
        elif kind == "code":
            # block = ("code", "lang", code)
            write_code(c, st, block[2])
        elif kind == "blank":
            st.y -= LINE_HEIGHT

    # Code listings
    for path, lang, code in C.CODE_LISTINGS_BACKEND:
        # Each filename is rendered as a small sub-label (file-path style)
        write_subheading(c, st, path, add_to_toc=False)
        write_code(c, st, code)

    # Frontend section heading
    write_subheading(c, st, "Frontend", add_to_toc=True)
    write_paragraph(
        c, st,
        "Սա օգտատիրոջ տեսած մասն է։ React-ը կառուցում է UI-ը փոքր "
        "components-երից, react-router-dom-ը կառավարում է, թե որ էջն է "
        "բացվում, axios-ը Backend-ին հարցումներ է ուղարկում, "
        "TanStack Query-ն cache-ում է պատասխանները, իսկ Vite-ը վերջում "
        "բոլոր ֆայլերը հավաքում է մեկ bundle-ի մեջ։",
    )
    for path, lang, code in C.CODE_LISTINGS_FRONTEND:
        write_subheading(c, st, path, add_to_toc=False)
        write_code(c, st, code)

    # Conclusion
    for block in C.CONCLUSION:
        kind = block[0]
        if kind == "h":
            write_heading(c, st, block[1])
        elif kind == "p":
            write_paragraph(c, st, block[1])

    # References
    write_heading(c, st, "Գրականության ցանկ")
    for url in C.REFERENCES:
        _ensure_space(c, st, LINE_HEIGHT)
        st.y -= LINE_HEIGHT
        c.setFont(REGULAR, BODY_SIZE)
        c.drawString(LEFT_MARGIN, st.y, url)
    st.y -= PARA_SPACE


def render_toc(c: canvas.Canvas, st: LayoutState, toc: List[Tuple[str, int, int]],
               page_offset: int) -> None:
    """Draw the TOC page(s).  *page_offset* is the number of pages the TOC
    itself occupies (the body's page numbers must shift by this amount).
    """
    # TOC heading - centered
    heading = "ԲՈՎԱՆԴԱԿՈՒԹՅՈՒՆ"
    w = _string_width(heading, REGULAR, HEADING_SIZE)
    _draw_bold_string(c, (PAGE_W - w) / 2, st.y, heading, REGULAR,
                      HEADING_SIZE, stroke_w=0.4)
    st.y -= 28

    c.setFont(REGULAR, BODY_SIZE)
    for label, level, pg in toc:
        line_y = st.y
        if line_y < BOTTOM_MARGIN + LINE_HEIGHT:
            _new_page(c, st, show_number=False)
            line_y = st.y

        indent = 0 if level == 0 else 20
        label_disp = label
        page_str = str(pg + page_offset)
        # Compute available space for dotted leader
        c.setFont(REGULAR, BODY_SIZE)
        label_w = _string_width(label_disp, REGULAR, BODY_SIZE)
        page_w = _string_width(page_str, REGULAR, BODY_SIZE)
        dots_start_x = LEFT_MARGIN + indent + label_w + 4
        dots_end_x = PAGE_W - RIGHT_MARGIN - page_w - 4

        # If label is too long, wrap it on multiple lines (no dotted leader on
        # first line; page number stays right of last line).
        if dots_start_x > dots_end_x:
            # try to wrap label across multiple lines
            wrapped = _wrap_text(label_disp, REGULAR, BODY_SIZE,
                                 USABLE_W - indent - page_w - 8)
            for i, wl in enumerate(wrapped):
                if st.y < BOTTOM_MARGIN + LINE_HEIGHT:
                    _new_page(c, st, show_number=False)
                st.y -= LINE_HEIGHT
                c.drawString(LEFT_MARGIN + indent, st.y, wl)
                if i == len(wrapped) - 1:
                    # draw dots + page number on last line
                    lw = _string_width(wl, REGULAR, BODY_SIZE)
                    dx_start = LEFT_MARGIN + indent + lw + 4
                    dx_end = PAGE_W - RIGHT_MARGIN - page_w - 4
                    if dx_start < dx_end:
                        dot = "."
                        dot_w = _string_width(dot, REGULAR, BODY_SIZE)
                        n = max(0, int((dx_end - dx_start) / dot_w))
                        c.drawString(dx_start, st.y, dot * n)
                    c.drawString(PAGE_W - RIGHT_MARGIN - page_w, st.y, page_str)
            st.y -= 2
            continue

        # Single line case
        st.y -= LINE_HEIGHT
        c.drawString(LEFT_MARGIN + indent, st.y, label_disp)
        dot = "."
        dot_w = _string_width(dot, REGULAR, BODY_SIZE)
        n = max(0, int((dots_end_x - dots_start_x) / dot_w))
        c.drawString(dots_start_x, st.y, dot * n)
        c.drawString(PAGE_W - RIGHT_MARGIN - page_w, st.y, page_str)


# ---------------------------------------------------------------------------
# Two-pass build
# ---------------------------------------------------------------------------
def _count_toc_pages(toc: List[Tuple[str, int, int]]) -> int:
    """Estimate how many pages the TOC will occupy.  We allow ~38 entries per
    page (the original document has ~30 on a single TOC page that's quite
    dense — we're slightly more generous to be safe)."""
    if not toc:
        return 1
    # 28pt header + ~14.5pt per entry, page height usable ~720pt
    per_page = max(1, int((PAGE_H - TOP_MARGIN - BOTTOM_MARGIN - 28) // LINE_HEIGHT))
    pages = (len(toc) + per_page - 1) // per_page
    return max(1, pages)


def build(output_path: str) -> None:
    register_fonts()

    # ---- Pass 1: render body to a throwaway canvas to capture TOC entries
    import io
    buf = io.BytesIO()
    c1 = canvas.Canvas(buf, pagesize=LETTER)
    st1 = LayoutState()
    # Pass 1 starts from a "blank body page 1" — the absolute page numbers
    # we record here will later be shifted by the size of the TOC.
    st1.page = 1
    st1.y = PAGE_H - TOP_MARGIN
    _render_body(c1, st1)
    # Discard the dry-run canvas.  We only need st1.toc_entries.
    toc = st1.toc_entries

    # ---- Estimate TOC pages and determine page offset
    toc_pages = _count_toc_pages(toc)
    # Title (1) + Assignment (2) + TOC(toc_pages) = number of pages BEFORE
    # body page 1.  Body page 1's printed number must be (2 + toc_pages + 1).
    page_offset = 2 + toc_pages  # the body's first page absolute number = page_offset + 1

    # ---- Pass 2: real canvas
    c = canvas.Canvas(output_path, pagesize=LETTER)
    c.setTitle(
        "Նախագծերի և առաջադրանքների կառավարման համակարգի տվյալների "
        "հենքի նախագծում (PTMS)"
    )
    c.setAuthor(C.STUDENT_NAME)
    c.setSubject("Տվյալների հենքերի նախագծում - կուրսային աշխատանք")

    st = LayoutState()
    # Page 1: title page (no page number)
    draw_title_page(c, st)

    # Page 2: assignment page (no page number)
    c.showPage()
    st.page = 2
    st.y = PAGE_H - TOP_MARGIN
    draw_assignment_page(c, st)

    # Page 3..: TOC (page numbers shown starting at 3)
    c.showPage()
    st.page = 3
    st.y = PAGE_H - TOP_MARGIN
    _draw_page_number(c, st.page, show=True)
    render_toc(c, st, toc, page_offset)

    # Body
    c.showPage()
    st.page = page_offset + 1
    st.y = PAGE_H - TOP_MARGIN
    _draw_page_number(c, st.page, show=True)
    # we need a fresh state for body so headings record real page numbers,
    # but we don't care about toc_entries in this pass.
    st.toc_entries = []
    _render_body(c, st)

    c.save()


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(HERE),
                       "PTMS_kursayin_ashkhatank.pdf")
    build(out)
    size = os.path.getsize(out)
    print(f"Wrote {out} ({size/1024:.1f} KB)")
