from pathlib import Path
import zipfile,json,hashlib
r=Path('projects/main-website/refactor-v03');out=Path('projects/main-website/exports/20261105-ctuav-main-website-v03.zip');out.parent.mkdir(exist_ok=True);assert not out.exists()
files=[r/'index.html',r/'_headers']+[p for folder in ['assets','pages'] for p in (r/folder).rglob('*') if p.is_file()]
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:z.write(p,p.relative_to(r).as_posix())
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None;names=z.namelist();assert 'index.html' in names and '_headers' in names;assert all(n.startswith(('assets/','pages/')) or n in ['index.html','_headers'] for n in names)
 target=r/'checks/20261105-zip-validation';assert not target.exists();z.extractall(target)
manifest={'archive':str(out),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'files':len(files),'internal_notes_excluded':True,'root_entry':'index.html','source_hashes':{p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
(r/'checks/20261105-zip-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print('ZIP',out.stat().st_size,'bytes',len(files),'files; CRC passed')
