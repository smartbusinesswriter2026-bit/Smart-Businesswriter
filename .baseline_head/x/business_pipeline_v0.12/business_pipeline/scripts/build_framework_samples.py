"""Build the SWOT and PESTEL+SWOT sample papers in APA 7 and Harvard .docx.

The papers reuse the live, traceable sources used by the PESTEL sample.  Internal
strengths and weaknesses are labelled as case assumptions; external claims carry
citations.  Formatting is the same as the academic renderer: Times New Roman 12,
double spacing, 1-inch margins, title page, page numbers and hanging references.
"""

import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from build_sample_paper import (
    HARVARD_REFERENCES,
    REFERENCES,
    LEVEL2,
    SECTIONS as PESTEL_SECTIONS,
    add_page_number,
    body,
    double,
    heading,
    reference,
    structure,
)

OUT_DIR = Path(__file__).resolve().parents[3] / "samples"

SWOT_TITLE = "Apple's Entry into Iran: A SWOT Analysis"
COMBINED_TITLE = "Apple's Entry into Iran: A PESTEL and SWOT Analysis"

SWOT_SECTIONS = [
    ("", [
        "This paper treats Apple's entry into Iran as a hypothetical decision and uses SWOT to place the "
        "company's internal position against the external evidence. Strengths and weaknesses are stated as case "
        "assumptions, not retrieved facts. Opportunities and threats are drawn from published sources and quoted "
        "with their citations.",
    ]),
    ("Strengths", [
        "Apple's strengths are substantial. Its brand is among the most valuable in technology, its hardware, "
        "software and services form an integrated ecosystem that raises switching costs, and its balance sheet "
        "gives it the capacity to absorb a costly entry (case assumptions). Its services revenue also provides a "
        "recurring income base that a hardware-only competitor lacks. These advantages would support a premium "
        "offer if the external environment allowed it.",
    ]),
    ("Weaknesses", [
        "The same model creates weaknesses in Iran. Apple prices at the top of the market while Iranian incomes "
        "are eroded by inflation. It has no local distribution or service network, and its services depend on "
        "cross-border payments and data flows that sanctions and filtering disrupt (case assumptions). Warranty "
        "and repair coverage would also be difficult to guarantee without an authorised local partner, and a "
        "hardware-only offer would weaken the ecosystem advantage.",
    ]),
    ("Opportunities", [
        "Iran has a large, urban and connected population. In 2025, 77.4% of residents lived in cities and 69.4% "
        "were aged 15 to 64, while internet use reached 85.3% in 2024 (World Bank, 2026b). The World Bank (2026a) "
        "describes a market of over 80 million people with a well-educated workforce. The working-age majority "
        "supports a long-term consumer base rather than a narrow luxury niche. If sanctions eased, that combination "
        "would give Apple a sizeable audience for premium devices and digital services, although the premium segment "
        "would remain smaller than the headline population suggests.",
    ]),
    ("Threats", [
        "The threats are stronger. Koruzhde (2025) shows that US sanctions are sustained by a transnational "
        "investment bloc and survived the temporary pause created by the nuclear deal, and the World Bank (2026a) "
        "reports that financial sanctions continue to constrain trade. Inflation reached 42.2% in 2025 and output "
        "contracted by 2.8% (World Bank, 2026b). Conduit (2026) and Bashirov et al. (2026) document digital "
        "surveillance and filtering, while Haji and Fallah Haghighi (2026) and Ahmadi et al. (2026) show water "
        "stress that raises operating costs. The World Bank (2026a) also reports that water and energy shortages "
        "disrupt activity and that poverty is expected to increase, which narrows the premium segment.",
    ]),
    ("Implications", [
        "The SWOT balance is unfavourable. Apple's strengths are real, but they cannot neutralise sanctions, "
        "currency instability and digital controls. Entry should wait for durable sanctions relief and then use "
        "authorised local partners rather than a direct subsidiary. A distributor agreement would shift some legal "
        "and logistics risk, but Apple would still need to control branding, pricing and compliance.",
    ]),
    ("Limitations", [
        "Strengths and weaknesses are case assumptions, not verified findings. The matrix does not weight the "
        "factors or test financial feasibility, and the sources are quoted rather than audited.",
    ]),
]

COMBINED_SECTIONS = [
    ("", [
        "This paper treats Apple's entry into Iran as a hypothetical decision. PESTEL explains the external "
        "environment, and SWOT places Apple's internal strengths and weaknesses against the opportunities and "
        "threats that environment creates. Strengths and weaknesses are case assumptions; external evidence is "
        "quoted with its citation.",
    ]),
] + [(name, lines) for name, lines in PESTEL_SECTIONS
     if name not in ("", "Implications", "Limitations", "Conclusion", "References", "Bibliography")] + [
    ("Strengths", [
        "Apple's brand, integrated ecosystem and financial capacity are real advantages (case assumptions). They "
        "would support a premium offer and absorb the cost of a patient entry.",
    ]),
    ("Weaknesses", [
        "Apple's premium pricing, lack of local distribution and dependence on cross-border services are weaknesses "
        "in this market (case assumptions). A hardware-only offer would weaken the ecosystem advantage.",
    ]),
    ("Opportunities", [
        "Iran's urban, connected population is the clearest opportunity. In 2025, 77.4% of residents lived in "
        "cities and 69.4% were aged 15 to 64, while internet use reached 85.3% in 2024 (World Bank, 2026b). The "
        "World Bank (2026a) describes a market of over 80 million people with a well-educated workforce. If "
        "sanctions eased, Apple could reach a large audience for premium devices and services.",
    ]),
    ("Threats", [
        "Sanctions remain the decisive threat. Koruzhde (2025) shows that US sanctions are sustained by a "
        "transnational investment bloc and survived the nuclear deal's temporary pause, and the World Bank (2026a) "
        "reports that financial sanctions constrain trade. Inflation reached 42.2% in 2025 and output contracted "
        "by 2.8% (World Bank, 2026b). Digital surveillance and filtering (Conduit, 2026; Bashirov et al., 2026) "
        "and water stress (Haji & Fallah Haghighi, 2026; Ahmadi et al., 2026) add operating and reputational risk.",
    ]),
    ("Integration of PESTEL and SWOT", [
        "PESTEL identifies the external conditions that frame the decision, and SWOT places the student's internal "
        "strengths and weaknesses against the opportunities and threats drawn from that evidence. The matrix keeps "
        "each opportunity and threat tied to its PESTEL origin. Read together, the two frameworks connect the "
        "external environment to Apple's position; the implications below state the resulting judgment.",
    ]),
    ("Implications", [
        "PESTEL and SWOT point the same way: political and legal constraints dominate. Apple's strengths would "
        "matter only after sanctions relief; until then, direct entry is not defensible. A partner-led, "
        "compliance-first option is the only structure worth preparing.",
    ]),
    ("Limitations", [
        "Strengths and weaknesses are case assumptions, not verified findings. Opportunities and threats are "
        "selected from the accepted evidence; the paper does not weight them, test financial feasibility or "
        "recommend a price. The sources are quoted rather than audited.",
    ]),
]


SWOT_KEYS = ("Ahmadi", "Bashirov", "Conduit", "Haji", "Koruzhde", "World Bank")
SWOT_REFERENCES = [entry for entry in REFERENCES if entry[0][0].startswith(SWOT_KEYS)]
SWOT_HARVARD_REFERENCES = [entry for entry in HARVARD_REFERENCES if entry[0][0].startswith(SWOT_KEYS)]


SWOT_CONCLUSION = ("The SWOT balance is unfavourable. Apple's strengths are real, but they cannot neutralise "
                   "sanctions, currency instability and digital controls. Entry should wait for durable sanctions relief "
                   "and then use authorised local partners rather than a direct subsidiary.")

COMBINED_CONCLUSION = ("PESTEL and SWOT point the same way: political and legal constraints dominate. Apple's strengths "
                       "would matter only after sanctions relief; until then, direct entry is not defensible. A "
                       "partner-led, compliance-first option is the only structure worth preparing.")


def build(title, sections, style, out_path, references):
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

    title_paragraph = document.add_paragraph()
    title_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    double(title_paragraph)
    run = title_paragraph.add_run(title)
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

    title_paragraph = document.add_paragraph()
    title_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    double(title_paragraph)
    run = title_paragraph.add_run(title)
    run.bold = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)

    conclusion = SWOT_CONCLUSION if title == SWOT_TITLE else COMBINED_CONCLUSION
    for name, lines in structure(sections, conclusion):
        if name:
            heading(document, name, 2 if name in LEVEL2 else 1)
        for line in lines:
            if style == "harvard":
                line = line.replace("(UNCTAD, n.d.)", "(UNCTAD, no date)")
            body(document, line)

    document.add_page_break()
    heading(document, "References" if style == "apa" else "Bibliography")
    for runs in references:
        reference(document, runs)

    document.save(str(out_path))
    return len(document.paragraphs)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    built = []
    for framework, title, sections, refs in (
            ("swot", SWOT_TITLE, SWOT_SECTIONS, (SWOT_REFERENCES, SWOT_HARVARD_REFERENCES)),
            ("pestel-swot", COMBINED_TITLE, COMBINED_SECTIONS, (REFERENCES, HARVARD_REFERENCES))):
        for index, style in enumerate(("apa", "harvard")):
            out = OUT_DIR / ("apple-iran-%s-%s.docx" % (framework, style))
            build(title, sections, style, out, refs[index])
            built.append(str(out))
    for path in built:
        print(path)


if __name__ == "__main__":
    main()
