src = open("qa/manual/probe_complex.py").read()
start = src.find('TEXT = """')
end = src.find('"""', start + 8)
text = src[start+8:end]
import re
_is_statement_prep = bool(re.search(
    r"prepare\s+(?:the\s+)?(?:income\s+statement|balance\s+sheet|statement\s+of\s+cash\s+flows|classified\s+balance\s+sheet)",
    text, re.I))
print("is_statement_prep:", _is_statement_prep)
from bp.product import financial_computations as fc
print("detect_sections:", fc.detect_sections(text))
