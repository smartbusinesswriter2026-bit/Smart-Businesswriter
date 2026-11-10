html = open('web/admin-sbw.html', encoding='utf-8').read()
# Find the autoresearch button area and replace the mess
import re
# Replace everything from data-panel="autoresearch" to the next </button>
pattern = r'data-panel="autoresearch">.*?</button>'
replacement = 'data-panel="autoresearch">Autoresearch</button>'
html = re.sub(pattern, replacement, html, count=1, flags=re.DOTALL)
open('web/admin-sbw.html', 'w', encoding='utf-8').write(html)
print("done")