# Unfreeze request — People metrics the frozen core does not implement

**Status:** DRAFT request for the computation owner. It requests; it does not
decide, and it is not authority.

**Why it exists:** the People & organisation shelf is asked to cover headcount,
turnover, absence, hiring, pay position, workforce gap, engagement and the
nine-box distribution. `bp.methods.LIBRARY` (142 methods) implements none of them.
A similar method is not a substitute for a missing one, so nothing was built on
a substitute and the shelf says so on the page.

**What is already delivered without an unfreeze:** three calculators, each on an
existing frozen method with its own preset — training ROI
(`return_on_investment`), labour-market tightness (`labour_market`) and people
programme cost-effectiveness (`cost_effectiveness`).

**What each request below specifies:** the proposed method id, the tier, the
claim ceiling, the declared inputs, the outputs, the checks, and the work that is
refused. Every number is declared by the student. Nothing is estimated, imputed
or read from a system.

---

## 1. `workforce_headcount` — headcount and FTE

**Covers:** candidate 1 (headcount and FTE).

- **Tier:** T2. **Claim ceiling:** descriptive.
- **Inputs:** `headcount` (int, required); `fte` (decimal, required, the sum of the
  declared full-time equivalents); `roles` (record list, optional: `role`,
  `headcount`, `fte`).
- **Outputs:** `headcount`; `total_fte`; `average_fte`; `fte_by_role`; `part_time_equivalent`.
- **Checks:** `headcount_equals_the_sum_of_the_role_headcounts`; `total_fte_equals_the_declared_fte`;
  `average_fte_is_total_fte_over_headcount`; `fte_per_head_is_between_zero_and_one_point_five`;
  `a_negative_headcount_or_fte_is_refused`; `a_headcount_of_zero_is_refused`.
- **Refused:** inferring headcount from turnover; estimating FTE from hours
  worked without a declared contract; treating a headcount as a workforce sample.

## 2. `staff_turnover` — turnover and retention

**Covers:** candidate 2 (turnover and retention).

- **Tier:** T2. **Claim ceiling:** descriptive.
- **Inputs:** `headcount_start` (int); `headcount_end` (int); `leavers` (int);
  `starters` (int); `period_months` (int).
- **Outputs:** `turnover_rate`; `retention_rate`; `net_headcount_change`; `annualised_turnover_rate`.
- **Checks:** `turnover_is_leavers_over_headcount_at_the_start`; `retention_and_turnover_sum_to_one`;
  `starters_minus_leavers_equals_the_change_in_headcount`; `leavers_cannot_exceed_the_headcount_at_the_start`;
  `every_rate_is_between_zero_and_one`; `the_annualised_rate_uses_the_declared_period`.
- **Refused:** a voluntary / involuntary split that is not declared; a rolling
  twelve-month rate without a declared period; comparing two employers' rates
  without the same starting headcount basis.

## 3. `absence_rate` — absenteeism

**Covers:** candidate 3 (absenteeism).

- **Tier:** T2. **Claim ceiling:** descriptive.
- **Inputs:** `scheduled_days` (decimal, required); `absence_days` (decimal,
  required); `headcount` (int, optional).
- **Outputs:** `absence_rate`; `absence_days_per_head`; `lost_days`.
- **Checks:** `absence_rate_is_absence_days_over_scheduled_days`; `the_rate_is_between_zero_and_one`;
  `absence_days_cannot_exceed_the_scheduled_days`; `a_scheduled_days_of_zero_is_refused`.
- **Refused:** distinguishing sickness absence from other absence without a
  declared reason; imputing a rate for a period without declared days.

## 4. `recruitment_cost_and_time` — cost per hire and time to hire

**Covers:** candidates 4 and 5 (cost per hire, time to hire).

- **Tier:** T2. **Claim ceiling:** descriptive.
- **Inputs:** `hires` (int, required); `recruitment_cost` (decimal, required);
  `days_to_hire` (record list, optional: `days`, `role`); `source` (enum: agency,
  referral, internal, other).
- **Outputs:** `cost_per_hire`; `average_time_to_hire_days`; `median_time_to_hire_days`;
  `cost_per_hire_by_source`.
- **Checks:** `cost_per_hire_is_recruitment_cost_over_hires`; `a_hire_count_of_zero_is_refused`;
  `average_time_to_hire_is_the_mean_of_the_declared_days`; `the_median_is_the_median_of_the_declared_days`;
  `a_negative_cost_or_day_count_is_refused`.
- **Refused:** a time to hire that starts at the application rather than at a
  declared stage without saying so; attributing a cost per hire to a source that
  was not declared; a vacancy rate.

## 5. `pay_position` — compa-ratio and salary range penetration

**Covers:** candidate 7 (compa-ratio and salary range penetration).

- **Tier:** T2. **Claim ceiling:** descriptive.
- **Inputs:** `roles` (record list, required: `role`, `salary`, `midpoint`,
  `range_min`, `range_max`); `currency` (enum, optional).
- **Outputs:** `compa_ratio` (mean salary over mean midpoint, on the same roles);
  `range_penetration` (salary minus minimum over the range width, per role);
  `below_range_count`; `above_range_count`; `compa_ratio_by_role`.
- **Checks:** `every_midpoint_sits_inside_its_own_range`; `a_range_of_zero_width_is_refused`;
  `compa_ratio_uses_the_same_roles_in_both_figures`; `range_penetration_is_between_zero_and_one`;
  `a_negative_salary_is_refused`; `a_role_list_with_one_entry_is_refused`.
- **Refused:** a pay-equity conclusion from a compa-ratio; a gender or ethnicity
  pay gap without a declared and comparable grouping; a recommendation on pay.

## 6. `people_ratio` — the declared ratios of a workforce

**Covers:** candidates 8, 9, 10, 11 and 12 (span of control, revenue per employee,
labour cost as % of revenue, overtime %, benefits cost) and candidate 16
(diversity ratio).

- **Tier:** T2. **Claim ceiling:** descriptive.
- **Inputs:** `ratio` (enum, required, from a closed vocabulary: `span_of_control`,
  `revenue_per_employee`, `labour_cost_share_of_revenue`, `overtime_share`,
  `benefits_cost_share_of_labour_cost`, `diversity_share`); `numerator` (decimal,
  required); `denominator` (decimal, required); `headcount` (int, required for
  `span_of_control` and `revenue_per_employee`); `population` (record list,
  required for `diversity_share`: `group`, `count`).
- **Outputs:** `value`; `numerator`; `denominator`; `value_by_group` (for
  `diversity_share`).
- **Checks:** `the_ratio_is_the_declared_numerator_over_the_declared_denominator`;
  `a_denominator_of_zero_is_refused`; `every_value_carries_its_unit`; `the_share_ratios_are_between_zero_and_one`;
  `the_group_counts_sum_to_the_declared_population`; `the_ratio_comes_from_the_closed_vocabulary`.
- **Refused:** a ratio whose numerator or denominator the method would have to
  infer; a ratio outside the closed vocabulary; a diversity claim that compares
  groups the student did not declare.

## 7. `nine_box_distribution` — the nine-box count

**Covers:** candidate 14 (nine-box distribution).

- **Tier:** T2. **Claim ceiling:** descriptive.
- **Inputs:** `placements` (record list, required: `name`, `performance_band`
  (enum 1–3), `potential_band` (enum 1–3)).
- **Outputs:** `cell_counts` (nine); `headcount`; `share_by_cell`; `high_performer_high_potential_count`.
- **Checks:** `the_cell_counts_sum_to_the_headcount`; `every_band_is_one_to_three`;
  `no_person_appears_twice`; `the_share_by_cell_sums_to_one`; `an_empty_placement_list_is_refused`.
- **Refused:** placing a person the method would have to guess; a score or rank;
  a prediction of future performance; a calibration verdict.

## 8. `engagement_index` — engagement and eNPS

**Covers:** candidate 15 (engagement index and eNPS).

- **Tier:** T2. **Claim ceiling:** descriptive.
- **Inputs:** `items` (record list, required: `item`, `mean`, `scale_min`,
  `scale_max`, `responses`); `recommenders` (int, required for eNPS);
  `passives` (int, required for eNPS); `detractors` (int, required for eNPS).
- **Outputs:** `overall_index`; `item_means`; `responses`; `enps`; `response_rate_basis`.
- **Checks:** `the_overall_index_is_the_mean_of_the_declared_item_means`;
  `every_item_mean_sits_between_its_declared_scale_min_and_max`;
  `enps_is_the_promoter_share_minus_the_detractor_share`; `the_enps_denominator_is_the_sum_of_the_three_counts`;
  `a_negative_count_is_refused`.
- **Refused:** an engagement score that is not built from the declared items; a
  claim that engagement causes performance; a benchmark the method would have to
  supply.

## 9. `job_evaluation` — job evaluation points

**Covers:** candidate 17 (job evaluation points).

- **Tier:** T2. **Claim ceiling:** descriptive.
- **Inputs:** `roles` (record list, required: `role`, `factor_points` (record list:
  `factor`, `points`)); `grades` (record list, optional: `grade`, `min_points`,
  `max_points`).
- **Outputs:** `total_points_by_role`; `grade_by_role`; `ungraded_roles`.
- **Checks:** `the_total_points_are_the_sum_of_the_declared_factor_points`;
  `a_negative_point_value_is_refused`; `a_role_with_no_factors_is_refused`;
  `a_grade_band_is_assigned_only_when_the_points_sit_inside_it`; `a_role_outside_every_band_is_reported_as_ungraded`.
- **Refused:** assigning points to a factor; ranking roles on merit; a pay
  recommendation from the points.

---

## Why the nearest existing methods were not used

| Candidate | Method that looks close | Why it is not a substitute |
|---|---|---|
| Turnover and retention | `cohort_retention` | Its declared subject is customer cohorts; staff turnover is not that computation. |
| Cost per hire | `unit_economics` | It is customer acquisition economics: contribution per unit and payback. |
| Revenue per employee, labour cost share | `ratio_analysis` | It takes financial-statement lines (current assets, revenue, total liabilities) and computes statement ratios. People figures are not statement lines. |
| Workforce gap | `demand_supply_equilibrium`, `capacity_analysis` | The first is a market model with demand and supply curves; the second is resource capacity against demand. A workforce gap is required posts against people. |
| Engagement and eNPS | `cohort_retention`, `social_engagement` | The first retains customers, the second is a social-media engagement rate. |
| Diversity ratio | `gini_coefficient` | It measures inequality of a continuous income or wealth distribution, not a group share. |
| Headcount and FTE | `descriptive_stats` | It summarises a declared variable; it does not total a workforce or convert headcount to FTE. |
| Motivation | `theories` (THE-02) | It is a reading lens by design and computes nothing. |

## Cost of the request

Nine methods, all T2, all declared-input, all descriptive. Every one of them adds
to the frozen contract, so each needs the owner's unfreeze, a matching decision
row, the fixture update and the frozen-contract test in the same change.
