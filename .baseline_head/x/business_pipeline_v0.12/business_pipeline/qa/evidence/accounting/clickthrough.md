# Accounting click-through on http://127.0.0.1:8001

```
PASS  page marker 'railSubject'
PASS  page marker 'markCurrentRailItem'
PASS  page marker 'activate("new")'
PASS  page marker 'calculator'
PASS  page marker 'subjectgallery'
PASS  page marker 'not teacher-approved'
PASS  page marker 'Confirm the account mapping and post'
PASS  no reviewer surface 'Reviewer name'
PASS  no reviewer surface 'Sign-off'
PASS  no reviewer surface 'Review status'
PASS  GET /api/cases/subjects/accounting -> 200, 12 tools
PASS  accounts         accounts -> delivered (2 checkpoints)
PASS  tbcheck          tbcheck -> delivered (1 checkpoint)
PASS  ratios           ratios -> delivered (1 checkpoint)
PASS  scv              scv -> delivered (1 checkpoint)
PASS  abc              abc -> delivered (1 checkpoint)
PASS  salesvar         salesvar -> delivered (1 checkpoint)
PASS  breakeven        breakeven -> delivered (1 checkpoint)
PASS  multibreakeven   multibreakeven -> delivered (1 checkpoint)
PASS  workingcapital   workingcapital -> delivered (1 checkpoint)
PASS  loan             loan -> delivered (1 checkpoint)
PASS  trendanalysis    trendanalysis -> delivered (1 checkpoint)
PASS  tax              tax -> delivered (1 checkpoint)

0 failure(s)
```
