"""Apply the Batch 1 code changes to the readable copies in source-code/ and rename them to the new delivery names."""
import re, sys
from pathlib import Path
src = Path(__file__).resolve().parent
def loose(old):
    return re.compile(r'\s*'.join(re.escape(c) for c in old if not c.isspace()))
D_OLD = "const bytes=Uint8Array.from(atob(data),c=>c.charCodeAt(0));"
D_NEW = "const bytes=typeof data==='string'?Uint8Array.from(atob(data),c=>c.charCodeAt(0)):new Uint8Array(data);"
M_OLD = "if(source)return source.textContent.trim();"
M_NEW = "if(source)return source.ctuavBytes||source.textContent.trim();"
plan = {
 'shared-script-3029b0a74f02.js': ('shared-script-bac24ddbcb61.js', 'COPY'),
 'ctencyscript-8cf4c5ebaf22.js': ('ctencyscript-eb34eac6a0c9.js', [(
   "document.querySelectorAll('iframe').forEach(f=>{watchFrame(f);f.addEventListener('load',()=>{watchFrame(f);if(f===activeFrame()){modal();later(400);setTimeout(()=>later(0),2400)}})});",
   "const ctWatch=f=>{watchFrame(f);f.addEventListener('load',()=>{watchFrame(f);if(f===activeFrame()){modal();later(400);setTimeout(()=>later(0),2400)}})};\ndocument.querySelectorAll('iframe').forEach(ctWatch);\n// Page frames are created on demand (Batch 1, v04).\ndocument.addEventListener('ctuav:frame',ev=>ctWatch(ev.detail));")]),
 'ctencymascotengine-d0c6d79f4b88.js': ('ctencymascotengine-b2eac36087de.js', [(
   "data=b64bytes(text('ctEncyModel'));",
   "var mn=document.getElementById('ctEncyModel');data=mn&&mn.ctuavBytes?mn.ctuavBytes.buffer.slice(0):b64bytes(text('ctEncyModel'));")]),
 'shared-script-269b807a4894.js': ('shared-script-1410cd0c4244.js', [(M_OLD, M_NEW), (D_OLD, D_NEW)]),
 'shared-script-374445ec9d83.js': ('shared-script-f5b69f661722.js', [(M_OLD, M_NEW), (D_OLD, D_NEW)]),
 'shared-script-6b26a41a7755.js': ('shared-script-147dde031892.js', [(M_OLD, M_NEW), (D_OLD, D_NEW)]),
 'shared-script-a784b66ff68a.js': ('shared-script-72c298408fef.js', [(M_OLD, M_NEW), (D_OLD, D_NEW)]),
 'shared-script-8fbf3c17f301.js': ('shared-script-8fa5ef83d2b3.js', [(
   "return parentElement('uav3dModel-'+key)?.textContent.trim()||null;}",
   "const n=parentElement('uav3dModel-'+key);return n?.ctuavBytes||n?.textContent.trim()||null;}"), (D_OLD, D_NEW)]),
 'shared-script-73886e44d624.js': ('shared-script-1052bc532e17.js', 'APPEND'),
}
delivery = src.parent / 'assets' / 'js'
for old, (new, steps) in plan.items():
    p = src / old
    if not p.exists():
        sys.exit(f'STOP: {old} missing')
    if steps == 'COPY':
        text = (delivery / new).read_text(encoding='utf-8')
    elif steps == 'APPEND':
        d = (delivery / new).read_text(encoding='utf-8')
        tail = d[d.rfind("\n(()=>{const run=()=>document.querySelectorAll('#productRail"):]
        text = p.read_text(encoding='utf-8').rstrip() + "\n// Product rail images load on first menu intent (Batch 1, v04).\n" + tail.lstrip('\n')
    else:
        text = p.read_text(encoding='utf-8')
        for o, n in steps:
            text, k = loose(o).subn(lambda m: n, text)
            if k != 1:
                sys.exit(f'STOP: {old}: {k} matches for {o[:40]}')
    (src / new).write_text(text, encoding='utf-8', newline='')
    p.unlink()
    print(old, '->', new)
