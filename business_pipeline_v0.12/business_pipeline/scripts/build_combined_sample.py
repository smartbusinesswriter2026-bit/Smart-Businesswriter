"""Build the polished PESTEL+SWOT sample: fixed hierarchy, concise prose."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from build_sample_paper import (
    HARVARD_REFERENCES,
    REFERENCES,
    LEVEL2,
    add_page_number,
    body,
    double,
    heading,
    reference,
)

TITLE = "Apple's Prospective Entry into Iran: A Combined PESTEL and SWOT Analysis"
OUT = Path(__file__).resolve().parents[3] / "samples"

SECTIONS = [
    ("Introduction", 1, [
        "The decision under analysis is whether Apple should enter the Iranian market. This paper argues that it "
        "should not do so directly while the current sanctions regime remains in force; a partner-led entry after "
        "durable sanctions relief is the only defensible route. PESTEL establishes the external conditions, and SWOT "
        "places Apple's internal position against the opportunities and threats those conditions create. Strengths "
        "and weaknesses are stated as case assumptions; external claims are cited.",
    ]),
    ("PESTEL", 1, [
        "The external environment is assessed across six dimensions, each of which bears on the same entry decision.",
    ]),
    ("Political", 2, [
        "The political environment is defined by a sanctions regime that has outlasted diplomatic openings. Koruzhde "
        "(2025) shows that US sanctions are sustained by a transnational investment bloc and continued after the "
        "temporary pause created by the nuclear deal. For a US-headquartered firm, the main exposure is secondary "
        "sanctions: banks, insurers and shippers may refuse to support sales even where demand exists. The World Bank "
        "(2026a) confirms that financial sanctions still constrain Iran's trade. Political risk therefore enters the "
        "decision before commercial demand is considered.",
    ]),
    ("Economic", 2, [
        "Economic conditions reinforce that caution. Inflation reached 42.2% in 2025 and output contracted by 2.8%, "
        "while the World Bank (2026a) expects high inflation and falling real incomes to suppress demand. Pesaran and "
        "Smith (2026) argue that sanctions and conflict have compounded structural weaknesses and left the outlook "
        "unusually uncertain. A premium hardware business would face a narrow addressable segment, rapid price erosion "
        "and difficult currency repatriation. These conditions weaken the case for a direct subsidiary and favour a "
        "partner that can absorb currency and inventory risk.",
    ]),
    ("Social", 2, [
        "Iran's social profile is the strongest part of the external case. In 2025, 77.4% of residents lived in cities "
        "and 69.4% were aged 15 to 64, while internet use reached 85.3% in 2024 (World Bank, 2026b). The World Bank "
        "(2026a) describes a market of over 80 million people with a well-educated workforce. Yet youth unemployment "
        "stood at 21.9% in 2025 (World Bank, 2026b), limiting disposable income among younger consumers. Demand would "
        "concentrate among wealthier urban households, so the opportunity is real but narrower than the headline "
        "population suggests.",
    ]),
    ("Technological", 2, [
        "Technology is widespread but politically mediated. Conduit (2026) documents how the Iranian state uses "
        "technology to monitor and control online activity, and Bashirov et al. (2026) show that practices of digital "
        "authoritarianism have diffused into Iran. Apple's model depends on connected services such as the App Store, "
        "iCloud and Apple Pay, which require stable cross-border data and payment flows. Filtering, blackouts and "
        "platform restrictions would fragment that ecosystem. A hardware-only presence would preserve the device but "
        "lose the services revenue that makes the model distinctive.",
    ]),
    ("Environmental", 2, [
        "Water and energy stress is a material operating constraint. Haji and Fallah Haghighi (2026) attribute the "
        "Lake Urmia crisis to climate change and intensive water use, while Ahmadi et al. (2026) describe Iran as arid "
        "and semi-arid, with food production dependent on limited water. The World Bank (2026a) reports that water and "
        "energy shortages already disrupt economic activity. These conditions raise the cost of local facilities and "
        "data capacity, and they invite scrutiny of a technology firm's resource footprint.",
    ]),
    ("Legal", 2, [
        "Iran's Foreign Investment Promotion and Protection Act offers guarantees to approved foreign investors "
        "(UNCTAD, n.d.), but those protections cannot override US sanctions. Compliance obligations cut across "
        "jurisdictions: conduct permitted under Iranian law may be prohibited under US rules. Import restrictions, "
        "intellectual-property enforcement and currency controls add further uncertainty. Legal risk is therefore "
        "decisive for Apple because it affects the ability to bank, ship, warrant and service products, not merely the "
        "ability to advertise them.",
    ]),
    ("SWOT", 1, [
        "SWOT translates those external conditions into the firm's own position. The internal factors below are case "
        "assumptions; the external factors are drawn from the PESTEL evidence.",
    ]),
    ("Strengths", 2, [
        "Apple's strengths are substantial. Its brand is among the most valuable in technology, its hardware, software "
        "and services form an integrated ecosystem that raises switching costs, and its balance sheet gives it the "
        "capacity to absorb a costly entry (case assumptions). These advantages would support a premium offer if the "
        "external environment allowed it.",
    ]),
    ("Weaknesses", 2, [
        "The same model creates weaknesses in Iran. Apple prices at the top of the market while inflation erodes "
        "incomes. It has no local distribution or service network, and its services depend on cross-border payments "
        "and data flows that sanctions and filtering disrupt (case assumptions). Warranty and repair coverage would be "
        "difficult without an authorised partner, and a hardware-only offer would weaken the ecosystem advantage.",
    ]),
    ("Opportunities", 2, [
        "Iran's urban, connected population is the clearest opportunity. In 2025, 77.4% of residents lived in cities "
        "and 69.4% were aged 15 to 64, while internet use reached 85.3% in 2024 (World Bank, 2026b). The World Bank "
        "(2026a) describes a market of over 80 million people with a well-educated workforce. If sanctions eased, "
        "Apple could reach a large audience for premium devices and services. The segment would still be concentrated "
        "among wealthier households.",
    ]),
    ("Threats", 2, [
        "Sanctions remain the decisive threat. Koruzhde (2025) shows that US sanctions are sustained by a transnational "
        "investment bloc and survived the nuclear deal's temporary pause, and the World Bank (2026a) reports that "
        "financial sanctions constrain trade. Inflation reached 42.2% in 2025 and output contracted by 2.8% (World "
        "Bank, 2026b). Digital surveillance and filtering (Conduit, 2026; Bashirov et al., 2026) and water stress "
        "(Haji & Fallah Haghighi, 2026; Ahmadi et al., 2026) add operating and reputational risk.",
    ]),
    ("Discussion", 1, []),
    ("Integration of PESTEL and SWOT", 2, [
        "The two frameworks answer the same question from opposite directions. PESTEL shows that the external "
        "conditions are dominated by political and legal constraints; SWOT shows that Apple's strengths are real but "
        "cannot neutralise those constraints. The social and economic evidence creates a genuine long-term "
        "opportunity, yet the same sanctions that limit trade also limit the services that make Apple's offer "
        "distinctive. The opportunities are therefore conditional on sanctions relief, while the threats are active "
        "now. That asymmetry, rather than the size of the market, is the central finding.",
    ]),
    ("Implications", 2, [
        "The implication is a sequencing decision. Apple should not enter directly while the sanctions regime remains "
        "in force. It should monitor relief, prepare a compliance-first partner structure and preserve the option to "
        "move if the legal position changes. A distributor agreement would shift some logistics and legal risk, but "
        "Apple would still need to control branding, pricing and service standards. The market is worth watching; it "
        "is not worth a direct subsidiary today.",
    ]),
    ("Limitations", 2, [
        "The internal factors are case assumptions, not verified findings. The evidence is selected from published "
        "sources and does not test financial feasibility, valuation or expected returns. The paper also does not weigh "
        "the factors quantitatively; it establishes the conditions and the direction of the decision.",
    ]),
    ("Conclusion", 1, [
        "The paper asked whether Apple should enter Iran. The PESTEL evidence shows that political and legal "
        "constraints dominate the external environment; the SWOT evidence shows that Apple's strengths cannot "
        "overcome those constraints in the current period. The answer is therefore conditional: do not enter directly "
        "now, and prepare a partner-led entry only if durable sanctions relief changes the legal position.",
    ]),
]

REFERENCE_KEYS = ("Ahmadi", "Bashirov", "Conduit", "Haji", "Koruzhde", "Pesaran", "UNCTAD", "World Bank")


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
    pool = REFERENCES if style == "apa" else HARVARD_REFERENCES
    for entry in pool:
        if entry[0][0].startswith(REFERENCE_KEYS):
            reference(document, entry)
    document.save(str(out_path))


if __name__ == "__main__":
    for style in ("apa", "harvard"):
        out = OUT / ("apple-iran-pestel-swot-sample-%s.docx" % style)
        build(style, out)
        print(out)
