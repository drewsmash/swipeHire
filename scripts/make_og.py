r"""Draw the link-preview images (1200x630) and the app icon for SwipeHire.

Writes static/og-seeker.png, static/og-employer.png and static/icon-180.png.
Needs Pillow and the Segoe UI fonts; on Windows run it in a throwaway container:

    docker run --rm -v "%cd%:/app" -v "C:\Windows\Fonts:/fonts:ro" python:3.12-slim ^
      sh -c "pip install -q pillow && python /app/scripts/make_og.py /app/static"
"""
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = sys.argv[1]
F = "/fonts/"
W, H = 1200, 630
BRAND = (79, 70, 229)
BRAND_DARK = (55, 48, 163)
INK = (23, 26, 43)
MUTED = (100, 106, 130)
LIKE = (22, 163, 74)
PASS = (225, 29, 72)


def font(name, size):
    return ImageFont.truetype(F + name, size)


def card(title, sub, chips, sections, footer, header_photo=None):
    """A tilted job/applicant card on a transparent layer."""
    cw, ch = 400, 470
    layer = Image.new("RGBA", (cw + 80, ch + 80), (0, 0, 0, 0))
    shadow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((40, 52, 40 + cw, 52 + ch), 28, fill=(10, 8, 60, 110))
    layer = Image.alpha_composite(layer, shadow.filter(ImageFilter.GaussianBlur(16)))
    d = ImageDraw.Draw(layer)
    x0, y0 = 40, 40
    d.rounded_rectangle((x0, y0, x0 + cw, y0 + ch), 28, fill="white")
    x, y = x0 + 30, y0 + 30
    if header_photo:
        d.ellipse((x, y, x + 64, y + 64), fill=(224, 231, 255))
        d.text((x + 32, y + 32), header_photo, font=font("segoeuib.ttf", 32), fill=BRAND, anchor="mm")
        d.text((x + 80, y + 4), title, font=font("segoeuib.ttf", 28), fill=INK)
        d.text((x + 80, y + 40), sub, font=font("seguisb.ttf", 20), fill=MUTED)
        y += 84
    else:
        d.text((x, y), title, font=font("segoeuib.ttf", 30), fill=INK)
        d.text((x, y + 42), sub, font=font("seguisb.ttf", 21), fill=MUTED)
        y += 84
    cx = x
    for c in chips:
        tw = d.textlength(c, font=font("segoeui.ttf", 17))
        d.rounded_rectangle((cx, y, cx + tw + 24, y + 32), 16, fill=(246, 247, 251), outline=(225, 228, 238))
        d.text((cx + 12, y + 16), c, font=font("segoeui.ttf", 17), fill=MUTED, anchor="lm")
        cx += tw + 32
    y += 52
    d.line((x, y, x0 + cw - 30, y), fill=(225, 228, 238), width=2)
    y += 18
    for heading, lines in sections:
        d.text((x, y), heading, font=font("segoeuib.ttf", 15), fill=BRAND)
        y += 26
        for ln in lines:
            d.ellipse((x + 2, y + 9, x + 8, y + 15), fill=INK)
            d.text((x + 18, y), ln, font=font("segoeui.ttf", 18), fill=INK)
            y += 28
        y += 10
    d.text((x, y + 2), footer, font=font("segoeuib.ttf", 28), fill=INK)
    # "INTERESTED" stamp
    stamp = Image.new("RGBA", (220, 64), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp)
    sd.rounded_rectangle((4, 4, 216, 60), 10, outline=LIKE, width=5, fill=(255, 255, 255, 235))
    sd.text((110, 32), "INTERESTED" if not header_photo else "MATCH", font=font("segoeuib.ttf", 26), fill=LIKE, anchor="mm")
    stamp = stamp.rotate(14, expand=True, resample=Image.BICUBIC)
    # (stamp drawn but not placed: it covered card text at this size)
    return layer.rotate(5, expand=True, resample=Image.BICUBIC)


def round_button(img, cx, cy, color, mark):
    d = ImageDraw.Draw(img)
    d.ellipse((cx - 40, cy - 40, cx + 40, cy + 40), fill="white")
    if mark == "x":
        d.line((cx - 14, cy - 14, cx + 14, cy + 14), fill=color, width=7)
        d.line((cx - 14, cy + 14, cx + 14, cy - 14), fill=color, width=7)
    else:
        d.line((cx - 17, cy + 1, cx - 5, cy + 13), fill=color, width=7)
        d.line((cx - 5, cy + 13, cx + 18, cy - 12), fill=color, width=7)


def logo(img, x, y, s):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x, y, x + s, y + s), int(s * 0.25), fill="white")
    back = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(back).rounded_rectangle((int(s * .22), int(s * .27), int(s * .62), int(s * .80)), int(s * .08), fill=(165, 180, 252))
    img.alpha_composite(back.rotate(10, resample=Image.BICUBIC, center=(s * .42, s * .53)), (x, y))
    d.rounded_rectangle((x + int(s * .34), y + int(s * .20), x + int(s * .78), y + int(s * .77)), int(s * .08), fill=BRAND)
    d.line((x + s * .45, y + s * .49, x + s * .53, y + s * .57), fill="white", width=max(3, s // 16))
    d.line((x + s * .53, y + s * .57, x + s * .68, y + s * .40), fill="white", width=max(3, s // 16))


def make(path, headline, sub, pill, card_layer):
    img = Image.new("RGBA", (W, H), BRAND)
    d = ImageDraw.Draw(img)
    for i in range(H):  # soft diagonal-ish gradient
        t = i / H
        d.line((0, i, W, i), fill=tuple(int(BRAND[k] * (1 - t) + BRAND_DARK[k] * t) for k in range(3)))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((700, -150, 1350, 500), fill=(129, 140, 248, 90))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(60)))
    d = ImageDraw.Draw(img)

    logo(img, 70, 70, 84)
    d.text((172, 112), "SwipeHire", font=font("segoeuib.ttf", 46), fill="white", anchor="lm")
    y = 220
    for line in headline:
        d.text((70, y), line, font=font("segoeuib.ttf", 64), fill="white")
        y += 78
    d.text((72, y + 14), sub, font=font("segoeui.ttf", 28), fill=(224, 231, 255))
    pf = font("segoeuib.ttf", 28)
    pw = d.textlength(pill, font=pf)
    d.rounded_rectangle((70, 500, 70 + pw + 56, 560), 30, fill="white")
    d.text((70 + 28, 530), pill, font=pf, fill=BRAND, anchor="lm")

    img.alpha_composite(card_layer, (690, 6))
    round_button(img, 830, 578, PASS, "x")
    round_button(img, 970, 578, LIKE, "check")
    img.convert("RGB").save(path, optimize=True)
    print("wrote", path)


make(OUT + "/og-seeker.png", ["Swipe right on", "your next job."],
     "One profile. Real matches. No long applications.", "Try it now  →  no sign-up",
     card("Junior Web Developer", "Biscayne Software Co.", ["Hybrid", "Full time", "Miami, FL"],
          [("RESPONSIBILITIES", ["Build pages in React", "Fix bugs reported by users"]),
           ("REQUIREMENTS", ["HTML, CSS and JavaScript", "Git basics"])],
          "$55k–$75k / yr"))
make(OUT + "/og-employer.png", ["Hire by swiping.", "Match in minutes."],
     "Only see people who already want the job.", "Try it as an employer  →",
     card("Maria Gonzalez", "Data Analyst", ["Hybrid", "Full time", "$60k+ / yr"],
          [("ABOUT", ["Loves SQL and dashboards", "Bilingual English/Spanish"]),
           ("CERTIFICATIONS", ["Google Data Analytics"])],
          "Wants: Data Analyst", header_photo="M"))


icon = Image.new("RGBA", (180, 180), BRAND)
logo(icon, 18, 18, 144)
icon.convert("RGB").save(OUT + "/icon-180.png", optimize=True)
print("wrote", OUT + "/icon-180.png")
