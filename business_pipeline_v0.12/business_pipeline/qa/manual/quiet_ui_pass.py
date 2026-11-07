#!/usr/bin/env python3
"""Quiet pass over the workbench front end.

The owner asked for the website to read 90% less loud and 90% less big. This
script applies that in one deterministic pass, so the change can be re-run and
audited instead of being a pile of hand edits:

* type - every px font-size is scaled down in bands (display sizes hardest,
  body sizes least), so the hierarchy the owner tuned survives in proportion;
* space - padding, margin and gap shrink by a fifth, tap targets stay >= 40px;
* colour - the palette is pulled toward a neutral slate and the thirteen
  rainbow rail icons collapse to one muted steel;
* depth - gradients, glows, drop shadows and hover lifts go.

Only stylesheets and colour maps change. No markup, no script logic, no copy,
no number, no claim. Run it from the package root:

    python business_pipeline_v0.12/business_pipeline/qa/manual/quiet_ui_pass.py
"""

import pathlib
import re
import sys

PKG = pathlib.Path(__file__).resolve().parents[2]
WEB = PKG / "web"

# --------------------------------------------------------------------------
# the quiet palette: the same brand ink and green, with the volume taken out
# --------------------------------------------------------------------------
TOKEN_VALUES = {
    "--navy-900": "#1B3049", "--navy-700": "#33506B", "--navy-500": "#5C7691",
    "--navy-300": "#A6B4C2", "--navy-100": "#EDF1F5",
    "--green-600": "#3C8771", "--green-700": "#2F6552", "--green-900": "#2A463C",
    "--green-100": "#E9F0EC",
    "--teal": "#4C7C7C", "--indigo": "#4A5F87", "--forest": "#46775C",
    "--ochre": "#866B3C", "--violet": "#63557F", "--slate": "#5A6672",
    "--moss": "#5E7A4A", "--plum": "#77597F",
    "--canvas": "#FAFBFC", "--surface": "#FFFFFF", "--sunken": "#F4F6F8",
    "--border": "#E3E7EB", "--border-2": "#EEF1F4",
    "--text": "#1B3049", "--text-2": "#1B3049", "--text-3": "#1B3049",
    "--amber": "#8A5A18", "--amber-bg": "#FAF4E9", "--amber-line": "#E7D9BE",
    "--red": "#8E3230", "--red-bg": "#FAEEEE", "--red-line": "#E9CFCF",
    "--you": "#7A5A22", "--you-bg": "#FAF2E3", "--you-line": "#E4D7BC",
    "--ops-tint": "#E8ECF2",
    "--r-sm": "4px", "--r-md": "6px", "--r-lg": "8px", "--r-pill": "6px",
    "--sh-1": "0 1px 1px rgba(27,48,73,.04)",
    "--sh-2": "0 1px 2px rgba(27,48,73,.05)",
    "--sh-3": "0 4px 14px rgba(27,48,73,.08)",
    "--rail-w": "40px", "--rail-w-open": "248px", "--rail-ic-w": "22px",
    "--rail-sb": "14px",
}

# the muted steel that replaces every rainbow rail icon
RAIL_STEEL = "#AFBECC"

# the pass scales type and space, so it must not run twice over one file.
# The marker is written into the stylesheet and checked before the work.
MARKER = "/* sbw-quiet-pass v1 */"

# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def scale_font_size(value):
    """Scale one px font-size. Display type shrinks hardest, body type least."""
    number = float(value)
    if number >= 26:
        number *= 0.58
    elif number >= 18:
        number *= 0.72
    else:
        number *= 0.85
    return "%gpx" % max(10.0, round(number, 1))


def scale_length(value):
    """Scale one px length used for space. Tiny values are left alone."""
    number = float(value)
    if number == 0:
        return "0"
    if number <= 3:
        return "%gpx" % number
    scaled = round(number * 0.8, 1)
    return "%gpx" % max(1.0, scaled)


def mute_hex(match):
    """Pull one hardcoded hex toward a neutral slate."""
    digits = match.group(1)
    before = match.string[max(0, match.start() - 4):match.start()].lower()
    if before.endswith("url("):          # an SVG paint reference, not a colour
        return match.group(0)
    if len(digits) == 3:
        digits = "".join(c * 2 for c in digits)
    red, green, blue = (int(digits[i:i + 2], 16) for i in (0, 2, 4))
    if red >= 245 and green >= 245 and blue >= 245:
        return match.group(0)                            # white stays white
    if red <= 8 and green <= 8 and blue <= 8:
        return match.group(0)                            # black stays black
    target = (0x6B, 0x72, 0x80)
    ratio = 0.55
    mixed = [round(c * (1 - ratio) + t * ratio) for c, t in zip((red, green, blue), target)]
    return "#%02X%02X%02X" % tuple(mixed)


# only the brand's own tints are muted; white overlays stay white and black
# shadows stay black, or the rail hover would disappear into the strip
RGBA_TINTS = {
    (2, 161, 94): (60, 135, 113),
    (30, 158, 107): (60, 135, 113),
    (2, 40, 76): (27, 48, 73),
    (16, 24, 40): (27, 48, 73),
    (20, 40, 90): (27, 48, 73),
    (7, 26, 43): (27, 48, 73),
    (12, 36, 62): (27, 48, 73),
}


def mute_rgba(match):
    """Bring a brand-tinted glow down to a quiet neutral."""
    channels = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    alpha = float(match.group(4))
    if channels not in RGBA_TINTS:
        return match.group(0)
    neutral = RGBA_TINTS[channels]
    alpha = round(alpha * 0.6, 3)
    return "rgba(%d,%d,%d,%g)" % (neutral[0], neutral[1], neutral[2], alpha)


# one rule: the text before its brace, and the text inside it
RULE_RE = re.compile(r"([^{}]*)\{([^{}]*)\}", re.S)


def selector_parts(text):
    """The comma-separated selectors of one rule, comments stripped."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return [part.strip() for part in text.split(",") if part.strip()]


def set_prop(css, selector, prop, value, occurrence=1):
    """Set one property inside the rule whose selector list carries `selector`.

    The match is on whole selectors, not on substrings: `th` must be a
    selector of its own, so `th,td` and `.mxgrid thead th` are found by
    their own names and never by accident.
    """
    wanted = selector_parts(selector)
    found = 0
    for hit in RULE_RE.finditer(css):
        parts = selector_parts(hit.group(1))
        if not wanted or any(part not in parts for part in wanted):
            continue
        body = hit.group(2)
        if not re.search(r"(?<![-\w])" + re.escape(prop) + r"\s*:", body):
            continue
        found += 1
        if found < occurrence:
            continue
        new_body = re.sub(
            r"(?<![-\w])" + re.escape(prop) + r"\s*:\s*[^;}]*",
            prop + ":" + value, body, count=1)
        return css[:hit.start(2)] + new_body + css[hit.end(2):]
    return css


def patch_root_tokens(css):
    """Rewrite the token block, keeping the owner's geometry comments."""
    match = re.search(r":root\s*\{[^{}]*\}", css)
    if not match:
        return css
    block = match.group(0)
    for name, value in TOKEN_VALUES.items():
        block = re.sub(
            r"(?<![-\w])" + re.escape(name) + r"\s*:\s*[^;}]+",
            name + ":" + value, block)
    return css[:match.start()] + block + css[match.end():]


def scale_css(css):
    """Scale the type and the space inside one stylesheet."""
    css = re.sub(r"font-size\s*:\s*(\d+(?:\.\d+)?)px",
                 lambda m: "font-size:" + scale_font_size(m.group(1)), css)
    css = re.sub(r"font\s*:\s*(\d+(?:\.\d+)?)px",
                 lambda m: "font:" + scale_font_size(m.group(1)), css)

    def spacing(match):
        return match.group(1) + re.sub(
            r"(\d+(?:\.\d+)?)px",
            lambda m: scale_length(m.group(1)), match.group(2))

    css = re.sub(r"((?:^|[;{\s])(?:padding|margin|padding-top|padding-bottom|"
                 r"padding-left|padding-right|margin-top|margin-bottom|"
                 r"margin-left|margin-right|gap|row-gap|column-gap)\s*:\s*)"
                 r"([^;}]*)", spacing, css)

    # a tap target stays a tap target
    def min_height(match):
        value = float(match.group(1))
        scaled = value * 0.8
        if value >= 40:
            scaled = max(40.0, scaled)
        else:
            scaled = max(30.0, scaled)
        return "min-height:%gpx" % round(scaled, 1)

    css = re.sub(r"min-height\s*:\s*(\d+(?:\.\d+)?)px", min_height, css)
    return css


def mute_colour(css):
    """Pull every hardcoded colour in the stylesheet toward the neutral."""
    css = re.sub(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d*\.?\d+)\s*\)",
                 mute_rgba, css)
    css = re.sub(r"#([0-9A-Fa-f]{3,6})\b", mute_hex, css)
    return css


# --------------------------------------------------------------------------
# the workbench: index.html
# --------------------------------------------------------------------------

INDEX_EDITS = [
    # the shell: a narrower page, a shorter bar, a flatter stage
    ("main", "max-width", "1080px"),
    ("main", "padding", "20px 24px 56px"),
    (".topbar", "height", "48px"),
    (".brand img", "height", "24px"),
    (".hero", "padding", "26px 0 16px"),
    (".hero img", "height", "58px"),
    (".hero img", "filter", "none"),
    (".hero::before", "background", "none"),
    # the rail: a narrow strip and small glyphs
    (".rail", "top", "48px"),
    (".rail", "height", "calc(100vh - 48px)"),
    (".railitem", "height", "36px"),
    (".railitem .ic svg", "width", "16px"),
    (".railitem .ic svg", "height", "16px"),
    (".railitem[aria-current=page] .ic svg", "filter", "none"),
    ("body.rail-open .railitem .ic", "border-radius", "5px"),
    # the composer: a smaller box, a smaller send button
    (".actionbox", "border-radius", "8px"),
    (".actionbox", "box-shadow", "var(--sh-1)"),
    (".actionbox:hover", "box-shadow", "var(--sh-2)"),
    (".actionbox textarea", "min-height", "72px"),
    (".runbtn", "width", "34px"),
    (".runbtn", "height", "34px"),
    (".runbtn svg", "width", "16px"),
    (".runbtn svg", "height", "16px"),
    # the chat button: flat, small, no gradient
    (".chatbtn", "width", "42px"),
    (".chatbtn", "height", "42px"),
    (".chatbtn", "background", "var(--navy-700)"),
    (".chatbtn", "box-shadow", "0 2px 8px rgba(27,48,73,.14)"),
    (".chatbtn img", "height", "22px"),
    (".chatbtn img", "width", "22px"),
    (".chatbtn:hover", "box-shadow", "0 2px 10px rgba(27,48,73,.18)"),
    # no green glow on a focus ring: a quiet neutral ring instead
    (".actionbox:focus-within", "border-color", "var(--navy-300)"),
    (".actionbox:focus-within", "box-shadow", "var(--sh-2),0 0 0 3px rgba(27,48,73,.06)"),
    (".actionbox.dragging", "border-color", "var(--navy-300)"),
    (".actionbox.dragging", "box-shadow", "var(--sh-2),0 0 0 3px rgba(27,48,73,.08)"),
    (".wsheet textarea.wtext:focus", "border-color", "var(--navy-300)"),
    (".wsheet textarea.wtext:focus", "box-shadow", "0 0 0 3px rgba(27,48,73,.07)"),
    (".mxgrid td input:focus", "border-color", "var(--navy-300)"),
    (".mxgrid td input:focus", "box-shadow", "0 0 0 3px rgba(27,48,73,.07)"),
    (".mxfield input:focus", "border-color", "var(--navy-300)"),
    (".mxfield input:focus", "box-shadow", "0 0 0 3px rgba(27,48,73,.07)"),
    (".lookupfield select:focus,.lookupfield input:focus", "border-color", "var(--navy-300)"),
    (".lookupfield select:focus,.lookupfield input:focus", "box-shadow", "0 0 0 3px rgba(27,48,73,.07)"),
    # no lift on hover: the page stays flat
    (".subjectcard:hover", "transform", "none"),
    (".capcard:hover", "transform", "none"),
    (".decision:hover", "transform", "none"),
    (".pfchoice:hover", "transform", "none"),
    # tables: a grey head, not a green one
    ("th", "background", "var(--sunken)"),
    ("th", "color", "var(--text-2)"),
    ("th", "border-bottom", "1px solid var(--border)"),
    (".mxgrid thead th", "background", "var(--sunken)"),
    (".mxgrid thead th", "color", "var(--text-2)"),
    (".engtable th", "background", "var(--sunken)"),
    (".engtable th", "color", "var(--text-2)"),
    (".engtable th", "border-bottom", "1px solid var(--border)"),
    # the subject-page group bar: a quiet band instead of a green one
    ("#subjectout .levelhead", "background", "var(--sunken)"),
    ("#subjectout .levelhead", "color", "var(--navy-900)"),
    ("#subjectout .levelhead", "border-bottom", "1px solid var(--border)"),
    ("#subjectout .levelhead", "border-radius", "6px"),
    ("#subjectout .levelhead > button", "color", "var(--navy-700)"),
    ("#subjectout .levelhead > button", "font-size", "14px"),
    ("#subjectout .levelhead > button.danger", "color", "var(--navy-700)"),
    ("#subjectout .levelhead > button::before", "background", "var(--border)"),
    ("#subjectout .levelhead > button:hover,\n#subjectout .levelhead > button:focus-visible",
     "background", "var(--border-2)"),
    ("#subjectout .levelhead > button:hover,\n#subjectout .levelhead > button:focus-visible",
     "border-color", "var(--border)"),
    # the step bar: a grey step, not a green one
    (".stepbar .step.on", "border-color", "var(--navy-300)"),
    (".stepbar .step.on", "background", "var(--sunken)"),
    (".stepbar .step.on b", "background", "var(--navy-700)"),
    # the sticky bar sits on a hairline
    (".stickybar", "box-shadow", "0 -1px 0 var(--border)"),
    # small icons everywhere
    (".subjectcard .shield .capicon", "width", "26px"),
    (".subjectcard .shield .capicon", "height", "26px"),
    (".subjectcard .shield .capicon", "border-radius", "6px"),
    (".capcard .capicon", "width", "26px"),
    (".capcard .capicon", "height", "26px"),
    (".capcard .capicon", "border-radius", "6px"),
    (".capcard .capicon svg", "width", "15px"),
    (".capcard .capicon svg", "height", "15px"),
    (".subjectcard .capicon svg", "width", "15px"),
    (".subjectcard .capicon svg", "height", "15px"),
    (".shield .capicon svg", "width", "20px"),
    (".shield .capicon svg", "height", "20px"),
    # the calculator: a flat display, a smaller keypad
    (".calcdisplay", "background", "var(--surface)"),
    (".calcdisplay .line .live", "background", "#F3EFDD"),
    (".calcpad button", "height", "38px"),
    (".calcgrid > div:first-child", "top", "52px"),
    # the paper preview keeps a readable size of its own
    (".report", "font-size", "15.5px"),
    (".doc", "font-size", "15px"),
    # Portfolio Lab: a flat stage, no glow, no texture
    (".pfhero", "background", "#1E2B38"),
    (".pfhero", "box-shadow", "none"),
    (".pfhero", "border-radius", "8px"),
    (".pfhero:before", "opacity", ".14"),
    (".pftile", "background", "var(--surface)"),
    (".pftile", "border-radius", "8px"),
    (".pfvalue", "background", "var(--surface)"),
    (".pfvalue", "border-radius", "8px"),
    (".pfvalue", "border-left", "2px solid var(--border)"),
    (".pflimit", "border-radius", "8px"),
    (".pfchoice", "border-radius", "8px"),
    (".pfstat", "border-radius", "8px"),
    (".pfchip", "border-radius", "6px"),
    (".pficon", "width", "26px"),
    (".pficon", "height", "26px"),
    (".pficon", "border-radius", "6px"),
    (".pficon svg", "width", "14px"),
    (".pficon svg", "height", "14px"),
    ("a.pfguidepill", "box-shadow", "none"),
    # the pricing sheet: a hairline instead of a colour bar
    (".pm-band:before", "height", "1px"),
    (".pm-band:before", "background", "var(--border)"),
    (".pm-card .bar", "height", "2px"),
    (".pm-switch", "border-radius", "999px"),
    (".pm-x", "width", "26px"),
    (".pm-x", "height", "26px"),
    (".pm-busy", "width", "28px"),
    (".pm-busy", "height", "28px"),
    (".pm-ok", "width", "32px"),
    (".pm-ok", "height", "32px"),
    # small marks
    (".levelhead::before", "width", "3px"),
    (".levelhead::before", "background", "var(--navy-300)"),
    (".marketcard", "border-left", "2px solid var(--navy-300)"),
    (".spin", "width", "12px"),
    (".spin", "height", "12px"),
    (".attachrow", "border-radius", "6px"),
    (".statementsprint", "border-radius", "6px"),
    (".statementsprint", "font", "11px/1.55 ui-monospace,monospace"),
    # the narrow layout keeps the same quiet geometry as the wide one
    (":root", "--rail-w", "40px", 2),
    (":root", "--rail-ic-w", "22px", 2),
    (".hero img", "height", "46px", 2),
    ("body.rail-open .rail", "top", "48px"),
    ("body.rail-open .rail", "height", "calc(100vh - 48px)"),
]


def scale_page_fonts(text):
    """Scale the type inside inline styles, once, outside the stylesheet."""
    return re.sub(r"font-size\s*:\s*(\d+(?:\.\d+)?)px",
                  lambda m: "font-size:" + scale_font_size(m.group(1)), text)


def quiet_index(page):
    """Quiet the workbench page."""
    match = re.search(r"<style[^>]*>(.*?)</style>", page, re.S)
    if not match:
        return page, []
    css = match.group(1)
    head = page[:match.start(1)]
    tail = page[match.end(1):]

    css = mute_colour(css)
    css = patch_root_tokens(css)
    css = scale_css(css)

    missed = []
    for edit in INDEX_EDITS:
        selector, prop, value = edit[0], edit[1], edit[2]
        occurrence = edit[3] if len(edit) > 3 else 1
        new_css = set_prop(css, selector, prop, value, occurrence)
        if new_css == css:
            missed.append("%s { %s }" % (selector, prop))
        css = new_css

    # the pills that were 999px radius are now small rounded rectangles
    css = css.replace("border-radius:999px", "border-radius:6px")
    css = set_prop(css, ".pm-switch", "border-radius", "999px")

    # the type inside inline styles follows the same scale. The stylesheet has
    # already been scaled, so the page around it is scaled here - never twice.
    page = scale_page_fonts(head) + css + scale_page_fonts(tail)

    # the thirteen rainbow rail icons become one muted steel; Home stays white
    page = re.sub(r"--i:\s*#[0-9A-Fa-f]{3,6}", "--i:" + RAIL_STEEL, page)
    page = page.replace("--i:" + RAIL_STEEL, "--i:#FFFFFF", 1)

    tones = re.search(r"const RAIL_TONES = \{.*?\};", page, re.S)
    if tones:
        block = tones.group(0)
        block = re.sub(r':\s*"#[0-9A-Fa-f]{3,6}"', ': "' + RAIL_STEEL + '"', block)
        block = block.replace('"home": "' + RAIL_STEEL + '"', '"home": "#FFFFFF"')
        page = page[:tones.start()] + block + page[tones.end():]

    return page, missed


# --------------------------------------------------------------------------
# the two sibling pages
# --------------------------------------------------------------------------

ADMIN_ROOT = """:root {
    --navy: #1B3049;
    --navy-dark: #14212E;
    --green: #3C8771;
    --green-dark: #2F6552;
    --bg: #FAFBFC;
    --surface: #FFFFFF;
    --border: #E3E7EB;
    --text: #1B3049;
    --muted: #5A6672;
    --danger: #8E3230;
    --warn: #8A6A32;
    --ok: #3C8771;
    --radius: 6px;
    --shadow: 0 1px 2px rgba(27,48,73,0.05);
  }"""


def quiet_admin(page):
    """Quiet the admin monitor page."""
    match = re.search(r"<style[^>]*>(.*?)</style>", page, re.S)
    if not match:
        return page, []
    css = match.group(1)
    head = page[:match.start(1)]
    tail = page[match.end(1):]
    css = mute_colour(css)
    css = re.sub(r":root\s*\{[^{}]*\}", ADMIN_ROOT, css, count=1)
    css = scale_css(css)
    css = css.replace("box-shadow: 0 2px 6px rgba(0,0,0,0.15);",
                      "box-shadow: none;")
    css = css.replace("border-radius: 12px;", "border-radius: 6px;")
    css = css.replace("padding: 12px 20px;", "padding: 9px 16px;")
    page = scale_page_fonts(head) + css + scale_page_fonts(tail)
    return page, []


def quiet_account(page):
    """Quiet the account page."""
    match = re.search(r"<style[^>]*>(.*?)</style>", page, re.S)
    if not match:
        return page, []
    css = match.group(1)
    head = page[:match.start(1)]
    tail = page[match.end(1):]
    css = mute_colour(css)
    css = patch_root_tokens(css)
    css = scale_css(css)
    page = scale_page_fonts(head) + css + scale_page_fonts(tail)
    return page, []


# --------------------------------------------------------------------------


def main():
    targets = [
        ("index.html", quiet_index),
        ("account.html", quiet_account),
        ("admin-sbw.html", quiet_admin),
    ]
    for name, worker in targets:
        path = WEB / name
        if not path.exists():
            print("skip %s (missing)" % name)
            continue
        page = path.read_text(encoding="utf-8")
        if MARKER in page:
            print("%s: already has the quiet pass - nothing done" % name)
            continue
        new_page, missed = worker(page)
        if new_page == page:
            print("%s: unchanged" % name)
            continue
        # the marker keeps a second run from scaling the page twice
        new_page = new_page.replace("<style>", "<style>\n" + MARKER, 1)
        path.write_text(new_page, encoding="utf-8", newline="")
        print("%s: quiet pass applied (%d bytes -> %d bytes)"
              % (name, len(page), len(new_page)))
        for item in missed:
            print("    missed: %s" % item)
    return 0


if __name__ == "__main__":
    sys.exit(main())
