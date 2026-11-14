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
  agents:[{slot:'spec-stats', role:'specialist', track:'stats', assigned_model:'claude-sonnet-5-5', model:'claude-sonnet-5-5',
           attempt:1, tool_calls:4, session_calls:9, tokens:5000, state:'done', findings:1, none_found:false, labels:['spec-stats']},
          {slot:'recorder', role:'recorder', track:'ingest', assigned_model:'claude-haiku-5-5', model:null, attempt:1, tool_calls:4,
           session_calls:12, tokens:42000, state:'completed', findings:0, none_found:false, labels:['ingest', 'write review']}],
  models_unverified:['recorder'],
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
                    'spec-stats · stats track · model asked claude-sonnet-5-5 · model ran claude-sonnet-5-5 · attempt 1 · 4 tool calls · 5000 tokens · done · 1 findings</li>',
                    'Agents (2)',
                    'recorder · ingest track · model asked claude-haiku-5-5 · model ran not recorded · attempt 1 · 4 tool calls · 42000 tokens · completed · tasks ingest, write review</li>',
                    '<p class="unverified">The model that ran was not recorded for 1 slot (recorder), so the model asked for it is unverified.</p>',
                    'marked blocked afterwards: rate limit', 'runtime.json is not valid JSON &lt;x&gt;',
                    'Not publishable: 1 file(s) could not be read in full',
                    'Findings by track: field 1 · core 1', 'Advisory only.']) {
  assert.ok(panel.includes(text), text);
}
assert.ok(!panel.includes('<script>'));
// The model asked is never shown as the model that ran.
assert.ok(!panel.includes('model ran claude-haiku-5-5'));

// The run panel shows the hand-written fixture ledger as run_view.py hands it over.
context.ledgerView = JSON.parse(fs.readFileSync('tests/fixtures/citations/view.json', 'utf8'));
vm.runInContext('review.run.citations = ledgerView; cards();', context);
assert.ok(html('#run-panel').includes(
  '<details class="citations" open><summary>Citations: 6 references, 8 in-text uses, check incomplete</summary>'));
const citations = vm.runInContext('citationPanel(ledgerView)', context);
// Abstracts, passages and worker notes are shown escaped, as quoted text.
assert.ok(!/<img|<script/i.test(citations));
for (const text of ['&lt;img src=x onerror=alert(1)&gt;', '&lt;script&gt;alert(2)&lt;/script&gt;']) {
  assert.ok(citations.includes(text), text);
}
// Each reference state keeps its own count, and no two are added together.
for (const text of [
  '<p class="count">6 references: 2 found in an index · 1 DOI not held by the DOI resolver · 1 title not located in Crossref or Europe PMC · 1 could not be checked · 1 never looked up</p>',
  '<p class="count">8 in-text uses: 1 supports · 1 partly supports · 1 does not support · 2 cannot tell · 2 not yet judged · 1 marker matches no reference</p>',
  '<p class="count">Also flagged: 1 with a printed field that differs from the index · 1 retracted</p>',
  '<p class="error">The citation check did not finish, so these counts do not cover the whole reference list.</p>',
  'References to check (5)', '<strong>[2] DOI not held by the DOI resolver</strong>',
  '<strong>[3] title not located in Crossref or Europe PMC</strong>', '<strong>[4] could not be checked</strong>',
  '<strong>[5] found in an index</strong>', '<strong>[6] never looked up</strong>',
  'That is weak evidence, because much of the literature is in neither index.',
  'The lookups did not answer, so this says nothing about whether the work is real.',
  'The printed year differs from the indexed record.',
  'The indexed record is marked retracted (retraction 10.5555/fixture.notice).',
  'Worker verdicts on in-text uses (8)',
  '<strong>[1] supports, judged by cite-1</strong>', '<strong>[1] partly supports, judged by cite-1</strong>',
  '<strong>[5] does not support, judged by cite-1</strong>', '<strong>[3] cannot tell, judged by cite-2</strong>',
  'Source passage the worker quoted, fetched from the internet</span><br>Retromer sorts transmembrane cargo',
  'Source passage the worker quoted, fetched from the internet</span><br>In cultured neurons the loss of VPS35 slowed',
  'Source passage the worker quoted, fetched from the internet</span><br>The D620N variant left retromer assembly intact',
  'The marker 7 matches no entry in the reference list.', '<strong>[4] Not yet judged.</strong>']) {
  assert.ok(citations.includes(text), text);
}
assert.equal(citations.split('The worker had no source text for this reference.').length - 1, 2);
// Outside the engine's own problem lines, nothing says a work does not exist or was made up.
let prose = citations;
for (const line of vm.runInContext('ledgerView.problems.map(esc)', context)) prose = prose.split(line).join('');
assert.ok(!/not exist|fabricat|fake|made up|hallucinat/i.test(prose));
// A planned lane with no ledger and an unreadable ledger each say so and show no rows.
const noLedger = vm.runInContext(`citationPanel({complete:false, ledger:false, readable:false, counts:{},
  problems:['this run planned a citations lane and wrote no citation ledger, so there are no ledger counts'],
  references:[], references_not_shown:0, uses:[], uses_not_shown:0})`, context);
assert.ok(noLedger.startsWith('<details class="citations" open><summary>Citations</summary><p class="error">this run planned'));
assert.ok(!noLedger.includes('class="count"'));
// The engine names an unreadable ledger in a problem line, and the panel shows that line alone.
const unreadableLine = 'review/citations/ledger.jsonl is present and could not be read (Permission denied), so this run has no citation counts';
context.unreadableLine = unreadableLine;
const unreadable = vm.runInContext('citationPanel({...ledgerView, readable:false, counts:{}, problems:[unreadableLine], references:[], uses:[]})', context);
assert.ok(unreadable.includes(`<p class="error">${unreadableLine}</p>`));
assert.ok(!unreadable.includes('The citation ledger could not be read'));
assert.ok(!unreadable.includes('class="count"'));
// With no problem line to show, the panel still says the ledger could not be read.
const unexplained = vm.runInContext('citationPanel({...ledgerView, readable:false, counts:{}, problems:[], references:[], uses:[]})', context);
assert.ok(unexplained.includes('The citation ledger could not be read, so the panel shows no citation counts.'));
assert.ok(!unexplained.includes('class="count"'));
assert.ok(vm.runInContext('citationPanel({...ledgerView, complete:true, problems:[]})', context)
  .startsWith('<details class="citations"><summary>Citations: 6 references, 8 in-text uses</summary>'));
assert.equal(vm.runInContext('citationPanel(null)', context), '');
// Only https links leave the page.
assert.equal(vm.runInContext("sourceLink('javascript:alert(1)', 'Source') + sourceLink('http://example.org', 'Source')", context), '');
// A citation worker writes no findings, and its line says so.
assert.equal(vm.runInContext(`agentFacts({slot:'cite-1', role:'citation-worker', track:'citations', assigned_model:'claude-haiku-5-5',
  model:'claude-haiku-5-5', tool_calls:6, findings:0})`, context),
  'cite-1 · citations track · citation worker, writes no findings · model asked claude-haiku-5-5 · model ran claude-haiku-5-5 · 6 tool calls');

// A run that records no plan says so, and a run with every model observed shows no unverified note.
assert.equal(vm.runInContext("agentFacts({slot:'core-1', model:'claude-opus-5-5'})", context),
             'core-1 · model asked not recorded · model ran claude-opus-5-5');
assert.equal(vm.runInContext("unverifiedNote([])", context), '');
assert.equal(vm.runInContext("unverifiedNote(['core-2', 'editor'])", context),
             'The model that ran was not recorded for 2 slots (core-2, editor), so the model asked for them is unverified.');

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
