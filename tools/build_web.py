"""只打包运行所需文件，转换浏览器音频/图片，不改动桌面原素材。"""
from pathlib import Path
import json
import hashlib
import os
import shutil
import subprocess
import sys
from PIL import Image
import soundfile

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'build' / 'web-app'
DIST = ROOT / 'dist' / 'web'
CACHE = ROOT / 'build' / 'web-assets'
MODULES = ('main.py', 'model.py', 'config.py', 'art.py', 'progress.py',
           'browser_progress.py', 'game_audio.py')


def clean_generated(path):
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT) or resolved == ROOT:
        raise ValueError('拒绝清理项目之外的目录')
    if path.exists():
        for item in (path, *path.rglob('*')):
            if item.is_symlink() or os.path.isjunction(item):
                raise ValueError('生成目录不能含链接')
        shutil.rmtree(resolved)


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    # 缓存转换结果，迭代 Python/UI 时无需反复压缩全部图片。
    def cache_path(source, suffix):
        digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
        return CACHE / f'{source.stem}-{digest}{suffix}'

    clean_generated(STAGE)
    STAGE.mkdir(parents=True)
    for name in MODULES:
        # 精灵图大小和坐标保持原样，仅转换编码。字符串路径同步更新。
        text = (ROOT / name).read_text(encoding='utf-8')
        (STAGE / name).write_text(text, encoding='utf-8')
    target_assets = STAGE / 'assets'
    target_assets.mkdir()
    for source in sorted((ROOT / 'assets').glob('*.png')):
        cached = cache_path(source, '-palette256.png')
        if not cached.exists():
            with Image.open(source) as image:
                # wasm SDL 的图片加载器依赖 PNG 预加载；保留格式和像素尺寸。
                image.convert('RGBA').quantize(colors=256, method=Image.Quantize.FASTOCTREE).save(
                    cached, 'PNG', optimize=True)
        shutil.copy2(cached, target_assets / source.name)
    shutil.copytree(ROOT / 'assets' / 'fonts', target_assets / 'fonts')
    audio = target_assets / 'audio'
    audio.mkdir()
    for source in sorted((ROOT / 'assets' / 'audio').glob('*.wav')):
        samples, rate = soundfile.read(source)
        soundfile.write(audio / (source.stem + '.ogg'), samples, rate, format='OGG', subtype='VORBIS')
    with Image.open(ROOT / 'assets' / 'star-tower.png') as image:
        image.thumbnail((96, 96))
        image.save(STAGE / 'favicon.png')
    subprocess.run([sys.executable, '-u', '-m', 'pygbag', '--build', '--no_opt',
                    '--title', '保卫大肥鱼', '--width', '1280', '--height', '800',
                    '--ume_block', '0', '--package', 'game.defendbigfish',
                    '--template', str(ROOT / 'web' / 'game.tmpl'), str(STAGE)],
                   cwd=ROOT, check=True, env=dict(os.environ, PYTHONUTF8='1'))
    clean_generated(DIST)
    shutil.copytree(STAGE / 'build' / 'web', DIST)
    shutil.copy2(STAGE / 'favicon.png', DIST / 'favicon.png')
    shutil.copy2(ROOT / 'web' / 'audio.js', DIST / 'audio.js')
    (DIST / 'audio').mkdir()
    shutil.copy2(ROOT / 'assets' / 'audio' / 'garden-loop.wav', DIST / 'audio' / 'garden-loop.wav')
    (DIST / '.nojekyll').touch()
    manifest = dict(files=len(list(target_assets.rglob('*'))),
                    asset_bytes=sum(p.stat().st_size for p in target_assets.rglob('*') if p.is_file()),
                    native_music_bytes=(DIST / 'audio' / 'garden-loop.wav').stat().st_size)
    (DIST / 'build-info.json').write_text(json.dumps(manifest), encoding='utf-8')
    print(f'Web build ready: {DIST} ({manifest["asset_bytes"] / 1024 / 1024:.1f} MiB assets)')


if __name__ == '__main__':
    main()
