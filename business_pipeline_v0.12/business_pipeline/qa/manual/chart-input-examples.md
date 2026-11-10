# Chart input: what the reader accepts

The Chart window reads your figures with one deterministic reader. It shows
what it understood before it makes the chart. It never adds up, rounds,
invents or silently changes a number.

## Typed or pasted figures

One row per line. Any of these separators works:

```
Q1, 120000
Q2 240000
Q3: 360000
Q4	480000
Q1 | 120000
Q1 ; 120000
```

A label may contain spaces:

```
North Region, 120000
North Region 2 120000
```

A bare number gets a label you can change:

```
480000
```

It is shown as `Item 1 = 480000 (auto label)`.

## Numbers

Accepted:

```
120000
120,000
120 000
$120,000
€1.200,50
(1,200)        -> -1200
-1200
−1200
12%
1.2k           -> 1200
1.2M           -> 1200000
```

A single three-digit separator is shown as parsed so you can catch it:

```
1,200   -> 1200
1.200   -> 1200
1.20    -> 1.2
```

If you meant a decimal, write it with a point: `1.2`.

## Pareto

A pareto needs a **third number on every line**: the running total. The reader
does not add up the bars for you.

```
A, 10, 10
B, 20, 30
C, 5, 35
```

The running total must never fall. A fall is refused with the line number.

## Data files

Accepted: CSV, TSV, XLSX, XLSM, TXT.

The reader picks a label column and a value column. If the file has more than
one number column, it uses the first and shows dropdowns so you can change it.

A file with no header row is detected: if the last column name is a number, the
first row is kept as data.

## Instruction files

Accepted: PDF, DOCX, DOCM, TXT, MD.

The reader looks for a title, a chart kind ("bar chart", "pie chart", "pareto",
...) and a table of figures. It shows what it found, what it ignored and what it
will do. If it cannot find figures, it says so and does not invent them.

A scanned PDF with no text layer is refused with the reason. A PDF whose labels
and values are on separate lines is refused rather than guessed; upload the data
as CSV/XLSX or paste it.

## What is refused

- no numbers at all;
- two numbers and no label;
- a third number on a line that is not a pareto;
- a pareto line without a running total;
- a pareto whose running total falls;
- a negative value in a pie or stacked bar;
- one point for a chart (a single figure is a sentence, not a chart);
- an instruction that asks for a chart the data cannot carry.
