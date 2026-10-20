import sys
from PIL import Image, ImageChops
a, b, views = sys.argv[1], sys.argv[2], sys.argv[3:]
R = sys.argv[0].rsplit('/', 1)[0] + '/renders/'
for v in views:
    A = Image.open(R + a + '_' + v + '.png').convert('L'); B = Image.open(R + b + '_' + v + '.png').convert('L')
    d = ImageChops.difference(A, B)
    hist = d.histogram(); tot = sum(hist)
    big = sum(hist[25:]) / tot * 100      # pixels differing by >10% brightness
    print('%-11s max %3d  pixels>25: %.2f%%' % (v, d.getextrema()[1], big))
    d.point(lambda x: min(255, x * 4)).save(R + 'diff_%s_%s_%s.png' % (a, b, v))
