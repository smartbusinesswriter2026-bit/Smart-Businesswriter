html = open('web/admin-sbw.html', encoding='utf-8').read()

# Add difficulty dropdown to the row with Problems
old = """          <label>Problems: <select id="healCount">
            <option value="3">3 (light)</option>
            <option value="5" selected>5 (moderate)</option>
            <option value="10">10 (severe)</option>
          </select></label>"""

new = """          <label>Problems: <select id="healCount">
            <option value="3">3 (light)</option>
            <option value="5" selected>5 (moderate)</option>
            <option value="10">10 (severe)</option>
          </select></label>
          <label>Difficulty: <select id="healDifficulty">
            <option value="easy">Easy</option>
            <option value="medium" selected>Medium</option>
            <option value="hard">Hard</option>
            <option value="expert">Expert (stress test)</option>
          </select></label>"""

assert old in html, "problems select not found"
html = html.replace(old, new, 1)

# Update the instruction construction in healFreeGen
old_js = """  if (!instruction) {
    if (!subjectSel.value) { toast('Select a subject or enter an instruction'); return; }
    instruction = 'Generate ' + count + ' varied and diverse case studies or problems about ' + (tileLabel || subjectLabel) +
      (tileWhat ? ' (' + tileWhat + ')' : '') +
      ' in the ' + subjectLabel + ' domain. Make them realistic, varied in difficulty, and covering different aspects.';
  }"""

new_js = """  if (!instruction) {
    if (!subjectSel.value) { toast('Select a subject or enter an instruction'); return; }
    const diff = document.getElementById('healDifficulty').value;
    const diffDesc = {
      easy: 'simple, single-concept problems with clear given values',
      medium: 'moderate problems combining 2-3 concepts with some ambiguity',
      hard: 'complex multi-step problems with missing information and edge cases',
      expert: 'expert-level stress-test problems with contradictory data, multiple periods, unusual account placements, and tricky adjustments designed to break the pipeline'
    }[diff] || 'moderate problems';
    instruction = 'Generate ' + count + ' ' + diff + '-difficulty, highly varied and complex case studies or problems about ' + (tileLabel || subjectLabel) +
      (tileWhat ? ' (' + tileWhat + ')' : '') +
      ' in the ' + subjectLabel + ' domain. Difficulty: ' + diffDesc + '.' +
      ' Make them realistic but challenging. Include edge cases, unusual values, multi-period scenarios, and tricky placements.' +
      ' Vary the format: some as word problems, some as trial balances, some as journal entries, some as narrative instructions.';
  }"""

assert old_js in html, "js instruction block not found"
html = html.replace(old_js, new_js, 1)

open('web/admin-sbw.html', 'w', encoding='utf-8').write(html)
print("done")