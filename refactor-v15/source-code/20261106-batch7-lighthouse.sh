#!/usr/bin/env bash
# Batch 7: three Lighthouse 13.6.0 mobile runs (default mobile, simulated throttling), same setup as v06.
# Local laboratory test on the 8766 review server. Run when no other browser test is running.
# 6 Nov 2026: from Git Bash, Edge failed to start ("waiting for dynamic debugging port"). The three runs were made
# with the same node command from PowerShell (CHROME_PATH = C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe);
# the summary block below was then run on the saved JSON files.
set -u
LH="$HOME/AppData/Local/npm-cache/_npx/0f94ee7615faf582/node_modules/lighthouse/cli/index.js"
OUT="$(cd "$(dirname "$0")/.." && pwd)/checks/20261106-batch7"
export CHROME_PATH="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
for i in 1 2 3; do
  node "$LH" "http://127.0.0.1:8766/refactor-v07/" --quiet --output=json \
    --output-path="$OUT/lighthouse-mobile-run$i.json" --chrome-flags="--headless=new" || echo "run $i failed"
done
python - "$OUT" <<'EOF'
import json, sys
from pathlib import Path
out = Path(sys.argv[1]); rows = []
for i in (1, 2, 3):
    d = json.loads((out / f'lighthouse-mobile-run{i}.json').read_text(encoding='utf-8'))
    items = d['audits']['network-requests']['details']['items']
    video = sum(x.get('transferSize', 0) for x in items if (x.get('mimeType') or '').startswith('video/') or x['url'].endswith('.mp4'))
    total = sum(x.get('transferSize', 0) for x in items)
    c = d['categories']
    rows.append({'perf': round(c['performance']['score'] * 100), 'a11y': round(c['accessibility']['score'] * 100),
                 'bp': round(c['best-practices']['score'] * 100), 'seo': round(c['seo']['score'] * 100),
                 'lcp': round(d['audits']['largest-contentful-paint']['numericValue']), 'tbt': round(d['audits']['total-blocking-time']['numericValue']),
                 'nv': total - video, 'video': video, 'warn': len(d.get('runWarnings', []))})
(out / 'lighthouse-summary.json').write_text(json.dumps(rows, indent=1), encoding='utf-8')
print(json.dumps(rows))
EOF
