"""Marketing shelf probe — inventory, resolution, records, contract, papers, figures.

Reproduce the measurements in the marketing manual.
"""

import sys
sys.path.insert(0, "src")

from bp.product import subjects, completion, framework_profiles
from bp import server, templates as T
from bp.methods import LIBRARY

SUBJECT = "marketing"

def main():
    detail = subjects.detail(SUBJECT)
    
    print("=" * 60)
    print(f"SHELF: {SUBJECT}")
    print("=" * 60)
    
    # Tools
    print(f"\nTOOLS ({len(detail['tools'])}):")
    for tool in detail['tools']:
        print(f"  {tool['key']}: preset={tool.get('preset')}, method={tool.get('method')}, group={tool.get('group')}, level={tool.get('level')}")
    
    # Worksheets
    print(f"\nWORKSHEETS ({len(detail['worksheets'])}):")
    for ws in detail['worksheets']:
        print(f"  {ws['key']}: group={ws.get('group')}, draftable={ws.get('draftable')}")
    
    # Tiles
    print(f"\nTILES ({len(detail['tiles'])}):")
    for tile in detail['tiles']:
        print(f"  {tile['key']}: label={tile['label']}, tools={len(tile['tools'])}, worksheets={len(tile['worksheets'])}, records={len(tile['records'])}")
        for tool in tile['tools']:
            print(f"    tool: {tool['key']}")
        for ws in tile['worksheets']:
            print(f"    ws: {ws['key']}")
        for rec in tile['records']:
            print(f"    rec: {rec['id']}")
    
    # Records
    print(f"\nRECORDS ({len(detail['records'])}):")
    for rec in detail['records']:
        methods = []
        for l in rec.get('linked_methods', []):
            if isinstance(l, dict):
                methods.append(l.get('method_id', ''))
            else:
                methods.append(str(l))
        print(f"  {rec['id']}: form={rec['form']}, status={rec['status_short']}, methods={methods}")
    
    # Catalogue
    print(f"\nCATALOGUE ({len(detail['catalogue'])}):")
    for cat in detail['catalogue']:
        print(f"  {cat['id']}: form={cat['form']}, status={cat['status_short']}")

if __name__ == "__main__":
    main()