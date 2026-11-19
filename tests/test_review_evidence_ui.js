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

// A workspace review keeps its result map and quantity comparisons, each linking to a line of a document.
vm.runInContext(`
state = {};
paper = {id: 'p', main: 'paper.md'};
decisions = {items:{}};
review = {id:'workspace', findings:[], raw_response:{
  result_map:{nodes:[{document:'paper.md', line:1}],edges:[{document:'paper.md', from:1, quote:'Fig 1',
    to:[{document:'paper.md', line:2}, {document:'S1.md', line:3}]}],checks:[],limitation:'Literal references only.'},
  result_comparisons:[{status:'needs_reconciliation',limitation:'Not independently verified.',observations:[{document:'paper.md',line:1,value:'1.2',metric:'slope',quote:'<script>value</script>'}]}]
}};
cards();
`, context);
assert.equal(elements.get('#handoff-details').hidden, false);
assert.equal(elements.get('#run-panel').hidden, true);
assert.equal(elements.get('#filter-escalated').hidden, true);
assert.ok(html('#handoff-ledger').includes('<p><a href="#line-paper.2emd-1">line 1</a> cites Fig 1: '
  + '<a href="#line-paper.2emd-2">line 2</a>, <a href="#line-S1.2emd-3">S1.md, line 3</a></p>'));
assert.ok(html('#handoff-ledger').includes('&lt;script&gt;value&lt;/script&gt;'));
assert.ok(!html('#handoff-ledger').includes('<script>'));

// A PeerReviewAgents run shows one card per issue, as run_view.py hands it over: the required
// changes, then the suggestions under their categories.
vm.runInContext(`
paper = {id: 'p', main: 'paper.md', documents: {'paper.md': ['alpha beta gamma']}, assets: [],
  pieces: [{document:'paper.md', lines:[1, 1], kind:'paragraph', section:'Results'}]};
const member = (uid, extra) => ({finding_uid:uid, slot:'core-1', track:'core', severity:'major', kind:'issue',
  basis:'judgement', escalate:false, title:'Finding '+uid, document:'paper.md', line:1, end_line:1, quote:'alpha',
  evidence_lines:[1], comment:'Comment '+uid, start:0, end:5, placement:'anchored', ...extra});
const issue = (id, rank, group, extra) => ({id, source_id:id, number:rank, rank, group, name:'Issue '+id,
  title:'Issue '+id, statement:'Statement '+id, comment:'Statement '+id, severity:'major',
  category:'statistics-and-inference', raised_by:1,
  members:[], audits:[], rebuttal_quote:null, rebuttal_line:null, rebuttal_document:'paper.md',
  kind:'issue', escalate:false, evidence:[{document:'paper.md', line:1}],
  document:'paper.md', line:1, end_line:1, quote:'alpha', start:0, end:5, placement:'anchored', replacement:null, ...extra});
// Every review is a fresh panel. The fields i01 carries about an earlier round are read by nothing.
review = {id:'run', summary:'Editor summary', raw_response:undefined, findings:[
  issue('i01', 1, 'required', {raised_by:2, escalate:true, status:'persisting', status_reason:'Still <b>wrong</b>',
    prior_id:'i01', prior_rank:2, text_unchanged_reason:'Same <b>text</b>',
    surviving_quotes:[{finding_uid:'old', document:'paper.md', line:1, quote:'beta gamma'}],
    audits:['audit_stats.md'], rebuttal_quote:'gamma', rebuttal_line:1,
    evidence:[{document:'paper.md', line:1}, {document:'S1.md', line:2}], members:[
      member('u1', {track:'field', basis_reason:'No arithmetic receipt.', escalate:true,
                    source_urls:['https://example.org/a', 'javascript:alert(1)']}),
      member('u2', {slot:'core-2', basis:'two-quotes', quote:'alpha beta', end:10, counterevidence:'Checked the methods.'})]}),
  issue('i02', 2, 'suggestion', {severity:'minor', category:'presentation', kind:'edit', quote:'gamma', start:11,
    end:16, replacement:'delta', members:[member('u3', {kind:'edit', severity:'minor', quote:'gamma', start:11, end:16,
                                                        replacement:'delta'})]}),
  issue('i03', 3, 'suggestion', {severity:'minor', category:'reproducibility', placement:'unplaced', start:null,
    end:null, members:[member('u4', {severity:'minor', placement:'unplaced', start:null, end:null, slot:'spec-code',
      track:'code', basis:'code-checked', code_evidence:{path:'analysis/<fdr>.py', start_line:2, end_line:3,
        text:'if q < 0.05:\\n    keep(<row>)', sha256:'fcc34629203ab7066790d8b5d78f005de4b936ea6c4fb30bb4147642ffba90df'}})]}),
], run:{arm:'full-two-track', reviewer_count:3, status:'complete', escalated_count:1, review_guard_status:'clean',
  cause:null, note:'the review was written and the run was marked blocked afterwards: rate limit',
  problems:['runtime.json is not valid JSON <x>'], publishable:false,
  not_publishable_reasons:['1 file(s) could not be read in full, and they are named in problems'],
  findings_source:'issues', issues_source:'editor',
  missing_stages:[], none_found:[], limitations:['Advisory only.'],
  verdict:{significance:'High if true', strength_of_evidence:'Weak', reasoning:'Correlation only', basis:'judgement', limitation:'Not a score.'},
  escalation_rulings:[{finding_uid:'u1', ruling:'Accepted as central.'}],
  audits:{stats:'# Stats audit <script>x</script>'},
  agents:[{slot:'spec-stats', role:'specialist', track:'stats', assigned_model:'claude-sonnet-5-5', model:'claude-sonnet-5-5',
           attempt:1, tool_calls:4, session_calls:9, tokens:5000, state:'done', findings:1, none_found:false, labels:['spec-stats']},
          {slot:'recorder', role:'recorder', track:'ingest', assigned_model:'claude-haiku-5-5', model:null, attempt:1, tool_calls:4,
           session_calls:12, tokens:42000, state:'completed', findings:0, none_found:false, labels:['ingest', 'write review']}],
  models_unverified:['recorder'],
  code:{reviewed:true, kind:'folder', source:'/home/someone/paper-repo', commit:'0123456789abcdef0123', branch:'main',
        dirty:true, snapshot:'/home/someone/run/code', files_in_snapshot:3, files_skipped:1,
        truncated:'more than 400 files of text source', source_cut:0, files_opened:['analysis/<fdr>.py'], opened:1, searches:2,
        data_listed:0, data_fetched:0, data_partial:0, data_refused:0, data_bytes:0, data:[]},
  code_check:null,
  findings_by_track:{field:1, core:1}, wall_seconds:600, tokens_total:1234}};
cards();
`, context);
const comments = html('#comments');
const panel = html('#run-panel');
assert.equal(elements.get('#run-panel').hidden, false);
for (const name of ['required', 'suggestions', 'escalated']) assert.equal(elements.get('#filter-' + name).hidden, false, name);
for (const name of ['scientific', 'copyedit', 'questions']) assert.equal(elements.get('#filter-' + name).hidden, true, name);
assert.equal(elements.get('#finding-count').textContent, '1 required · 2 suggestions');
// A run that is not publishable says so above its comments, with every reason, and only there.
assert.ok(comments.startsWith('<div class="not-publishable error" role="note"><p><strong>This run is not publishable.</strong>'));
assert.ok(comments.includes('<li>1 file(s) could not be read in full, and they are named in problems</li>'));
assert.ok(!html('#run-panel').includes('could not be read in full'));
// Required changes come first in rank order, then the suggestions under their categories.
const order = ['Required changes (1)', 'id="note-i01"', 'Suggestions (2)', '<h4 class="issue-category">Presentation</h4>',
               'id="note-i02"', '<h4 class="issue-category">Reproducibility</h4>', 'id="note-i03"'];
order.forEach((text, index) => {
  assert.ok(comments.includes(text), text);
  if (index) assert.ok(comments.indexOf(text) > comments.indexOf(order[index - 1]), text);
});
// Nothing in the review or the run panel speaks of an earlier round.
for (const text of ['prior round', 'Prior round', 'closed-issues', 'class="badge status', 'persisting', 'Still &lt;b&gt;wrong',
                    'Same &lt;b&gt;text', 'beta gamma']) {
  assert.ok(!comments.includes(text) && !panel.includes(text), text);
}
// Nothing of the per-finding viewer is left: no appendix and no fallback for a server without revisions.
const sources = code + fs.readFileSync('paper_workspace/web/style.css', 'utf8') + fs.readFileSync('paper_workspace/web/index.html', 'utf8');
for (const text of ['appendix', 'legacyServer']) assert.ok(!sources.includes(text), text);
const cardOf = id => comments.slice(comments.indexOf(`id="note-${id}"`)).split('</article>')[0];
// Each card shows the issue, how many reviewers raised it and its members as evidence.
for (const text of ['Major · Statistics and inference', 'Issue i01</span>',
                    'Raised by 2 reviewers', 'Escalated', '<h3>1. Issue i01</h3>', 'Statement i01',
                    'Specialist reports: audit_stats.md',
                    'Evidence: 2 findings', 'core-1 · field track · issue · major', 'core-2 · core track · issue · major',
                    'Basis: judgement', 'title="No arithmetic receipt."', 'Basis: two-quotes', 'Comment u1', 'Comment u2',
                    '<blockquote>alpha beta</blockquote>', 'Counterevidence checked', 'Escalation ruling',
                    'Accepted as central.', 'href="https://example.org/a"', 'href="#anchor-i01-1">Go to passage',
                    'href="#anchor-i01-2">Go to passage', 'Mark for follow-up',
                    'Manuscript text the editor weighed against the computed finding</strong></p><blockquote>gamma</blockquote>'
                    + '<p><a href="#line-paper.2emd-1">Go to passage</a></p>',
                    'Evidence: <a href="#line-paper.2emd-1">line 1</a> <a href="#line-S1.2emd-2">S1.md, line 2</a>']) {
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
// A code-checked finding names its file and lines in the code snapshot and quotes the code, escaped.
for (const text of ['spec-code · code track', 'Basis: code-checked',
                    '<div class="cross-check code-evidence"><p><strong>Code checked</strong><br><code>analysis/&lt;fdr&gt;.py</code>, lines 2 to 3 of the run\'s code snapshot</p>',
                    '<pre>if q &lt; 0.05:\n    keep(&lt;row&gt;)</pre>']) {
  assert.ok(cardOf('i03').includes(text), text);
}
assert.ok(!cardOf('i03').includes('<fdr>'));
// A finding with no code_evidence shows no code block.
for (const id of ['i01', 'i02']) assert.ok(!cardOf(id).includes('Code checked'), id);
assert.equal(vm.runInContext("codeEvidence({code_evidence:{path:'a.py', start_line:4, end_line:4, text:'x = 1'}})", context),
  '<div class="cross-check code-evidence"><p><strong>Code checked</strong><br><code>a.py</code>, line 4 of the run\'s code snapshot</p><pre>x = 1</pre></div>');
assert.equal(vm.runInContext("codeEvidence({code_evidence:{path:'a.py', start_line:'4', end_line:4}})", context), '');
for (const text of ['Arm full-two-track', '3 reviewers', 'Status complete', 'Issues grouped by the editor',
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
// The panel says which code the run was reviewed against, naming a local folder by its own name only.
assert.ok(panel.includes('<div class="code-reviewed"><p><strong>Code reviewed</strong><br><code>paper-repo</code> at 0123456789ab with uncommitted changes'
  + '<br>1 of 3 files opened, 2 searches, 1 path left out of the snapshot, the snapshot stopped early: more than 400 files of text source</p>'
  + '<details><summary>Files opened (1)</summary><ul><li><code>analysis/&lt;fdr&gt;.py</code></li></ul></details></div>'));
assert.ok(!panel.includes('/home/someone'));
// A run given no code says nothing about code, as REVIEW.md does.
assert.equal(vm.runInContext("codeReviewed({reviewed:false, kind:'', source:'', files_opened:[]}) + codeReviewed(undefined)", context), '');
assert.ok(vm.runInContext("codeReviewed({reviewed:true, kind:'git-clone', source:'https://github.com/lab/paper', commit:'', opened:0, files_in_snapshot:1, files_opened:[], source_cut:0, data_listed:0, data:[]})", context)
  .includes('<code>https://github.com/lab/paper</code><br>0 of 1 file opened</p></div>'));
// The model asked is never shown as the model that ran.
assert.ok(!panel.includes('model ran claude-haiku-5-5'));
// The panel says which data files the review fetched, whole or in part, and that a cut snapshot is not the whole of the code.
const dataPanel = vm.runInContext(`codeReviewed({reviewed:true, kind:'folder', source:'/x/paper-repo', commit:'', opened:3,
  files_in_snapshot:2, files_opened:['a.py'], source_cut:2, data_listed:5, data_fetched:2, data_partial:1, data_refused:1,
  data:[{path:'analysis/<scores>.csv', bytes:367794, stored_bytes:19991, partial:true, changed:''},
        {path:'analysis/summary.json', bytes:42, stored_bytes:42, partial:false,
         changed:'changed since the snapshot was taken: 40 byte(s) then, 42 now'}]})`, context);
for (const text of ['<br>2 of 5 data files fetched, 1 only in part, 1 refused</p>',
                    '<p class="unverified">2 program source files did not fit in the snapshot, so it is not the whole of the code, and no finding may say the code never does something.</p>',
                    '<details><summary>Data files fetched (2)</summary><ul><li><code>analysis/&lt;scores&gt;.csv</code>, only the first 19991 of 367794 bytes read</li>',
                    '<li><code>analysis/summary.json</code>, read whole, 42 bytes, changed since the snapshot was taken: 40 byte(s) then, 42 now</li>']) {
  assert.ok(dataPanel.includes(text), text);
}
// A run whose reviewers fetched no data file and whose snapshot cut nothing says nothing of either.
assert.ok(!panel.includes('data file') && !panel.includes('did not fit') && !panel.includes('Code check'));
// Code evidence that is a data file says how much of it the review read.
assert.ok(vm.runInContext("codeEvidence({code_evidence:{path:'s.csv', start_line:2, end_line:2, text:'P1,1'}, code_data:{path:'s.csv', bytes:900, stored_bytes:300, partial:true, changed:''}})", context)
  .includes("<code>s.csv</code>, line 2 of the run's code snapshot<br>A data file, only the first 300 of 900 bytes read</p><pre>P1,1</pre>"));

// A finding the code check threw out is listed after every issue, marked as thrown out with the code that
// disproved it, and is never a card: it takes no decision and no author response.
vm.runInContext(`review.run.code_check = {cap:20, checked:2, over_cap:1, counts:{confirmed:1, contradicted:1, 'not-shown':0},
  thrown_out:[{id:'u9', finding_uid:'u9', slot:'spec-numbers', track:'numbers', severity:'major',
    title:'The mean <hides> the spread', comment:'Show each repeat.', quote:'alpha', document:'paper.md', line:1, end_line:1,
    basis:'judgement', assumed_method:'The figure plots the mean.', note:'It is the <median>.',
    code_evidence:{path:'analysis/summary.json', start_line:2, end_line:2, text:'  "figure": "median"', sha256:'x'},
    code_data:{path:'analysis/summary.json', bytes:42, stored_bytes:42, partial:false, changed:''},
    start:0, end:5, anchor_text:'alpha', placement:'anchored', page:null, bbox:null}]}; cards();`, context);
const withThrown = html('#comments');
const thrown = withThrown.slice(withThrown.indexOf('<details class="thrown-out"'));
assert.ok(withThrown.includes('<details class="thrown-out" id="thrown-out" open><summary>Thrown out: the code does not do what the finding said (1)</summary>'));
assert.ok(withThrown.indexOf('<details class="thrown-out"') > withThrown.indexOf('id="note-i03"'));
for (const text of ['spec-numbers · numbers track · major',
                    '<p class="thrown-out-mark" role="note">Thrown out by the code check. This is not an open issue: the code does not do what this finding said.</p>',
                    '<h4>The mean &lt;hides&gt; the spread</h4>', '<blockquote>alpha</blockquote>', '<a href="#line-paper.2emd-1">Go to passage</a>',
                    '<strong>What the finding took the code to do</strong><br>The figure plots the mean.',
                    '<strong>Code that contradicts it</strong><br><code>analysis/summary.json</code>, line 2 of the run\'s code snapshot<br>A data file, read whole, 42 bytes</p><pre>  &quot;figure&quot;: &quot;median&quot;</pre>',
                    '<strong>Code check note</strong><br>It is the &lt;median&gt;.']) {
  assert.ok(thrown.includes(text), text);
}
for (const text of ['<article', 'data-action', 'Accept wording', 'Author comment', '<hides>']) assert.ok(!thrown.includes(text), text);
assert.ok(!withThrown.includes('id="note-u9"'));
assert.equal(elements.get('#finding-count').textContent, '1 required · 2 suggestions · 1 thrown out by the code check');
assert.ok(html('#run-panel').includes('<p class="count">Code check: 2 checked, 1 confirmed, 1 thrown out, 0 not shown in the code, 1 over its cap of 20 left unchecked</p>'));
// A filter shows only issues, so the thrown-out findings leave the view with it.
vm.runInContext("filter = 'required'; cards();", context);
assert.ok(!html('#comments').includes('thrown-out'));
// A thrown-out finding carried from an earlier draft says so, and is not counted among the open problems.
// The rows are shaped as /api/ledger hands them over: ledger_view in revisions.py, with each row's status.
vm.runInContext(`filter = 'all'; ledger = [{id:'original:run:u9', raised_on:'original', review_id:'run', source_id:'u9',
  paper_id:'p', raised_as:'thrown_out', status:'thrown_out', title:'The mean <hides> the spread', category:null,
  statement:'Show each repeat.', severity:'major', evidence:[{document:'paper.md', line:1, end_line:1, quote:'alpha'}],
  wording:null, decisions:[], fix_checks:[], finding:review.run.code_check.thrown_out[0]}]; cards(); history();`, context);
const carried = html('#history-ledger');
for (const text of ['<span class="badge">original:run:u9</span> Thrown out by the code check',
                    'Thrown out by the code check. This is not an open issue', '<strong>Code that contradicts it</strong>',
                    'It is the &lt;median&gt;.', 'Raised on draft original by review run. Its quotes are from that draft.']) {
  assert.ok(carried.includes(text), text);
}
for (const text of ["Author's decision", 'fix check']) assert.ok(!carried.includes(text), text);
assert.ok(!elements.get('#finding-count').textContent.includes('earlier problem'));
// An earlier problem shows the author's decisions, the latest first with the draft each was made on, then a
// later check that did not reach it, then the latest verdict with the engine's own verdict and basis names and
// the quote of the checked draft it rests on. Each fix check is shaped as fix_check_entries in revisions.py
// records it, and each decision as ledger_of reads it. The earlier checks stay below.
vm.runInContext(`ledger = [{id:'original:run:i03', raised_on:'original', review_id:'run', source_id:'i03', paper_id:'p',
  raised_as:'problem', status:'open', title:'The seed is <unstated>', category:'reproducibility',
  statement:'State the seed.', severity:'major', evidence:[{document:'paper.md', line:1, end_line:1, quote:'alpha'}],
  wording:'noted', decisions:[{draft:'original', status:'addressed', note:'We added it.', rationale:'Methods now name the seed.'},
                              {draft:'third', status:'addressed', note:'', rationale:'The <generator> is named now.'}],
  fix_checks:[{draft:'second', run:'/checks/one', date:'2026-11-01', verdict:'cannot-tell', basis:'old-quote-stands',
               evidence:null, old_evidence:[{document:'paper.md', quote:'An <older> quote.', present:true}],
               searches:['seed', 'random state'], reason:'The draft keeps the sentence.', note:''},
              {draft:'third', run:'/checks/two', date:'2026-11-17', verdict:'not-fixed', basis:'quote',
               evidence:{document:'paper.md', line:4, end_line:4, page:2, section:'Methods', quote:'The seed is <42>.'},
               old_evidence:[{document:'paper.md', quote:'alpha', present:false}], searches:[], reason:'',
               note:'The generator is not named.'},
              {draft:'fourth', run:'/checks/three', date:'2026-11-18', verdict:null, basis:'', evidence:null,
               old_evidence:[], searches:[], reason:'Past the cap of 40 problems one fix check reads.', note:''}],
  finding:{}},
  {id:'original:run:i04', raised_on:'original', review_id:'run', source_id:'i04', paper_id:'p', raised_as:'problem',
  status:'declined', title:'Scope', category:'claims-and-conclusions', statement:'Widen the claim.', severity:'minor',
  evidence:[], wording:'noted', decisions:[{draft:'original', status:'declined', note:'', rationale:'Out of scope.'}],
  fix_checks:[], finding:{}},
  {id:'second:round-1:i01', raised_on:'second', review_id:'round-1', source_id:'i01', paper_id:'p', raised_as:'problem',
  status:'open', title:'Donors', category:'methods', statement:'Name the donors.', severity:'major',
  evidence:[{document:'paper.md', line:null, end_line:null, quote:'one donor'}], wording:null, decisions:[],
  fix_checks:[], finding:{}}];
  cards(); history();`, context);
const problems = html('#history-ledger');
for (const text of ['<span class="badge">original:run:i03</span> Open', 'Reproducibility: The seed is &lt;unstated&gt;</strong> · major',
                    'State the seed.', '<blockquote>alpha</blockquote>',
                    "<p>Wording noted on draft original</p><p><strong>Author's decision on draft third</strong><br>Issue addressed by the author<br>Rationale: The &lt;generator&gt; is named now.</p>"
                    + "<p><strong>Author's decision on draft original</strong><br>Issue addressed by the author<br>Note: We added it.<br>Rationale: Methods now name the seed.</p>"
                    + '<p class="muted"><strong>Not checked on draft fourth on 2026-11-18</strong><br>Past the cap of 40 problems one fix check reads.</p>'
                    + '<p><strong>Fix check of draft third on 2026-11-17: not-fixed</strong><br>Basis: quote<br>'
                    + "Checker's note: The generator is not named.</p>"
                    + '<p class="muted">From draft third, page 2 of its PDF, section Methods</p><blockquote>The seed is &lt;42&gt;.</blockquote>'
                    + '<details><summary>Earlier fix checks (1)</summary><p><strong>Fix check of draft second on 2026-11-01: cannot-tell</strong>'
                    + '<br>Basis: old-quote-stands<br>Reason: The draft keeps the sentence.<br>Searched the draft for: seed, random state</p>'
                    + '<p class="muted">Still in draft second word for word</p><blockquote>An &lt;older&gt; quote.</blockquote></details>',
                    '<span class="badge">original:run:i04</span> Declined by the author',
                    "<p>Wording noted on draft original</p><p><strong>Author's decision on draft original</strong><br>Issue declined by the author<br>Rationale: Out of scope.</p>",
                    'No later draft has been checked for this problem.',
                    // A problem an engine review raised has no wording, and the card says when no decision was made.
                    'Raised on draft second by review round-1. Its quotes are from that draft.</p><p class="muted">The author has not decided on this problem.</p><p class="muted">No later draft has been checked for this problem.</p>']) {
  assert.ok(problems.includes(text), text);
}
// The verdict is the engine's name as written, and the run folder path is not shown.
for (const text of ['not fixed', 'cannot tell', '/checks/']) assert.ok(!problems.includes(text), text);
// A verdict with no quote of the checked draft says whether each quote it was raised on is still there.
vm.runInContext(`ledger = [{...ledger[0], status:'fixed', fix_checks:[{draft:'second', run:'/checks/one', date:'2026-11-01',
  verdict:'fixed', basis:'old-quote-gone', evidence:null, old_evidence:[{document:'paper.md', quote:'alpha', present:false}],
  searches:['seed'], reason:'', note:''}]}]; history();`, context);
assert.ok(html('#history-ledger').includes('<p><strong>Fix check of draft second on 2026-11-01: fixed</strong><br>Basis: old-quote-gone<br>'
  + 'Searched the draft for: seed</p><p class="muted">No longer in draft second word for word</p><blockquote>alpha</blockquote>'));
assert.ok(!html('#history-ledger').includes('Earlier fix checks'));
// The count is of the ledger cards() last drew: the seed and the donors are open, and the scope is declined.
assert.ok(elements.get('#finding-count').textContent.endsWith(' · 2 earlier problems open'));
// A card's author response can decline the issue.
assert.ok(html('#comments').includes('<option value="declined" >Declined by author</option>'));
vm.runInContext('ledger = []; review.run.code_check = null; cards();', context);

// The run panel shows the fixture ledger, which the engine's own ledger code wrote, as run_view.py hands it over.
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

// A review with no findings says whether the reviewers raised none, the guard held them all or the code check threw them out.
assert.equal(vm.runInContext("runStatus({status:'complete-without-findings', quarantined_findings_count:0, code_check:null})", context),
             'Status complete-without-findings: the reviewers raised none');
assert.equal(vm.runInContext("runStatus({status:'complete-without-findings', quarantined_findings_count:2, code_check:null})", context),
             'Status complete-without-findings: the guard quarantined all 2');
const checked=contradicted=>`{cap:20, checked:${contradicted}, over_cap:0, counts:{confirmed:0, contradicted:${contradicted}, 'not-shown':0}, thrown_out:[]}`;
assert.equal(vm.runInContext(`runStatus({status:'complete-without-findings', quarantined_findings_count:0, code_check:${checked(1)}})`, context),
             'Status complete-without-findings: the code check threw out all 1');
assert.equal(vm.runInContext(`runStatus({status:'complete-without-findings', quarantined_findings_count:2, code_check:${checked(1)}})`, context),
             'Status complete-without-findings: the guard quarantined 2 and the code check threw out 1');
assert.equal(vm.runInContext(`runStatus({status:'complete-without-findings', quarantined_findings_count:0, code_check:${checked(0)}})`, context),
             'Status complete-without-findings: the reviewers raised none');
// A check whose record named no cap says how many were over it without a number for the cap.
assert.ok(vm.runInContext("codeCheckCounts({cap:null, checked:0, over_cap:3, counts:{confirmed:0, contradicted:0, 'not-shown':0}})", context)
  .includes('3 over its cap left unchecked'));

// Every anchored member marks the manuscript, overlapping quotes included, each pinned with its issue's number.
// The issue that is one edit shows its wording, and the unplaced member marks nothing.
assert.equal(vm.runInContext("quoteMarkup('paper.md', 1)", context),
  '<span class="anchor" id="anchor-i01-2"></span><mark class="question-mark anchor" id="anchor-i01-1">alpha</mark>'
  + '<a class="pin" href="#note-i01" aria-label="Comment 1">1</a><mark class="question-mark"> beta</mark>'
  + '<a class="pin" href="#note-i01" aria-label="Comment 1">1</a> <span class="before anchor" id="anchor-i02-1">gamma</span>'
  + ' <span class="after">delta</span><a class="pin" href="#note-i02" aria-label="Comment 2">2</a>');
// Accepting the edit issue applies its one member's wording.
assert.equal(vm.runInContext("decisions = {items:{i02:'accepted'}}; acceptedText('paper.md', 1)", context), 'alpha beta delta');
vm.runInContext('decisions = {items:{}};', context);

// Each run filter keeps its own cards.
const shown = name => vm.runInContext(`filter = '${name}'; cards(); review.findings.map(item => item.id)
  .filter(id => document.querySelector('#comments').innerHTML.includes('id="note-' + id + '"')).join(' ')`, context);
assert.equal(shown('required'), 'i01');
assert.equal(shown('suggestions'), 'i02 i03');
assert.equal(shown('escalated'), 'i01');
assert.equal(shown('all'), 'i01 i02 i03');
// A workspace filter does not survive onto a run, and a run filter does not survive onto a workspace review.
assert.equal(shown('questions'), 'i01 i02 i03');
assert.equal(vm.runInContext('filter', context), 'all');
vm.runInContext("filter = 'escalated'; review = {id:'workspace', findings:[]}; cards();", context);
assert.equal(vm.runInContext('filter', context), 'all');
assert.equal(elements.get('#run-panel').hidden, true);
for (const name of ['required', 'suggestions', 'escalated']) assert.equal(elements.get('#filter-' + name).hidden, true, name);
for (const name of ['scientific', 'copyedit', 'questions']) assert.equal(elements.get('#filter-' + name).hidden, false, name);

// A run that is not publishable and has nothing to show says why, not that the review is empty.
vm.runInContext(`review = {id:'run', summary:'', findings:[], run:{status:'complete', problems:[], publishable:false,
  not_publishable_reasons:['the run folder has no readable issues.json'], findings_source:'none', issues_source:null,
  missing_stages:[], agents:[], limitations:[]}}; cards();`, context);
assert.equal(html('#comments'), '<div class="not-publishable error" role="note"><p><strong>This run is not publishable.</strong> '
  + 'It has no review to show.</p><ul><li>the run folder has no readable issues.json</li></ul></div>');
assert.equal(elements.get('#finding-count').textContent, 'No findings');

// A run with no issues shows its recorded findings under their own heading.
vm.runInContext(`review.run.findings_source = 'ledger';
review.findings = [{id:'aa11', source_id:'aa11', number:1, group:'ledger', title:'Recorded finding', comment:'Comment',
  severity:'major', category:null, raised_by:1, kind:'issue', document:'paper.md', line:1, end_line:1,
  quote:'beta', start:6, end:10, placement:'anchored', evidence:[], audits:[],
  members:[{finding_uid:'aa11', slot:'core-1', title:'Recorded finding', comment:'Comment', quote:'beta',
            document:'paper.md', line:1, end_line:1, start:6, end:10, placement:'anchored', evidence_lines:[]}]}];
cards();`, context);
assert.ok(html('#comments').includes('<h3 class="issue-group">Findings recorded before any issues were written (1)</h3>'));
assert.ok(html('#comments').includes('It has no review to show.') === false);
assert.equal(elements.get('#finding-count').textContent, '1 finding, not grouped into issues');
// The member repeats neither the card's title nor its comment.
assert.equal(html('#comments').split('Recorded finding').length - 1, 1);

// A card with no engine id is numbered by its place and takes no decision. A decision saved
// under its number is neither shown nor applied, and it is counted with the other stale ones.
vm.runInContext(`review.findings = [{id:'run-1', source_id:'not a uid', number:1, group:'ledger', decidable:false,
  title:'Recorded edit', comment:'Comment', severity:'minor', category:null, raised_by:1, kind:'edit',
  replacement:'delta', document:'paper.md', line:1, end_line:1, quote:'gamma', start:11, end:16, placement:'anchored',
  evidence:[], audits:[], members:[{finding_uid:'not a uid', slot:'core-1', title:'Recorded edit',
  comment:'Comment', kind:'edit', replacement:'delta', quote:'gamma', document:'paper.md', line:1, end_line:1, start:11,
  end:16, placement:'anchored', evidence_lines:[]}]}];
decisions = {items:{'run-1':'accepted'}, annotations:{'run-1':{author_comment:'Saved on another card', issue_status:'open', rationale:''}}};
cards();`, context);
const placed = html('#comments');
assert.ok(placed.includes('<p class="muted no-engine-id" role="note">This card has no engine id, so a decision on it could land on another card. Re-run the review to decide on it.</p>'));
for (const text of ['data-action', 'author-response', 'Saved on another card', '>accepted<']) assert.ok(!placed.includes(text), text);
assert.equal(vm.runInContext("acceptedText('paper.md', 1)", context), 'alpha beta gamma');
assert.ok(placed.startsWith('<p class="stale-decisions muted" role="note">1 saved decision no longer matches a card in this review. '
  + 'The decisions file is left as it is.</p>'));

// Decisions saved under an earlier viewer's per-finding keys, or under an issue this run no longer
// holds, are counted once above the cards. A file with none says nothing.
vm.runInContext(`review = {id:'run', summary:'', findings:[issue('i05', 1, 'required', {raised_by:2, members:[
  member('u5', {}), member('u6', {slot:'core-2'})]})], run:{status:'complete', problems:[], publishable:true,
  not_publishable_reasons:[], findings_source:'issues', issues_source:'editor', missing_stages:[],
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
assert.equal(vm.runInContext("quoteMarkup('paper.md', 1)", context),
  '<mark class="question-mark anchor" id="anchor-i05-1">alpha</mark><a class="pin" href="#note-i05" aria-label="Comment 1">1</a> beta gamma');
const twice = html('#comments');
for (const text of ['core-1 · core track · issue · major', 'core-2 · core track · issue · major', 'Evidence: 2 findings']) {
  assert.ok(twice.includes(text), text);
}
assert.equal(twice.split('href="#anchor-i05-1">Go to passage').length - 1, 2);
assert.ok(!twice.includes('anchor-i05-2'));

// A quote across a line break marks the end of its first line and the start of its last. Its wording
// and its pin go on the last line, and accepting it leaves both lines in place with their numbers.
vm.runInContext(`paper = {id:'p', main:'paper.md', documents:{'paper.md':['alpha beta', 'gamma delta']}, pieces:[], assets:[]};
review = {id:'workspace', findings:[{id:'w-1', kind:'edit', document:'paper.md', line:1, end_line:2, start:6, end:5,
  placement:'anchored', quote:'beta gamma', replacement:'beta, gamma'}]};
decisions = {items:{}};`, context);
assert.equal(vm.runInContext("quoteMarkup('paper.md', 1)", context), 'alpha <span class="before anchor" id="anchor-w-1">beta</span>');
assert.equal(vm.runInContext("quoteMarkup('paper.md', 2)", context),
  '<span class="before">gamma</span> <span class="after">beta, gamma</span><a class="pin" href="#note-w-1" aria-label="Comment 1">1</a> delta');
assert.equal(vm.runInContext("decisions = {items:{'w-1':'accepted'}}; acceptedText('paper.md', 1) + '|' + acceptedText('paper.md', 2)", context),
  'alpha beta, gamma| delta');
// A span that ends before it starts marks nothing.
assert.equal(vm.runInContext("review.findings[0].end_line = 1; review.findings[0].end = 2; quoteMarkup('paper.md', 1)", context), 'alpha beta');

// The manuscript below is one the engine's own Read stage wrote, through its scripted reader, as
// /api/paper serves it. tests/fixtures/reader/README.md says what the reader did. Each piece a model
// wrote says so, with the model the engine's Read stage names. A piece read again from the page image
// keeps the converter's reading beside it, a figure description is not the authors' words, and a page
// the converter returned nothing from is named above the manuscript and linked to the first line the
// engine says its transcription became. The reader's note is shown first, as that model's account and
// escaped as text. A piece the reader read again as three says which part it is and keeps the
// converter's whole reading, a prose part is the converter's text with spans cut out, and debris folded
// into a piece is kept under it as the converter read it, on the one part the engine wrote it on.
context.readerFixture = JSON.parse(fs.readFileSync('tests/fixtures/reader/paper.json', 'utf8'));
const showReaderFixture = half => {
  vm.runInContext(`review = {id:'none', findings:[]}; decisions = {items:{}};
    document.querySelector('#search').value = ''; paper = readerFixture.${half}; manuscript();`, context);
  const out = html('#manuscript');
  const rows = context.readerFixture[half].pieces;
  const block = test => {
    const row = rows.find(test);
    return out.split('<section').find(part => part.includes(`id="line-paper.2emd-${row.lines[0]}"`));
  };
  const original = row => row.original || {};
  return {out, block, rows,
    equation: block(row => row.kind === 'equation'),
    described: block(row => row.kind === 'figure-description'),
    lost: block(row => row.page === 3),
    converted: block(row => row.source === 'text' && row.kind === 'paragraph'),
    part: n => block(row => original(row).of === 3 && original(row).part === n),
    cut: block(row => original(row).of === 1)};
}
const read = showReaderFixture('read');
const folded = '<summary>One piece the converter read separately, folded into this one</summary>';
assert.equal(read.out.split('<section').length - 1, read.rows.length);
assert.ok(!read.converted.includes('model-written') && !read.converted.includes('provenance'));
assert.ok(read.equation.includes('model-written') && read.equation.includes(
  'Read from the image of page 2 by claude-sonnet-5-5, because the converter garbled it</p>'));
assert.ok(read.equation.includes("<summary>The converter's reading</summary><pre>E = m c^{2</pre>"));
assert.ok(read.described.includes("AI description of the figure image by claude-sonnet-5-5, not the authors' words"));
assert.ok(read.described.includes(folded + '<pre>0 10 20 30 40 mm</pre>'));
assert.ok(read.lost.includes('Written by claude-sonnet-5-5 from the image of page 3, a page the converter returned no text from'));
assert.ok(read.part(1).includes("The converter's text, cut by claude-sonnet-5-5 after reading the image of page 2. Every character in it is the converter's. It is part 1 of 3 of what the converter read as one paragraph</p>"));
for (const n of [1, 2, 3]) {
  assert.ok(read.part(n).includes("<summary>The converter's reading, all 3 parts</summary><pre>The current was logged every hour. Hour Current (mA) 1 4.5 2 9.0</pre>"), n);
}
assert.ok(read.part(2).includes('Read from the image of page 2 by claude-sonnet-5-5, because the converter garbled it. It is part 2 of 3 of what the converter read as one paragraph</p>'));
assert.ok(read.part(3).includes('It is part 3 of 3 of what the converter read as one paragraph</p>'));
// The engine writes a re-read's debris on its first part that is not prose, the table, and the viewer
// shows it there as written. The description's own debris is the only other fold on the page.
assert.ok(read.part(2).includes(folded + '<pre>with $\\{$</pre>'));
assert.ok(!read.part(1).includes('folded into') && !read.part(3).includes('folded into'));
assert.equal(read.out.split(folded).length - 1, 2);
// A prose-only re-read is one part, so it names no part.
assert.ok(read.cut.includes("The converter's text, cut by claude-sonnet-5-5 after reading the image of page 2. Every character in it is the converter's</p>"));
assert.ok(read.cut.includes("<summary>The converter's reading</summary><pre>The readings held across the week qn,s,d else and no widget moved.</pre>"));
assert.ok(!read.cut.includes('part 1 of'));
const lostLine = context.readerFixture.read.ai_read.lost_pages[0].added[0].lines[0];
assert.ok(read.out.startsWith('<aside class="reader-note" role="note"><p><strong>A note from claude-sonnet-5-5, the model that read the pages.</strong> '
  + "It is that model's account of what it found, not the authors' text and not a review finding.</p>"
  + '<blockquote>Table 1 came back as a paragraph of run-together cells and is a table again. '
  + 'The &lt;b&gt;axis&lt;/b&gt; numbers of Figure 1 were a paragraph of their own and are folded into its description.</blockquote></aside>'
  + `<p class="lost-pages" role="note">Page <a href="#line-paper.2emd-${lostLine}">3</a> came only from claude-sonnet-5-5.`));
assert.ok(read.lost.includes(`id="line-paper.2emd-${lostLine}"`));
// The Scaffold port of that manuscript names the reader as the model that wrote its pieces and claims
// no page image: the engine records that model as ai_model, with no lost page and no note.
const written = showReaderFixture('ported');
assert.ok(!written.out.includes('lost-pages') && !written.out.includes('Read from the image') && !written.out.includes('from the image of'));
assert.ok(!written.out.includes('reader-note'));
for (const block of [written.equation, written.lost]) {
  assert.ok(block.includes('Written by claude-sonnet-5-5. No page image was read here, so there is no page to compare it with</p>'));
}
assert.ok(written.equation.includes('<summary>The text it replaced</summary><pre>E = m c^{2</pre>'));
assert.ok(written.described.includes("AI description of the figure image by claude-sonnet-5-5, not the authors' words"));
assert.ok(written.part(1).includes("The converter's text, cut by claude-sonnet-5-5. Every character in it is the converter's. It is part 1 of 3"));
assert.ok(written.part(1).includes('<summary>The text it replaced, all 3 parts</summary>'));
assert.ok(written.part(2).includes('Written by claude-sonnet-5-5. No page image was read here, so there is no page to compare it with. It is part 2 of 3'));
assert.ok(written.part(2).includes(folded + '<pre>with $\\{$</pre>'));
assert.equal(written.out.split(folded).length - 1, 2);
console.log('Review rendering checks passed');
