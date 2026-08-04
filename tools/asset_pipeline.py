from PIL import Image
from pathlib import Path


def optimize_image(path, output_path, max_size=(1920, 1080), quality=85):
    p = Path(path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(p)
    img.thumbnail(max_size)
    img.save(out, optimize=True, quality=quality)


if __name__ == '__main__':
    print("Asset pipeline placeholder. Import optimize_image() in your build scripts.")
