"""只在本机提供网页预览；窗口保持打开期间可反复刷新。"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'dist' / 'web'


if __name__ == '__main__':
    if not (DIRECTORY / 'index.html').is_file():
        raise SystemExit('请先运行 tools/build_web.py 生成网页版。')
    handler = partial(SimpleHTTPRequestHandler, directory=str(DIRECTORY))
    try:
        server = ThreadingHTTPServer(('127.0.0.1', 8000), handler)
    except OSError as error:
        raise SystemExit(f'无法启动预览服务，8000 端口可能被占用：{error}')
    print('保卫大肥鱼网页预览：http://127.0.0.1:8000/', flush=True)
    print('保持此窗口打开，按 Ctrl+C 停止。', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
