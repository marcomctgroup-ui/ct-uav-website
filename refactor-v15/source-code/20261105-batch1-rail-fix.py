"""Fix guardian blocking item 1 (5 Nov 2026): Navbar rail rebuild must use the deferred image URLs."""
import hashlib, re, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
pairs = [(root/'assets/js/shared-script-1052bc532e17.js', True), (root/'source-code/shared-script-1052bc532e17.js', False)]
def loose(old):
    return re.compile(r'\s*'.join(re.escape(c) for c in old if not c.isspace()))
R = [
 ("[\"ct-decarb.png\",\"ct-fyran.png\",\"ct-crova.png\",\"ct-camel.png\",\"ct-garon.png\"][index],image.src]",
  "[\"ct-decarb.png\",\"ct-fyran.png\",\"ct-crova.png\",\"ct-camel.png\",\"ct-garon.png\"][index],image.dataset.deferSrc?new URL(image.dataset.deferSrc,document.baseURI).href:image.src]"),
 ("image.src=embeddedProductImages[product.image];",
  "if(window.ctuavRailReady)image.src=embeddedProductImages[product.image];else image.dataset.deferSrc=embeddedProductImages[product.image];"),
 ("const run=()=>document.querySelectorAll('#productRail img[data-defer-src]')",
  "const run=()=>{window.ctuavRailReady=true;document.querySelectorAll('#productRail img[data-defer-src]')"),
 ("i.removeAttribute('data-defer-srcset')});['productsToggle'",
  "i.removeAttribute('data-defer-srcset')})};['productsToggle'"),
]
for p, _ in pairs:
    s = p.read_text(encoding='utf-8')
    for o, n in R:
        s, k = loose(o).subn(lambda m: n, s)
        if k != 1: sys.exit(f'STOP {p.name}: {k} matches for {o[:50]}')
    p.write_text(s, encoding='utf-8', newline='')
d = pairs[0][0]
new = d.with_name('shared-script-' + hashlib.sha256(d.read_bytes()).hexdigest()[:12] + '.js')
d.rename(new); pairs[1][0].rename(root/'source-code'/new.name)
idx = root/'index.html'; t = idx.read_text(encoding='utf-8')
if t.count(d.name) != 1: sys.exit('STOP index reference')
idx.write_text(t.replace(d.name, new.name), encoding='utf-8', newline='')
print(d.name, '->', new.name)
