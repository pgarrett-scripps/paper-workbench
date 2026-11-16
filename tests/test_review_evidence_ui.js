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

// A PeerReviewAgents run shows one card per issue, as run_view.py hands it over: the required
// changes, the suggestions under their categories, then the prior round's closed issues.
vm.runInContext(`
paper = {id: 'p', blocks: [{id:'b1', text:'alpha beta gamma', kind:'paragraph', section:'Results'}]};
const member = (uid, extra) => ({finding_uid:uid, slot:'core-1', track:'core', severity:'major', kind:'issue',
  basis:'judgement', escalate:false, title:'Finding '+uid, block_id:'b1', quote:'alpha', evidence_blocks:['b1'],
  comment:'Comment '+uid, start:0, end:5, placement:'anchored', ...extra});
const issue = (id, rank, group, extra) => ({id, source_id:id, number:rank, rank, group, name:'Issue '+id,
  title:'Issue '+id, statement:'Statement '+id, comment:'Statement '+id, severity:'major',
  category:'statistics-and-inference', status:'new', status_reason:null, prior_id:null, prior_rank:null, raised_by:1,
  members:[], audits:[], surviving_quotes:[], rebuttal_quote:null, rebuttal_block_id:null, text_unchanged_reason:null,
  kind:'issue', escalate:false, evidence_blocks:['b1'], block_id:'b1', quote:'alpha', start:0, end:5,
  placement:'anchored', replacement:null, ...extra});
review = {id:'run', summary:'Editor summary', raw_response:undefined, findings:[
  issue('i01', 1, 'required', {raised_by:2, escalate:true, status:'persisting', status_reason:'Still <b>wrong</b>',
    prior_id:'i01', prior_rank:2, audits:['audit_stats.md'], members:[
      member('u1', {track:'field', basis_reason:'No arithmetic receipt.', escalate:true,
                    source_urls:['https://example.org/a', 'javascript:alert(1)']}),
      member('u2', {slot:'core-2', basis:'two-quotes', quote:'alpha beta', end:10, counterevidence:'Checked the methods.'})]}),
  issue('i02', 2, 'suggestion', {severity:'minor', category:'presentation', kind:'edit', quote:'gamma', start:11,
    end:16, replacement:'delta', members:[member('u3', {kind:'edit', severity:'minor', quote:'gamma', start:11, end:16,
                                                        replacement:'delta'})]}),
  issue('i03', 3, 'suggestion', {severity:'minor', category:'reproducibility', placement:'unplaced', start:null,
    end:null, members:[member('u4', {severity:'minor', placement:'unplaced', start:null, end:null})]}),
  issue('i04', null, 'closed', {status:'unverified', status_reason:'No editor ruled on it.', prior_id:'i04',
    prior_rank:4, raised_by:0, block_id:null, quote:null, start:null, end:null, placement:'unplaced',
    evidence_blocks:[], surviving_quotes:[{finding_uid:'old', block_id:'b1', quote:'beta gamma'}]}),
], run:{arm:'full-two-track', reviewer_count:3, status:'complete', escalated_count:1, review_guard_status:'clean',
  cause:null, note:'the review was written and the run was marked blocked afterwards: rate limit',
  problems:['runtime.json is not valid JSON <x>'], publishable:false,
  not_publishable_reasons:['1 file(s) could not be read in full, and they are named in problems'],
  findings_source:'issues', issues_source:'editor',
  prior_round:{file:'issues.json', digest:'0123456789abcdef', issues:2,
               tally:{new:2, persisting:1, regressed:0, resolved:0, unverified:1}},
  missing_stages:[], none_found:[], limitations:['Advisory only.'],
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
for (const name of ['required', 'suggestions', 'escalated']) assert.equal(elements.get('#filter-' + name).hidden, false, name);
for (const name of ['scientific', 'copyedit', 'questions']) assert.equal(elements.get('#filter-' + name).hidden, true, name);
assert.equal(elements.get('#finding-count').textContent, '1 required · 2 suggestions · 1 from the prior round');
// A run that is not publishable says so above its comments, with every reason, and only there.
assert.ok(comments.startsWith('<div class="not-publishable error" role="note"><p><strong>This run is not publishable.</strong>'));
assert.ok(comments.includes('<li>1 file(s) could not be read in full, and they are named in problems</li>'));
assert.ok(!html('#run-panel').includes('could not be read in full'));
// Required changes come first in rank order, then the suggestions under their categories, then the closed issues.
const order = ['Required changes (1)', 'id="note-i01"', 'Suggestions (2)', '<h4 class="issue-category">Presentation</h4>',
               'id="note-i02"', '<h4 class="issue-category">Reproducibility</h4>', 'id="note-i03"', 'id="closed-issues"',
               'Prior round: resolved and unverified (1)', 'id="note-i04"'];
order.forEach((text, index) => {
  assert.ok(comments.includes(text), text);
  if (index) assert.ok(comments.indexOf(text) > comments.indexOf(order[index - 1]), text);
});
assert.ok(comments.includes('<details class="closed-issues" id="closed-issues">'));
// Nothing of the per-finding viewer is left: no appendix and no fallback for a server without revisions.
const sources = code + fs.readFileSync('paper_workspace/web/style.css', 'utf8') + fs.readFileSync('paper_workspace/web/index.html', 'utf8');
for (const text of ['appendix', 'legacyServer']) assert.ok(!sources.includes(text), text);
const cardOf = id => comments.slice(comments.indexOf(`id="note-${id}"`)).split('</article>')[0];
// Each card shows the issue, its status against the prior round, how many reviewers raised it and its members as evidence.
for (const text of ['Major · Statistics and inference', 'Issue i01</span>', 'title="Persisting from the prior round">persisting</span>',
                    'Raised by 2 reviewers', 'Escalated', '<h3>1. Issue i01</h3>', 'Statement i01',
                    'Still &lt;b&gt;wrong&lt;/b&gt;', 'Rank in the prior round: 2', 'Specialist reports: audit_stats.md',
                    'Evidence: 2 findings', 'core-1 · field track · issue · major', 'core-2 · core track · issue · major',
                    'Basis: judgement', 'title="No arithmetic receipt."', 'Basis: two-quotes', 'Comment u1', 'Comment u2',
                    '<blockquote>alpha beta</blockquote>', 'Counterevidence checked', 'Escalation ruling',
                    'Accepted as central.', 'href="https://example.org/a"', 'href="#anchor-i01-1">Go to passage',
                    'href="#anchor-i01-2">Go to passage', 'Mark for follow-up']) {
  assert.ok(cardOf('i01').includes(text), text);
}
assert.ok(!cardOf('i01').includes('Accept wording'));
// The ruling belongs to the member it was made on.
assert.equal(comments.split('Accepted as central.').length - 1, 1);
assert.ok(!comments.includes('javascript:'));
assert.ok(!comments.includes('<b>'));
// An issue whose one member is an anchored edit takes the wording decision.
for (const text of ['Minor · Presentation', 'Accept wording', 'Decline wording', 'Suggested wording</p><blockquote>delta</blockquote>']) {
  assert.ok(cardOf('i02').includes(text), text);
}
assert.ok(cardOf('i03').includes('Unplaced: the quote is not found once in its passage'));
assert.ok(cardOf('i03').includes('No finding behind this issue is placed on the manuscript text'));
// A closed issue has no members and no rank, and shows the evidence that still stands.
for (const text of ['title="Unverified: not raised again and not shown fixed">unverified</span>', '<h3>Issue i04</h3>',
                    'No editor ruled on it.', 'Rank in the prior round: 4', "The prior round's evidence still in the manuscript",
                    '<blockquote>beta gamma</blockquote>']) {
  assert.ok(cardOf('i04').includes(text), text);
}
assert.ok(!cardOf('i04').includes('Raised by'));
assert.ok(!cardOf('i04').includes('Evidence:'));
for (const text of ['Arm full-two-track', '3 reviewers', 'Status complete', 'Issues grouped by the editor',
                    'Prior round issues.json: 2 issues carried, this round 2 new · 1 persisting · 0 regressed · 0 resolved · 1 unverified',
                    '1 escalated', 'Guard clean', '10 min',
                    "Editor's verdict", 'High if true', 'Basis: judgement. Not a score.', 'Specialist reports (1)',
                    '# Stats audit &lt;script&gt;x&lt;/script&gt;',
                    'spec-stats · stats track · model asked claude-sonnet-5-5 · model ran claude-sonnet-5-5 · attempt 1 · 4 tool calls · 5000 tokens · done · 1 findings</li>',
                    'Agents (2)',
                    'recorder · ingest track · model asked claude-haiku-5-5 · model ran not recorded · attempt 1 · 4 tool calls · 42000 tokens · completed · tasks ingest, write review</li>',
                    '<p class="unverified">The model that ran was not recorded for 1 slot (recorder), so the model asked for it is unverified.</p>',
                    'marked blocked afterwards: rate limit', 'runtime.json is not valid JSON &lt;x&gt;',
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

// Every anchored member marks the manuscript, overlapping quotes included, each pinned with its issue's number.
// The issue that is one edit shows its wording, and the unplaced member marks nothing.
assert.equal(vm.runInContext('quoteMarkup(paper.blocks[0])', context),
  '<span class="anchor" id="anchor-i01-2"></span><mark class="question-mark anchor" id="anchor-i01-1">alpha</mark>'
  + '<a class="pin" href="#note-i01" aria-label="Comment 1">1</a><mark class="question-mark"> beta</mark>'
  + '<a class="pin" href="#note-i01" aria-label="Comment 1">1</a> <span class="before anchor" id="anchor-i02-1">gamma</span>'
  + ' <span class="after">delta</span><a class="pin" href="#note-i02" aria-label="Comment 2">2</a>');
// Accepting the edit issue applies its one member's wording.
assert.equal(vm.runInContext("decisions = {items:{i02:'accepted'}}; acceptedText(paper.blocks[0])", context), 'alpha beta delta');
vm.runInContext('decisions = {items:{}};', context);

// Each run filter keeps its own cards.
const shown = name => vm.runInContext(`filter = '${name}'; cards(); review.findings.map(item => item.id)
  .filter(id => document.querySelector('#comments').innerHTML.includes('id="note-' + id + '"')).join(' ')`, context);
assert.equal(shown('required'), 'i01');
assert.equal(shown('suggestions'), 'i02 i03');
assert.equal(shown('escalated'), 'i01');
assert.equal(shown('all'), 'i01 i02 i03 i04');
// A workspace filter does not survive onto a run, and a run filter does not survive onto a workspace review.
assert.equal(shown('questions'), 'i01 i02 i03 i04');
assert.equal(vm.runInContext('filter', context), 'all');
vm.runInContext("filter = 'escalated'; review = {id:'workspace', findings:[]}; cards();", context);
assert.equal(vm.runInContext('filter', context), 'all');
assert.equal(elements.get('#run-panel').hidden, true);
for (const name of ['required', 'suggestions', 'escalated']) assert.equal(elements.get('#filter-' + name).hidden, true, name);
for (const name of ['scientific', 'copyedit', 'questions']) assert.equal(elements.get('#filter-' + name).hidden, false, name);

// A run that is not publishable and has nothing to show says why, not that the review is empty.
vm.runInContext(`review = {id:'run', summary:'', findings:[], run:{status:'complete', problems:[], publishable:false,
  not_publishable_reasons:['the run folder has no readable issues.json'], findings_source:'none', issues_source:null,
  prior_round:null, missing_stages:[], agents:[], limitations:[]}}; cards();`, context);
assert.equal(html('#comments'), '<div class="not-publishable error" role="note"><p><strong>This run is not publishable.</strong> '
  + 'It has no review to show.</p><ul><li>the run folder has no readable issues.json</li></ul></div>');
assert.equal(elements.get('#finding-count').textContent, 'No findings');

// A run with no issues shows its recorded findings under their own heading.
vm.runInContext(`review.run.findings_source = 'ledger';
review.findings = [{id:'aa11', source_id:'aa11', number:1, group:'ledger', title:'Recorded finding', comment:'Comment',
  severity:'major', category:null, status:null, raised_by:1, kind:'issue', block_id:'b1', quote:'beta', start:6, end:10,
  placement:'anchored', evidence_blocks:[], audits:[], surviving_quotes:[],
  members:[{finding_uid:'aa11', slot:'core-1', title:'Recorded finding', comment:'Comment', quote:'beta', block_id:'b1',
            start:6, end:10, placement:'anchored', evidence_blocks:[]}]}];
cards();`, context);
assert.ok(html('#comments').includes('<h3 class="issue-group">Findings recorded before any issues were written (1)</h3>'));
assert.ok(html('#comments').includes('It has no review to show.') === false);
assert.equal(elements.get('#finding-count').textContent, '1 finding, not grouped into issues');
// The member repeats neither the card's title nor its comment.
assert.equal(html('#comments').split('Recorded finding').length - 1, 1);

// A card with no engine id is numbered by its place and takes no decision. A decision saved
// under its number is neither shown nor applied, and it is counted with the other stale ones.
vm.runInContext(`review.findings = [{id:'run-1', source_id:'not a uid', number:1, group:'ledger', decidable:false,
  title:'Recorded edit', comment:'Comment', severity:'minor', category:null, status:null, raised_by:1, kind:'edit',
  replacement:'delta', block_id:'b1', quote:'gamma', start:11, end:16, placement:'anchored', evidence_blocks:[],
  audits:[], surviving_quotes:[], members:[{finding_uid:'not a uid', slot:'core-1', title:'Recorded edit', comment:'Comment',
  kind:'edit', replacement:'delta', quote:'gamma', block_id:'b1', start:11, end:16, placement:'anchored', evidence_blocks:[]}]}];
decisions = {items:{'run-1':'accepted'}, annotations:{'run-1':{author_comment:'Saved on another card', issue_status:'open', rationale:''}}};
cards();`, context);
const placed = html('#comments');
assert.ok(placed.includes('<p class="muted no-engine-id" role="note">This card has no engine id, so a decision on it could land on another card. Re-run the review to decide on it.</p>'));
for (const text of ['data-action', 'author-response', 'Saved on another card', '>accepted<']) assert.ok(!placed.includes(text), text);
assert.equal(vm.runInContext('acceptedText(paper.blocks[0])', context), 'alpha beta gamma');
assert.ok(placed.startsWith('<p class="stale-decisions muted" role="note">1 saved decision no longer matches a card in this review. '
  + 'The decisions file is left as it is.</p>'));

// Decisions saved under an earlier viewer's per-finding keys, or under an issue this run no longer
// holds, are counted once above the cards. A file with none says nothing.
vm.runInContext(`review = {id:'run', summary:'', findings:[issue('i05', 1, 'required', {raised_by:2, members:[
  member('u5', {}), member('u6', {slot:'core-2'})]})], run:{status:'complete', problems:[], publishable:true,
  not_publishable_reasons:[], findings_source:'issues', issues_source:'editor', prior_round:null, missing_stages:[],
  agents:[], limitations:[]}};
decisions = {items:{'f-0001':'noted', i05:'noted', i09:'noted'}, annotations:{'f-0001':{author_comment:'Old'}, 'f-0002':{author_comment:'Old'}}};
cards();`, context);
const stale = html('#comments');
assert.ok(stale.startsWith('<p class="stale-decisions muted" role="note">3 saved decisions no longer match a card in this review. '
  + 'The decisions file is left as it is.</p>'));
assert.equal(stale.split('stale-decisions').length - 1, 1);
assert.ok(stale.includes('<span>noted</span>'));
vm.runInContext("decisions = {items:{i05:'noted'}, annotations:{}}; cards();", context);
assert.ok(!html('#comments').includes('stale-decisions'));

// Two members of one issue quoting the same span are one mark and one pin, and the card lists both,
// each linking to that one mark.
assert.equal(vm.runInContext('quoteMarkup(paper.blocks[0])', context),
  '<mark class="question-mark anchor" id="anchor-i05-1">alpha</mark><a class="pin" href="#note-i05" aria-label="Comment 1">1</a> beta gamma');
const twice = html('#comments');
for (const text of ['core-1 · core track · issue · major', 'core-2 · core track · issue · major', 'Evidence: 2 findings']) {
  assert.ok(twice.includes(text), text);
}
assert.equal(twice.split('href="#anchor-i05-1">Go to passage').length - 1, 2);
assert.ok(!twice.includes('anchor-i05-2'));
console.log('Review rendering checks passed');
