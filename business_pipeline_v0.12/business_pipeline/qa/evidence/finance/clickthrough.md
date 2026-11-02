# Finance click-through on http://127.0.0.1:8001

```
PASS  page marker 'railSubject'
PASS  page marker 'markCurrentRailItem'
PASS  page marker 'activate("new")'
PASS  page marker 'calculator'
PASS  page marker 'subjectgallery'
PASS  page marker 'not teacher-approved'
PASS  no reviewer surface 'Reviewer name'
PASS  no reviewer surface 'Sign-off'
PASS  no reviewer surface 'Review status'
PASS  GET /api/cases/subjects/finance -> 200, 35 tools, 23 records
PASS  tvm              tvm -> delivered
PASS  loan             loan -> delivered
PASS  dupont           dupont -> delivered
PASS  trendanalysis    trendanalysis -> delivered
PASS  workingcapital   workingcapital -> delivered
PASS  ratios           ratios -> delivered
PASS  breakeven        breakeven -> delivered
PASS  multibreakeven   multibreakeven -> delivered
PASS  unitecon         unitecon -> delivered
PASS  forecast         forecast -> delivered
PASS  descriptive      descriptive -> delivered
PASS  npv              npv -> delivered
PASS  irr              irr -> delivered
PASS  dpayback         dpayback -> delivered
PASS  projectmetrics   projectmetrics -> delivered
PASS  wacc             wacc -> delivered
PASS  capm             capm -> delivered
PASS  leverage         leverage -> delivered
PASS  scenario         scenario -> delivered
PASS  case_decision    case_decision -> delivered
PASS  dcf              dcf -> delivered
KNOWN dcfmid           dcfmid -> blocked (D-FIN-01)
PASS  equitybridge     equitybridge -> delivered
PASS  multiples        multiples -> delivered
PASS  portfolioval     portfolioval -> delivered
PASS  portfolioperf    portfolioperf -> delivered
PASS  bond             bond -> delivered
PASS  portfolio        portfolio -> delivered
PASS  pearson          pearson -> delivered
PASS  ols              ols -> delivered
SKIP  ols_robust       no preset (G-fin-05)
PASS  risk             risk -> delivered
PASS  options          options -> delivered
PASS  fx               fx -> delivered
PASS  currency         currency -> delivered

0 failure(s), 1 known-blocked
```
