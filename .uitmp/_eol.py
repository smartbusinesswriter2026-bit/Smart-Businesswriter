p = r'D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\index.html'
raw = open(p, 'rb').read()
print('bytes', len(raw))
print('CRLF count', raw.count(b'\r\n'), 'bare LF', raw.count(b'\n') - raw.count(b'\r\n'))
