# UI phase closure

**Status:** implementation complete for the student-facing workbench.
**Build:** 1.30 (UI orientation increment).
**Scope:** the local workbench in `web/index.html`, served by `bp.server`. It is presentation
only: every number, caveat, limitation, tier label and refusal message is printed exactly as
the API returned it. The client never computes a business number.

## What is closed

- [x] **Home has a path chooser.** “Which one do I need?” offers one calculation, one topic,
  a guided paper or a business plan, and each choice opens the right workspace.
- [x] **Every subject has a Student guide.** Each subject page states what the shelf is for,
  a “Start here” path with the recommended first tools, and an explicit “What this shelf
  does not do” list.
- [x] **The Help drawer explains the entry points and key words** — calculation, worked
  example, checks, T1/T2 and blocked — so a student can read the result without guessing.
- [x] **Plain-language orientation on the primary surface.** The Home steps now describe the
  case/paper path, the subject/calculator path and the checked result, instead of assuming
  the student already knows the product.
- [x] **Mobile and keyboard basics.** The decision grid stacks below 640 px, the rail is
  keyboard reachable, inputs carry labels, focus is visible and reduced motion is respected.
- [x] **The UI guards are in the suite.** The served-page test asserts the path chooser, the
  Student guide, the start steps, the Help key words and the existing build marker.
- [x] **No client-side arithmetic and no hidden caveats.** The result still shows the API’s
  report, checks, limits and refusal wording verbatim.

## What is not part of this closure

- **Backend/product features** that are not UI screens: AI-use disclosure export, reviewer
  sign-off workflow, case retention/privacy, model pinning/drift, security review and durable
  storage. These remain in `HANDOFF.md` §5F/§6 and are not claimed by this closure.
- **A formal usability study with students.** The implementation is test-guarded and reviewed
  against the closure standard, but no external student session has been recorded.
- **A full assistive-technology audit.** Keyboard, labels, focus, contrast, reduced motion and
  the 360 px layout are covered; a screen-reader pass with a real user is still advisable.
- **Subject catalogue depth.** Some subjects still show catalogued frameworks with no
  worksheet yet; those rows stay labelled as catalogue-only.

## How this was verified

- The full suite runs green; the served-UI test asserts the new orientation strings.
- The page’s JavaScript is syntax-checked with `node --check`.
- The UI still prints API text verbatim; no number is computed in the browser.
- Every subject now returns a non-empty guidance, start-step list and “does not” list from
  the product subject index.
