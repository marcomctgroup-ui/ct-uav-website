"""Local test server for refactor-v04 that applies _headers like Netlify (exact paths and trailing * splats).
Serves http://127.0.0.1:8767/ with this version folder as the site root. Local testing only."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
ROOT = Path(__file__).resolve().parents[1]

def load_rules():
    rules, cur = [], None
    for line in (ROOT / '_headers').read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if not line.startswith(' '):
            cur = (line.strip(), []); rules.append(cur)
        else:
            k, v = line.strip().split(':', 1); cur[1].append((k.strip(), v.strip()))
    return rules

def match(pattern, path):
    return path.startswith(pattern[:-1]) if pattern.endswith('*') else path == pattern

class Server(ThreadingHTTPServer):
    request_queue_size = 128; daemon_threads = True

class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.woff2': 'font/woff2', '.glb': 'model/gltf-binary', '.webp': 'image/webp', '.js': 'text/javascript'}
    def log_message(self, *a): pass
    def end_headers(self):
        path = self.path.split('?')[0].split('#')[0]
        merged = {}
        for pattern, headers in RULES:
            if match(pattern, path):
                for k, v in headers:
                    merged[k] = merged[k] + ', ' + v if k in merged else v   # Netlify combines overlapping values
        for k, v in merged.items():
            self.send_header(k, v)
        super().end_headers()
    def do_GET(self):
        try: super().do_GET()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError): pass

RULES = load_rules()
if __name__ == '__main__':
    Server(('127.0.0.1', 8767), partial(Handler, directory=str(ROOT))).serve_forever()
