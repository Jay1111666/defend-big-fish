"""按源码字符重新生成 Noto Sans CJK SC 子集，保留原字体 OFL 许可。"""
from pathlib import Path
import hashlib
import urllib.request
from fontTools import subset

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf'


def main():
    cache = ROOT / 'build' / 'fonts'
    cache.mkdir(parents=True, exist_ok=True)
    original = cache / 'NotoSansCJKsc-Regular.otf'
    if not original.exists():
        urllib.request.urlretrieve(URL, original)
    text = ''.join(p.read_text(encoding='utf-8') for p in ROOT.glob('*.py'))
    text += ''.join(chr(n) for n in range(32, 127)) + '↑↓←→●×…'
    options = subset.Options()
    options.name_IDs = ['*']
    options.name_legacy = True
    font = subset.load_font(str(original), options)
    builder = subset.Subsetter(options=options)
    builder.populate(text=text)
    builder.subset(font)
    output = ROOT / 'assets' / 'fonts' / 'game-cjk.otf'
    subset.save_font(font, str(output), options)
    print(f'Font subset: {output.stat().st_size} bytes')
    print(f'Source SHA256: {hashlib.sha256(original.read_bytes()).hexdigest()}')


if __name__ == '__main__':
    main()
