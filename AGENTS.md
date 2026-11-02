# People & Organization Subject — Strategy & Design Worksheets

This project holds worksheets + `before` briefings for the **People and Organization** subject, specifically the **Strategy and Design** shelf, covering organizational theorists from **Kurt Lewin** through **Henry Mintzberg**.

## Directory layout

```
/catalogue            — CATALOGUE slice + worksheet registration
/subjects/people-organization/strategy-design/
  /lewin             — Kurt Lewin worksheet + before briefing
  /galbraith         — Jay Galbraith worksheet + before briefing
  /mintzberg         — Henry Mintzberg worksheet + before briefing
/tests               — Guard, registration, People, product-subject tests
/wiring              — CHG-15 wiring probe + empirical validation
/DECISIONS.md        — Decision log
/CHANGELOG.md        — Change log
```

## CHG item mapping

| CHG | Area | Owner |
|-----|------|-------|
| CHG-02 | People shelf consistency | before briefing |
| CHG-03 | strategy_design chain | before briefing (Lewin) |
| CHG-04 | strategy_design chain | before briefing (Lewin→Galbraith) |
| CHG-05 | strategy_design chain | before briefing (Galbraith) |
| CHG-06 | strategy_design chain | before briefing (Galbraith→Mintzberg) |
| CHG-07 | strategy_design chain | before briefing (Mintzberg) |
| CHG-08 | strategy_design chain | before briefing (Mintzberg synthesis) |
| CHG-09 | People shelf consistency | before briefing |
| CHG-10 | People shelf consistency | before briefing |
| CHG-13 | strategy_design chain | before briefing (cross-reference) |
| CHG-15 | People strategy_design tile wiring | wiring probe + CATALOGUE slice |

## Test commands

```
node tests/guard-test.mjs          # every People worksheet carries a before briefing
node tests/registration-test.mjs   # worksheet registration integrity
node tests/people-test.mjs         # People subject tests
node tests/product-subject-test.mjs# product subject tests
node run-suite.mjs                 # full suite
```
