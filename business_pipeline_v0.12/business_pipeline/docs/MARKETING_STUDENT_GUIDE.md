# Marketing & customers for students

This guide explains what the Marketing & customers shelf is for, what it assumes and how to use it on the
marketing section of a business plan, a case analysis or a marketing course assignment. It is written for
**senior high school ABM** students and for **first- and second-year undergraduate** students taking
principles of marketing, digital marketing or marketing analytics. Every number below is produced by the
method named, from the figures shown, in PHP, and can be reproduced in the app with the preset named.

The shelf does not connect to Google Analytics, Meta, Google Ads or any other platform, and it does not
recommend a budget. It computes the figures **you** declare, runs its checks and states what it cannot tell
you - so a marker can see where every number came from and what it does not prove.

## Reading the page

The page follows the order a marketing plan is written in, not the difficulty of the arithmetic:

| Group | What it is for | Tiles |
|---|---|---|
| Market size and demand | Size the market and describe what customers will buy | market size, demand line, price elasticity, purchase intent, trend forecast |
| Customer economics and retention | Check whether a customer is worth winning and keeping | unit economics, multi-product break-even, cohort retention |
| Campaigns, channels and web analytics | Measure the campaign and the channels that feed it | campaign efficiency, attribution, channel economics, email list health, social reach and engagement, web traffic and conversion |
| Funnel, surveys and testing | Follow the funnel, test a change, and check the survey | sales funnel, A/B test result, reliability (alpha), chi-square, power and sample size |

Each tile shows the period convention it expects - **annual**, **per period**, **per observation** - and an
expandable study note with the formula, the steps and the mistakes that most often cost marks. A monthly
campaign figure must never be entered as an annual one; an A/B test is per observation, not per period.

Below the tiles sit the **records**: 11 Marketing frameworks, 6 Customer and market analytics records and 16
Digital marketing records. A row marked **computed** already has a method the engine runs; **worksheet**
means a template you fill in; **no worksheet yet** means the framework can be read and cited but not worked
through here. The label says what the product can do with the record today - it is not a judgment on whether
the framework is valid.

## Your assignment requirement, and the tool that answers it

| What the assignment asks for | Tool | What you must supply |
|---|---|---|
| How big is the market, and how much can we serve and win? | `market_sizing` | customers in the market, annual spend per customer, a serviceable share, an obtainable share |
| What price and quantity will the market bear? | `demand_curve`, `elasticity` | price-quantity pairs from the same market, or two price-quantity observations |
| Will customers actually buy? | `purchase_intent` | survey counts by intent level, your weights, the population and price |
| What is a customer worth? | `unit_economics` | price, variable cost, acquisition cost, churn |
| Do we keep the customers we win? | `cohort_retention` | each cohort's starting size and the count still buying in each period |
| Where do we lose people between first contact and the sale? | `sales_funnel` | the stage counts in order and, optionally, the spend |
| Did the campaign pay for itself? | `campaign_efficiency` | impressions, clicks, conversions, spend, revenue, and optionally the contribution margin |
| Which channel gets credit for the sale? | `attribution_split` | each channel's credited conversions under first-click, last-click and linear |
| Which acquisition channel is worth the money? | `channel_economics` | each channel's spend, new customers, contribution margin and churn |
| Is our email list growing and still engaged? | `email_list_health` | list start, new subscribers, unsubscribes, bounces, sends, opens, clicks, revenue |
| Did our social activity reach and engage people? | `social_engagement` | impressions, reach, engagements, starting followers, net follower change, spend |
| Which traffic channel turns visits into revenue? | `web_analytics` | sessions, conversions and revenue by channel, optionally organic impressions and clicks |
| Did the new page really convert better? | `ab_test_two_proportion` | visitors and conversions for both arms, your alpha, and the effect worth detecting |
| How many visitors does the test need? | `power_analysis`, `ab_test_two_proportion` | the baseline rate, the effect you care about, your alpha and power |
| Are the survey items measuring one thing? | `reliability_alpha` | every respondent's answer to every item |
| Is answer A associated with segment B? | `chi_square` | the cross-tabulated counts |

If a requirement is not in the table, the shelf probably does not compute it: see **What is not built** at the
end rather than forcing a number into the nearest tool.

## Conventions used throughout

1. **Rates are decimals.** 6% is `0.06`, not `6`. The app warns when a rate above 100% appears, because that
   usually means a decimal was typed as a percentage.
2. **A conversion is what you declared it to be.** A "conversion" is not comparable across campaigns that
   define it differently, and the report says so.
3. **Revenue is what you attributed.** The engine never claims that attributed revenue was *caused* by the
   campaign. Only a controlled experiment can speak to cause.
4. **Periods must match.** Impressions, clicks, spend and revenue must cover the same window, and sessions,
   conversions and revenue must cover the same window.
5. **Declare, do not default silently.** Optional inputs (contribution margin, organic impressions, posts, a
   minimum detectable effect) change what is reported. When one is absent, the report says the figure is not
   reported rather than guessing.
6. **Nothing is read from a platform.** Every count is typed in by you, so a platform's own attribution window,
   bot filtering or deduplication is not applied.

## Worked examples

### 1. Did the campaign pay for itself? - `campaign` (`campaign_efficiency`)

Inputs: 250,000 impressions, 6,000 clicks, 220 conversions, spend PHP 60,000, revenue PHP 150,000, contribution
margin 45%.

- Click-through rate = 6,000 / 250,000 = **2.40%**
- Cost per click = 60,000 / 6,000 = **PHP 10.00**; cost per thousand impressions = **PHP 240.00**
- Conversion rate = 220 / 6,000 = **3.67%**; cost per acquisition = 60,000 / 220 = **PHP 272.73**
- Return on ad spend = 150,000 / 60,000 = **2.50**; advertising cost of sales = **40.00%**
- Break-even return on ad spend = 1 / 0.45 = **2.22**
- Profit after media = 150,000 x 0.45 - 60,000 = **PHP 7,500.00**

The campaign is above break-even (2.50 against 2.22), but the margin is thin: a small rise in cost per click
would take it below. The report states that no incrementality is modelled - some of those conversions may
have happened anyway.

### 2. Did the new page convert better? - `abtest` (`ab_test_two_proportion`)

Inputs: 4,000 visitors and 320 conversions for A, 4,000 and 380 for B, alpha 0.05, power 0.8, minimum effect
10%.

- Rate A = **8.00%**, rate B = **9.50%**, absolute lift **1.50%**, relative lift **18.75%**
- Pooled rate = 700 / 8,000 = 8.75%; the pooled test gives z = **2.3740** and p = **1.76%**
- The 95% interval for the difference runs from **0.26%** to **2.74%**
- To detect a 10% relative lift at 80% power, each arm would need **18,869 visitors**

The test observed 4,000 per arm, so it was under-powered for the effect it was asked to find: the result is
significant, but the interval is wide and a repeat test could plausibly show a much smaller gain. Note also
that "significant" is not "proved": the method refuses to say the change caused the lift.

### 3. Which channel gets credit? - `attribution` (`attribution_split`)

Inputs: credited conversions under three rules.

| Channel | First-click | Last-click | Linear |
|---|---|---|---|
| Search | 420 | 260 | 320 |
| Social | 180 | 310 | 290 |
| Email | 120 | 150 | 110 |

Every rule allocates 720 conversions, but the shares move sharply: search gets **58.33%** of first-click
credit and only **36.11%** of last-click credit; social moves the other way. The largest disagreement across
the three rules is **22.22%**. That spread is the honest headline: "the value of search" depends on the rule
you chose, and credit is not causation.

### 4. Which acquisition channel is worth the money? - `channelecon` (`channel_economics`)

Inputs: search PHP 60,000 for 400 customers (margin 150, churn 4%); social PHP 35,000 for 180 (margin 95,
churn 6%); referral PHP 15,000 for 150 (margin 150, churn 3%).

- Acquisition cost: search **PHP 150.00**, social **PHP 194.44**, referral **PHP 100.00**
- Payback: search **1.00** period, social **2.05**, referral **0.67**
- Lifetime value: search **PHP 3,750**, social **PHP 1,583.33**, referral **PHP 5,000**
- Lifetime value per unit of acquisition cost: search **25.00**, social **8.14**, referral **50.00**
- Blended acquisition cost: 110,000 / 730 = **PHP 150.68**

Referral is the strongest channel on both payback and value; social is the weakest. The blended figure hides
that, which is why the page shows both. The report states that no cross-channel effect or saturation is
modelled: shifting budget would change all three numbers.

### 5. Is the list growing and engaged? - `email` (`email_list_health`)

Inputs: list 8,000, 600 new subscribers, 90 unsubscribes, 40 bounces, 7,500 sends, 2,250 opens, 450 clicks,
revenue PHP 38,000.

- List end = 8,000 + 600 - 90 - 40 = **8,470**
- Growth = **5.88%**; churn = 130 / 8,000 = **1.62%**
- Open rate = **30.00%**; click rate = **6.00%**; click-to-open = **20.00%**
- Revenue per subscriber = 38,000 / 8,470 = **PHP 4.49**

The open rate is an upper bound: a machine-opened message still counts. Read growth and churn together - a
growing list can still be losing its most engaged readers.

### 6. Did social reach and engage people? - `social` (`social_engagement`)

Inputs: 150,000 impressions, 95,000 reach, 5,700 engagements, 18,000 starting followers, 900 net new
followers, PHP 25,000 spend, 15 posts.

- Engagement rate = 5,700 / 95,000 = **6.00%**
- Frequency = 150,000 / 95,000 = **1.5789**
- Cost per thousand impressions = **PHP 166.67**; cost per engagement = **PHP 4.39**
- Follower growth = 900 / 18,000 = **5.00%**
- Engagement per post = **380**

Engagements are counted the way the platform counts them, so the rate is only comparable with the same
platform, the same definition and the same period. No bot filtering or sentiment is applied.

### 7. Which traffic channel turns visits into revenue? - `web` (`web_analytics`)

Inputs: organic search 42,000 sessions / 1,350 conversions / PHP 680,000; paid search 24,000 / 960 /
PHP 430,000; email 9,000 / 540 / PHP 260,000; organic 600,000 impressions and 24,000 clicks.

- Total sessions **75,000**, conversions **2,850**, blended conversion rate **3.80%**
- Revenue per session = 1,370,000 / 75,000 = **PHP 18.27**
- Session shares: organic **56%**, paid **32%**, email **12%**
- Conversion rates: organic **3.21%**, paid **4.00%**, email **6.00%**
- Organic click-through = 24,000 / 600,000 = **4.00%**

Email converts best but brings the smallest volume; paid converts better than organic but at a cost that this
tool does not see - pair it with `channel_economics`. Direct and unattributed traffic must be one of the rows
or every other channel's share is overstated.

## Practice set

Use the presets, change one input at a time, and write down the effect before you look.

1. With the `campaign` preset, cut spend to PHP 40,000 while revenue stays at PHP 150,000. What happens to the
   return on ad spend and to profit after media?
2. With the `campaign` preset, set the contribution margin to 30%. Is the campaign still above break-even?
3. With the `abtest` preset, halve both arms' conversions. Does the lift change? Does the verdict?
4. With the `attribution` preset, move 100 first-click conversions from email to social. Which channel's spread
   changes most?
5. With the `channelecon` preset, raise social's churn from 6% to 12%. What happens to its lifetime value and
   its ratio to acquisition cost?
6. With the `email` preset, double the bounces. Which figures move, and which do not?
7. With the `social` preset, raise reach to 120,000 while impressions stay at 150,000. Can reach exceed
   impressions?
8. With the `web` preset, add a `direct` row with 20,000 sessions, 200 conversions and PHP 100,000 revenue.
   Whose share falls?

### Answer key

1. Return on ad spend rises to 3.75 and profit after media to PHP 27,500; the cost per click and cost per
   acquisition also fall. Fewer clicks would normally mean fewer conversions, which is exactly the trade the
   tool cannot model.
2. Break-even return rises to 3.33, so 2.50 is now below it and profit after media is negative (PHP -15,000).
3. The **relative** lift stays at 18.75% and the absolute lift halves to 0.75%; the p-value rises to about 10%
   and the difference is no longer significant at 5%. Significance depends on the sample, not only on the gap.
4. Social's spread falls and email's rises; the maximum spread may move to a different channel. The totals stay
   at 720 under each rule.
5. Lifetime value halves (PHP 791.67) and the ratio falls to about 4.07, below search. Payback is unchanged,
   because payback uses the margin, not churn.
6. List end, growth and churn move; open rate, click rate and click-to-open do not, because they depend on
   sends, opens and clicks.
7. No. The method refuses reach above impressions, because that is not a rate question but an impossible count.
8. Every other channel's share falls (organic to about 44%, paid to 25%, email to 9% of 95,000 sessions), and
   the blended conversion rate falls to 3.21%; the tool cannot warn you about a channel you left out, because
   it only sees the rows you gave it.

## Handing it in

For each figure you report, state: the method or tile, the inputs you supplied (with their source), the
period, the currency, and the check the delivery passed. Where the report says the method cannot tell you
something - incrementality, platform reconciliation, bot filtering - keep that sentence in your write-up. It
is usually worth marks, and it is always more honest than a number with no limits.

## What is not built

- **Platform connectors.** No Google Analytics, Ads, Meta, TikTok or email-platform login. Every count is
  typed in, so it is only as good as your export.
- **Incrementality, holdouts and lift tests.** The tools measure association and declared attribution; none of
  them proves that a campaign *caused* a sale.
- **Multi-touch causal attribution, time-decay and data-driven models.** Only first-click, last-click and
  linear are compared.
- **Automated bidding, budget optimisation and spend recommendations.** The shelf describes; it does not
  advise.
- **Sequential tests, peeking-adjusted p-values, more than two arms, and Bayesian tests.** The A/B method is
  one two-proportion test at a declared alpha.
- **Sentiment, bot filtering, view-through, cross-device identity and consent analysis.** These need data the
  product does not read.
- **SEO rank tracking, keyword research and content scoring.** `MKT-14` is a read-only record: the plan can be
  written and cited, not computed here.
- **Lead scoring and marketing automation execution.** `MKT-21` is a read-only record for the same reason.
