from manim import *

BG_COLOR = ManimColor.from_rgb((2, 164, 211))
BOARD_FILL = ManimColor.from_rgb((0, 0, 175))

FONT = "Arial"

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