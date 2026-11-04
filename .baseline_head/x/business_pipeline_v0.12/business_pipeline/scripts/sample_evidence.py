"""Frozen evidence for the conductor sample papers.

Every record below is a source already cited in this repository's Apple-Iran
sample (`scripts/build_sample_paper.py`).  The `abstract` line is the claim that
sample makes from the source, kept so the conductor can quote it.  Nothing here
was newly retrieved or newly written for the sample, and no source is invented.

`PLACEMENT` states, per framework, which source supports which dimension.  That
placement is a declared editorial choice for the worked example, not a retrieval
result; a live paper places sources by the conductor's own ranking.
"""

SOURCES = [
    {"key": "ahmadi", "authors_list": ["Ahmadi, S. H.", "Razzaghi, F.", "Sepaskhah, A. R."],
     "year": 2026, "title": "Dryland farming in Iran: Feasibilities, constraints, and challenges towards sustainable expansion",
     "venue": "Sustainable Futures", "volume": "11", "pages": "101859",
     "doi": "https://doi.org/10.1016/j.sftr.2026.101859", "database": "CrossRef",
     "abstract": "Iran is arid and semi-arid, and its food production depends on a limited water supply."},
    {"key": "bashirov", "authors_list": ["Bashirov, G.", "Akbarzadeh, S.", "Yilmaz, I.", "Ahmed, Z. S."],
     "year": 2026, "title": "Diffusion of digital authoritarian practices in China's neighbourhood: The cases of Iran and Pakistan",
     "venue": "Democratization", "volume": "33", "issue": "2", "pages": "247-270",
     "doi": "https://doi.org/10.1080/13510347.2025.2504588", "database": "CrossRef",
     "abstract": "Digital authoritarian practices have diffused into Iran and Pakistan through regional policy transfer."},
    {"key": "conduit", "authors_list": ["Conduit, D."],
     "year": 2026, "title": "The political economy of digital authoritarianism: Evidence from the Iranian regime's implementation of technology",
     "venue": "Democratization", "volume": "33", "issue": "1", "pages": "62-84",
     "doi": "https://doi.org/10.1080/13510347.2025.2514766", "database": "CrossRef",
     "abstract": "The Iranian state uses technology to monitor and control online activity."},
    {"key": "haji", "authors_list": ["Haji, L.", "Fallah Haghighi, N."],
     "year": 2026, "title": "Assessing water governance challenges in the Lake Urmia Basin, Iran: A DPSIR-based approach",
     "venue": "Frontiers in Environmental Science", "volume": "14", "pages": "1737501",
     "doi": "https://doi.org/10.3389/fenvs.2026.1737501", "database": "CrossRef",
     "abstract": "The Lake Urmia crisis is attributed to climate change and intensive water use."},
    {"key": "koruzhde", "authors_list": ["Koruzhde, M."],
     "year": 2025, "title": "The sanctions must go on: The transnational investment bloc support for the Iran sanctions",
     "venue": "Middle East Critique",
     "doi": "https://doi.org/10.1080/19436149.2025.2499774", "database": "CrossRef",
     "abstract": "US sanctions are sustained by a transnational investment bloc and continued after the temporary pause created by the nuclear deal."},
    {"key": "pesaran", "authors_list": ["Pesaran, M. H.", "Smith, R."],
     "year": 2026, "title": "Sanctions, wars and prospects for the Iranian economy",
     "venue": "University of Cambridge Working Paper", "publisher": "University of Cambridge",
     "doi": "https://doi.org/10.17863/cam.134180", "database": "CrossRef",
     "abstract": "Sanctions and conflict have compounded structural weaknesses and left the outlook unusually uncertain."},
    {"key": "thomas", "authors_list": ["Thomas, A."],
     "year": 2024, "title": "Sanctions and postcolonial statecraft in Iran: Resisting the Iran Libya Sanctions Act and beyond",
     "venue": "All Azimuth", "volume": "13", "issue": "2", "pages": "285-306",
     "doi": "https://doi.org/10.20991/allazimuth.1511004", "database": "CrossRef",
     "abstract": "Sanctions have often strengthened Iranian resistance rather than produced compliance."},
    {"key": "worldbank_overview", "authors_list": ["World Bank"],
     "year": "2026a", "title": "Islamic Republic of Iran: Overview",
     "venue": "World Bank", "url": "https://www.worldbank.org/ext/en/country/iran", "database": "World Bank",
     "abstract": "Financial sanctions continue to constrain Iran's trade, and water and energy shortages disrupt economic activity."},
    {"key": "worldbank_data", "authors_list": ["World Bank"],
     "year": "2026b", "title": "World Bank Open Data: Iran, Islamic Republic",
     "venue": "World Bank", "url": "https://data.worldbank.org/country/iran-islamic-republic", "database": "World Bank",
     "abstract": "In 2025, 77.4% of residents lived in cities and 69.4% were aged 15 to 64, while internet use reached 85.3% in 2024."},
]

SOURCE_BY_KEY = {record["key"]: record for record in SOURCES}

#: framework id -> dimension key -> source keys
PLACEMENT = {
    "ansoff": {
        # Existing customers and frequency: the urban, connected audience is the base.
        "penetration": ["worldbank_data"],
        # New markets: trade is constrained, and sanctions have outlasted openings.
        "development": ["worldbank_overview", "thomas"],
        # New products: digital services depend on cross-border data and payment flows.
        "product": ["conduit", "bashirov"],
        # Diversification: the macro and conflict risk makes an unrelated venture harder.
        "diversification": ["koruzhde", "pesaran"],
    },
    "value_chain": {
        "inbound": ["worldbank_overview"],
        "operations": ["ahmadi"],
        "outbound": ["thomas"],
        "marketing": ["worldbank_data"],
        "procurement": ["koruzhde"],
        "technology": ["conduit", "bashirov"],
        "human": ["worldbank_data"],
        "infrastructure": ["pesaran", "worldbank_overview"],
        # No source supports a service activity for a firm that does not operate in the market.
    },
}
