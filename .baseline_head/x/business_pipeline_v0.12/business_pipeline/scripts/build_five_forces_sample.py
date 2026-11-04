"""Five Forces + break-even sample for the stress case."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from build_sample_paper import add_page_number, body, double, heading, reference

TITLE = "Acquiring a Saudi Cold-Chain Provider: A Five Forces and Break-even Analysis"
OUT = Path(__file__).resolve().parents[3] / "samples"

SECTIONS = [
    ("Introduction", 1, [
        "The decision under analysis is whether a mid-sized grocery chain should acquire a cold-chain logistics "
        "provider in Saudi Arabia. The paper argues that the acquisition is financially plausible only if expected "
        "volume clears break-even with a margin of safety and buyer and supplier pressure can be contained; otherwise "
        "the chain should not proceed. Five Forces assesses industry attractiveness, and break-even tests the declared "
        "cost structure. The financial inputs are case assumptions, not audited company data.",
    ]),
    ("Five Forces", 1, [
        "The industry is assessed through five pressures that determine whether the acquisition can earn a return.",
    ]),
    ("Industry rivalry", 2, [
        "Saudi grocery retail is competitive and increasingly omnichannel. Alsaid and Almesha (2023) show that the "
        "omnichannel customer experience shapes grocery choice, while Alflayyeh and Naeem (2021) find that store "
        "environment and retailscape affect how shoppers evaluate grocery stores. E-grocery adoption adds another "
        "front: Alsulaimani (2024) identifies consumer intention as a key condition for online grocery use. For an "
        "acquirer, rivalry means pressure on price, service and delivery speed, not only store location.",
    ]),
    ("Threat of new entrants", 2, [
        "Barriers are moderate. A grocery entrant needs sites, supplier relationships and a delivery network, but "
        "e-grocery lowers the cost of reaching customers. The cold-chain asset itself is a barrier once acquired: "
        "Khalilpoor et al. (2026) show that perishable supply chains depend on coordinated sourcing, inventory and "
        "location decisions. The acquisition would buy capability rather than build it, which raises the strategic "
        "value of the target but also the price.",
    ]),
    ("Threat of substitutes", 2, [
        "Substitutes are strong and varied. Consumers can use traditional markets, discount stores, direct-to-consumer "
        "suppliers and meal delivery instead of a full grocery basket. Malik and Bustami (2023) show that demand and "
        "supply factors differ across Saudi sectors, so a grocery format cannot assume the same loyalty as other retail "
        "categories. The acquirer would need clear service differentiation, not only a larger delivery fleet.",
    ]),
    ("Buyer power", 2, [
        "Buyer power is moderate to high. Consumers are price-sensitive and compare formats, and modern retail buyers "
        "can concentrate volume in a few chains. Asiri et al. (2024) show that operational risks affect customer "
        "satisfaction in Saudi grocery retail; a late or spoiled delivery is visible to the buyer immediately. That "
        "visibility strengthens buyer power because switching costs are low for a single basket.",
    ]),
    ("Supplier power", 2, [
        "Supplier power is moderate to high in cold chain. Capacity, fuel, labour and imported food all constrain the "
        "system, and a dedicated cold-chain provider has specialised assets that are not easily replaced. Khalilpoor "
        "et al. (2026) emphasise coordinated sourcing and location decisions for perishable dairy; the same logic "
        "applies to a grocery chain's fresh and frozen ranges. A supplier with scarce capacity can negotiate better "
        "terms, especially during peak demand.",
    ]),
    ("Financial Feasibility", 1, [
        "The break-even calculation tests the declared cost structure at the proposed price.",
    ]),
    ("Break-even Analysis", 2, [
        "At a declared fixed cost of 2,000,000, a price of 40 per unit and a variable cost of 28 per unit, the "
        "break-even quantity is 166,666.67 units and the break-even revenue is 6,666,666.67. The contribution margin is "
        "12 per unit, or 30.0% of the price. At the declared expected volume of 250,000 units, the margin of safety is "
        "83,333.33 units. On these figures, expected volume is about 50% above break-even, and a one-third shortfall in "
        "volume would reach the break-even point. The result is sensitive to the declared price and variable cost; a "
        "lower price or a higher variable cost would raise the required volume.",
    ]),
    ("Discussion", 1, []),
    ("Integration of Five Forces and Break-even", 2, [
        "Five Forces and break-even answer different parts of the same decision. Five Forces shows that rivalry, "
        "substitutes and supplier power could compress price and volume; break-even shows how much volume cushion the "
        "declared price and cost structure provide. The cushion is meaningful but not generous: it depends on reaching "
        "250,000 units while holding a 30% contribution margin. If buyer pressure forces a lower price or cold-chain "
        "costs rise, the break-even quantity moves up and the margin of safety narrows. Financial feasibility is "
        "therefore necessary but not sufficient.",
    ]),
    ("Implications", 2, [
        "The chain should proceed only to due diligence, not straight to acquisition. It should verify the target's "
        "cold-chain utilisation, contract terms with suppliers and the durability of buyer demand at the declared price. "
        "A staged acquisition or a long-term supply agreement would limit exposure while preserving the option to "
        "complete. If the expected volume cannot be supported by contracts or a credible forecast, the break-even "
        "cushion is not enough to justify the purchase.",
    ]),
    ("Limitations", 2, [
        "The fixed cost, price, variable cost and expected volume are declared case assumptions, not audited figures. "
        "The break-even model assumes a constant unit contribution and does not forecast demand, tax, financing cost or "
        "synergies. The industry sources describe the Saudi grocery context but do not value this target.",
    ]),
    ("Conclusion", 1, [
        "The acquisition is not justified by industry attractiveness alone. Five Forces shows a competitive, "
        "substitute-rich market with meaningful buyer and supplier pressure; break-even shows that the declared "
        "economics work only if volume remains well above 166,666.67 units. The defensible answer is conditional: "
        "proceed with due diligence and a staged structure, and walk away if the volume cushion cannot be evidenced.",
    ]),
]

APA = [
    [("Alsaid, K. N., & Almesha, S. A. (2023). Factors affecting the omnichannel customer experience: Evidence from "
      "grocery retail in Saudi Arabia. ", False),
     ("International Journal of Management & Information Technology, 18", True),
     (", 1–12. https://doi.org/10.24297/ijmit.v18i.9373", False)],
    [("Alflayyeh, S., & Naeem, H. A. (2021). An integrative framework of retailscape: Case of grocery retail stores in "
      "Saudi Arabia. ", False),
     ("International Journal of Advanced and Applied Sciences, 8", True),
     ("(5), 20–29. https://doi.org/10.21833/ijaas.2021.05.003", False)],
    [("Alsulaimani, M. M. (2024). Factors affecting consumer intention to use e-grocery shopping in Saudi Arabia. ", False),
     ("International Journal of E-Business Research, 20", True),
     ("(1), 1–17. https://doi.org/10.4018/ijebr.347500", False)],
    [("Asiri, M., Hassan, A.-F., & Jarad, F. (2024). The impact of operational risks on customer satisfaction in the "
      "grocery retail sector: A case study of Panda Retail Company. ", False),
     ("International Journal for Scientific Research, 3", True),
     ("(8), 635–678. https://doi.org/10.59992/ijsr.2024.v3n8p19", False)],
    [("Khalilpoor, S., Abdulbaqi, A., Afsharfar, S., Babazadeh, R., & Kamran, M. A. (2026). Cold-chain resilience for "
      "perishable dairy: A simulation-based sourcing, inventory, and location decisions. ", False),
     ("Journal of Expert Systems and Sustainable Development, 2", True),
     ("(1), 133–151. https://doi.org/10.65069/jessd21202618", False)],
    [("Malik, S. A., & Bustami, R. (2023). Understanding demand and supply side factors: A cross-sector analysis from "
      "Saudi Arabia. ", False),
     ("Management & Sustainability: An Arab Review, 3", True),
     ("(1), 30–42. https://doi.org/10.1108/msar-12-2022-0058", False)],
]

HARVARD = [
    [("Alsaid, K. N. and Almesha, S. A. (2023) 'Factors affecting the omnichannel customer experience: evidence from "
      "grocery retail in Saudi Arabia', ", False),
     ("International Journal of Management & Information Technology, 18", True),
     (", pp. 1–12. Available at: https://doi.org/10.24297/ijmit.v18i.9373.", False)],
    [("Alflayyeh, S. and Naeem, H. A. (2021) 'An integrative framework of retailscape: case of grocery retail stores in "
      "Saudi Arabia', ", False),
     ("International Journal of Advanced and Applied Sciences, 8", True),
     ("(5), pp. 20–29. Available at: https://doi.org/10.21833/ijaas.2021.05.003.", False)],
    [("Alsulaimani, M. M. (2024) 'Factors affecting consumer intention to use e-grocery shopping in Saudi Arabia', ", False),
     ("International Journal of E-Business Research, 20", True),
     ("(1), pp. 1–17. Available at: https://doi.org/10.4018/ijebr.347500.", False)],
    [("Asiri, M., Hassan, A.-F. and Jarad, F. (2024) 'The impact of operational risks on customer satisfaction in the "
      "grocery retail sector: a case study of Panda Retail Company', ", False),
     ("International Journal for Scientific Research, 3", True),
     ("(8), pp. 635–678. Available at: https://doi.org/10.59992/ijsr.2024.v3n8p19.", False)],
    [("Khalilpoor, S., Abdulbaqi, A., Afsharfar, S., Babazadeh, R. and Kamran, M. A. (2026) 'Cold-chain resilience for "
      "perishable dairy: a simulation-based sourcing, inventory, and location decisions', ", False),
     ("Journal of Expert Systems and Sustainable Development, 2", True),
     ("(1), pp. 133–151. Available at: https://doi.org/10.65069/jessd21202618.", False)],
    [("Malik, S. A. and Bustami, R. (2023) 'Understanding demand and supply side factors: a cross-sector analysis from "
      "Saudi Arabia', ", False),
     ("Management & Sustainability: An Arab Review, 3", True),
     ("(1), pp. 30–42. Available at: https://doi.org/10.1108/msar-12-2022-0058.", False)],
]


def build(style, out_path):
    document = Document()
    section = document.sections[0]
    for side in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(section, side, Inches(1))
    normal = document.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    add_page_number(section.header.paragraphs[0])

    for _ in range(3):
        double(document.add_paragraph())
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    double(title)
    run = title.add_run(TITLE)
    run.bold = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    for line in ("[Student Name]", "[Department, Institution]", "[Course Code: Course Name]",
                 "[Instructor Name]", "28 October 2026"):
        paragraph = document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        double(paragraph)
        run = paragraph.add_run(line)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
    document.add_page_break()

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    double(title)
    run = title.add_run(TITLE)
    run.bold = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)

    for name, level, lines in SECTIONS:
        heading(document, name, level)
        for line in lines:
            body(document, line)

    document.add_page_break()
    heading(document, "References" if style == "apa" else "Bibliography")
    for entry in (APA if style == "apa" else HARVARD):
        reference(document, entry)
    document.save(str(out_path))


if __name__ == "__main__":
    for style in ("apa", "harvard"):
        out = OUT / ("saudi-cold-chain-five-forces-breakeven-%s.docx" % style)
        build(style, out)
        print(out)
