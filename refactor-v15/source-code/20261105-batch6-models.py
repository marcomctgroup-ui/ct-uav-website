"""Batch 6 step B (3D models), 5 November 2026. Haykal: "Do A and B" (B = compress model files).
gltf-transform 4.5.1 `meshopt --level medium` (EXT_meshopt_compression + KHR_mesh_quantization).
The product viewer already sets the Meshopt decoder. Shapes, materials and nodes are kept.
Only models that become smaller are replaced: CT-FRYAN (Firefighting) and CT-FRONA 44.
CT-FYRAN 256, CT-PEGAS 230 and DECARB 54 were already meshopt-compressed and stay unchanged.
Original GLB files are moved to checks/before-batch6/ (not deleted)."""
import hashlib, re, shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TMP = Path(sys.argv[1])
bak = ROOT / 'checks/before-batch6'
texts = [ROOT / 'index.html', *(ROOT / 'pages').glob('*.html'), *(ROOT / 'assets/js').glob('*.js')]
texts += [p for p in ROOT.glob('*/**/index.html') if p.relative_to(ROOT).parts[0] not in ('checks', 'source-code', 'source-inputs', 'assets', 'pages')]
for old in ['ct-fyran-firefighting-40293a020e74.glb', 'ct-frona-44-32a1f01d6f.glb']:
    data = (TMP / old).read_bytes()
    new = re.sub(r'-[0-9a-f]{10,12}\.glb$', '', old) + '-' + hashlib.sha256(data).hexdigest()[:12] + '.glb'
    (ROOT / 'assets/models' / new).write_bytes(data)
    shutil.move(str(ROOT / 'assets/models' / old), str(bak / old))
    n = 0
    for t in texts:
        b = t.read_bytes()
        if old.encode() in b:
            t.write_bytes(b.replace(old.encode(), new.encode())); n += 1
    print(old, '->', new, len(data), 'bytes; references updated in', n, 'files')
