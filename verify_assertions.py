with open('d:\\SMART BUSINESSWRITER\\business_pipeline_v0.12\\business_pipeline\\web\\index.html', 'rb') as f:
    c = f.read().decode('utf-8', errors='replace')
bootAt = c.indexOf('function boot(')
shimAt = c.indexOf('<script id="tile-close-shim">')
shimClose = c.indexOf('</script>', shimAt)
bodyAt = c.indexOf('</body>', shimAt)
import re
shim_count = len(re.findall('tile-close-shim', c))
print('A1:', shimAt > bootAt)
print('A2:', shimClose > shimAt and shimClose < bodyAt)
print('A3:', shim_count == 1)
all_ok = (shimAt > bootAt) and (shimClose > shimAt and shimClose < bodyAt) and (shim_count == 1)
print('ALL:', all_ok)