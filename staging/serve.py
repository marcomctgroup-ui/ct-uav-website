"""Local HTTP review of the generated Cloudflare Pages output and headers."""
import argparse
import fnmatch
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from build import parse_headers

ROOT = Path(__file__).resolve().parent / 'dist'


class Server(ThreadingHTTPServer):
    request_queue_size = 128
    daemon_threads = True


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.woff2': 'font/woff2',
                      '.glb': 'model/gltf-binary', '.webp': 'image/webp', '.js': 'text/javascript'}

    def log_message(self, *args):
        pass

    def end_headers(self):
        path = urlsplit(self.path).path
        merged = {}
        for pattern, headers in self.server.header_rules:
            if fnmatch.fnmatchcase(path, pattern):
                for name, value in headers.items():
                    merged[name] = merged[name] + ', ' + value if name in merged else value
        for name, value in merged.items():
            self.send_header(name, value)
        super().end_headers()

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path.endswith('.html'):
            target = '/'.join(url.path.split('/')[:-1]) + '/' if url.path.endswith('/index.html') else url.path[:-5]
            self.send_response(308)
            self.send_header('Location', urlunsplit(('', '', target, url.query, '')))
            self.end_headers()
            return
        if not Path(self.translate_path(url.path)).exists() and Path(self.translate_path(url.path + '.html')).is_file():
            self.path = urlunsplit(('', '', url.path + '.html', url.query, ''))
        try:
            super().do_GET()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8788)
    args = parser.parse_args()
    server = Server(('127.0.0.1', args.port), partial(Handler, directory=str(ROOT)))
    server.header_rules = parse_headers((ROOT / '_headers').read_text(encoding='utf-8'))
    print(f'Local staging review: http://127.0.0.1:{args.port}/', flush=True)
    server.serve_forever()
