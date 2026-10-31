const s = '<button class="btn" type="button" data-plan-act="know" data-plan-method="irr" data-plan-input="cashflows" data-plan-field="plan-in-a1-0">I know this value</button>';
const re = /<button\b([^>]*?)data-plan-act="([^"]+)"([^>]*)>/g;
let m = re.exec(s);
console.log('match:', m && JSON.stringify([m[1], m[2], m[3]]));
