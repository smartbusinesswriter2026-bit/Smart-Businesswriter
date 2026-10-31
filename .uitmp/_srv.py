import re
p = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\src\bp\server.py'
src = open(p, encoding='utf-8').read()
for m in re.finditer(r'^.*(index\.html|WEB_DIR|web_dir|HTML).*$', src, re.M):
    print(m.group(0).strip()[:160])
