"""
Generate a synthetic wine-label PNG so you have a real image to drop into the UI
without hunting for one. (They didn't ship sample data — see README for real ones.)

Usage:  python scripts/make_sample_label.py
Output: tests/sample_data/sample_label.png  (matches tests/sample_data/sample_application.json)
"""

from PIL import Image, ImageDraw, ImageFont
import os, textwrap

OUT = os.path.join(os.path.dirname(__file__), "..", "tests", "sample_data", "sample_label.png")

GOV = ("GOVERNMENT WARNING: (1) According to the Surgeon General, women should not "
       "drink alcoholic beverages during pregnancy because of the risk of birth defects. "
       "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
       "operate machinery, and may cause health problems.")


def font(size, bold=False):
    # Fall back to default if Arial isn't present.
    for name in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main():
    W, H = 700, 900
    img = Image.new("RGB", (W, H), "#f3 efe6".replace(" ", ""))
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, W - 20, H - 20], outline="#8a6d3b", width=3)

    d.text((W // 2, 90), "STONE'S THROW", font=font(54, bold=True), fill="#3a2a1a", anchor="mm")
    d.text((W // 2, 150), "Red Wine", font=font(30), fill="#5a4632", anchor="mm")
    d.text((W // 2, 200), "Napa Valley, California", font=font(22), fill="#5a4632", anchor="mm")
    d.text((W // 2, 430), "Alc. 13.5% by Vol", font=font(26), fill="#3a2a1a", anchor="mm")
    d.text((W // 2, 470), "750 mL", font=font(26), fill="#3a2a1a", anchor="mm")
    d.text((W // 2, 520), "Acme Winery, Napa CA", font=font(20), fill="#5a4632", anchor="mm")

    y = 600
    for line in textwrap.wrap(GOV, width=58):
        d.text((45, y), line, font=font(16, bold=True), fill="#1a1a1a")
        y += 24

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT)
    print("Wrote", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
