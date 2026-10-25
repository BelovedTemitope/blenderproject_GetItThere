import sys
from PIL import Image, ImageDraw
out, cols = sys.argv[1], int(sys.argv[2]); files = sys.argv[3:]
ims = [Image.open(f).resize((688, 384)) for f in files]
rows = (len(ims) + cols - 1) // cols
sh = Image.new('RGB', (688 * cols, 384 * rows), 'white')
d = ImageDraw.Draw(sh)
for i, (im, f) in enumerate(zip(ims, files)):
    x, y = (i % cols) * 688, (i // cols) * 384
    sh.paste(im, (x, y)); d.text((x + 8, y + 6), f.split('/')[-1][:-4], fill='black')
sh.save(out, quality=88)
