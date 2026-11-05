p = "src/bp/product/schedules.py"
text = open(p).read()
# Rename the dict definition
text = text.replace("SCHEMAS = {\n", "_SCHEMAS_SEED = {\n", 1)
# Rename the entry additions
text = text.replace('SCHEMAS["asset_disposal"]', '_SCHEMAS_SEED["asset_disposal"]')
text = text.replace('SCHEMAS["ratio_computation"]', '_SCHEMAS_SEED["ratio_computation"]')
# Add wiring after the last seed entry. The seed block ends before TRIAL_BALANCE_MARK.
marker = "TRIAL_BALANCE_MARK = re.compile"
wiring = "from . import tier1_tables as _t1\nSCHEMAS = _t1.SCHEMAS\n\n"
text = text.replace(marker, wiring + marker, 1)
open(p, "w").write(text)
print("done")
import ast; ast.parse(open(p).read()); print("syntax OK")
