import shutil, os

web = r"d:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\index.html"
bak = web + ".bak-tileclose"

# Step 0: Prove backup exists and restore if needed
if os.path.exists(bak):
    print("Backup exists - restoring...")
    shutil.copy2(bak, web)
    print("Backup restored to index.html")
else:
    print("NO backup found!")

# Verify tile-close-shim is NOT in the file
with open(web, 'r') as f:
    content = f.read()

if 'tile-close-shim' in content:
    print("ERROR: tile-close-shim already present - patch was applied")
else:
    print("Good: tile-close-shim NOT present - clean state")