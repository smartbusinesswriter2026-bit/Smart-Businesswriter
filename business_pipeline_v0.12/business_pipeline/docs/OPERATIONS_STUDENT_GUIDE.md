# Operations and supply chain for students

This guide explains what the Operations management and Supply chain & logistics shelves are for, what
level they assume and how to use them on a process, capacity, inventory or queueing assignment. It is
written for **senior high school ABM** students and **first- and second-year undergraduate** operations
students. Every number below is produced by the method named, from the figures shown, in PHP, and can be
reproduced in the app.

The shelf computes from the figures you declare. It does not observe your process, estimate demand or
schedule the work.

## Reading the pages

| Group | What it is for | Tiles |
|---|---|---|
| Process and capacity | How much can the process make, and where is the constraint? | Capacity and bottleneck, queue length and waiting time, break-even, multi-product break-even, unit economics |
| Inventory and planning | How much stock, when to order, what it costs | Order quantity and reorder point, trend forecast, missing-data bounds, descriptive statistics |
| Quality and evidence | Is the process in control and capable, and is the evidence distinguishable from noise? | Overall equipment effectiveness, control chart and capability, chi-square association, power and sample size |

**Supply chain** carries the same process tools with the inventory-and-network, demand-and-planning and
cost-and-mix groups, because a distribution problem is an inventory and capacity problem first.

## Conventions

- **Capacity is steady-state.** Available hours x 60 / minutes per unit, with no allowance for breaks,
  changeover, maintenance or scrap unless you take them out of the available hours.
- **The bottleneck sets throughput.** Extra capacity at any other resource does not raise output.
- **Inventory costs are annual.** Annual demand pairs with an annual holding cost per unit.
- **Safety stock needs both** a service level and a demand standard deviation; without them the reorder
  point covers lead-time demand only.
- **A queue needs arrivals below the service capacity.** With one server that means below the service
  rate, with several servers below servers x service rate; at or above it the queue never clears and the
  method blocks.
- **OEE and capability are arithmetic on declared figures.** The method does not classify losses or judge
  whether a Cp is acceptable.

## Your assignment requirement, and the tool that answers it

| What the assignment asks for | Tool | What you supply |
|---|---|---|
| Where is the bottleneck, and what is the capacity? | `capacity_analysis` | each resource's name, available hours and minutes per unit |
| How long do customers wait? | `queue_analysis` | the average arrival rate and the single server's rate |
| How much should we order, and when? | `inventory_policy` | annual demand, order cost, holding cost, lead time and, optionally, variability and a service level |
| How much stock and cash does working capital tie up? | `working_capital` | revenue, cost of sales, inventory, receivables, payables |
| What does a product contribute, and where is break-even? | `breakeven`, `multi_product_breakeven`, `unit_economics` | fixed and variable costs, prices and mix |
| What is the trend in demand? | `trend_forecast` | a series in period order |
| Is the line effective, and is the process in control? | `oee_analysis`, `process_control` | planned time, downtime, cycle time and counts; or observations with optional specification limits |
| Is the difference between two groups real? | `chi_square`, `power_analysis` | your counts or the effect you want to detect |

## Worked examples

### 1. Capacity and the bottleneck — `capacity`

Cutting 8 hours at 5 minutes a unit (96 units), assembly 8 hours at 8 minutes (60), packing 8 hours at 3
minutes (160). Demand 50.

- Process capacity = **60 units**, set by assembly
- Utilisation: cutting 50/96 = **52.08%**, assembly 50/60 = **83.33%**, packing 50/160 = **31.25%**
- Capacity gap = 60 - 50 = **10 units**

**Common mistake:** adding the three capacities to claim a 316-unit process. The smallest resource sets
the rate.

### 2. A single-server queue — `queue`

18 customers arrive an hour; the server handles 24.

- Utilisation = 18/24 = **0.75**
- Customers in the queue = 0.75²/(1 - 0.75) = **2.25**
- In the system = 3.00; wait in the queue = 2.25/18 = **0.125 hours (7.5 minutes)**
- Time in the system = 3/18 = **0.167 hours (10 minutes)**

With two servers the same 18 arrivals give utilisation 18/(2 x 24) = 0.375, about **0.12 customers**
waiting and a wait of about **0.007 hours (25 seconds)**: adding a server does far more than halve the
queue.

**Common mistake:** reading 75% utilisation as "a quarter of the time idle, so no queue". Variability
puts 2.25 customers in line on average at that load.

### 3. Order quantity and reorder point — `inventory`

Annual demand 12,000; order cost 500; holding cost 30 a unit-year; lead time 10 days; service level 95%;
daily demand SD 20.

- EOQ = sqrt(2 x 12,000 x 500 / 30) = **632.46 units**; orders = **18.97** a year
- Safety factor z = **1.645**; safety stock = 1.645 x 20 x sqrt(10) = **104.03**
- Reorder point = (12,000/365 x 10) + 104.03 = **432.80 units**
- Average inventory = 316.23 + 104.03 = 420.26 units

**Common mistake:** using a monthly holding cost with annual demand, which halves or doubles the EOQ by
the square root of the period.

### 4. Overall equipment effectiveness — `oee`

Planned time 480 minutes, downtime 40, ideal cycle 0.5 minutes, 760 units, 740 good.

- Availability = (480 - 40) / 480 = **91.67%**
- Performance = 0.5 x 760 / 440 = **86.36%**
- Quality = 740 / 760 = **97.37%**
- OEE = **77.08%**

**Common mistake:** using the actual cycle time in performance. That always gives 100% and hides the
speed loss.

### 5. Control chart and capability — `spc`

Eight observations: 10, 11, 9, 10, 12, 9, 10, 11. Mean 10.25; average moving range 1.5714; sigma
1.3931; limits **6.07 to 14.43**; no point outside and no run of eight. With specification 7 to 13, Cp
= **0.72** and Cpk = **0.66**.

**Common mistake:** reading control limits as specification limits. A process can be in control and
still incapable.

## Practice set

1. Annual demand 8,000, order cost 250, holding cost 20, lead time 5 days, no variability. Find the EOQ,
   the orders per year and the reorder point.
2. Arrivals 9 an hour, service 15 an hour. Find utilisation, the average queue, the average wait and the
   probability the server is idle.
3. Resources: 6 hours at 4 minutes a unit and 6 hours at 6 minutes a unit; demand 54. Find each capacity,
   the bottleneck, utilisation and the gap.
4. Inventory 120,000; receivables 90,000; payables 60,000; cost of sales 730,000; revenue 1,095,000.
   Find the cash conversion cycle.

### Answer key

1. EOQ 447.21; orders 17.89; reorder point 8,000/365 x 5 = **109.59 units**.
2. Utilisation **0.60**; queue **0.90**; wait 0.90/9 = **0.10 hours**; probability idle **0.40**.
3. Capacities **90** and **60**; bottleneck **60**; utilisation **0.90**; gap **6**.
4. DIO = 120,000/730,000 x 365 = 60 days; DSO = 90,000/1,095,000 x 365 = 30 days; DPO =
   60,000/730,000 x 365 = 30 days; CCC = 60 + 30 - 30 = **60 days**.

## What is not built

- **No multi-echelon inventory** (two or more stocking points): the method sizes one item at one
  location. Distribution networks need a declared multi-echelon model.
- **No scheduling, sequencing, line balancing or theory-of-constraints buffers.** CPM/PERT lives on the
  Project management shelf; this shelf does not schedule work.
- **No subgroup control charts (X-bar/R, p, c, u), EWMA, CUSUM or measurement-system analysis.** The
  control chart is individuals with moving ranges.
- **No six-big-losses split, TEEP or multi-machine OEE.**
- **No quantity discounts, variable lead times or multi-item inventory optimisation.**
- **No forecasting beyond a declared linear trend**, and no seasonality or causal demand model.
- **No facility location, routing or transport optimisation.**

If your assignment needs one of these, state it in the limitations and show the method you used by hand.
