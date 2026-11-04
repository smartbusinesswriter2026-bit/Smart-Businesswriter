# BUNDLE PRICING — Write Smarter + Smart Business Writer

**Status: the payment side is built and unit-tested (2026-11-03); the live charge is not yet
taken, and the shared login is not yet built.** If a session starts with no context, this file is
the whole brief. Read §5 for what exists and §6 for what still has to be *proved* against live
PayPal.

Verified against the code on **2026-11-03**. Anything not verified is marked **owner to supply**.

**What was built since this file was first written** (B-208, B-209):

| Piece | Where |
|---|---|
| The bundle tier — $99.99 / $959.90, "Unlimited", both products | `src/bp/product/billing.py` (`PLANS`, the `agency` key, an `unlimited` flag) |
| A plan change that prorates, on the running subscription | `src/bp/product/paypal.py` (`change_plan`), `POST /api/billing/change` |
| The ledger records a plan change (it used to be first-wins) | `src/bp/product/billing.py` (`activate`, `_activation`, `current`) |
| The unlimited wallet — a bundle holder never receives a 402 | `src/bp/product/credits.py`, `src/bp/product/api.py` |
| The hand-off to the other product, so the charge happens once | `src/bp/product/write_smarter.py` (new), `POST /api/billing/confirm`, `POST /api/billing/cancel` |
| The other product's side of the hand-off | Write Smarter's `Backend/bundle-entitlement.js` (new), `POST /api/pay/paypal/bundle-entitlement`, `GET /api/pay/paypal/bundle-status`, the unlimited pool tier in `auth.js` |
| The bundle **band** below the pricing grid, and the account page | `web/index.html`, `web/account.html` |
| Tests | `tests/test_product_bundle.py` (37), `tests/test_product_billing.py` (updated), Write Smarter's `Backend/tests/bundle-entitlement.test.mjs` (9) |

**Not built:** the one shared login (I4) — the owner asked for the payment to be proved against
live PayPal first. **Not yet done:** the live charge itself, so §6's seven checks are still open.

---

## 1. What the owner decided (2026-11-03, plain language)

1. **There is a bundle at $99.99/month that gives unlimited use of both products.** Not a
   combination of two metered tiers — *unlimited* on both sides.
2. **One charge.** The bundle is one order that creates a subscription on each product's PayPal
   app, but the customer is billed **once, $99.99**. Two live $99.99 subscriptions would charge
   $199.98, so one of them must not bill.
3. **One login.** A customer signs up once and the same email + password works on
   `write-smarter.com` and inside the Smart Business Writer workbench.
4. **Smart Business Writer's existing $99.99 tier (Agency) becomes the bundle.** One $99.99
   meaning across both sites.
5. **The lower tiers keep their current prices** and stay single-product, so the $7.99 entry
   point survives.
6. **The lower bundle tiers carry limits, not unlimited.** The owner will set those limits later.
   The bundle's **Write Smarter limit is the same limit the business pipeline defines for that
   tier** — one limit, set on the Smart Business Writer side, applied to both products.
7. **The purchase happens in Smart Business Writer, not in Write Smarter.** The bundle is
   marketed through Smart Business Writer; the money is taken by Smart Business Writer's own
   checkout. *(Owner correction, 2026-11-03 — the earlier draft had it the other way round.)*
8. **Switching plans is "just adjust"**: PayPal changes the plan on the subscription and prorates
   the unused part of the period — the difference is charged on an upgrade and credited on a
   downgrade. No cancel-and-resubscribe. *(Owner correction, 2026-11-03.)*
9. **Order of work: the payment first.** The payment is settled and proved against live PayPal
   before the limits, the allowance numbers and the credit refill are built.
10. **Smart Business Writer is hosted over HTTPS on a VPS** (owner, 2026-11-03), so its own
    checkout can run — the PayPal SDK needs an HTTPS origin, and the workbench no longer only
    runs on a laptop.

The first draft of this brief described the bundle as "Write Smarter Pro + Smart Business Writer
Agency". **That was wrong** and the owner corrected it: the bundle is unlimited, so there is no
pair-of-tiers to aggregate and no "20% off the sum" claim to make.

---

## 2. The prices

### 2.1 Write Smarter — unchanged, metered (from the live pricing page)

| Tier | SKU | Monthly | Annual | Text-Gen | Humanizer | Video |
|---|---|---|---|---|---|---|
| Basic | `tier_1` | $7.99 | $76.70 | 25,000 words | 5,000 words | 30 min |
| Standard | `plus` | $14.99 | $143.90 | 50,000 words | 12,000 words | 2 hrs |
| Pro | `tier_2` | $24.99 | $239.90 | 100,000 words | 30,000 words | 6 hrs |

Annual = monthly × 12 less 20%. Pools: Text-Gen, Research Assistant, Humanizer & AI-Detector,
Video. Source Finder is unlimited on every plan. Arabic / Spanish / Mandarin count 3× toward
Text-Gen. Free tier: 3 generations a week, 250 words each, no account.

### 2.2 Smart Business Writer — the checkout, and the bundle

| Tier | Monthly | Annual | Allowance |
|---|---|---|---|
| Starter | $14.99 | $143.90 | to be confirmed |
| Pro | $29.99 | $287.90 | to be confirmed |
| Studio | $49.99 | $479.90 | to be confirmed |
| Agency → **the bundle** | $99.99 | $959.90 | **unlimited** |

Source: `src/bp/product/billing.py` — `PLANS`, `ANNUAL_DISCOUNT = 0.20`, `price()`,
`annual_saving()`, `card()`, `catalogue()`.

**$99.99 / month · $959.90 / year** (annual = 99.99 × 12 less 20%, derived — do not hand-type it).

The bundle is a **declared price, not a discount**: "unlimited Write Smarter + unlimited Smart
Business Writer" has no published sum to take 20% off. Do not put a "% off" or "save $" line on
that card.

### 2.3 Lower bundle rungs — proposed, NOT confirmed, deferred by the owner

| Rung | Write Smarter | Smart Business Writer | Monthly | Annual | Saving |
|---|---|---|---|---|---|
| Bundle Basic | Basic | Starter | $18.99 | $182.30 | $3.99 |
| Bundle Standard | Standard | Pro | $35.99 | $345.50 | $8.99 |
| Bundle Pro | Pro | Studio | $59.99 | $575.90 | $14.99 |
| Business Bundle | unlimited | unlimited | $99.99 | $959.90 | — |

Rungs 1–3 are the two published prices less 20%, rounded to `.99` — so the true discount is
17.4% / 20.0% / 20.0%, not a flat 20%. The limits are **not pooled**: one limit value per tier,
enforced once per product, in each product's own unit (words on the Write Smarter side, exports
on the Smart Business Writer side).

---

## 3. Verified facts — do not re-derive these, they were checked

- **Both products share one PayPal merchant account.** The `.env` files at
  `business_pipeline_v0.12/business_pipeline/Backend/.env` and `D:\Write-Smarter\Backend\.env`
  carry the **same** `PAYPAL_CLIENT_ID` and the same 80-character secret, both
  `PAYPAL_ENV=live`. (The client id is the public one the browser SDK loads; the secret was never
  printed.) Consequence: either backend can create plans and subscriptions for the other, the
  Smart Business Writer side can read the Write Smarter subscription directly, and PayPal's vault
  lets a second subscription be created from the first approval's payment source.
  **Therefore: two live $99.99 subscriptions would charge $199.98 a month.** The Write Smarter
  side's subscription must be created and then made not to bill (suspend or cancel — prove which
  against live PayPal; do not assume the verb). Because a switched-off record does not renew,
  **both products watch the real subscription for status**, never the record.
- **Smart Business Writer's checkout needs an HTTPS origin — and it has one.** The workbench runs
  at `http://127.0.0.1:8000` when local, so `web/index.html` states in its own error copy that
  PayPal's script will not load and "the page needs an HTTPS origin … Nothing was charged", and
  HANDOFF §3 says "live checkout generally needs an HTTPS origin". `deploy/README.md` and
  `deploy/nginx.conf` exist for exactly this (TLS terminated at nginx, one instance behind it).
  **The owner confirmed on 2026-11-03 that Smart Business Writer is hosted over HTTPS on a VPS**,
  so the bundle's checkout has a working origin. The hosted instance can also reach the Write
  Smarter service directly — which is what the shared login and the vault handoff need.
- **The ledger is first-wins on a subscription id, so a plan change would not be recorded.**
  `src/bp/product/billing.py:175-178` — `activate()` returns the *first* activation event for a
  subscription id and records nothing after it; `current()` (`:223-227`) takes the last activation
  event overall; `_activation()` (`:205-211`) returns the first one, and `cancel()` uses it. A
  PayPal plan change keeps the **same subscription id** with a new plan, so an upgrade from
  Starter to the bundle would never appear on the account page. The plan-change path must make
  `current()` and `_activation()` read the **latest** activation for that subscription id, and
  must ship a trap test.
- **There is no public Smart Business Writer marketing or pricing site.** The only Smart Business
  Writer checkout in existence is the pricing dialog inside the workbench: `web/index.html`
  `pmCheckout()` → `POST /api/billing/subscribe` → `src/bp/product/paypal.py`
  `create_subscription()`. The `mockup/` and `DEMO/` pages are mockups and a submission demo, not
  a storefront. **"The purchase happens in Smart Business Writer" therefore means in the
  workbench's Pricing dialog** (or on a hosted instance of it) — a hosted Smart Business Writer
  pricing page would be new work.
- **The Write Smarter code on this disk is stale.** `D:\Write-Smarter` and
  `D:\AA-WRITE SMARTER COPY FROM VPS\Backend` are March 2026 snapshots on a *different* price model
  ($9.99 / $24.99 / $49.99, one-time PayPal orders, SKUs `tier_0`–`tier_3`). The live page the
  owner supplied is the subscription model ($7.99 / $14.99 / $24.99, SKUs `tier_1` / `plus` /
  `tier_2`, annual toggle, `/api/pricing-mode`, `/api/pay/paypal/subscribe` +
  `/api/pay/paypal/subscription-confirm`). **Pull the live backend before editing it.** SSH alias
  `vps` → `root@75.119.136.89`, key present in `~/.ssh` (`id_ed25519`, config has the `vps` host).
- **Smart Business Writer has exactly one meter: the export wallet.**
  `src/bp/product/api.py:955-958` quotes before every export and returns **402** when the cost
  exceeds the balance; `src/bp/product/credits.py:133` enforces it. `PRICE_TABLE` =
  html 0, csv 0, docx 1, spreadsheetml 1, xlsx 1, pptx 3. The **first export of an artefact is
  free whatever its format**.
- **Nothing in the product layer gates a feature on the plan.** No "upgrade required" path exists;
  the plan is a record and a label today. Every tier's `credits` is `None`, which the catalogue
  returns as `null` and the page prints as "to be confirmed".
- **The wallet never refills.** `credits.py:80-86` grants the free tier's 100 credits **once per
  account, ever** (`_grant_if_new` fires only when the account has no ledger entries). There is no
  subscription cycle behind it and no top-up path. A paid tier that promises "N exports a month"
  needs a per-cycle refresh that **does not exist yet**.
- **The wallet ledger is already keyed by account** (`credits.py:89-96`, `account="local"` today),
  so per-account wallets for the shared login are a parameter change, not a new store.
- **Smart Business Writer has no accounts, no login and makes no outbound network calls** by
  design — `web/account.html:16-24` states it as a product promise. `deploy/README.md:13` lists
  "no authentication, tenancy or per-user quota" and `:64` lists per-user isolation and auth as
  **not done**. The shared login overturns that promise, so `web/account.html` must be rewritten
  and `deploy/README.md` updated.
- **D1 reopens.** `docs/PRODUCT_BACKEND_PLAN.md:13` records the deployment model as
  "Local single-user v1: one person, one machine, files on disk, no accounts". The shared login
  is an amendment to D1 and should be recorded as one, not smuggled in.
- **Smart Business Writer's checkout has never taken an approved payment** (HANDOFF §3, B-163:
  "the one step never taken is an approved payment, so a real charge is untested"). The bundle's
  first real charge lands here.
- **Layout facts — SUPERSEDED 2026-11-03.** The Smart Business Writer pricing dialog grid was
  `repeat(4,minmax(0,1fr))` (`web/index.html:425`), so the bundle was drawn as the **fourth card**.
  The owner looked at the dialog and said the bundle was not visible there, and the reason was
  structural: *a fourth card in the pricing grid reads as "a fourth tier of this product"*, and the
  bundle is two products at one price. **The bundle is now a band below the grid**, the three
  single-product tiers sit in a **three**-column grid, and the band names what the one price buys in
  each product. The Write Smarter grid is `repeat(3,1fr)`. The Write Smarter stylesheet carries an
  **unused** `.tier-plus` gold treatment (gold button, navy text) — a ready hook for a band row's
  distinct look.

---

## 4. What the owner still has to supply

### 4.1 Smart Business Writer tier details — **DEFERRED by the owner (2026-11-03)**

The owner has not decided the allowance numbers yet and will add them later. This is **not** a
blocker for the $99.99 bundle, and it must not stop the payment work. Fields needed when the
owner is ready:

| Tier | Export credits per cycle (or "unlimited") | Write Smarter limit — *the same value, in words* | Price confirmed? |
|---|---|---|---|
| Starter | | | $14.99 |
| Pro | | | $29.99 |
| Studio | | | $49.99 |
| Agency (the bundle) | unlimited | unlimited | $99.99 |

Two readings of "per cycle" to confirm with the owner: **per billing month** (reset on the
subscription date) or **per calendar month**. The existing free grant of 100 export credits is
the anchor — a paid tier should be above it. Note the wallet's own rules: the **first export of
an artefact is free whatever its format**, and a *second* format of the same artefact is charged.

### 4.2 Whether the lower rungs ship at launch — **DEFERRED by the owner (2026-11-03)**

One SKU ($99.99 only) or four (`$18.99` / `$35.99` / `$59.99` / `$99.99`). The owner has not
decided; the lower rungs carry limits the owner will set later. Recommendation on the record:
**one SKU at launch**; add the ladder when the allowance and the per-cycle refresh exist.

### 4.3 Where the Write Smarter pricing page points — **OPEN (owner asked for plain wording)**

The purchase happens in Smart Business Writer, so the Write Smarter page's bundle band cannot take
money. Two choices, in plain words:

- **Advertise it** — the band stays at the bottom of the Write Smarter pricing page, shows
  "$99.99/month — unlimited Write Smarter + unlimited Smart Business Writer", and its button
  **sends the visitor to Smart Business Writer to buy**. Nothing is charged on write-smarter.com.
- **Leave it off** — the Write Smarter page shows only its own three tiers, and the bundle is
  advertised and sold only through Smart Business Writer.

Recommendation on the record: **advertise it**. The Write Smarter page is the largest audience
either product has, and the bundle is the strongest offer either product makes. It needs the
**Smart Business Writer URL to point at — the owner to supply the hosted URL** (or the marketing
landing page) for that button.

### 4.4 Nothing else blocks the $99.99 bundle.

---

## 5. The build, in order

**The payment first** (owner instruction). The PayPal mechanics do not depend on the login — the
login only decides *which account* the subscription attaches to — so the charge, the vault
handoff, the Write Smarter-side record and the proration can all be built and **proved with a
real $99.99 charge** before the identity work starts.

| # | Scope | Where | Acceptance | State |
|---|---|---|---|---|
| **I0** | Decision row + D1 amendment | `docs/DECISIONS.md` (next B-number), `HANDOFF.md`, `KNOWN_LIMITATIONS.md`, `WORKLOG.md` | The bundle's price, the one-charge rule, the one-login rule, that the purchase is taken in Smart Business Writer, what it grants and what it does not | **Done** — B-208, B-209 |
| **I1** | Smart Business Writer: the bundle tier and its checkout | `src/bp/product/billing.py` (`PLANS` — keep the `agency` key so the PayPal plan cache and the ledger stay valid; display name becomes the bundle; add an `unlimited` flag, not a number), `src/bp/product/paypal.py` (the bundle plan, and **a plan-change method that prorates**), `src/bp/product/api.py` (the checkout attaches to the signed-in account; the export route consults the plan), `web/index.html` (the bundle band below the grid) | The pricing dialog's **band below the grid** is the bundle at $99.99 reading "Both products" and naming what the one price buys in each product; one real approved $99.99 charge is recorded **once**; an upgrade from Starter prorates and the recorded tier changes | **Built and tested.** The live charge is §6's job, not done yet. "The checkout attaches to the signed-in account" waits on I4. |
| **I2** | The plan-change path and the ledger fix | `src/bp/product/billing.py` (`activate()` must record a tier change for the same subscription id; `current()` and `_activation()` must read the **latest** activation for that id), `src/bp/product/paypal.py` (`change_plan()`), `src/bp/product/api.py` (the change route), tests | Starter → bundle on the same subscription id updates the account page; a trap test fails on the old first-wins code; downgrade credits the unused time | **Built and tested.** The proration itself is PayPal's arithmetic and is passed on untouched (`billing_info.outstanding_balance`); the live proof is §6.3. |
| **I3** | The Write Smarter side of the payment | live Write Smarter `Backend` (pull from `vps` first): the entitlement endpoint, the Write Smarter-side subscription record created from the vault and switched off, the unlimited grant for the account | One charge appears; the Write Smarter-side record never bills; the account is unlimited on the Write Smarter side | **Built and tested** — `Backend/bundle-entitlement.js`, two service routes, the unlimited pool tier in `auth.js`, 9 Node tests. The live proof is §6.2. |
| **I4** | One shared login | new `src/bp/product/identity.py`, auth routes, per-account wallet / cases / state, sign-in in the workbench, `web/account.html` rewritten | The same email + password signs in on both products; the plan and the wallet are per account; the workbench still works offline; existing machine-local records migrate without loss | **Not built** — the owner asked for the payment to be proved against live PayPal first |
| **I5** | The Write Smarter pricing page | live `pricing.html` — the band as a pointer (§4.3), or none; the modal credits line | The page points at the Smart Business Writer purchase; it never implies the money is taken there | **Not built** — blocked on the owner's hosted URL (§4.3) |
| **I6** | The unlimited wallet | `src/bp/product/credits.py` (the wallet stops blocking for an unlimited account), `web/account.html` | A bundle holder never receives a 402 on an export | **Built and tested** |
| **I7** | **DEFERRED by the owner** — the per-tier limits, the lower bundle rungs, and the per-cycle credit refill | `src/bp/product/billing.py`, `src/bp/product/credits.py`, the Write Smarter pool checks | Each rung carries one limit — the business pipeline's limit for that tier, applied in each product's own unit; the wallet refills on the subscription date; the limits are stated, never estimated | **Deferred** — B-180a, B-180b |
| **I8** | Docs + release | `HOME.md`, `CONTRIBUTORS.md`, `CHANGELOG.md`, `WORKLOG.md`, `KNOWN_LIMITATIONS.md` | Counts and version digits updated per B-081; `scripts/ci.py` green | **In progress** — this pass |

### 5.1 How the one charge works (the design, now built)

- **Smart Business Writer's checkout takes the money**: the bundle plan
  "Smart BusinessWriter - Business Bundle (monthly)" at $99.99, created on first use and cached in
  `state/paypal_plans.json` under the price hash, exactly as `paypal.plan_id()` already does for
  the other tiers. The cache key also carries the plan's **name**, because a PayPal plan id is
  immutable and cannot be renamed under a new label.
- On approval, Smart Business Writer verifies the subscription with PayPal, records it in its
  ledger, and grants the unlimited plan locally.
- The workbench then hands the approved subscription's `payment_source.vault_id` to the **hosted
  Write Smarter service** (`src/bp/product/write_smarter.py` → `POST /api/pay/paypal/bundle-entitlement`),
  which creates its **own** subscription record ("Write Smarter — Business Bundle") from that vault
  and switches it off so it never bills. Two guards: the record's plan is **$0**, and the switch-off
  is proved by reading the record back — a record PayPal still calls ACTIVE fails the grant rather
  than being reported as switched off. That service also grants the unlimited entitlement on the
  Write Smarter side.
- Status is re-read on demand, never pushed — PayPal cannot reach a laptop, and the repo already
  works this way. **Both sides watch the real subscription**, not the Write Smarter-side record.
- Cancelling from either side stops both: cancelling here revokes the grant on the other product,
  and the other product reads the *real* subscription's status, so a cancellation made there stops
  this one too.
- **Switching plans** = PayPal plan change with proration: the subscription id stays, PayPal
  charges the difference for an upgrade and credits the unused time for a downgrade. The ledger
  must record that tier change (§3, the first-wins finding).
- **A failed hand-off never undoes a real payment.** The customer paid and the subscription is
  ACTIVE, so the local grant stands; the failure is reported as a failure of the *other* product's
  half, with the reason, on the confirm and cancel replies and on the account page.
- **The vault id is remembered between the two calls.** PayPal names the vault id when it *creates*
  a subscription and does not always name it when the subscription is *read back*. The note kept at
  creation (`state/pending_subscriptions.json`) is what the confirmation falls back on, and it is
  dropped once the subscription is confirmed. This matters for the live test: without it the
  bundle would be granted here and not there, and the failure would look like a PayPal problem
  rather than a missing note.

---

## 6. Verification that must be *proved*, not asserted

1. One approved $99.99 charge on the bundle plan — **the first real charge this product has
   taken** (HANDOFF §3, B-163). **Open.**
2. The Write Smarter-side subscription **never bills** — absence of a second charge, and the
   subscription's `billing_info.next_billing_time` read back. **Open.** The code proves the
   switch-off and the $0 plan; the live account has not been watched yet.
3. An upgrade from a cheaper tier prorates, the difference is charged, and the recorded tier
   changes. **Half open.** The recorded tier changes and the adjustment is passed on untouched
   (unit-tested); PayPal's own arithmetic on a live subscription is not yet observed.
4. Cancelling one side stops both products. **Open.** The revocation path and the
   real-subscription status read are built and tested; the live round trip is not yet run.
5. Annual bills $959.90 once. **Open.**
6. A bundle holder really is uncapped: the export route never returns 402. **Open on the live
   account** — the unit test proves the route's behaviour against the recorded plan.
7. The same credentials sign in on both products, and the plan shows on both. **Not built**
   (I4) — and it waits on checks 1-2.

### 6.1 What the live test needs, before it is run

| Setting | Where | Why |
|---|---|---|
| `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_ENV=live` | Smart Business Writer's `Backend/.env` | Already set (the merchant account is shared) |
| `BP_WRITE_SMARTER_URL` | Smart Business Writer's `Backend/.env` | The hosted Write Smarter service — **owner to supply** |
| `BP_BUNDLE_HANDOFF_SECRET` | **Both** products' `.env` | The shared secret; it must be the same value on both sides — **owner to supply** |
| `PAYPAL_PLAN_ID_BUNDLE_RECORD` | Write Smarter's `.env` | A **$0** PayPal plan for this side's own record, so even a failed switch-off could not take a second payment — **owner to create** |
| `PAYPAL_PLAN_ID` for the bundle | Smart Business Writer's `Backend/.env` | The $99.99 plan — the product creates and caches it itself, so it needs no manual step |

The $0 plan is the one setting the product cannot create for itself, because a $0 plan is not a
plan this product would ever sell. Until it exists, the hand-off **fails closed** with a named
reason rather than creating a record that could bill.

---

## 7. Non-negotiables that apply to this work

- **No invented numbers.** Every allowance that has not been decided is named as undecided, not
  estimated — that is why the bundle's Smart Business Writer half must print "Unlimited" (an
  owner declaration) and never a guessed figure.
- **No silent framework substitution** and no rendering-layer price edits: the price lives in
  `billing.py` (Smart Business Writer) and in the page's `PRICING` object (Write Smarter).
- **A paper never contains template instructions**; the same applies to the pricing page — no
  instruction text ships to a customer.
- **Export stays blocked when the paper is incomplete** — untouched by this work.
- **Global product.** No PSE/PSEi name, no Philippine place name, no home-market example,
  currency or market claim (B-177). Both products are USD; keep it that way.
- **Stdlib only at runtime** in the Smart Business Writer product layer.
- **Fail closed**: a missing credential, an unknown SKU or an unverifiable subscription blocks
  with a reason; nothing pretends a payment happened.

---

## 8. Where the code lives

| | Path |
|---|---|
| Smart Business Writer (this repo) | `D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline` |
| ↳ product layer (billing, PayPal, API) | `src/bp/product/` — `billing.py`, `paypal.py`, `credits.py`, `api.py`, **`write_smarter.py`** |
| ↳ workbench UI | `web/index.html`, `web/account.html` |
| ↳ credentials | `Backend/.env` (`PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_ENV`, `WRITE_SMARTER_URL`, `BUNDLE_HANDOFF_SECRET`) |
| ↳ deployment slice | `deploy/` — `README.md`, `nginx.conf`, `Dockerfile` |
| Write Smarter (local, **stale**) | `D:\Write-Smarter` — `Backend/`, `FrontEnd/pricing.html` |
| Write Smarter (live) | VPS `vps`; the live pricing page was supplied as a turn attachment |
| ↳ the pulled live backend, with this work's edits | `D:\Write-Smarter-live\Backend\` — `bundle-entitlement.js` (new), `tests/bundle-entitlement.test.mjs` (new), `auth.js` (the unlimited pool tier), `server.mjs` (the two service routes) |
| ↳ the patch to apply to the VPS | `D:\Write-Smarter-live\bundle-entitlement.patch` |

Run the tests from the repo root:

```powershell
Set-Location "D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
$env:PYTHONPATH="src"
python -m unittest discover -s tests     # read the "OK" line, not the exit code
python -m bp.server 8000                 # workbench at http://127.0.0.1:8000
```

The other product's tests:

```powershell
Set-Location "D:\Write-Smarter-live\Backend"
node --test tests/bundle-entitlement.test.mjs
```

---

## 9. Cold start

1. Read this file, then `docs/HANDOFF.md` §3 (the pricing and PayPal bullet) and
   `docs/DECISIONS.md`'s last three rows.
2. Check the table at the top of this file against the code (`git status`, `git log -5`). The
   payment side is built; **the live charge has not been taken**, so §6 is where the work is.
3. Check whether the owner has supplied §4.1 — that is the only input the lower rungs need, and
   it does not block anything else.
4. **Next: run the live test (§6.1 lists what it needs).** Do not start I4 (the shared login)
   before the charge is proved. Do not touch the Write Smarter backend before pulling it from
   `vps`; the working copy is already at `D:\Write-Smarter-live` with its patch.
