"""Keep the language toggle's label under its own controller, not generic i18n."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'checks/20261105-visual-refinement'
index=ROOT/'index.html';text=index.read_text(encoding='utf8')
old='class="language-button" id="languageButton"'
new='class="language-button" data-i18n-skip="" id="languageButton"'
assert text.count(old)==1
shutil.copy2(index,OUT/'index-before-label-fix.html')
index.write_text(text.replace(old,new),encoding='utf8',newline='')
p=ROOT/'assets/js/shared-script-96ab1a036400.js';text=p.read_text(encoding='utf8')
old='languageButton.setAttribute("aria-label",next==="en"?"Change language to Vietnamese":"Chuyển sang tiếng Anh");renderProducts();showStatus();}'
new='renderProducts();showStatus();languageButton.setAttribute("aria-label",next==="en"?"English. Change language to Vietnamese":"Tiếng Việt. Chuyển sang tiếng Anh");}'
assert text.count(old)==1
shutil.copy2(p,OUT/'nav-script-before-label-fix.js')
text=text.replace(old,new);p.write_text(text,encoding='utf8',newline='')
(ROOT/'source-code'/p.name).write_text(text,encoding='utf8',newline='')
print('Language button now owns its current-language and switch-action label.')
