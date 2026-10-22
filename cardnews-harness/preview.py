"""PNG 내보내기 이후 검수용 축소 보기/미리보기. Pillow가 필요하다."""
import argparse
from pathlib import Path
from PIL import Image


def build(folder):
    images = [Image.open(folder / f'{i:02}.png').convert('RGB') for i in range(1, 7)]
    for width in (375, 432):
        height = round(1350 * width / 1080)
        canvas = Image.new('RGB', (3 * width + 32, 2 * height + 16), '#e7e7e7')
        for i, image in enumerate(images):
            image = image.resize((width, height), Image.Resampling.LANCZOS)
            image.save(folder / f'{i+1:02}-{width}.png')
            canvas.paste(image, ((i % 3)*(width+16), (i//3)*(height+16)))
        canvas.save(folder / f'preview-{width}.png')
        if width == 432: canvas.save(folder / 'preview.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    build(parser.parse_args().folder)
