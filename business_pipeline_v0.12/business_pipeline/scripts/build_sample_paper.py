"""Build the sample paper: APA 7 or Harvard, Times New Roman 12, double-spaced, 1-inch margins."""

import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

STYLE = (sys.argv[1] if len(sys.argv) > 1 else "apa").lower()
if STYLE not in ("apa", "harvard"):
    raise SystemExit("style must be apa or harvard")
TITLE = "Apple's Prospective Entry into Iran: A PESTEL Analysis"
OUT = str(Path(__file__).resolve().parents[3] / "samples" / ("apple-iran-pestel-%s.docx" % ("apa7" if STYLE == "apa" else STYLE)))

SECTIONS = [
    ("", [
        "This paper treats Apple's entry into Iran as a hypothetical decision. A PESTEL analysis examines the "
        "political, economic, social, technological, environmental and legal conditions a foreign technology firm "
        "would face. The evidence indicates that political and legal constraints dominate and that direct entry "
        "would be premature until sanctions are durably resolved.",
    ]),
    ("Political", [
        "Iran's political environment is shaped by a sanctions regime that has outlasted diplomatic openings. "
        "Koruzhde (2025) shows that US sanctions are sustained by a transnational investment bloc and continued "
        "after the temporary pause created by the nuclear deal. Thomas (2024) adds that sanctions have often "
        "strengthened Iranian resistance rather than produced compliance. For a US-headquartered firm such as Apple, "
        "the main exposure is secondary sanctions: banks, insurers and shippers may refuse to support sales even when "
        "demand exists. The World Bank (2026a) confirms that financial sanctions still constrain Iran's trade.",
    ]),
    ("Economic", [
        "Macroeconomic conditions are unstable. Inflation reached 42.2% in 2025 and output contracted by 2.8%, and "
        "the World Bank (2026a) expects high inflation and falling real incomes to suppress demand. Pesaran and Smith "
        "(2026) argue that sanctions and conflict have compounded structural weaknesses and left the outlook unusually "
        "uncertain. A premium hardware business would face a narrow addressable segment, rapid price erosion and "
        "difficult currency repatriation, while payment routes remain constrained by compliance controls.",
    ]),
    ("Social", [
        "Iran is predominantly urban: 77.4% of residents lived in cities in 2025 and 69.4% were aged 15 to 64 "
        "(World Bank, 2026b). Internet use reached 85.3% in 2024, giving a premium brand visibility and a broad "
        "digital audience (World Bank, 2026b). Yet youth unemployment stood at 21.9% in 2025, limiting disposable "
        "income among younger consumers (World Bank, 2026b). Demand would concentrate among wealthier urban "
        "households, and social restrictions would constrain advertising and lifestyle positioning.",
    ]),
    ("Technological", [
        "Digital infrastructure is extensive but politically mediated. Conduit (2026) documents how the Iranian state "
        "uses technology to monitor and control online activity, and Bashirov et al. (2026) show that practices of "
        "digital authoritarianism have diffused into Iran. Apple's model depends on connected services such as the "
        "App Store, iCloud and Apple Pay, which require stable cross-border data and payment flows. Filtering, "
        "blackouts and platform restrictions would fragment that ecosystem, leaving a hardware-only market with "
        "limited recurring revenue.",
    ]),
    ("Environmental", [
        "Water and energy stress is a material operating constraint. Haji and Fallah Haghighi (2026) attribute the "
        "Lake Urmia crisis to climate change and intensive water use, while Ahmadi et al. (2026) describe Iran as arid "
        "and semi-arid, with food production dependent on limited water. The World Bank (2026a) reports that water "
        "and energy shortages already disrupt economic activity. These conditions raise the cost of local facilities "
        "and data capacity and invite scrutiny of a technology firm's resource footprint.",
    ]),
    ("Legal", [
        "Iran's Foreign Investment Promotion and Protection Act offers guarantees to approved foreign investors "
        "(UNCTAD, n.d.), but those protections cannot override US sanctions. Compliance obligations cut across "
        "jurisdictions: conduct permitted under Iranian law may be prohibited under US rules. Import restrictions, "
        "intellectual-property enforcement and currency controls add further uncertainty. Legal risk is therefore "
        "decisive for Apple because it affects the ability to bank, ship, warrant and service products.",
    ]),
    ("Implications", [
        "The evidence points to a cautious position: Apple should not enter Iran directly while the sanctions regime "
        "remains in force. The political and legal constraints dominate the economic and social opportunity, and the "
        "operational environment would make a direct subsidiary difficult to defend.",
    ]),
    ("Limitations", [
        "The analysis relies on published sources and does not test financial feasibility. The evidence is quoted "
        "rather than audited, and some dimensions remain thinner than others.",
    ]),
    ("Conclusion", [
        "PESTEL indicates that politics and law are the binding constraints on Apple's entry into Iran. Economic "
        "volatility, high youth unemployment and controlled digital infrastructure weaken the commercial case, while "
        "environmental stress raises operating costs. The rational posture is to monitor sanctions relief and, if "
        "conditions change, enter through authorised local partners under a compliance-first structure rather than a "
        "direct subsidiary.",
    ]),
]

REFERENCES = [
    [("Ahmadi, S. H., Razzaghi, F., & Sepaskhah, A. R. (2026). Dryland farming in Iran: Feasibilities, constraints, "
      "and challenges towards sustainable expansion. ", False),
     ("Sustainable Futures, 11", True), (", Article 101859. https://doi.org/10.1016/j.sftr.2026.101859", False)],
    [("Bashirov, G., Akbarzadeh, S., Yilmaz, I., & Ahmed, Z. S. (2026). Diffusion of digital authoritarian practices "
      "in China's neighbourhood: The cases of Iran and Pakistan. ", False),
     ("Democratization, 33", True), ("(2), 247\u2013270. https://doi.org/10.1080/13510347.2025.2504588", False)],
    [("Conduit, D. (2026). The political economy of digital authoritarianism: Evidence from the Iranian regime's "
      "implementation of technology. ", False),
     ("Democratization, 33", True), ("(1), 62\u201384. https://doi.org/10.1080/13510347.2025.2514766", False)],
    [("Haji, L., & Fallah Haghighi, N. (2026). Assessing water governance challenges in the Lake Urmia Basin, Iran: "
      "A DPSIR-based approach. ", False),
     ("Frontiers in Environmental Science, 14", True), (", Article 1737501. https://doi.org/10.3389/fenvs.2026.1737501", False)],
    [("Koruzhde, M. (2025). The sanctions must go on: The transnational investment bloc support for the Iran "
      "sanctions. ", False),
     ("Middle East Critique", True), (". Advance online publication. https://doi.org/10.1080/19436149.2025.2499774", False)],
    [("Pesaran, M. H., & Smith, R. (2026). Sanctions, wars and prospects for the Iranian economy [Working paper]. "
      "University of Cambridge. https://doi.org/10.17863/cam.134180", False)],
    [("Thomas, A. (2024). Sanctions and postcolonial statecraft in Iran: Resisting the Iran Libya Sanctions Act and "
      "beyond. ", False),
     ("All Azimuth, 13", True), ("(2), 285\u2013306. https://doi.org/10.20991/allazimuth.1511004", False)],
    [("UNCTAD. (n.d.). Iran, Islamic Republic of: Foreign investment law. ", False),
     ("Investment Laws Navigator", True),
     (". https://investmentpolicy.unctad.org/investment-laws/laws/94/iran-islamic-republic-of-foreign-investment-law", False)],
    [("World Bank. (2026a). ", False),
     ("Islamic Republic of Iran: Overview", True), (". https://www.worldbank.org/ext/en/country/iran", False)],
    [("World Bank. (2026b). ", False),
     ("World Bank Open Data: Iran, Islamic Republic", True),
     (" [Data set]. https://data.worldbank.org/country/iran-islamic-republic", False)],
]

HARVARD_REFERENCES = [
    [("Ahmadi, S. H., Razzaghi, F. and Sepaskhah, A. R. (2026) 'Dryland farming in Iran: feasibilities, constraints, "
      "and challenges towards sustainable expansion', ", False),
     ("Sustainable Futures, 11", True),
     (", Article 101859. Available at: https://doi.org/10.1016/j.sftr.2026.101859.", False)],
    [("Bashirov, G., Akbarzadeh, S., Yilmaz, I. and Ahmed, Z. S. (2026) 'Diffusion of digital authoritarian practices "
      "in China's neighbourhood: the cases of Iran and Pakistan', ", False),
     ("Democratization, 33", True),
     ("(2), pp. 247\u2013270. Available at: https://doi.org/10.1080/13510347.2025.2504588.", False)],
    [("Conduit, D. (2026) 'The political economy of digital authoritarianism: evidence from the Iranian regime's "
      "implementation of technology', ", False),
     ("Democratization, 33", True),
     ("(1), pp. 62\u201384. Available at: https://doi.org/10.1080/13510347.2025.2514766.", False)],
    [("Haji, L. and Fallah Haghighi, N. (2026) 'Assessing water governance challenges in the Lake Urmia Basin, Iran: "
      "a DPSIR-based approach', ", False),
     ("Frontiers in Environmental Science, 14", True),
     (", Article 1737501. Available at: https://doi.org/10.3389/fenvs.2026.1737501.", False)],
    [("Koruzhde, M. (2025) 'The sanctions must go on: the transnational investment bloc support for the Iran "
      "sanctions', ", False),
     ("Middle East Critique", True),
     (", pp. 1\u201321. Advance online publication. Available at: "
      "https://doi.org/10.1080/19436149.2025.2499774.", False)],
    [("Pesaran, M. H. and Smith, R. (2026) ", False),
     ("Sanctions, wars and prospects for the Iranian economy", True),
     (". Working paper. University of Cambridge. Available at: https://doi.org/10.17863/cam.134180.", False)],
    [("Thomas, A. (2024) 'Sanctions and postcolonial statecraft in Iran: resisting the Iran Libya Sanctions Act and "
      "beyond', ", False),
     ("All Azimuth, 13", True),
     ("(2), pp. 285\u2013306. Available at: https://doi.org/10.20991/allazimuth.1511004.", False)],
    [("UNCTAD (no date) ", False),
     ("Iran, Islamic Republic of: foreign investment law", True),
     (". Investment Laws Navigator. Available at: "
      "https://investmentpolicy.unctad.org/investment-laws/laws/94/iran-islamic-republic-of-foreign-investment-law "
      "(Accessed: 28 October 2026).", False)],
    [("World Bank (2026a) ", False),
     ("Islamic Republic of Iran: overview", True),
     (". Available at: https://www.worldbank.org/ext/en/country/iran (Accessed: 28 October 2026).", False)],
    [("World Bank (2026b) ", False),
     ("World Bank Open Data: Iran, Islamic Republic", True),
     (". Available at: https://data.worldbank.org/country/iran-islamic-republic "
      "(Accessed: 28 October 2026).", False)],
]


def double(paragraph):
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.DOUBLE
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run()
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = "PAGE"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instruction)
    run._r.append(end)


LEVEL2 = {"Political", "Economic", "Social", "Technological", "Environmental", "Legal",
          "Strengths", "Weaknesses", "Opportunities", "Threats", "Integration of PESTEL and SWOT",
          "Implications", "Limitations"}


def heading(document, text, level=1):
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if level == 1 else WD_ALIGN_PARAGRAPH.LEFT
    double(paragraph)
    run = paragraph.add_run(text)
    run.bold = True
    if level >= 3:
        run.italic = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)


def body(document, text):
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.first_line_indent = Inches(0.5)
    double(paragraph)
    run = paragraph.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)


def reference(document, runs):
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.left_indent = Inches(0.5)
    paragraph.paragraph_format.first_line_indent = Inches(-0.5)
    double(paragraph)
    for text, italic in runs:
        run = paragraph.add_run(text)
        run.italic = italic
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)


PESTEL_DIMS = {"Political", "Economic", "Social", "Technological", "Environmental", "Legal"}
PESTEL_CONCLUSION = ("The PESTEL evidence points to political and legal constraints as the binding conditions for "
                     "Apple's entry into Iran. Economic instability and controlled digital infrastructure weaken the "
                     "commercial case, while environmental stress raises operating costs. Entry should wait for a "
                     "durable sanctions settlement and then proceed through authorised local partners rather than a "
                     "direct subsidiary.")


def structure(sections, conclusion):
    out, pestel, swot, discussion = [], False, False, False
    for name, lines in sections:
        if name in PESTEL_DIMS and not pestel:
            out.append(("PESTEL", []))
            pestel = True
        if name in {"Strengths", "Weaknesses", "Opportunities", "Threats"} and not swot:
            out.append(("SWOT", []))
            swot = True
        if name in {"Integration of PESTEL and SWOT", "Implications", "Limitations"} and not discussion:
            out.append(("Discussion", []))
            discussion = True
        out.append((name, lines))
    if not any(name == "Conclusion" for name, _lines in out):
        reference = next((i for i, (name, _lines) in enumerate(out)
                          if name in ("References", "Bibliography")), len(out))
        out.insert(reference, ("Conclusion", [conclusion]))
    return out


def main():
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    normal = document.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")

    add_page_number(section.header.paragraphs[0])

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

    # the title page is its own section, centred vertically on the page
    from docx.enum.section import WD_SECTION
    document.add_section(WD_SECTION.NEW_PAGE)
    first, body_section = document.sections[0], document.sections[1]
    centre = OxmlElement("w:vAlign")
    centre.set(qn("w:val"), "center")
    first._sectPr.append(centre)
    for element in body_section._sectPr.findall(qn("w:vAlign")):
        body_section._sectPr.remove(element)

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    double(title)
    run = title.add_run(TITLE)
    run.bold = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)

    for name, paragraphs in structure(SECTIONS, PESTEL_CONCLUSION):
        if name:
            heading(document, name, 2 if name in LEVEL2 else 1)
        for text in paragraphs:
            if STYLE == "harvard":
                text = text.replace("(UNCTAD, n.d.)", "(UNCTAD, no date)")
            body(document, text)

    document.add_page_break()
    heading(document, "References" if STYLE == "apa" else "Bibliography")
    for runs in (REFERENCES if STYLE == "apa" else HARVARD_REFERENCES):
        reference(document, runs)

    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    document.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
