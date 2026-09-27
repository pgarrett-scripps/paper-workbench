// Exercise the real evidence rendering functions with a minimal DOM surface.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const elements = new Map();
const document = {querySelector(selector) {
  if (!elements.has(selector)) elements.set(selector, {innerHTML: '', querySelectorAll: () => []});
  return elements.get(selector);
}};
const context = vm.createContext({document, URLSearchParams, location: {search: ''}});
const code = fs.readFileSync('paper_workspace/web/app.js', 'utf8');
vm.runInContext(code.slice(0, code.indexOf("$('#draft-select').addEventListener")), context);
vm.runInContext(`
state = {};
paper = {id: 'p'};
decisions = {items:{}};
review = {findings:[], raw_response:{
  result_map:{nodes:[{block_id:'b1'}],edges:[{from:'b1',quote:'Fig 1',to:['b2']}],checks:[],limitation:'Literal references only.'},
  result_comparisons:[{status:'needs_reconciliation',limitation:'Not independently verified.',observations:[{block_id:'b1',value:'1.2',metric:'slope',quote:'<script>value</script>'}]}],
  epistemic_audit:{limitations:['Source location is separate from truth.'],issues:[{issue_id:'issue-1',assertion_status:'unverified_hypothesis',selection_status:'selected',scientific_truth_status:'not_mechanically_determined',qualifications:['Control already reported.'],decision_history:[{decision_reason:'Keep a narrower question.',strongest_author_defense:'Control already reported.'}]}]}
}};
cards();
`, context);
const html = elements.get('#handoff-ledger').innerHTML;
assert.equal(elements.get('#handoff-details').hidden, false);
assert.ok(html.includes('unverified hypothesis'));
assert.ok(html.includes('not mechanically determined'));
assert.ok(html.includes('href="#b2"'));
assert.ok(html.includes('Control already reported.'));
assert.ok(html.includes('&lt;script&gt;value&lt;/script&gt;'));
assert.ok(!html.includes('<script>'));
console.log('Review evidence rendering checks passed');
