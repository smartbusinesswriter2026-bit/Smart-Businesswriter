# Vetted sources by topic

The pipeline does not search the open web indiscriminately. It searches a
**curated registry** of official, data, research and press sites, and it ranks
that registry by the paper's topic. The registry lives in
`src/bp/product/sources.py` (`VETTED_SITES`, `TOPIC_SITES`, `TOPICS`,
`SITE_TOPICS`, `SITE_PRIORITY`). This document is the owner-facing map.

## The rule

```text
1. Corpus / Meilisearch      cited, first, fastest
2. Vetted web by topic       cited if the page is substantive;
                             orientation only if it is a paywalled snippet
3. Journal APIs              last resort, only when 1 and 2 miss
```

A site is vetted because a researcher would accept it as a starting point, not
because every page on it is citable. The relevance gate and the evidence ledger
still decide what enters the paper. A paywalled source is marked
`access: "paywalled"` and ranked below a free one; its snippet is orientation,
never quoted as if the full text had been read.

Each site carries:

| Field | Meaning |
|---|---|
| `domain` | the host the search is filtered to |
| `tier` | `official`, `data`, `research` or `news` |
| `category` | `legal`, `economic`, `social`, `company` or `news` |
| `academic_fit` | `primary`, `research` or `background` |
| `access` | `free`, `mixed` or `paywalled` |
| `topics` | the topics it serves, primary topic first |
| `priority` | the order a researcher would try it inside a topic |

## How a topic is chosen

`retrieve()` receives a `topic` from the paper:

- the conductor passes the paper's subject (`management`, `marketing`,
  `finance`, ...);
- a worksheet profile passes its own `subject` when it has one;
- if neither is present, `search_web()` infers the topic from the query with
  `topic_for_text()`;
- if nothing matches, the whole registry is used, never a guessed subject.

`topic_for_text()` uses whole-word matching for short tokens (`ai`, `hr`,
`esg`) and substring matching for phrases. This matters: the first pass
matched `ai` inside `chain`, so a supply-chain paper was classified as
technology.

On a **no-framework paper** the only dimension is the generic `Evidence`
block. Its query is the decision sentence, which is often too long for a
topic source. If that query returns no accepted page, the retriever asks the
topic label once — `Business ethics and governance evidence`,
`Culture and cross-cultural management evidence` — and merges those results.
That is how the Stanford Encyclopedia, the Institute of Business Ethics and
the GLOBE Project are actually reached in a live run.

## The topic map

The first five sites in each row are the ones the Brave adapter filters to; the
rest are available to the other web providers.

| Topic | First sources |
|---|---|
| **Business ethics** | Stanford Encyclopedia of Philosophy (`plato.stanford.edu`), Internet Encyclopedia of Philosophy (`iep.utm.edu`), Markkula Center (`scu.edu`), Institute of Business Ethics (`ibe.org.uk`), Transparency International (`transparency.org`), UN Global Compact, Carnegie Council, UNODC |
| **Culture / cross-cultural** | Geert Hofstede (`geerthofstede.com`), GLOBE Project (`globeproject.com`), UNESCO, Afrobarometer, Latinobarometro, Hofstede Insights, Arab Barometer, World Values Survey, Pew, Kantar |
| **Finance** | SEC EDGAR, BIS, CFA Institute, FASB, IFRS/IASB, ECB, IMF, AnnualReports, Companies House, CDP |
| **Accounting** | FASB, IFRS/IASB, AICPA, SEC EDGAR, AnnualReports, GRI, CFA Institute, PwC |
| **Marketing** | American Marketing Association (`ama.org`), Nielsen, Kantar, Statista, Mintel, eMarketer, WARC, Bain, McKinsey, HBR, Euromonitor |
| **Management / strategy** | HBR, MIT Sloan Management Review, McKinsey Insights, BCG, Bain, Deloitte, PwC, Accenture, Strategy+Business, Gartner, Forrester, MIT Technology Review, Stanford HAI |
| **Operations** | MIT CTL, World Bank Logistics Performance Index, NIST, ASCM (APICS), CSCMP, Bain, BCG, McKinsey |
| **Supply chain / logistics** | MIT CTL, World Bank LPI, ASCM, CSCMP, Institute for Supply Management |
| **People / HR** | SHRM, CIPD, Gallup, Hofstede, GLOBE, ILO, BLS, Census, UNESCO |
| **Entrepreneurship** | Kauffman Foundation, CB Insights, Crunchbase, Startup Genome, PitchBook |
| **Technology / innovation** | EPO, USPTO, NIST, Stanford HAI, Forrester, Gartner, MIT Technology Review, WIPO |
| **Environment / sustainability** | IPCC, EPA, UNEP, CDP, GRI, IEA, WRI, IFRS/ISSB, World Bank, OECD |
| **Health** | CDC, WHO, NIH, IHME, EPA, World Bank, OECD, Our World in Data |
| **Law / regulation** | Congress.gov, EUR-Lex, CURIA, legislation.gov.uk, Supreme Court, UNODC, World Justice Project, SEC |
| **Project management** | PMI, IPMA, AXELOS |
| **Industry / market data** | IBISWorld, Statista, Euromonitor, Mintel, Nielsen, Kantar, CB Insights, PitchBook, Crunchbase, SEC EDGAR |
| **Company / filings** | SEC EDGAR, AnnualReports, Companies House, stock exchanges, PitchBook, Crunchbase |
| **Economics / policy** | NBER, CEPR, VoxEU, Brookings, PIIE, Bruegel, Our World in Data, Gapminder, IMF, World Bank, OECD |
| **Country data** | World Bank, IMF, UN, OECD, Eurostat, BLS, Census, UN Statistics, Data.gov, national statistical offices |
| **Research methods** | Our World in Data, Gapminder, ICPSR, Pew, Gallup, UN Statistics, OECD |
| **News** | Reuters, Financial Times, Bloomberg, WSJ, The Economist, SCMP, Caixin, Arab News, The National |

## Adding a site

1. Add a dict to `TOPIC_SITES` (or add the domain to `VETTED_SITES` and its
   topics to `SITE_TOPICS`).
2. Give it `domain`, `tier`, `category`, `academic_fit`, `access`, `topics` and
   a one-line `use`. Add `priority` if it is a canonical source.
3. Do not add a site you would not accept as a starting point. Do not add a
   site only because it ranks well in a search engine.
4. Add a test in `tests/test_sources.py` that the topic reaches it.
5. Run:

```powershell
python -m unittest tests.test_sources
```

`GET /api/cases/sources/sites?topic=ethics` returns the ranked list and the
topic labels, so the UI can show the same selection the pipeline uses.

## Mirror into SQLite

The pipeline reads the code registry, not the database.  For inspection and
reporting, the registry can be mirrored into the corpus database:

```powershell
python D:\SMART BUSINESSWRITER\corpus-db\build\sync_vetted_sites.py
```

It creates `vetted_sites` (one row per site, topics as a JSON array) and
upserts by `site_id`; `--keep-stale` keeps rows that are no longer in the
registry.  `--dry-run` prints the rows without touching the database.

Editing that table does **not** change the pipeline.  Change `sources.py`, run
the script again, and the mirror follows.  This is deliberate: a stopped
database must never stop the web layer from knowing where to look.

## What this does not do

- It does not make a paywalled page citable. The page is a pointer; the paper
  still needs the evidence.
- It does not replace the corpus. The corpus is still layer 1; this registry
  only decides where the web layer looks when the corpus misses.
- It does not invent a topic. An unknown brief falls back to the whole
  registry and is named as a general web search.
