"""Loopback-only review server for the private generated CMS candidate."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
class Server(ThreadingHTTPServer):
    request_queue_size = 128
    daemon_threads = True
    allow_reuse_address = True

class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def end_headers(self):
        self.send_header('X-Robots-Tag', 'noindex, nofollow')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        super().end_headers()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default=str(HERE / 'checks/cms-site-v11'))
    parser.add_argument('--port', type=int, default=8793)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not root.is_relative_to((HERE / 'checks').resolve()) or root == (HERE / 'checks').resolve():
        raise SystemExit('Serve only a generated candidate below staging/checks')
    Server(('127.0.0.1', args.port), partial(Handler, directory=str(root))).serve_forever()
