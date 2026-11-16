let paper, review, decisions, state, ledger=[], mode='markup', filter='all';
const pendingResponses=new Map();
const responseKey=id=>JSON.stringify([paper.id,review.id,id]);
const $=selector=>document.querySelector(selector);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const segment=(text,start,end)=>Array.from(text).slice(start,end).join('');
const requestedDraft=()=>new URLSearchParams(location.search).get('draft');
const withDraft=path=>path+(path.includes('?')?'&':'?')+'draft='+encodeURIComponent(state?.selected||requestedDraft()||'original');
function error(message){$('#error').textContent=message;$('#error').hidden=!message;}
async function api(path,options){const response=await fetch(path,options);const value=await response.json();if(!response.ok){const failure=Error(value.error||response.statusText);failure.status=response.status;throw failure;}return value;}
// The passages a card marks on the manuscript. A run's issue marks every anchored member, each
// with its own anchor id. A workspace finding has no members and marks its own quote.
function anchorsOf(item){
 const label=item.number??item.id.split('-').at(-1);
 const members=(item.members||[]).length?item.members.map((member,n)=>({...member,anchor:`${item.id}-${n+1}`})):[{...item,anchor:item.id}];
 return members.filter(member=>member.placement==='anchored'&&member.block_id&&Number.isInteger(member.start)&&Number.isInteger(member.end)&&member.start<member.end)
  .map(member=>({...member,target:item.id,label,edit:item.kind==='edit'&&typeof member.replacement==='string'?member.replacement:null}));
}
// Members of one issue, or of two, can quote the same or overlapping text, so the block is cut at
// every start and end. Each piece is marked by every passage that covers it, and each passage
// ends with its suggested wording, when it has one, and a pin to its card.
function quoteMarkup(block){
 const marks=review.findings.flatMap(anchorsOf).filter(mark=>mark.block_id===block.id);
 const length=Array.from(block.text).length;
 const cuts=[...new Set([0,length,...marks.flatMap(mark=>[mark.start,mark.end])])].filter(at=>at>=0&&at<=length).sort((a,b)=>a-b);
 let output='';
 cuts.forEach((at,index)=>{
  for(const mark of marks.filter(row=>row.end===at)){
   if(mark.edit!==null)output+=` <span class="after">${esc(mark.edit)}</span>`;
   output+=`<a class="pin" href="#note-${esc(mark.target)}" aria-label="Comment ${esc(mark.label)}">${esc(mark.label)}</a>`;
  }
  const next=cuts[index+1];
  if(next===undefined)return;
  const text=esc(segment(block.text,at,next));
  const covering=marks.filter(mark=>mark.start<=at&&mark.end>=next);
  if(!covering.length){output+=text;return;}
  const [first,...others]=marks.filter(mark=>mark.start===at);
  const tag=covering.some(mark=>mark.edit!==null)?['span','before']:['mark','question-mark'];
  output+=others.map(mark=>`<span class="anchor" id="anchor-${esc(mark.anchor)}"></span>`).join('')
   +`<${tag[0]} class="${tag[1]}${first?' anchor':''}"${first?` id="anchor-${esc(first.anchor)}"`:''}>${text}</${tag[0]}>`;
 });
 return output;
}
function acceptedText(block){
 let text=block.text;
 const notes=review.findings.filter(item=>item.block_id===block.id&&decisions.items[item.id]==='accepted').sort((a,b)=>b.start-a.start);
 for(const item of notes)text=segment(text,0,item.start)+item.replacement+segment(text,item.end);
 return esc(text);
}
function tableMarkup(block,text){
 const structure=block.table_structure;
 const validCell=cell=>cell&&typeof cell.text==='string'&&Number.isInteger(cell.colspan)&&cell.colspan>0
  &&(cell.rowspan===undefined||(Number.isInteger(cell.rowspan)&&cell.rowspan>0));
 if(!structure||!Number.isInteger(structure.columns)||structure.columns<1||!Array.isArray(structure.rows)
  ||!structure.rows.every(row=>Array.isArray(row)&&row.every(validCell)))return null;
 const columns=Array.from({length:structure.columns},()=>'<col>').join('');
 const rows=structure.rows.map(row=>`<tr>${row.map(cell=>{
  const colspan=cell.colspan>1?` colspan="${cell.colspan}"`:'';
  const rowspan=cell.rowspan>1?` rowspan="${cell.rowspan}"`:'';
  return `<td${colspan}${rowspan}>${esc(cell.text)}</td>`;
 }).join('')}</tr>`).join('');
 const hasAnchors=review.findings.some(item=>anchorsOf(item).some(mark=>mark.block_id===block.id));
 const fallbackLabel=hasAnchors&&mode==='markup'?'Exact source text with comment anchors':'Exact source text';
 return `<div class="table-scroll"><table class="source-table"><colgroup>${columns}</colgroup><tbody>${rows}</tbody></table></div><details class="table-source"><summary>${fallbackLabel}</summary><p class="table-text">${text}</p></details>`;
}
function manuscript(){
 let previous='';const nav=[];
 $('#manuscript').innerHTML=paper.blocks.map(block=>{
  const newSection=block.section!==previous;previous=block.section;
  if(newSection)nav.push(`<a href="#${esc(block.id)}">${esc(block.section)}</a>`);
  if(block.kind==='heading')return `<section class="source-block" id="${esc(block.id)}"><h2>${esc(paper.source_format==='scaffold-typst'?block.text.replace(/^=+\s+/,''):block.text)}</h2></section>`;
  const text=mode==='markup'?quoteMarkup(block):mode==='accepted'?acceptedText(block):esc(block.text);
  const source=block.page?`<button class="page-preview" data-page="${block.page}">Original page ${block.page}</button>`:block.source_span?`Editable source · ${esc(block.source_span.file)}`:paper.source_format==='scaffold-typst'?'Protected source region':block.document==='main'?'Page anchor unavailable':`<a href="${esc(withDraft('/supplements/'+encodeURIComponent(block.document)))}">Supplement source</a>`;
  const table=block.kind==='table'?tableMarkup(block,text):null;
  const content=table||`<p class="${block.kind==='table'?'table-text':block.kind==='reference'?'refs':''}">${text}</p>`;
  return `<section class="source-block" id="${esc(block.id)}">${newSection?`<h2>${esc(block.section)}</h2>`:''}<div class="source-link">${source} <span class="muted">· ${esc(block.id)}</span></div>${content}</section>`;
 }).join('');
 const assets=paper.assets.filter(item=>item.path).map(item=>`<a href="${esc(withDraft('/'+(item.preview||item.path)))}" target="_blank" rel="noopener">${esc(item.label)}</a>`);
 $('#outline').innerHTML=nav.join('')+'<h3>Source files</h3>'+assets.join('');
 $('#manuscript').querySelectorAll('[data-page]').forEach(button=>button.addEventListener('click',()=>showPage(Number(button.dataset.page))));
 applySearch();
}
function showPage(page){$('#page-image').src=withDraft(`/pages/${page}.png`);$('#page-image').alt=`Original manuscript page ${page}`;$('#page-title').textContent=`Original page ${page}`;$('#page-dialog').showModal();}
function categoryOf(item){return item.category==='copyedit'?'copyedit':'scientific';}
function externalCard(card,quote=''){
 const link=typeof card.source_url==='string'&&card.source_url.startsWith('https://')?`<a href="${esc(card.source_url)}" target="_blank" rel="noopener noreferrer">Source record</a>`:'';
 return `<details class="cross-check"><summary>${esc(card.provider)}: ${esc(card.identifier)} (${esc(card.status)})</summary><p>${link}<br>Version: ${esc(card.record_version||'Unknown')}<br>Retrieved or captured: ${esc(card.retrieved_at||card.captured_at||'Unavailable')}<br>Evidence mode: ${esc(card.evidence_mode)}<br>Eligible evidence: ${card.eligible?'Yes':'No'}</p>${quote?`<blockquote>${esc(quote)}</blockquote>`:''}<p>${esc(card.limitation)}</p><pre style="white-space:pre-wrap">${esc(card.evidence_text)}</pre></details>`;
}
function externalFinding(item){
 const all=item.external_sources||review.raw_response?.source_cards||[];
 const grouped=new Map();
 for(const ref of item.source_evidence||[]){
  if(!grouped.has(ref.evidence_id))grouped.set(ref.evidence_id,new Set());
  grouped.get(ref.evidence_id).add(ref.quote);
 }
 return [...grouped].map(([id,quotes])=>{
  const card=all.find(row=>row.evidence_id===id);
  return card?externalCard(card,[...quotes].join('\n\n')):'<p>External evidence record is unavailable in this review export.</p>';
 }).join('');
}
function history(){
 $('#history-details').hidden=!ledger.length;
 if(ledger.length&&!review.findings.length)$('#history-details').open=true;
 $('#history-ledger').innerHTML=ledger.map(row=>{
  const finding=row.finding||{};
  const feedback=row.author_feedback||{};
  const current=paper.blocks.find(block=>block.id===finding.block_id&&block.sha256===finding.block_sha256);
  const location=current?`<p><a href="#${esc(current.id)}">View unchanged passage in this draft</a></p>`:'';
  return `<div class="cross-check"><p><strong>${esc(categoryOf(finding))}: ${esc(finding.title||'Historical finding')}</strong></p><p>${esc(finding.comment||'')}</p><blockquote>${esc(finding.quote||'')}</blockquote>${location}<p>Origin draft: ${esc(row.origin_revision||'unknown')}<br>Wording decision: ${esc(row.wording_decision||'proposed')}<br>Scientific status: ${esc(row.scientific_status||'open')}</p>${feedback.author_comment?`<p>Author response: ${esc(feedback.author_comment)}<br>Author status: ${esc(feedback.issue_status)}<br>${esc(feedback.rationale||'')}</p>`:''}<p>${esc(row.note||'Historical anchors require reassessment on this draft.')}</p></div>`;
 }).join('');
}
// A run's cards are the editor's issues. Each status is the engine's, against the prior round.
const ISSUE_STATUS={new:'New this round',persisting:'Persisting from the prior round',regressed:'Regressed since the prior round',
 resolved:'Resolved: the editor read the revision and found it fixed',unverified:'Unverified: not raised again and not shown fixed'};
const categoryLabel=name=>name?String(name).charAt(0).toUpperCase()+String(name).slice(1).replaceAll('-',' '):'No category';
const isRunCard=item=>Boolean(review.run&&Array.isArray(item.members));
const plural=(count,noun)=>`${count} ${noun}${count===1?'':'s'}`;
function issueBadges(item){
 const run=review.run;
 const status=ISSUE_STATUS[item.status];
 const badges=[item.group!=='ledger'&&item.source_id&&`<span class="badge">Issue ${esc(item.source_id)}</span>`,
  status&&(run.prior_round||item.status!=='new')&&`<span class="badge status ${esc(item.status)}" title="${esc(status)}">${esc(item.status)}</span>`,
  item.group!=='closed'&&Number.isInteger(item.raised_by)&&`<span class="badge">Raised by ${esc(plural(item.raised_by,'reviewer'))}</span>`,
  item.escalate&&'<span class="badge escalated">Escalated</span>'];
 return `<div class="run-badges">${badges.filter(Boolean).join('')}</div>`;
}
function issueNotes(item){
 const quotes=(item.surviving_quotes||[]).filter(row=>row&&row.quote);
 const notes=[item.status_reason&&`<p><strong>${esc(ISSUE_STATUS[item.status]||'Status')}</strong><br>${esc(item.status_reason)}</p>`,
  Number.isInteger(item.prior_rank)&&`<p class="muted">Rank in the prior round: ${esc(item.prior_rank)}${item.prior_id&&item.prior_id!==item.source_id?`, as issue ${esc(item.prior_id)}`:''}</p>`,
  item.rebuttal_quote&&`<p><strong>Manuscript text the editor weighed against the computed finding</strong></p><blockquote>${esc(item.rebuttal_quote)}</blockquote>${item.rebuttal_block_id?`<p><a href="#${esc(item.rebuttal_block_id)}">Go to passage</a></p>`:''}`,
  item.text_unchanged_reason&&`<p><strong>Why it is fixed although the passages it cited still read the same</strong><br>${esc(item.text_unchanged_reason)}</p>`,
  quotes.length&&`<p><strong>The prior round's evidence still in the manuscript</strong></p>${quotes.map(row=>`<blockquote>${esc(row.quote)}</blockquote>${row.block_id?`<p><a href="#${esc(row.block_id)}">Go to passage</a></p>`:''}`).join('')}`,
  (item.audits||[]).length&&`<p class="muted">Specialist reports: ${item.audits.map(esc).join(', ')}</p>`].filter(Boolean);
 return notes.length?`<div class="cross-check">${notes.join('')}</div>`:'';
}
// Each member is a reviewer's finding behind the issue, with its own passage on the manuscript.
function memberItem(item,member,index){
 const ruling=(review.run.escalation_rulings||[]).find(row=>row.finding_uid===member.finding_uid);
 const facts=[member.slot,member.track&&`${member.track} track`,member.kind,member.severity].filter(Boolean).map(esc).join(' · ');
 const badges=[member.basis&&`<span class="badge basis" title="${esc(member.basis_reason||'')}">Basis: ${esc(member.basis)}</span>`,
  member.escalate&&'<span class="badge escalated">Escalated</span>'].filter(Boolean).join('');
 const wording=member.kind==='edit'&&typeof member.replacement==='string'?`<p class="muted">Suggested wording</p><blockquote>${esc(member.replacement)}</blockquote>`:'';
 const links=(member.source_urls||[]).filter(url=>typeof url==='string'&&url.startsWith('https://')).map(url=>`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(url)}</a>`).join('<br>');
 const where=member.placement==='anchored'?`<a href="#anchor-${esc(item.id)}-${index+1}">Go to passage</a>`:'Unplaced: the quote is not found once in its passage';
 const evidence=(member.evidence_blocks||[]).map(id=>`<a href="#${esc(id)}">${esc(id)}</a>`).join(' ');
 return `<li class="member"><p class="muted">${facts}</p>${badges?`<div class="run-badges">${badges}</div>`:''}${member.basis_reason?`<p class="muted">${esc(member.basis_reason)}</p>`:''}${member.title&&member.title!==item.title?`<p><strong>${esc(member.title)}</strong></p>`:''}${member.comment&&member.comment!==item.comment?`<p class="comment-text">${esc(member.comment)}</p>`:''}${member.quote?`<blockquote>${esc(member.quote)}</blockquote>`:''}${wording}${member.counterevidence?`<div class="cross-check"><p><strong>Counterevidence checked</strong><br>${esc(member.counterevidence)}</p></div>`:''}${ruling?`<div class="cross-check ruling"><p><strong>Escalation ruling</strong><br>${esc(ruling.ruling)}</p></div>`:''}${links?`<p class="muted">Sources cited: ${links}</p>`:''}<div class="evidence">${where}${evidence?`<br>Evidence: ${evidence}`:''}</div></li>`;
}
function memberList(item){
 if(!item.members.length)return '';
 return `<details class="members" open><summary>Evidence: ${esc(plural(item.members.length,'finding'))}</summary><ol>${item.members.map((member,index)=>memberItem(item,member,index)).join('')}</ol></details>`;
}
function runStatus(run){
 if(run.status!=='complete-without-findings')return `Status ${run.status}`;
 return run.quarantined_findings_count?`Status ${run.status}: the guard quarantined all ${run.quarantined_findings_count}`
  :`Status ${run.status}: the reviewers raised none`;
}
function agentFacts(row){
 const tasks=(row.labels||[]).filter(label=>label!==row.slot);
 const raises=['core','specialist'].includes(row.role)||row.findings>0||row.none_found;
 return [row.slot,row.track&&`${row.track} track`,row.role==='citation-worker'&&'citation worker, writes no findings',`model asked ${row.assigned_model||'not recorded'}`,
  `model ran ${row.model||'not recorded'}`,Number.isInteger(row.attempt)&&`attempt ${row.attempt}`,
  Number.isInteger(row.tool_calls)&&`${row.tool_calls} tool calls`,Number.isFinite(row.tokens)&&`${row.tokens} tokens`,row.state,
  tasks.length&&`tasks ${tasks.join(', ')}`,
  raises&&(row.none_found?'reported no findings':`${row.findings||0} findings`)].filter(Boolean).map(esc).join(' · ');
}
function unverifiedNote(slots){
 if(!(slots||[]).length)return '';
 const one=slots.length===1;
 return `The model that ran was not recorded for ${slots.length} ${one?'slot':'slots'} (${slots.join(', ')}), so the model asked for ${one?'it':'them'} is unverified.`;
}
// The citation ledger. Each reference state keeps its own count, and none of them is read as a verdict on whether a work is real.
const REFERENCE_STATES={'yes':'found in an index','no':'DOI not held by the DOI resolver','not located':'title not located in Crossref or Europe PMC',
 'could not check':'could not be checked','never looked up':'never looked up','not recorded':'state not recorded'};
const PRINTED_FIELDS={title:'title',first_author:'first author',year:'year',venue:'venue'};
const quoted=(label,text)=>text?`<blockquote class="untrusted"><span class="muted">${esc(label)}</span><br>${esc(text)}</blockquote>`:'';
const sourceLink=(url,text)=>typeof url==='string'&&url.startsWith('https://')?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(text)}</a>`:'';
const workText=work=>[work.first_author,work.year,work.title,work.venue,work.doi&&`DOI ${work.doi}`].filter(Boolean).join('. ');
function referenceNotes(row){
 const state={'no':`The reference list gives DOI ${row.printed.doi||'(not recorded)'} and the DOI resolver has no record of it. Check it against the PDF.`,
  'not located':'Neither Crossref nor Europe PMC lists this title. That is weak evidence, because much of the literature is in neither index.',
  'could not check':'The lookups did not answer, so this says nothing about whether the work is real.',
  'never looked up':'This reference was never looked up.',
  'not recorded':'The ledger holds a lookup for this reference with a state the viewer does not know.'}[row.state];
 const fields=row.mismatched.map(field=>PRINTED_FIELDS[field]||field);
 return [state,fields.length&&`The printed ${fields.join(' and ')} ${fields.length===1?'differs':'differ'} from the indexed record.`,
  row.retracted&&`The indexed record is marked retracted${row.retraction_notice?` (${row.retraction_notice})`:''}.`,
  row.printed_doi_registered===false&&row.state!=='no'&&(row.printed_doi_source==='raw'
   ?'The DOI read off the reference text is not registered with any agency. A DOI broken across a line looks the same, so check the PDF.'
   :'The DOI the reference list gives is not registered with any agency.'),
  row.candidate&&'A work with a similar title was found, and nothing confirms it is this one.',
  row.error&&'Looking this reference up failed inside the ledger.'].filter(Boolean);
}
function referenceItem(row){
 const lookups=row.lookups.length?`Lookup results: ${row.lookups.join(', ')}`:'';
 const link=sourceLink(row.source_url,'Source record');
 return `<li><strong>[${esc(row.label||'?')}] ${esc(REFERENCE_STATES[row.state]||row.state)}</strong>${quoted('Printed in the manuscript',workText(row.printed))}${referenceNotes(row).map(text=>`<p>${esc(text)}</p>`).join('')}${row.record?quoted('Indexed record, fetched from the internet',workText(row.record)):''}${row.candidate?quoted('Similar title, fetched from the internet',workText(row.candidate)):''}${lookups||link?`<p class="muted">${esc(lookups)}${lookups&&link?' · ':''}${link}</p>`:''}</li>`;
}
function useVerdict(row){
 if(!row.reference_id)return `The marker ${row.marker||'(not recorded)'} matches ${row.ambiguous?'more than one entry':'no entry'} in the reference list.`;
 if(!row.verdict)return row.claimed_by?`Not yet judged. ${row.claimed_by} claimed it and left no verdict.`:'Not yet judged.';
 return `${row.verdict}, judged by ${row.judged_by||'a worker not recorded'}`;
}
function useItem(row){
 const where=[row.section&&esc(row.section),row.block_id&&`<a href="#${esc(row.block_id)}">Go to passage</a>`,
  sourceLink(row.source_url,row.source_kind?`Source ${row.source_kind}`:'Source')].filter(Boolean).join(' · ');
 const blind=row.verdict==='cannot tell'&&!row.source_kind?'<p class="muted">The worker had no source text for this reference.</p>':'';
 return `<li data-verdict="${esc(row.verdict||'none')}"><strong>${row.label?`[${esc(row.label)}]`:''} ${esc(useVerdict(row))}</strong>${quoted('Sentence in the manuscript',row.sentence)}${quoted('Source passage the worker quoted, fetched from the internet',row.passage)}${quoted('Worker note',row.note)}${blind}${where?`<p class="muted">${where}</p>`:''}</li>`;
}
function citationCounts(counts){
 const line=(total,noun,pairs,always)=>`${total??0} ${noun}: ${pairs.filter(([key])=>always||counts[key]).map(([key,label])=>`${counts[key]??0} ${label}`).join(' · ')}`;
 const lines=[line(counts.references,'references',[['resolved','found in an index'],['not_found','DOI not held by the DOI resolver'],
   ['not_located','title not located in Crossref or Europe PMC'],['could_not_check','could not be checked'],['unresolved','never looked up']],true),
  line(counts.uses,'in-text uses',[['supported','supports'],['partly_supported','partly supports'],['not_supported','does not support'],
   ['cannot_tell','cannot tell'],['uses_unjudged','not yet judged'],['uses_unmatched','marker matches no reference']],true)];
 const flagged=[['mismatched','with a printed field that differs from the index'],['retracted','retracted'],['candidates','with an unconfirmed similar title']].filter(([key])=>counts[key]);
 if(flagged.length)lines.push(`Also flagged: ${flagged.map(([key,label])=>`${counts[key]} ${label}`).join(' · ')}`);
 return lines;
}
function citationPanel(citations){
 if(!citations)return '';
 const counts=citations.counts||{},shown=citations.ledger&&citations.readable;
 // An unreadable ledger has its own engine line, which says why. This one is for a ledger that came with none.
 const lines=[citations.ledger&&!citations.readable&&!citations.problems.length&&'The citation ledger could not be read, so the panel shows no citation counts.',
  shown&&!citations.complete&&'The citation check did not finish, so these counts do not cover the whole reference list.',
  ...citations.problems].filter(Boolean);
 const more=(count,noun)=>count?`<p class="muted">${esc(count)} more ${noun} not shown.</p>`:'';
 const references=citations.references.length?`<details><summary>References to check (${citations.references.length})</summary><ul>${citations.references.map(referenceItem).join('')}</ul>${more(citations.references_not_shown,'references')}</details>`:'';
 const uses=citations.uses.length?`<details><summary>Worker verdicts on in-text uses (${citations.uses.length})</summary><ul>${citations.uses.map(useItem).join('')}</ul>${more(citations.uses_not_shown,'uses')}</details>`:'';
 const title=shown?`Citations: ${counts.references??0} references, ${counts.uses??0} in-text uses${citations.complete?'':', check incomplete'}`:'Citations';
 return `<details class="citations"${citations.complete&&!citations.problems.length?'':' open'}><summary>${esc(title)}</summary>${shown?citationCounts(counts).map(text=>`<p class="count">${esc(text)}</p>`).join(''):''}${lines.map(text=>`<p class="error">${esc(text)}</p>`).join('')}${references||uses?'<p class="muted">Indexed records and source passages were fetched from the internet, and the notes were written by a citation worker. The panel shows them as quoted text.</p>':''}${references}${uses}</details>`;
}
const RUN_FILTERS=['required','suggestions','escalated'],WORKSPACE_FILTERS=['scientific','copyedit','questions'];
function runPanel(){
 const run=review.run;
 $('#run-panel').hidden=!run;
 for(const name of RUN_FILTERS)$('#filter-'+name).hidden=!run;
 for(const name of WORKSPACE_FILTERS)$('#filter-'+name).hidden=Boolean(run);
 if(filter!=='all'&&!(run?RUN_FILTERS:WORKSPACE_FILTERS).includes(filter)){
  filter='all';document.querySelectorAll('[data-filter]').forEach(item=>item.setAttribute('aria-pressed',item.dataset.filter==='all'));
 }
 if(!run){$('#run-panel').innerHTML='';return;}
 const prior=run.prior_round;
 const tally=prior&&Object.entries(prior.tally||{}).map(([status,count])=>`${count} ${status}`).join(' · ');
 const facts=[run.arm&&`Arm ${run.arm}`,run.reviewer_count&&`${run.reviewer_count} reviewers`,run.status&&runStatus(run),
  run.issues_source==='editor'&&'Issues grouped by the editor',run.issues_source==='server'&&'Issues written by the server, one per finding, with no editor',
  prior&&`Prior round ${prior.file||'issues.json'}: ${prior.issues??0} issues carried${tally?`, this round ${tally}`:''}`,
  Number.isInteger(run.escalated_count)&&`${run.escalated_count} escalated`,run.review_guard_status&&`Guard ${run.review_guard_status}`,
  run.quarantined_findings_count?`${run.quarantined_findings_count} quarantined`:'',
  Number.isFinite(run.wall_seconds)&&`${Math.round(run.wall_seconds/60)} min`,Number.isFinite(run.tokens_total)&&`${run.tokens_total} tokens`].filter(Boolean);
 // Why a run is not publishable is shown once, above its comments.
 const warnings=[run.cause,run.note,...(run.problems||[]),(run.missing_stages||[]).length&&`Stages that did not report: ${run.missing_stages.join(', ')}`].filter(Boolean);
 const unverified=unverifiedNote(run.models_unverified);
 const verdict=run.verdict;
 const verdictHtml=verdict?`<details open><summary>Editor's verdict</summary><p><strong>Significance</strong><br>${esc(verdict.significance)}</p><p><strong>Strength of evidence</strong><br>${esc(verdict.strength_of_evidence)}</p>${verdict.reasoning?`<p><strong>Reasoning</strong><br>${esc(verdict.reasoning)}</p>`:''}<p class="muted">Basis: ${esc(verdict.basis||'unstated')}. ${esc(verdict.limitation||'')}</p></details>`:'';
 const audits=Object.entries(run.audits||{});
 const auditHtml=audits.length?`<details><summary>Specialist reports (${audits.length})</summary>${audits.map(([track,text])=>`<details class="audit"><summary>${esc(track)}</summary><pre>${esc(text)}</pre></details>`).join('')}</details>`:'';
 const reviewers=run.agents||[],tracks=Object.entries(run.findings_by_track||{});
 const reviewerHtml=reviewers.length||tracks.length?`<details><summary>Agents (${reviewers.length})</summary><ul>${reviewers.map(row=>`<li>${agentFacts(row)}</li>`).join('')}</ul>${tracks.length?`<p class="muted">Findings by track: ${tracks.map(([track,count])=>`${esc(track)} ${esc(count)}`).join(' · ')}</p>`:''}</details>`:'';
 $('#run-panel').innerHTML=`<p class="count">${facts.map(esc).join(' · ')}</p>${warnings.map(text=>`<p class="error">${esc(text)}</p>`).join('')}${unverified?`<p class="unverified">${esc(unverified)}</p>`:''}${verdictHtml}${citationPanel(run.citations)}${auditHtml}${reviewerHtml}${(run.limitations||[]).map(text=>`<p class="muted">${esc(text)}</p>`).join('')}`;
}
function card(item){
 const wording=decisions.items[item.id]||'proposed';
 const annotation=pendingResponses.get(responseKey(item.id))||decisions.annotations?.[item.id]||{};
 const issueStatus=annotation.issue_status||'open';
 const run=isRunCard(item);
 const anchored=run?anchorsOf(item).length:item.placement==='anchored';
 const source=run&&!item.members.length?'':anchored?`<a href="#${esc(item.block_id)}">Go to passage</a>`:run?'No finding behind this issue is placed on the manuscript text':'Unplaced comment: source anchor needs review';
 const evidence=(item.evidence_blocks||[]).map(id=>`<a href="#${esc(id)}">${esc(id)}</a>`).join(' ');
 const actions=item.kind==='edit'?`<button data-action="accepted" ${wording!=='proposed'?'disabled':''}>Accept wording</button><button data-action="rejected" ${wording!=='proposed'?'disabled':''}>Decline wording</button>`:`<button data-action="noted" ${wording!=='proposed'?'disabled':''}>Mark for follow-up</button>`;
 const number=item.number?`${esc(item.number)}. `:'';
 const top=run?`<span class="category run ${esc(item.group)}">${esc(categoryLabel(item.severity||'unspecified'))} · ${esc(categoryLabel(item.category))}</span>`
  :`<span class="category ${esc(categoryOf(item))}">${esc(categoryOf(item))} · ${esc(item.kind)} · ${esc(item.severity||'unspecified')}</span>`;
 const details=run?issueBadges(item):'';
 const notes=run?issueNotes(item)+memberList(item):item.counterevidence?`<div class="cross-check"><p><strong>Counterevidence checked</strong><br>${esc(item.counterevidence)}</p></div>`:'';
 return `<article class="finding" id="note-${esc(item.id)}" data-id="${esc(item.id)}"><div class="card-top">${top}<span>${esc(wording)}</span></div>${details}<h3>${number}${esc(item.title||(run?'Review issue':'Review finding'))}</h3><p class="comment-text">${esc(item.comment||item.text||'')}</p>${notes}${source||evidence?`<div class="evidence">${source}${source&&evidence?'<br>':''}${evidence?`Evidence: ${evidence}`:''}</div>`:''}${externalFinding(item)}<div class="actions">${actions}${wording!=='proposed'?'<button data-action="proposed">Undo wording decision</button>':''}</div><div class="author-response"><label>Author comment<textarea data-field="comment" maxlength="4000">${esc(annotation.author_comment||'')}</textarea></label><label>Issue status<select data-field="issue"><option value="open" ${issueStatus==='open'?'selected':''}>Open</option><option value="addressed" ${issueStatus==='addressed'?'selected':''}>Addressed by author</option></select></label><label>Rationale for status<textarea data-field="rationale" maxlength="2000">${esc(annotation.rationale||'')}</textarea></label><button data-save-response>Save author response</button><p class="muted">Addressed records the author's assessment. It does not verify the scientific issue.</p></div>${annotation.history?.length?`<details><summary>Author response history (${annotation.history.length})</summary><ol>${annotation.history.map(row=>`<li>${esc(row.at)} · ${esc(row.issue_status)} · ${esc(row.rationale||'No rationale')}</li>`).join('')}</ol></details>`:''}</article>`;
}
function grouped(items){
 const groups={required:[],suggestion:[],closed:[],ledger:[]};
 for(const item of items)(groups[item.group]||groups.ledger).push(item);
 return groups;
}
function runCount(){
 const groups=grouped(review.findings);
 if(review.run.findings_source==='none')return 'No findings';
 if(review.run.findings_source!=='issues')return `${plural(groups.ledger.length,'finding')}, not grouped into issues`;
 return [`${groups.required.length} required`,`${plural(groups.suggestion.length,'suggestion')}`,
  groups.closed.length&&`${groups.closed.length} from the prior round`,groups.ledger.length&&`${plural(groups.ledger.length,'finding')} no issue holds`].filter(Boolean).join(' · ');
}
// A run's review: the required changes in rank order, the suggestions under their categories,
// the prior round's closed issues, then any finding no issue holds.
function runCards(){
 const run=review.run;
 const groups=grouped(review.findings.filter(item=>filter==='all'||(filter==='required'&&item.group==='required')
  ||(filter==='suggestions'&&item.group==='suggestion')||(filter==='escalated'&&item.escalate)));
 const reasons=(run.not_publishable_reasons||[]).map(reason=>`<li>${esc(reason)}</li>`).join('');
 const banner=run.publishable===false?`<div class="not-publishable error" role="note"><p><strong>This run is not publishable.</strong> ${review.findings.length?'Its comments are shown as the run recorded them. Read why before you use them.':'It has no review to show.'}</p>${reasons?`<ul>${reasons}</ul>`:''}</div>`:'';
 const suggestions=[];let category;
 for(const item of groups.suggestion){
  if(item.category!==category){category=item.category;suggestions.push(`<h4 class="issue-category">${esc(categoryLabel(category))}</h4>`);}
  suggestions.push(card(item));
 }
 const closedOpen=$('#closed-issues')?.open?' open':'';
 const loose=run.findings_source==='issues'?'Findings no issue holds':'Findings recorded before any issues were written';
 const sections=[groups.required.length&&`<h3 class="issue-group">Required changes (${groups.required.length})</h3>${groups.required.map(card).join('')}`,
  groups.suggestion.length&&`<h3 class="issue-group">Suggestions (${groups.suggestion.length})</h3>${suggestions.join('')}`,
  groups.closed.length&&`<details class="appendix" id="closed-issues"${closedOpen}><summary>Prior round: resolved and unverified (${groups.closed.length})</summary>${groups.closed.map(card).join('')}</details>`,
  groups.ledger.length&&`<h3 class="issue-group">${loose} (${groups.ledger.length})</h3>${groups.ledger.map(card).join('')}`].filter(Boolean);
 const empty=review.findings.length||run.publishable!==false?'<div class="empty">No comments in this view.</div>':'';
 return banner+(sections.join('')||empty);
}
function cards(){
 const openHistorical=ledger.filter(row=>row.scientific_status==='open').length;
 $('#finding-count').textContent=(review.run?runCount():review.findings.length+' new')+(openHistorical?' · '+openHistorical+' earlier questions open':'');$('#review-summary').textContent=review.summary||'';
 runPanel();
 const raw=review.raw_response||{};
 $('#handoff-details').hidden=!(raw.source_cards||[]).length&&!raw.domain_profile&&!raw.result_map&&!(raw.result_comparisons||[]).length;
 $('#handoff-ledger').innerHTML='';
 if(raw.domain_profile)$('#handoff-ledger').innerHTML+=`<p><strong>Selected domain guidance</strong>: ${(raw.domain_profile.selected||[]).map(item=>esc(item.name)).join(', ')||'Shared methods only'}</p><p>${esc(raw.domain_profile.limitation)}</p>`;
 $('#handoff-ledger').innerHTML+=(raw.source_cards||[]).map(card=>externalCard(card)).join('');
 if(raw.result_map){
  const map=raw.result_map;
  $('#handoff-ledger').innerHTML+=`<details><summary>Claims, figures and tables (${map.nodes.length} passages)</summary><p>${esc(map.limitation)}</p><p>Figure pixels require separate inspection.</p>${map.edges.map(edge=>`<p><a href="#${esc(edge.from)}">${esc(edge.from)}</a> cites ${esc(edge.quote)}: ${edge.to.length?edge.to.map(id=>`<a href="#${esc(id)}">${esc(id)}</a>`).join(', '):'Target not extracted'}</p>`).join('')}${map.checks.map(check=>`<p>${esc(check.reason)} ${check.blocks.map(id=>`<a href="#${esc(id)}">${esc(id)}</a>`).join(', ')}</p>`).join('')}</details>`;
 }
 for(const comparison of raw.result_comparisons||[]){
  $('#handoff-ledger').innerHTML+=`<details><summary>Quantity comparison: ${esc(comparison.status.replaceAll('_',' '))}</summary><p>${esc(comparison.limitation)}</p>${comparison.observations.map(obs=>`<p><a href="#${esc(obs.block_id)}">${esc(obs.block_id)}</a>: ${esc(obs.value)} (${esc(obs.metric)})</p><blockquote>${esc(obs.quote)}</blockquote>`).join('')}<p>Context labels are investigator assessments.</p></details>`;
 }
 $('#comments').innerHTML=review.run?runCards():(review.findings.filter(item=>filter==='all'||filter===categoryOf(item)||(filter==='questions'&&item.kind!=='edit')).map(card).join('')||'<div class="empty">No comments in this view.</div>');
 $('#comments').querySelectorAll('[data-action]').forEach(button=>button.addEventListener('click',()=>saveFinding(button.closest('article'),button.dataset.action)));
 $('#comments').querySelectorAll('[data-save-response]').forEach(button=>button.addEventListener('click',()=>saveFinding(button.closest('article'),decisions.items[button.closest('article').dataset.id]||'proposed')));
 $('#comments').querySelectorAll('[data-field]').forEach(input=>input.addEventListener('input',()=>{
  const card=input.closest('article');
  pendingResponses.set(responseKey(card.dataset.id),{...(decisions.annotations?.[card.dataset.id]||{}),author_comment:card.querySelector('[data-field=comment]').value,issue_status:card.querySelector('[data-field=issue]').value,rationale:card.querySelector('[data-field=rationale]').value});
  $('#save-status').textContent='Author response has unsaved changes.';
 }));
 if(state.legacyServer)$('#comments').querySelectorAll('.author-response').forEach(element=>element.hidden=true);
}
async function saveFinding(card,status){
 const issueStatus=card.querySelector('[data-field=issue]').value;
 const rationale=card.querySelector('[data-field=rationale]').value;
 if(issueStatus==='addressed'&&!rationale.trim()){error('Addressed issues require a rationale.');return;}
 card.classList.add('busy');
 try{
  decisions=await api(withDraft('/api/decisions'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({review_id:review.id,annotation_id:card.dataset.id,status,revision:decisions.revision,author_comment:card.querySelector('[data-field=comment]').value,issue_status:issueStatus,rationale})});
  pendingResponses.delete(responseKey(card.dataset.id));
  error('');render();$('#save-status').textContent='Saved locally. Scientific correctness still requires review.';
 }catch(e){error(e.message);card.classList.remove('busy');}
}
function render(){
 manuscript();cards();history();
 if(state.native)$('#build-revision').disabled=state.selected!==state.head.revision_id
  ||!review.findings.some(item=>item.kind==='edit'&&decisions.items[item.id]==='accepted');
}
function applySearch(){const query=$('#search').value.toLowerCase();document.querySelectorAll('.source-block').forEach(element=>element.hidden=query&&!element.textContent.toLowerCase().includes(query));}
async function loadReview(id){
 if(!id){review={id:'none',summary:ledger.length?'This revision has historical findings but no new review.':'No review has been imported for this draft.',findings:[]};decisions={paper_id:paper.id,revision:0,items:{},annotations:{}};$('#export').disabled=true;$('#build-revision').disabled=true;render();return;}
 [review,decisions]=await Promise.all([api(withDraft('/api/review?review='+encodeURIComponent(id))),api(withDraft('/api/decisions?review='+encodeURIComponent(id)))]);
 decisions.annotations=decisions.annotations||{};$('#export').disabled=false;$('#build-revision').disabled=state.selected!==state.head.revision_id;render();$('#save-status').textContent='Decisions and author responses save locally.';
}
function setDraftLink(id){const url=new URL(location.href);url.searchParams.set('draft',id);url.searchParams.delete('review');location.href=url;}
async function start(){
 try{
  try{state=await api(requestedDraft()?'/api/revisions?draft='+encodeURIComponent(requestedDraft()):'/api/revisions');}
  catch(failure){if(failure.status!==404)throw failure;state={selected:'original',head:{revision_id:'original',version:0},revisions:[{id:'original'}],native:false,has_original_pdf:true,legacyServer:true};}
  paper=await api(withDraft('/api/paper'));ledger=state.legacyServer?[]:await api(withDraft('/api/ledger'));
  $('#source-title').textContent=paper.title;document.title='Review · '+paper.title;
  $('#summary-counts').textContent=`${state.native?'Native source':paper.statistics.pdf_pages+' pages'} · ${paper.statistics.reference_entries} references · ${paper.statistics.blocks} source blocks`;
  $('#source-details').textContent=(paper.warnings||[]).join(' ')+' '+(paper.statistics.convention||'')+' Source fingerprint: '+paper.source_sha256.slice(0,16);
  $('#draft-select').innerHTML=state.revisions.map(item=>`<option value="${esc(item.id)}" ${item.id===state.selected?'selected':''}>${esc(item.id)}</option>`).join('');
  $('#revision-tools').hidden=!state.native;$('#head-state').textContent=`Active draft: ${state.head.revision_id} · pointer version ${state.head.version}`;
  $('#checkout-draft').disabled=state.selected===state.head.revision_id;
  $('#draft-pdf').hidden=!state.has_revision_pdf;$('#draft-pdf').href=withDraft('/draft.pdf');
  if(state.native){
   let exports=[];
   try{exports=await api(withDraft('/api/exports'));}catch(failure){if(failure.status!==404)throw failure;}
   const latest=exports[0];
   for(const [selector,name] of [['#export-pdf','paper.pdf'],['#export-word','paper.docx'],['#export-review-word','review.docx']]){
    $(selector).hidden=!latest?.files.includes(name);
    if(latest)$(selector).href=withDraft('/exports/'+encodeURIComponent(latest.id)+'/'+name);
   }
   if(latest?.files.includes('paper.pdf'))$('#draft-pdf').hidden=true;
  }
  $('#original-pdf').hidden=!state.has_original_pdf;$('#source-download').hidden=!state.has_source;$('#source-download').href=withDraft('/source.zip');
  const labels={run:'PeerReviewAgents run'};
  const ids=await api(withDraft('/api/reviews'));$('#review-select').innerHTML=ids.map(id=>`<option value="${esc(id)}">${esc(labels[id]||id)}</option>`).join('');
  const requested=new URLSearchParams(location.search).get('review');const preferred=ids.includes(requested)?requested:ids[0];
  if(preferred)$('#review-select').value=preferred;
  await loadReview(preferred);
  if(state.legacyServer)$('#save-status').textContent='Wording decisions save locally. Restart this viewer to enable author responses and draft history.';
 }catch(e){error(e.message);}
}
$('#draft-select').addEventListener('change',event=>setDraftLink(event.target.value));
$('#review-select').addEventListener('change',event=>loadReview(event.target.value).catch(e=>error(e.message)));
$('#search').addEventListener('input',applySearch);
// A link into a collapsed section, such as the prior round's closed issues, opens it, so the target is visible.
window.addEventListener('hashchange',()=>{const target=document.getElementById(decodeURIComponent(location.hash.slice(1)));const box=target?.closest('details');if(box)box.open=true;});
document.querySelectorAll('[data-mode]').forEach(button=>button.addEventListener('click',()=>{mode=button.dataset.mode;document.querySelectorAll('[data-mode]').forEach(item=>item.setAttribute('aria-pressed',item===button));manuscript();}));
document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{filter=button.dataset.filter;document.querySelectorAll('[data-filter]').forEach(item=>item.setAttribute('aria-pressed',item===button));cards();}));
$('#close-page').addEventListener('click',()=>$('#page-dialog').close());
$('#export').addEventListener('click',async()=>{try{const value=await api(withDraft('/api/export?review='+encodeURIComponent(review.id)));const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const anchor=document.createElement('a');anchor.href=url;anchor.download=paper.id+'-'+review.id+'-review.json';anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){error(e.message);}});
$('#build-revision').addEventListener('click',async()=>{const id=prompt('New revision ID. Use lowercase letters, numbers, underscores, or hyphens.');if(!id)return;try{$('#build-revision').disabled=true;$('#save-status').textContent='Compiling and verifying the new revision.';const value=await api(withDraft('/api/revisions'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision_id:id,review_id:review.id,decision_revision:decisions.revision,expected_head:state.head})});setDraftLink(value.head.revision_id);}catch(e){error(e.message);$('#build-revision').disabled=false;}});
$('#checkout-draft').addEventListener('click',async()=>{if(!confirm(`Make ${state.selected} the active draft? Existing revisions remain available.`))return;try{const value=await api(withDraft('/api/checkout'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision_id:state.selected,expected_head:state.head})});setDraftLink(value.revision_id);}catch(e){error(e.message);}});
start();
