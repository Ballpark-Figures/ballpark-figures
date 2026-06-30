from manim import *

BG_COLOR = ManimColor.from_rgb((2, 164, 211))
ACCENT_FILL = ManimColor.from_rgb((0, 0, 175))   # primary accent (deep blue)

# Secondary accent palette — a warm trio that reads against the blue primary and
# the cyan background. Use these (in order) for categorical / overlay / highlight
# colours so every video stays consistent.
ACCENT_GOLD   = ManimColor("#E8A33D")
ACCENT_ORANGE = ManimColor("#E87A2C")
ACCENT_RED    = ManimColor("#D6402C")
ACCENT_PALETTE = [ACCENT_GOLD, ACCENT_ORANGE, ACCENT_RED]

# Default card surface (cream), shared by the card asset + scorecard.
CARD_FILL = "#F7F2E7"

FONT = "Inter"

FONT_SIZE_XS = 15.0
FONT_SIZE_SM = 24.0
FONT_SIZE_MD = 36.0
FONT_SIZE_LG = 48.0

TEXT_SS = 10
TEXT_SS_MAX_FONT = 240

def _supersample(font_size):
    return max(1.0, min(TEXT_SS, TEXT_SS_MAX_FONT / font_size))

def crisp_text(text, **kwargs):
    fs = kwargs.pop("font_size", DEFAULT_FONT_SIZE)
    ss = _supersample(fs)
    return Text(text, font_size=fs * ss, **kwargs).scale(1 / ss)

def crisp_paragraph(*lines, **kwargs):
    fs = kwargs.pop("font_size", DEFAULT_FONT_SIZE)
    ss = _supersample(fs)
    return Paragraph(*lines, font_size=fs * ss, **kwargs).scale(1 / ss)