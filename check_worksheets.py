import sys
sys.path.insert(0, 'src')
from bp.product import subjects
page = subjects.detail('finance')
print('Finance worksheets:')
for w in page['worksheets']:
    print(f'  - {w["key"]}: {w["label"]}')
    print(f'    template: {w["template"]}')
    print()
