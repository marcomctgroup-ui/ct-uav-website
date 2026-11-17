from pathlib import Path
from bs4 import BeautifulSoup
import json,shutil
r=Path('projects/main-website/refactor-v03');data=json.loads((r/'checks/20261105-glova-sales-kit-source.json').read_text(encoding='utf-8'))['data'];model=data['models'][0];p=r/'pages/ct-glova.html';bak=r/'checks/20261105-ct-glova-before-saleskit.html';assert not bak.exists();shutil.copy2(p,bak);shutil.copy2(r/'index.html',r/'checks/20261105-index-before-glova-saleskit.html');s=BeautifulSoup(p.read_text(encoding='utf-8'),'html.parser')
s.select_one('.glova-model-overview .section-heading p:not(.section-kicker)').string=data['description']
lst=s.select_one('#applications .application-list');lst.clear()
for i,text in enumerate(data['functions']):
 item=s.new_tag('div',attrs={'class':'application-item'});num=s.new_tag('span');num.string=f'{i+1:02}';div=s.new_tag('div');h=s.new_tag('h3');h.string=text;div.append(h);item.extend([num,div]);lst.append(item)
wrap=s.select_one('#specifications .specifications-table-wrap');wrap.clear();table=s.new_tag('table',attrs={'class':'specifications-table'});cap=s.new_tag('caption',attrs={'class':'screen-reader-only'});cap.string='CT-GLOVA technical specifications';table.append(cap);body=s.new_tag('tbody')
for k,v in model['specs']:
 row=s.new_tag('tr');th=s.new_tag('th',scope='row');th.string=k;td=s.new_tag('td');td.string=v;row.extend([th,td]);body.append(row)
table.append(body);wrap.append(table)
tech=s.new_tag('section',attrs={'class':'technology-section','id':'technology','aria-labelledby':'technology-title'});inner=s.new_tag('div',attrs={'class':'page-width technology-inner'});heading=s.new_tag('div',attrs={'class':'technology-heading'});k=s.new_tag('p',attrs={'class':'section-kicker'});k.string='03 / TECHNOLOGY';h=s.new_tag('h2',id='technology-title');h.string='Advanced technologies';heading.extend([k,h]);ul=s.new_tag('ul',attrs={'class':'technology-list'})
for t in model['technologies']:
 li=s.new_tag('li');li.string=t;ul.append(li)
inner.extend([heading,ul]);tech.append(inner);s.select_one('#specifications').insert_before(tech)
nav=s.select_one('.product-nav');a=s.new_tag('a',href='#technology');a.string='Technology';nav.select_one('[href="#specifications"]').insert_before(a)
s.select_one('#specifications .section-kicker').string='04 / SPECIFICATIONS';s.select_one('#gallery .section-kicker').string='05 / GALLERY'
p.write_text(str(s),encoding='utf-8')
# Product-only copy uses the existing translation mechanism. Numeric values remain exactly as supplied.
p=r/'index.html';doc=BeautifulSoup(p.read_text(encoding='utf-8'),'html.parser');node=doc.select_one('#i18nVi');d=json.loads(node.string)
translations={data['description']:'Giải pháp hiện đại, thân thiện với môi trường thay thế pháo hoa cho lễ hội, hoạt động thương hiệu, sự kiện riêng, du lịch và trình diễn đa phương tiện.','Advanced technologies':'Công nghệ tiên tiến','Technology':'Công nghệ',data['functions'][0]:'Sự kiện lớn, lễ hội, đếm ngược và lễ khai mạc',data['functions'][1]:'Ra mắt thương hiệu, giới thiệu sản phẩm, sự kiện bất động sản, ô tô và công nghệ',data['functions'][2]:'Lễ kỷ niệm riêng và sự kiện cao cấp',data['functions'][3]:'Chương trình du lịch và giải trí',data['functions'][4]:'Kết hợp âm nhạc, laser và pháo hoa điện tử để tạo hiệu ứng 4D',model['technologies'][0]:'Đèn LED RGB công suất cao',model['technologies'][1]:'Mô-đun định vị GPS/RTK',model['technologies'][2]:'Phần mềm điều khiển bay đội hình',model['technologies'][3]:'Công nghệ bầy đàn','Dimensions':'Kích thước','Number of Rotors':'Số rotor','Gross Weight':'Khối lượng toàn bộ','Max Control Range':'Phạm vi điều khiển tối đa','CT-GLOVA technical specifications':'Thông số kỹ thuật CT-GLOVA','0 - 15 km (unobstructed)':'0 - 15 km (không có vật cản)','25 minutes (10 m/s)':'25 phút (10 m/s)','4 Rotors':'4 rotor'}
# Do not replace translations already used by other products.
for k,v in translations.items():d.setdefault(k,v)
node.string=json.dumps(d,ensure_ascii=False,separators=(',',':'));p.write_text(str(doc),encoding='utf-8')
print('Same GLOVA page updated',len(model['specs']),'specifications',len(model['technologies']),'technologies',len(data['functions']),'functions; HTML',p.stat().st_size)
