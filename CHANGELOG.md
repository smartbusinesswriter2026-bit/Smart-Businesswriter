# CHANGELOG — People & Organization Strategy & Design Worksheets

## [unreleased] — 2026-11-02

### Added
- Project scaffold (AGENTS.md, DECISIONS.md, CHANGELOG.md)
- Subject: People and Organization → Strategy and Design
- Worksheet: Kurt Lewin (Force Field Analysis, 3-Step Change Model)
- Worksheet: Jay Galbraith (Star Model, Information Processing)
- Worksheet: Henry Mintzberg (Five Organizational Configurations)
- `before` briefing for Lewin worksheet (CHG-03, CHG-04)
- `before` briefing for Galbraith worksheet (CHG-05, CHG-06)
- `before` briefing for Mintzberg worksheet (CHG-07, CHG-08, CHG-13)
- `before` briefing for People shelf consistency (CHG-02, CHG-09, CHG-10)
- CATALOGUE slice (`catalogue/slice.json`) registering all 3 worksheets
- Worksheet registration module (`catalogue/register.mjs`)
- CHG-15 wiring probe (`wiring/chg-15-probe.mjs`) — reachability + drift
- Guard test: every People worksheet carries a `before` briefing (`tests/guard-test.mjs`)
- Worksheet registration test (`tests/registration-test.mjs`)
- People subject test (`tests/people-test.mjs`)
- Product subject test (`tests/product-subject-test.mjs`)
- Full test suite runner (`run-suite.mjs`)

### Changed
- (none)

### Deprecated
- (none)

### Removed
- (none)

### Fixed
- (none)

### Security
- (none)