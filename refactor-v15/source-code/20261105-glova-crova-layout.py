from pathlib import Path
from PIL import Image
from bs4 import BeautifulSoup
import json,copy,shutil,rjsmin
r=Path('projects/main-website/refactor-v03');p=r/'pages/ct-glova.html';backup=r/'checks/20261105-ct-glova-before-crova-layout.html';assert not backup.exists();shutil.copy2(p,backup)
def parse(n):return BeautifulSoup((r/'pages'/n).read_text(encoding='utf-8'),'html.parser')
old=parse('ct-glova.html');s=parse('ct-crova-254.html');data=json.loads((r/'checks/20261105-glova-sales-kit-source.json').read_text(encoding='utf-8'))['data'];a=Path(r'C:/Users/ASUS/.t3/userdata/attachments');paths=[]
for number,key in [('01','cd50247f'),('02','61785343'),('03','fc4ad58a')]:
 f=next(a.glob('*'+key+'*.png'));shutil.copy2(f,r/'source-inputs'/('20261105-glova-white-'+number+'.png'));im=Image.open(f);print(number,im.mode,im.size)
 for w in [480,800,1200]:
  out=im.copy();out.thumbnail((w,w));out.save(r/'assets/img'/f'ct-glova-white-{number}-{w}.webp',quality=82)
 paths.append('../assets/img/ct-glova-white-'+number+'-1200.webp')
def setimage(img,number):
 path=paths[number-1];im=Image.open(r/'assets/img'/Path(path).name);img['src']=path;img['srcset']=', '.join(path.replace('-1200.webp',f'-{w}.webp')+f' {w}w' for w in [480,800,1200]);img['width']=im.width;img['height']=im.height;img['alt']='CT-GLOVA UAV — view '+str(number);img['class']=['is-model'];img['loading']='lazy'
# Only the template is copied. All product text and figures are GLOVA-specific.
s.title.string='CT-GLOVA | CT UAV';s.select_one('.product-bar__identity strong').string='CT-GLOVA';s.select_one('.product-bar__identity').find_all('span')[-1].string='Drone Light Show'
heroimg=copy.deepcopy(old.select_one('.hero-section__image'));heroimg['loading']='eager';heroimg['fetchpriority']='high';s.select_one('.hero-section__image').replace_with(heroimg);s.select_one('.hero-role').string='Light show UAV';s.select_one('#product-title').string='CT-GLOVA'
metrics=s.select('.metric');values=[('1.8','kg','Gross Weight'),('25','min','Hovering time (10 m/s)'),('15','m/s','Flight Speed')]
s.select_one('.metrics')['aria-label']='CT-GLOVA key specifications'
for el,(value,unit,label) in zip(metrics,values):
 strong=el.find('strong');strong.clear();strong.append(value+' ');sp=s.new_tag('span');sp.string=unit;strong.append(sp);el.find('p').string=label
s.select_one('#applications-title').string='Drone Light Show';s.select_one('#applications .section-heading p:not(.section-kicker)').string=data['description'];setimage(s.select_one('#applications .application-image img'),1)
caption=s.select_one('#applications figcaption');caption.clear();caption.append('CT-GLOVA');tag=s.new_tag('span');tag.string='MODEL IMAGE';caption.append(tag)
lst=s.select_one('.application-list');template=copy.deepcopy(lst.select_one('.application-item'));lst.clear();titles=['Events and festivals','Brand and product presentations','Private celebrations','Tourism and entertainment','Multimedia performances']
for i,(title,text) in enumerate(zip(titles,data['functions'])):
 item=copy.deepcopy(template);item.find('span').string=f'{i+1:02}';item.find('h3').string=title;item.find('p').string=text;lst.append(item)
button=s.select_one('.applications-actions button');link=s.new_tag('a',href='#specifications',attrs={'class':button.get('class',[])});link.append('View specifications ');sp=s.new_tag('span',attrs={'aria-hidden':'true'});sp.string='↗';link.append(sp);button.replace_with(link)
s.select_one('#technology-title').string='Advanced technologies';ul=s.select_one('.technology-list');ul.clear()
for text in data['models'][0]['technologies']:
 li=s.new_tag('li');li.string=text;ul.append(li)
s.select_one('#specifications .specifications-heading > p:not(.section-kicker)').string='CT-GLOVA';s.select_one('#specifications table').replace_with(copy.deepcopy(old.select_one('#specifications table')))
s.select_one('#gallery-title').string='CT-GLOVA images';grid=s.select_one('.gallery-grid');figure=copy.deepcopy(grid.find('figure'));grid.clear()
for i in range(1,4):
 fig=copy.deepcopy(figure);setimage(fig.img,i);fig.select_one('figcaption span').string='CT-GLOVA';fig.select_one('small').string='MODEL IMAGE';grid.append(fig)
s.select_one('#contact .section-kicker').string='CT UAV / CT-GLOVA';s.select_one('#contact .contact-inner > div > p:not(.section-kicker)').string='Contact CT UAV for CT-GLOVA configurations and Drone Light Show planning.'
d=s.select_one('#payloadDialog');close=copy.deepcopy(s.select_one('#payloadClose'));d.clear();d.append(close)
for x in s.select('.review-bar'):x.decompose()
# Use the exact CROVA interaction controller, with GLOVA's contact product line.
source=(r/'assets/js/shared-script-083d426cd1d0.js').read_text(encoding='utf-8').replace('09 Agricultural UAV','06 Drone Light Show');(r/'assets/js/glova-crova-layout-v03.js').write_text(rjsmin.jsmin(source),encoding='utf-8');(r/'source-code/glova-crova-layout-v03.js').write_text(source,encoding='utf-8')
for script in s.select('script[src]'):
 if 'shared-script-083d426cd1d0' in script['src']:script['src']='../assets/js/glova-crova-layout-v03.js'
p.write_text(str(s),encoding='utf-8')
print('CROVA layout applied with sales-kit GLOVA copy and three supplied white images')
