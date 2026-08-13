from manim import *

BG_COLOR = ManimColor.from_rgb((2, 164, 211))
# ── ACCENT COLOUR HIERARCHY (pick in this order; don't hand-pick hex) ──────────
# 1. PRIMARY   — ACCENT_FILL (deep blue): the default single accent, for data /
#    bars / fills. A scene that needs only one colour uses this.
# 2. HIGHLIGHT — ACCENT_GOLD: the "notice this" accent — highlights, medians,
#    peaks, the emphasised element. Reserve it for that role; don't spend gold as a
#    generic categorical fill in a scene that also needs a highlight colour.
# 3. CATEGORICAL — when several colours must be told apart AT ONCE, pull from
#    CATEGORICAL_PALETTE in order (warm gold/orange/red, then cool green/purple/
#    pink). These carry NO fixed meaning; they only have to differ.
# NOT accents: semantic score/status colours (points = green, zeroed/loss = red)
# are a per-video concern, defined in that video's config.py (e.g. yahtzee
# SCORE_GREEN / SCORE_RED) and deliberately DARKER than the accents. Do NOT reuse
# ACCENT_GREEN / ACCENT_RED for "good/bad" — they're categorical only.
ACCENT_FILL = ManimColor.from_rgb((0, 0, 175))   # 1. primary (deep blue)

# Secondary "warm trio". ACCENT_GOLD is the highlight accent (tier 2 above); the
# three together are the first categorical set and read against the blue primary
# and the cyan background.
ACCENT_GOLD   = ManimColor("#E8A33D")            # 2. highlight / median / emphasis
ACCENT_ORANGE = ManimColor("#E87A2C")
ACCENT_RED    = ManimColor("#D6402C")
ACCENT_PALETTE = [ACCENT_GOLD, ACCENT_ORANGE, ACCENT_RED]

# Cool complements — extend the categorical set past three. Chosen to stay legible
# on the cyan background — a medium blue is deliberately avoided (it blends with the
# BG), so the deep-blue primary ACCENT_FILL stays reserved for bars/fills.
ACCENT_GREEN  = ManimColor("#2E9E4F")
ACCENT_PURPLE = ManimColor("#7A3FB0")
ACCENT_PINK   = ManimColor("#C43B86")

# 3. A 6-way categorical palette (warm trio + cool trio), none of which is the
# primary ACCENT_FILL. Use in order for lines/series that must all differ at once.
CATEGORICAL_PALETTE = [ACCENT_GOLD, ACCENT_ORANGE, ACCENT_RED,
                       ACCENT_GREEN, ACCENT_PURPLE, ACCENT_PINK]

# ── LIGHT RAINBOW — bright light-on-dark sequential/categorical fills ───────────
# Six bright hues (red→purple), saturated but high-value so they POP on a DARK
# background yet still read clearly as colours (not near-white pastels). For a
# rainbow ramp distinct from the ACCENT / CATEGORICAL sets — e.g. a per-count or
# per-step colour scale. Listed red→purple; index (or reverse-index) as the scale needs.
LIGHT_RED    = ManimColor("#FF6B6B")
LIGHT_ORANGE = ManimColor("#FF9E42")
LIGHT_YELLOW = ManimColor("#FFD93D")
LIGHT_GREEN  = ManimColor("#3FD97A")
LIGHT_BLUE   = ManimColor("#3FAEF5")
LIGHT_PURPLE = ManimColor("#B072EE")
LIGHT_PALETTE = [LIGHT_RED, LIGHT_ORANGE, LIGHT_YELLOW,
                 LIGHT_GREEN, LIGHT_BLUE, LIGHT_PURPLE]

# Default card surface (cream), shared by the card asset + scorecard.
CARD_FILL = "#F7F2E7"

# Cooler crimson — deliberately tuned to sit against the cyan BG without the orange
# cast of the warm-trio ACCENT_RED. Shared across videos: the scorecard header /
# Total bars (yahtzee CARD_ACCENT) and the semantic "miss / loss" red.
CRIMSON = ManimColor("#B01E43")

# Neutral "no data yet / inactive" fill — a medium grey that reads clearly as
# placeholder against both WHITE (a real 0-value cell) and the accent fills, so an
# element can sit un-populated before its data animates in (e.g. a heatmap cell
# revealed only when its column is scaled in). Distinct from any accent/categorical.
MUTED_GREY = ManimColor("#888888")

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
    # Default to our brand FONT so callers can't accidentally render in manim's
    # built-in font by forgetting font=FONT (that was a real, repeated bug).
    kwargs.setdefault("font", FONT)
    fs = kwargs.pop("font_size", DEFAULT_FONT_SIZE)
    ss = _supersample(fs)
    return Text(text, font_size=fs * ss, **kwargs).scale(1 / ss)

def crisp_paragraph(*lines, **kwargs):
    kwargs.setdefault("font", FONT)
    fs = kwargs.pop("font_size", DEFAULT_FONT_SIZE)
    ss = _supersample(fs)
    return Paragraph(*lines, font_size=fs * ss, **kwargs).scale(1 / ss)