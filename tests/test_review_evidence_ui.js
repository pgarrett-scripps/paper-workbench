// Exercise the real review rendering functions with a minimal DOM surface.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const elements = new Map();
const document = {
  querySelector(selector) {
    if (!elements.has(selector)) elements.set(selector, {innerHTML: '', querySelectorAll: () => []});
    return elements.get(selector);
  },
  querySelectorAll: () => [],
};
const context = vm.createContext({document, URLSearchParams, location: {search: ''}});
const code = fs.readFileSync('paper_workspace/web/app.js', 'utf8');
vm.runInContext(code.slice(0, code.indexOf("$('#draft-select').addEventListener")), context);
const html = selector => elements.get(selector).innerHTML;

// A workspace review keeps its result map and quantity comparisons.
vm.runInContext(`
state = {};
paper = {id: 'p'};
decisions = {items:{}};
review = {id:'workspace', findings:[], raw_response:{
  result_map:{nodes:[{block_id:'b1'}],edges:[{from:'b1',quote:'Fig 1',to:['b2']}],checks:[],limitation:'Literal references only.'},
  result_comparisons:[{status:'needs_reconciliation',limitation:'Not independently verified.',observations:[{block_id:'b1',value:'1.2',metric:'slope',quote:'<script>value</script>'}]}]
}};
cards();
`, context);
assert.equal(elements.get('#handoff-details').hidden, false);
assert.equal(elements.get('#run-panel').hidden, true);
assert.equal(elements.get('#filter-escalated').hidden, true);
assert.ok(html('#handoff-ledger').includes('href="#b2"'));
assert.ok(html('#handoff-ledger').includes('&lt;script&gt;value&lt;/script&gt;'));
assert.ok(!html('#handoff-ledger').includes('<script>'));

// A PeerReviewAgents run shows tracks, basis, escalation, the specialist reports and the appendix.
vm.runInContext(`
paper = {id: 'p', blocks: [{id:'b1', text:'alpha beta gamma', kind:'paragraph', section:'Results'}]};
const finding = (uid, number, extra) => ({id:uid, finding_uid:uid, number, kind:'question', category:'scientific',
  severity:'major', title:'Finding '+uid, comment:'Comment', block_id:'b1', placement:'anchored', evidence_blocks:[], ...extra});
review = {id:'run', summary:'Editor summary', raw_response:undefined, findings:[
  finding('u1', 1, {start:0, end:5, quote:'alpha', track:'field', basis:'judgement', basis_reason:'No arithmetic receipt.',
    escalate:true, editor_reason:'Core <b>issue</b>', reviewers_raising:2, duplicate_uids:['u2'], section:'body',
    source_urls:['https://example.org/a', 'javascript:alert(1)']}),
  finding('u2', 2, {start:6, end:10, quote:'beta', track:'core', basis:'two-quotes', escalate:false,
    editor_reason:'Same objection', editor_placement:'duplicate', duplicate_of:'u1', section:'appendix'}),
], run:{arm:'full-two-track', reviewer_count:3, status:'complete', escalated_count:1, review_guard_status:'clean',
  cause:null, note:'the review was written and the run was marked blocked afterwards: rate limit',
  problems:['runtime.json is not valid JSON <x>'], publishable:false,
  not_publishable_reasons:['1 file(s) could not be read in full, and they are named in problems'],
  edited:true, missing_stages:[], none_found:[], limitations:['Advisory only.'],
  verdict:{significance:'High if true', strength_of_evidence:'Weak', reasoning:'Correlation only', basis:'judgement', limitation:'Not a score.'},
  escalation_rulings:[{finding_uid:'u1', ruling:'Accepted as central.'}],
  audits:{stats:'# Stats audit <script>x</script>'},
  agents:[{slot:'spec-stats', role:'specialist', track:'stats', model:'claude-sonnet-5-5', attempt:1, tool_calls:4,
           session_calls:9, tokens:5000, state:'done', findings:1, none_found:false, labels:['spec-stats']},
          {slot:'recorder', role:'recorder', track:'ingest', model:'claude-sonnet-5-5', attempt:1, tool_calls:4,
           session_calls:12, tokens:42000, state:'completed', findings:0, none_found:false, labels:['ingest', 'write review']}],
  findings_by_track:{field:1, core:1}, wall_seconds:600, tokens_total:1234}};
cards();
`, context);
const comments = html('#comments');
const panel = html('#run-panel');
assert.equal(elements.get('#run-panel').hidden, false);
assert.equal(elements.get('#filter-escalated').hidden, false);
assert.equal(elements.get('#finding-count').textContent, '1 in the report · 1 in the appendix');
for (const text of ['field track', 'Basis: judgement', 'title="No arithmetic receipt."', 'Escalated', 'Raised by 2',
                    'Escalation ruling', 'Accepted as central.', 'Core &lt;b&gt;issue&lt;/b&gt;', 'Duplicate</span>',
                    'Duplicate of finding <a href="#note-u1">1</a>', 'Merged duplicates: <a href="#note-u2">2</a>',
                    'href="https://example.org/a"']) {
  assert.ok(comments.includes(text), text);
}
assert.ok(!comments.includes('javascript:'));
assert.ok(!comments.includes('<b>'));
const appendixAt = comments.indexOf('id="appendix"');
assert.ok(appendixAt > comments.indexOf('id="note-u1"'));
assert.ok(comments.indexOf('id="note-u2"') > appendixAt);
for (const text of ['Arm full-two-track', '3 reviewers', 'Status complete', '1 escalated', 'Guard clean', '10 min',
                    "Editor's verdict", 'High if true', 'Basis: judgement. Not a score.', 'Specialist reports (1)',
                    '# Stats audit &lt;script&gt;x&lt;/script&gt;',
                    'spec-stats · stats track · claude-sonnet-5-5 · attempt 1 · 4 tool calls · 5000 tokens · done · 1 findings</li>',
                    'Agents (2)',
                    'recorder · ingest track · claude-sonnet-5-5 · attempt 1 · 4 tool calls · 42000 tokens · completed · tasks ingest, write review</li>',
                    'marked blocked afterwards: rate limit', 'runtime.json is not valid JSON &lt;x&gt;',
                    'Not publishable: 1 file(s) could not be read in full',
                    'Findings by track: field 1 · core 1', 'Advisory only.']) {
  assert.ok(panel.includes(text), text);
}
assert.ok(!panel.includes('<script>'));

// A review with no findings says whether the reviewers raised none or the guard held them all.
assert.equal(vm.runInContext("runStatus({status:'complete-without-findings', quarantined_findings_count:0})", context),
             'Status complete-without-findings: the reviewers raised none');
assert.equal(vm.runInContext("runStatus({status:'complete-without-findings', quarantined_findings_count:2})", context),
             'Status complete-without-findings: the guard quarantined all 2');

// The manuscript marks only the report's findings, numbered as in the comment column.
const markup = vm.runInContext("quoteMarkup(paper.blocks[0])", context);
assert.ok(markup.includes('href="#note-u1" aria-label="Comment 1">1</a>'));
assert.ok(!markup.includes('note-u2'));

// The escalated filter keeps only escalated findings, and a review without a run resets it.
vm.runInContext("filter = 'escalated'; cards();", context);
assert.ok(html('#comments').includes('id="note-u1"'));
assert.ok(!html('#comments').includes('id="appendix"'));
vm.runInContext("review = {id:'workspace', findings:[]}; cards();", context);
assert.equal(vm.runInContext('filter', context), 'all');
assert.equal(elements.get('#run-panel').hidden, true);
console.log('Review rendering checks passed');
