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
function quoteMarkup(block){
 // The editor's appendix stays in the comment column, so only the report's own findings mark the text.
 const notes=review.findings.filter(item=>item.block_id===block.id&&item.placement==='anchored'&&item.section!=='appendix').sort((a,b)=>a.start-b.start);
 let position=0,output='';
 for(const item of notes){
  if(item.start<position)continue;
  output+=esc(segment(block.text,position,item.start));
  const quote=esc(item.quote);
  const mark=item.kind==='edit'?`<span class="before">${quote}</span> <span class="after">${esc(item.replacement)}</span>`:`<mark class="question-mark">${quote}</mark>`;
  output+=`<span class="anchor" id="anchor-${esc(item.id)}">${mark}<a class="pin" href="#note-${esc(item.id)}" aria-label="Comment ${esc(item.number??item.id)}">${esc(item.number??item.id.split('-').at(-1))}</a></span>`;
  position=item.end;
 }
 return output+esc(segment(block.text,position));
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
 const hasAnchors=review.findings.some(item=>item.block_id===block.id&&item.placement==='anchored');
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
function findingLink(uid){
 const target=review.findings.find(row=>row.finding_uid===uid);
 return target?`<a href="#note-${esc(target.id)}">${esc(target.number??target.id)}</a>`:esc(uid);
}
function runBadges(item){
 if(!review.run||!item.track)return '';
 const placement=item.section!=='appendix'?'':item.editor_placement==='duplicate'?'Duplicate':'Appendix';
 const badges=[`<span class="badge">${esc(item.track)} track</span>`,
  item.basis?`<span class="badge basis" title="${esc(item.basis_reason||'')}">Basis: ${esc(item.basis)}</span>`:'',
  item.escalate?'<span class="badge escalated">Escalated</span>':'',
  placement?`<span class="badge">${placement}</span>`:'',
  item.reviewers_raising>1?`<span class="badge">Raised by ${esc(item.reviewers_raising)}</span>`:''];
 return `<div class="run-badges">${badges.join('')}</div>${item.basis_reason?`<p class="muted">${esc(item.basis_reason)}</p>`:''}`;
}
function runNotes(item){
 if(!review.run||!item.track)return '';
 const ruling=(review.run.escalation_rulings||[]).find(row=>row.finding_uid===item.finding_uid);
 const original=item.duplicate_of?`<p>Duplicate of finding ${findingLink(item.duplicate_of)}</p>`:'';
 const merged=(item.duplicate_uids||[]).length?`<p>Merged duplicates: ${item.duplicate_uids.map(findingLink).join(' ')}</p>`:'';
 const rebuttal=item.rebuttal_quote?`<p>Manuscript text the editor weighed against it</p><blockquote>${esc(item.rebuttal_quote)}</blockquote>`:'';
 const editor=item.editor_reason||original||merged||rebuttal?`<div class="cross-check"><p><strong>Editor</strong><br>${esc(item.editor_reason||'')}</p>${original}${merged}${rebuttal}</div>`:'';
 const links=(item.source_urls||[]).filter(url=>typeof url==='string'&&url.startsWith('https://')).map(url=>`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(url)}</a>`).join('<br>');
 return editor+(ruling?`<div class="cross-check ruling"><p><strong>Escalation ruling</strong><br>${esc(ruling.ruling)}</p></div>`:'')+(links?`<p class="muted">Sources cited: ${links}</p>`:'');
}
function runStatus(run){
 if(run.status!=='complete-without-findings')return `Status ${run.status}`;
 return run.quarantined_findings_count?`Status ${run.status}: the guard quarantined all ${run.quarantined_findings_count}`
  :`Status ${run.status}: the reviewers raised none`;
}
function agentFacts(row){
 const tasks=(row.labels||[]).filter(label=>label!==row.slot);
 const raises=['core','specialist'].includes(row.role)||row.findings>0||row.none_found;
 return [row.slot,row.track&&`${row.track} track`,row.model,Number.isInteger(row.attempt)&&`attempt ${row.attempt}`,
  Number.isInteger(row.tool_calls)&&`${row.tool_calls} tool calls`,Number.isFinite(row.tokens)&&`${row.tokens} tokens`,row.state,
  tasks.length&&`tasks ${tasks.join(', ')}`,
  raises&&(row.none_found?'reported no findings':`${row.findings||0} findings`)].filter(Boolean).map(esc).join(' · ');
}
function runPanel(){
 const run=review.run;
 $('#run-panel').hidden=!run;$('#filter-escalated').hidden=!run;
 if(!run){
  $('#run-panel').innerHTML='';
  if(filter==='escalated'){filter='all';document.querySelectorAll('[data-filter]').forEach(item=>item.setAttribute('aria-pressed',item.dataset.filter==='all'));}
  return;
 }
 const facts=[run.arm&&`Arm ${run.arm}`,run.reviewer_count&&`${run.reviewer_count} reviewers`,run.status&&runStatus(run),
  Number.isInteger(run.escalated_count)&&`${run.escalated_count} escalated`,run.review_guard_status&&`Guard ${run.review_guard_status}`,
  run.quarantined_findings_count?`${run.quarantined_findings_count} quarantined`:'',
  Number.isFinite(run.wall_seconds)&&`${Math.round(run.wall_seconds/60)} min`,Number.isFinite(run.tokens_total)&&`${run.tokens_total} tokens`].filter(Boolean);
 const warnings=[run.cause,run.note,...(run.problems||[]),
  ...(run.publishable===false?(run.not_publishable_reasons||[]).map(reason=>`Not publishable: ${reason}`):[]),(run.missing_stages||[]).length&&`Stages that did not report: ${run.missing_stages.join(', ')}`,
  !run.edited&&'The editor did not write a package. These are the findings recorded before editing.'].filter(Boolean);
 const verdict=run.verdict;
 const verdictHtml=verdict?`<details open><summary>Editor's verdict</summary><p><strong>Significance</strong><br>${esc(verdict.significance)}</p><p><strong>Strength of evidence</strong><br>${esc(verdict.strength_of_evidence)}</p>${verdict.reasoning?`<p><strong>Reasoning</strong><br>${esc(verdict.reasoning)}</p>`:''}<p class="muted">Basis: ${esc(verdict.basis||'unstated')}. ${esc(verdict.limitation||'')}</p></details>`:'';
 const audits=Object.entries(run.audits||{});
 const auditHtml=audits.length?`<details><summary>Specialist reports (${audits.length})</summary>${audits.map(([track,text])=>`<details class="audit"><summary>${esc(track)}</summary><pre>${esc(text)}</pre></details>`).join('')}</details>`:'';
 const reviewers=run.agents||[],tracks=Object.entries(run.findings_by_track||{});
 const reviewerHtml=reviewers.length||tracks.length?`<details><summary>Agents (${reviewers.length})</summary><ul>${reviewers.map(row=>`<li>${agentFacts(row)}</li>`).join('')}</ul>${tracks.length?`<p class="muted">Findings by track: ${tracks.map(([track,count])=>`${esc(track)} ${esc(count)}`).join(' · ')}</p>`:''}</details>`:'';
 $('#run-panel').innerHTML=`<p class="count">${facts.map(esc).join(' · ')}</p>${warnings.map(text=>`<p class="error">${esc(text)}</p>`).join('')}${verdictHtml}${auditHtml}${reviewerHtml}${(run.limitations||[]).map(text=>`<p class="muted">${esc(text)}</p>`).join('')}`;
}
function card(item){
 const wording=decisions.items[item.id]||'proposed';
 const annotation=pendingResponses.get(responseKey(item.id))||decisions.annotations?.[item.id]||{};
 const issueStatus=annotation.issue_status||'open';
 const source=item.placement==='anchored'?`<a href="#${esc(item.block_id)}">Go to passage</a>`:'Unplaced comment: source anchor needs review';
 const actions=item.kind==='edit'?`<button data-action="accepted" ${wording!=='proposed'?'disabled':''}>Accept wording</button><button data-action="rejected" ${wording!=='proposed'?'disabled':''}>Decline wording</button>`:`<button data-action="noted" ${wording!=='proposed'?'disabled':''}>Mark for follow-up</button>`;
 const number=item.number?`${esc(item.number)}. `:'';
 return `<article class="finding" id="note-${esc(item.id)}" data-id="${esc(item.id)}"><div class="card-top"><span class="category ${esc(categoryOf(item))}">${esc(categoryOf(item))} · ${esc(item.kind)} · ${esc(item.severity||'unspecified')}</span><span>${esc(wording)}</span></div>${runBadges(item)}<h3>${number}${esc(item.title||'Review finding')}</h3><p class="comment-text">${esc(item.comment||item.text||'')}</p>${item.counterevidence?`<div class="cross-check"><p><strong>Counterevidence checked</strong><br>${esc(item.counterevidence)}</p></div>`:''}${runNotes(item)}<div class="evidence">${source}<br>Evidence: ${(item.evidence_blocks||[]).map(id=>`<a href="#${esc(id)}">${esc(id)}</a>`).join(' ')}</div>${externalFinding(item)}<div class="actions">${actions}${wording!=='proposed'?'<button data-action="proposed">Undo wording decision</button>':''}</div><div class="author-response"><label>Author comment<textarea data-field="comment" maxlength="4000">${esc(annotation.author_comment||'')}</textarea></label><label>Issue status<select data-field="issue"><option value="open" ${issueStatus==='open'?'selected':''}>Open</option><option value="addressed" ${issueStatus==='addressed'?'selected':''}>Addressed by author</option></select></label><label>Rationale for status<textarea data-field="rationale" maxlength="2000">${esc(annotation.rationale||'')}</textarea></label><button data-save-response>Save author response</button><p class="muted">Addressed records the author's assessment. It does not verify the scientific issue.</p></div>${annotation.history?.length?`<details><summary>Author response history (${annotation.history.length})</summary><ol>${annotation.history.map(row=>`<li>${esc(row.at)} · ${esc(row.issue_status)} · ${esc(row.rationale||'No rationale')}</li>`).join('')}</ol></details>`:''}</article>`;
}
function cards(){
 const openHistorical=ledger.filter(row=>row.scientific_status==='open').length;
 const appendixCount=review.findings.filter(item=>item.section==='appendix').length;
 const counted=review.run?`${review.findings.length-appendixCount} in the report`+(appendixCount?` · ${appendixCount} in the appendix`:''):review.findings.length+' new';
 $('#finding-count').textContent=counted+(openHistorical?' · '+openHistorical+' earlier questions open':'');$('#review-summary').textContent=review.summary||'';
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
 const visible=review.findings.filter(item=>filter==='all'||filter===categoryOf(item)||(filter==='questions'&&item.kind!=='edit')||(filter==='escalated'&&item.escalate));
 const body=visible.filter(item=>item.section!=='appendix'),appendix=visible.filter(item=>item.section==='appendix');
 const appendixOpen=$('#appendix')?.open?' open':'';
 $('#comments').innerHTML=(body.map(card).join('')||'<div class="empty">No comments in this view.</div>')
  +(appendix.length?`<details class="appendix" id="appendix"${appendixOpen}><summary>Editor's appendix (${appendix.length}): duplicates and findings outside the report</summary>${appendix.map(card).join('')}</details>`:'');
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
// A link into the collapsed appendix opens it, so the target card is visible.
window.addEventListener('hashchange',()=>{const target=document.getElementById(decodeURIComponent(location.hash.slice(1)));const box=target?.closest('details');if(box)box.open=true;});
document.querySelectorAll('[data-mode]').forEach(button=>button.addEventListener('click',()=>{mode=button.dataset.mode;document.querySelectorAll('[data-mode]').forEach(item=>item.setAttribute('aria-pressed',item===button));manuscript();}));
document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{filter=button.dataset.filter;document.querySelectorAll('[data-filter]').forEach(item=>item.setAttribute('aria-pressed',item===button));cards();}));
$('#close-page').addEventListener('click',()=>$('#page-dialog').close());
$('#export').addEventListener('click',async()=>{try{const value=await api(withDraft('/api/export?review='+encodeURIComponent(review.id)));const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const anchor=document.createElement('a');anchor.href=url;anchor.download=paper.id+'-'+review.id+'-review.json';anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){error(e.message);}});
$('#build-revision').addEventListener('click',async()=>{const id=prompt('New revision ID. Use lowercase letters, numbers, underscores, or hyphens.');if(!id)return;try{$('#build-revision').disabled=true;$('#save-status').textContent='Compiling and verifying the new revision.';const value=await api(withDraft('/api/revisions'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision_id:id,review_id:review.id,decision_revision:decisions.revision,expected_head:state.head})});setDraftLink(value.head.revision_id);}catch(e){error(e.message);$('#build-revision').disabled=false;}});
$('#checkout-draft').addEventListener('click',async()=>{if(!confirm(`Make ${state.selected} the active draft? Existing revisions remain available.`))return;try{const value=await api(withDraft('/api/checkout'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision_id:state.selected,expected_head:state.head})});setDraftLink(value.revision_id);}catch(e){error(e.message);}});
start();
