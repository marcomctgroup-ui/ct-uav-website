"""Batch 6 step A/B (loading), 5 November 2026. Haykal: "Do A and B".

1. Hero videos: 720p phone versions (H.264, CRF 27, no audio, faststart) from the current hero files.
   hero.html gets data-video-src-small. Desktop keeps the original files.
2. page-loader: a video URL is set only after window load + 1.2 s. Until then the poster shows.
   A queued video that is paused before then is removed from the queue. Screens up to 900 px wide use
   the small file when one exists.
3. Router: at most 4 page frames stay in memory. The oldest frame that is not shown is removed and
   is created again from the template when the visitor returns.
Measured: blur and filter effects gave no scroll gain (checks/20261105-batch6/scroll-*.json), so the
glass look is unchanged.
Run 20261105-cache-safe-names.py and the header builder after this script.
Usage: python 20261105-batch6-loading-build.py <folder with *-720.mp4 files>"""
import hashlib, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VID = Path(sys.argv[1])
BAK = ROOT / 'checks/before-batch6'; BAK.mkdir(parents=True, exist_ok=True)


def once(s, old, new, label):
    if s.count(old) != 1:
        raise SystemExit(f'STOP {label}: {s.count(old)}')
    return s.replace(old, new)


# 1. Phone videos.
hero = ROOT / 'pages/hero.html'; shutil.copy2(hero, BAK / 'hero.html')
h = hero.read_bytes().decode('utf-8')
for v in ['decarb54-ce9bf3be66', 'ct-fyran-256-f0cafcc742-web', 'ct-frona-44-6312c7b4e1', 'ct-skysilk-e90dea1c7c-web']:
    data = (VID / f'{v}-720.mp4').read_bytes()
    stem = re.sub(r'-[0-9a-f]{10}(-web)?$', '', v)
    name = f'{stem}-720-{hashlib.sha256(data).hexdigest()[:12]}.mp4'
    (ROOT / 'assets/video' / name).write_bytes(data)
    h = once(h, f'data-video-src="../assets/video/{v}.mp4"',
             f'data-video-src="../assets/video/{v}.mp4" data-video-src-small="../assets/video/{name}"', v)
    print(v, '->', name, len(data))
hero.write_bytes(h.encode('utf-8'))

# 2. Page loader.
pl = next((ROOT / 'assets/js').glob('page-loader-*.js'))
shutil.copy2(pl, BAK / pl.name)
s = pl.read_bytes().decode('utf-8')
old = ("HTMLMediaElement.prototype.play=function(){if(this.dataset.videoSrc&&!this.getAttribute('src')){this.src=this.dataset.videoSrc;this.load()}return play.apply(this,arguments)};")
new = ("const pause=HTMLMediaElement.prototype.pause,small=matchMedia('(max-width: 900px)').matches,queue=[];let videoReady=document.readyState==='complete';\n"
       " // Batch 6: video files load after the page is ready; the poster shows first. Phones get the 720p file.\n"
       " const flush=()=>{videoReady=true;queue.splice(0).forEach(v=>v.play().catch(()=>{}))};\n"
       " if(!videoReady)addEventListener('load',()=>setTimeout(flush,1200),{once:true});\n"
       " HTMLMediaElement.prototype.pause=function(){const i=queue.indexOf(this);if(i>=0)queue.splice(i,1);return pause.apply(this,arguments)};\n"
       " HTMLMediaElement.prototype.play=function(){if(this.dataset.videoSrc&&!this.getAttribute('src')){if(!videoReady){if(!queue.includes(this))queue.push(this);return Promise.resolve()}"
       "this.src=(small&&this.dataset.videoSrcSmall)||this.dataset.videoSrc;this.load()}return play.apply(this,arguments)};")
s = once(s, old, new, 'page-loader play')
pl.write_bytes(s.encode('utf-8'))

# 3. Router frame limit.
idx = (ROOT / 'index.html').read_bytes().decode('utf-8')
router = ROOT / 'assets/js' / re.findall(r'assets/js/(shared-script-[0-9a-f]{12}\.js)', idx)[1]
shutil.copy2(router, BAK / router.name)
r = router.read_bytes().decode('utf-8')
r = once(r, 'function showRoute(next){', 'let recentFrames=[];function showRoute(next){', 'router recent')
r = once(r, "if(route!=='home'&&!loaded.has(route)){loaded.add(route);frameFor(route);}",
         "if(route!=='home'&&!loaded.has(route)){loaded.add(route);frameFor(route);}"
         "if(route!=='home'){recentFrames=recentFrames.filter(n=>n!==route);recentFrames.push(route);"
         "while(recentFrames.length>4){const old=recentFrames.shift();const f=frames[old];if(f){f.remove();delete frames[old];}loaded.delete(old);ready.delete(old);}}",
         'router limit')
router.write_bytes(r.encode('utf-8'))
print('page-loader and router updated')
