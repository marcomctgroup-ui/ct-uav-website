"""Cache-safe names, 5 November 2026 (v05 r02).

Problem found on the free staging host (ctuav.betadrop.site, Cloudflare): script and style files
without a version code (page-loader.js, resource-loader.js, ...) keep the same name in every
upload. Browsers and the Cloudflare cache keep them for up to 4 hours, so after a new upload the
host served old v03 loaders next to new v05 scripts, and the 3D model could fail.

Fix: every JS/CSS file gets a content-hash name. References in HTML, JS and CSS are updated.
A hashed file whose content changes because of a reference update is renamed again, until stable.
Readable copies in source-code/ follow the delivery files. Run the header builder after this.
Before-copies of changed text files: checks/before-cache-safe-names/.
"""
import hashlib, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
bak = ROOT / 'checks/before-cache-safe-names'; bak.mkdir(parents=True, exist_ok=True)
INTERNAL = ('checks', 'source-code', 'source-inputs')
HASHED = re.compile(r'-([0-9a-f]{10,12})(-[a-z0-9]+)?\.(js|css)$')


def served_texts():
    out = [ROOT / 'index.html', *(ROOT / 'pages').glob('*.html'),
           *(ROOT / 'assets/js').glob('*.js'), *(ROOT / 'assets/css').glob('*.css')]
    out += [p for p in ROOT.glob('*/**/index.html') if p.relative_to(ROOT).parts[0] not in INTERNAL + ('assets', 'pages')]
    return [p for p in out if p.is_file()]


def h12(data):
    return hashlib.sha256(data).hexdigest()[:12]


def target_name(p):
    data = p.read_bytes()
    m = HASHED.search(p.name)
    stem = p.name[:m.start()] if m else p.name.rsplit('.', 1)[0]
    return f'{stem}-{h12(data)}.{p.suffix[1:]}'


renames = {}
def verified(p):
    m = HASHED.search(p.name)
    if not m:
        return False
    data = p.read_bytes()
    return any(f(data).hexdigest().startswith(m.group(1)) for f in (hashlib.sha256, hashlib.md5, hashlib.sha1))


# Files without a version code, and files whose code does not match their content (edited in place).
pending = [p for d in ('assets/js', 'assets/css') for p in sorted((ROOT / d).iterdir())
           if p.is_file() and not verified(p)]
for _ in range(10):
    if not pending:
        break
    step = {}
    for p in pending:
        new = target_name(p)
        if new != p.name:
            step[p.name] = new
            dest = p.with_name(new)
            if dest.exists():
                # Two files with identical bytes get one name; the duplicate is removed.
                if dest.read_bytes() != p.read_bytes():
                    raise SystemExit('STOP name clash with different content: ' + new)
                p.unlink()
            else:
                p.rename(dest)
            src = ROOT / 'source-code' / p.name
            if src.exists():
                src.unlink()
                shutil.copy2(p.with_name(new), ROOT / 'source-code' / new)
    renames.update(step)
    changed = []
    for t in served_texts():
        b = t.read_bytes(); s = b.decode('utf-8')
        n = s
        for old, new in step.items():
            n = re.sub(r'(?<![A-Za-z0-9_.-])' + re.escape(old) + r'(?![A-Za-z0-9_-])', new, n)
        if n != s:
            rel = t.relative_to(ROOT).as_posix().replace('/', '__')
            if not (bak / rel).exists():
                (bak / rel).write_bytes(b)
            t.write_bytes(n.encode('utf-8'))
            if t.suffix in ('.js', '.css'):
                changed.append(t)
                src = ROOT / 'source-code' / t.name
                if src.exists():
                    shutil.copy2(t, src)
    pending = changed
else:
    raise SystemExit('STOP: names did not become stable')

# Check: every served JS/CSS name token equals its content hash, and no old name remains.
for d in ('assets/js', 'assets/css'):
    for p in (ROOT / d).iterdir():
        if not verified(p):
            raise SystemExit('STOP not content-hashed ' + p.name)
all_text = '\n'.join(t.read_bytes().decode('utf-8') for t in served_texts())
left = [o for o in renames if re.search(r'(?<![A-Za-z0-9_.-])' + re.escape(o) + r'(?![A-Za-z0-9_-])', all_text)]
if left:
    raise SystemExit('STOP old names still referenced: ' + ', '.join(left))
print(len(renames), 'renamed')
for o, n in renames.items():
    print(' ', o, '->', n)
