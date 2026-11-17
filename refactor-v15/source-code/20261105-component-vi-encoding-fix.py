"""Write new Vietnamese strings directly from UTF-8 source, not a shell pipe."""
from pathlib import Path
import json
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'assets/js/shared-script-c650fa76d9e4.js'
t=p.read_text(encoding='utf8');start=t.index('const viCats=')+len('const viCats=');end=t.index(';let lang',start)
cats=json.loads(t[start:end])
cats.update({'HVLi Pouch':'Pin túi HVLi','Intelligent Battery':'Pin thông minh','LiPo Pouch':'Pin túi LiPo','Semi-Solid Cell':'Cell bán rắn','Semi-Solid HV Pack':'Bộ pin bán rắn cao áp','Semi-Solid Pack':'Bộ pin bán rắn','Smart BMS':'BMS thông minh','Smart Charger':'Bộ sạc thông minh','Ground Controller':'Bộ điều khiển mặt đất','Rescue & Firefighting':'Cứu hộ & chữa cháy','EO-IR':'EO-IR','Gimbal & Mount':'Gimbal & giá đỡ','Payload Delivery':'Thiết bị thả hàng'})
t=t[:start]+json.dumps(cats,ensure_ascii=False,separators=(',',':'))+t[end:]
p.write_text(t,encoding='utf8');(ROOT/'source-code'/p.name).write_text(t,encoding='utf8')
a=json.loads((ROOT/'checks/20261105-components-navbar-model/source-record.json').read_text(encoding='utf8'))
for rec in a['records']:
    p=ROOT/'pages'/('component-'+rec['id']+'.html');s=BeautifulSoup(p.read_text(encoding='utf8'),'html.parser')
    for row in s.select('#specifications dl > div'):
        if row.dt.get('data-en',row.dt.text)=='Status':
            dd=row.dd;dd['data-en']=dd.text;dd['data-vi']={'Production':'Sản xuất','Production / R&D':'Sản xuất / R&D'}.get(dd.text,dd.text)
    p.write_text(str(s),encoding='utf8')
p=ROOT/'pages/uav-components.html';s=BeautifulSoup(p.read_text(encoding='utf8'),'html.parser');lead=s.select_one('.intro .lead')
lead['data-en']='Browse propulsion, electronics, batteries, ground controllers and payloads.'
lead['data-vi']='Khám phá hệ động lực, thiết bị điện tử, pin, bộ điều khiển mặt đất và thiết bị mang.'
lead.string=lead['data-en'];p.write_text(str(s),encoding='utf8')
print('Updated UTF-8 category, status and catalogue introduction text.')
