"""Do not turn malformed workbook column positions into technical claims."""
from pathlib import Path
import json, html
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];CHECK=ROOT/'checks/20261105-components-navbar-model'
ledger=json.loads((CHECK/'source-record.json').read_text(encoding='utf8'))
data_path=ROOT/'assets/js/shared-script-6b2b16428671.js'
data=json.loads(data_path.read_text(encoding='utf8').split('=',1)[1].strip().rstrip(';'))
by_id={p['id']:p for p in data};flags=[]
en='Some workbook specification columns are inconsistent. The remaining specification fields need confirmation from CT UAV.'
vi='Một số cột thông số trong bảng tính không nhất quán. Các trường thông số còn lại cần được CT UAV xác nhận.'
for rec in ledger['records']:
    m=rec['match']
    if not m or m['sheet']!='Pin':continue
    item=by_id[rec['id']]
    if item['category'] not in ['Intelligent Battery','Smart BMS','Smart Charger']:continue
    raw=m.get('raw_values',m['values'])
    allowed={'Category','Cell Config','Voltage','Capacity','Energy'} if item['category']=='Intelligent Battery' else {'Category'}
    safe=[[k,v] for k,v in raw if k in allowed]
    m['raw_values']=raw;m['values']=safe
    m['field_alignment']='PENDING CONFIRMATION: shifted or inconsistent workbook column labels; ambiguous values are not published.'
    item['specs']=safe
    rec['field_alignment_pending']=True
    page=ROOT/'pages'/('component-'+item['id']+'.html')
    s=BeautifulSoup(page.read_text(encoding='utf8'),'html.parser');sec=s.select_one('#specifications');dl=sec.select_one('dl')
    for div in list(dl.find_all('div',recursive=False)):
        if div.dt.get('data-en',div.dt.text) not in allowed:div.decompose()
    if not sec.select_one('.source-confirmation'):
        p=s.new_tag('p',attrs={'class':'source-confirmation','data-en':en,'data-vi':vi});p.string=en;sec.append(p)
    page.write_text(str(s),encoding='utf8');flags.append(item['name'])
text='window.CTComponents='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';'
data_path.write_text(text,encoding='utf8');(ROOT/'source-code'/data_path.name).write_text(text,encoding='utf8')
ledger['workbook_field_alignment_pending']=flags
(CHECK/'source-record.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'field_alignment_pending':flags}))
