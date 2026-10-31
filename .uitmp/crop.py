from PIL import Image
import sys

base = r"D:\SMART BUSINESSWRITER\.uitmp"

# collapsed rail top (toggle) and the whole collapsed strip
im = Image.open(base + r"\rail_now_collapsed.png")
im.crop((0, 56, 60, 200)).resize((60 * 6, 144 * 6), Image.LANCZOS).save(base + r"\z_toggle_collapsed.png")
im.crop((0, 56, 60, 900)).resize((60 * 2, 844 * 2), Image.LANCZOS).save(base + r"\z_strip_collapsed.png")

# expanded rail: the Subjects label area and the label column
im2 = Image.open(base + r"\rail_now_open.png")
im2.crop((0, 56, 280, 230)).resize((280 * 3, 174 * 3), Image.LANCZOS).save(base + r"\z_subjects_open.png")
im2.crop((0, 780, 280, 900)).resize((280 * 3, 120 * 3), Image.LANCZOS).save(base + r"\z_foot_open.png")
print("ok")
