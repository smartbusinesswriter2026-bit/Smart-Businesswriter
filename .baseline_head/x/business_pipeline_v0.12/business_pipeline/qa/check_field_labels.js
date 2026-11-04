/* Prove the input label format without a browser: extract fieldTitle/fieldLabel from the
 * served page, run them, and print what a student would see.
 *
 * Usage:  node qa/check_field_labels.js
 */
const fs = require("fs");

const page = fs.readFileSync("web/index.html", "utf8");
const start = page.indexOf("const FIELD_ACRONYMS");
const anchor = page.indexOf("function fieldLabel", start);
const end = page.indexOf("\n}\n", anchor) + 3;
if (start < 0 || anchor < 0 || end < 3) {
  console.error("the label helpers were not found in web/index.html");
  process.exit(1);
}
const source = page.slice(start, end);
const esc = (s) => String(s === null || s === undefined ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const api = new Function("esc", source + "\n return { fieldTitle: fieldTitle, fieldLabel: fieldLabel };")(esc);

const cases = [
  ["present_value", "amount you have today (the lump sum)"],
  ["periods", "number of YEARS the money is invested or borrowed"],
  ["rate", "annual rate as a decimal; 6% is 0.06"],
  ["cashflows", "the outlay first, then each period"],
  ["ebit", "earnings before interest and tax"],
  ["tax_rate", "the declared rate, not a jurisdiction's law"],
  ["annual_rate", "the nominal annual rate"],
  ["x", "the first variable"],
];

let failures = 0;
for (const [name, desc] of cases) {
  const title = api.fieldTitle(name);
  const label = api.fieldLabel(name, desc).replace(/<[^>]+>/g, "");
  console.log(`${name.padEnd(14)} -> ${title.padEnd(16)} | ${label}`);
  if (label.indexOf(title + " - " + desc) !== 0) {
    console.error(`  FAIL: expected "${title} - ${desc}"`);
    failures += 1;
  }
}
console.log(`\n${failures} failure(s)`);
process.exit(failures ? 1 : 0);
