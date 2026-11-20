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
// The manuscript is each document's lines, and a finding cites a document and a line, as the engine
// found its quote there. Each line is one element, so every link lands on the line it names.
const lineId=(name,line)=>'line-'+String(name).replace(/[^\w-]/g,c=>'.'+c.codePointAt(0).toString(16))+'-'+line;
const lineLabel=(name,line)=>name===paper.main?`line ${line}`:`${name}, line ${line}`;
const lineLink=(name,line,text)=>`<a href="#${esc(lineId(name,line))}">${esc(text??lineLabel(name,line))}</a>`;
const lineText=(name,line)=>paper.documents[name]?.[line-1]??'';
const pieceAt=(name,line)=>Number.isInteger(line)?paper.pieces.find(row=>(row.document||paper.main)===name&&row.lines[0]<=line&&line<=row.lines[1]):undefined;
// The passages a card marks on the manuscript. A run's issue marks every anchored member, each
// with its own anchor id. A workspace finding has no members and marks its own quote. Members of
// one issue that quote the same span are one passage, marked and pinned once. A span starts at
// an offset into its first line and ends at one into its last.
const isMarked=member=>member.placement==='anchored'&&typeof member.document==='string'
 &&[member.line,member.end_line,member.start,member.end].every(Number.isInteger)
 &&(member.line<member.end_line||(member.line===member.end_line&&member.start<member.end));
const spanKey=member=>JSON.stringify([member.document,member.line,member.start,member.end_line,member.end]);
function anchorsOf(item){
 const label=item.number??item.id.split('-').at(-1);
 const members=(item.members||[]).length?item.members.map((member,n)=>({...member,anchor:`${item.id}-${n+1}`})):[{...item,anchor:item.id}];
 const seen=new Set();
 return members.filter(member=>isMarked(member)&&!seen.has(spanKey(member))&&seen.add(spanKey(member)))
  .map(member=>({...member,target:item.id,label,edit:item.kind==='edit'&&typeof member.replacement==='string'?member.replacement:null}));
}
// Each passage that covers part of a line, as offsets into that line. A passage opens on its first
// line and closes on its last, where its suggested wording and its pin go.
function lineMarks(name,line,length){
 return review.findings.flatMap(anchorsOf).filter(mark=>mark.document===name&&mark.line<=line&&line<=mark.end_line)
  .map(mark=>({...mark,from:mark.line===line?mark.start:0,to:mark.end_line===line?mark.end:length,opens:mark.line===line,closes:mark.end_line===line}));
}
// Members of one issue, or of two, can quote the same or overlapping text, so the line is cut at
// every start and end. Each piece is marked by every passage that covers it. The text before
// ``skip`` is not shown, such as the hashes of a heading.
function quoteMarkup(name,line,skip=0){
 const text=lineText(name,line);
 const length=Array.from(text).length;
 const marks=lineMarks(name,line,length).map(mark=>({...mark,from:Math.max(mark.from,skip),to:Math.max(mark.to,skip)}));
 const cuts=[...new Set([skip,length,...marks.flatMap(mark=>[mark.from,mark.to])])].filter(at=>at>=skip&&at<=length).sort((a,b)=>a-b);
 let output='';
 cuts.forEach((at,index)=>{
  for(const mark of marks.filter(row=>row.closes&&row.to===at)){
   if(mark.edit!==null)output+=` <span class="after">${esc(mark.edit)}</span>`;
   output+=`<a class="pin" href="#note-${esc(mark.target)}" aria-label="Comment ${esc(mark.label)}">${esc(mark.label)}</a>`;
  }
  const next=cuts[index+1];
  const opening=marks.filter(mark=>mark.opens&&mark.from===at);
  if(next===undefined){output+=opening.map(mark=>`<span class="anchor" id="anchor-${esc(mark.anchor)}"></span>`).join('');return;}
  const piece=esc(segment(text,at,next));
  const covering=marks.filter(mark=>mark.from<=at&&mark.to>=next);
  if(!covering.length){output+=piece;return;}
  const [first,...others]=opening;
  const tag=covering.some(mark=>mark.edit!==null)?['span','before']:['mark','question-mark'];
  output+=others.map(mark=>`<span class="anchor" id="anchor-${esc(mark.anchor)}"></span>`).join('')
   +`<${tag[0]} class="${tag[1]}${first?' anchor':''}"${first?` id="anchor-${esc(first.anchor)}"`:''}>${piece}</${tag[0]}>`;
 });
 return output;
}
// A line with every accepted edit applied. An edit's wording takes the place of its span on its first
// line, and the lines it spans after that keep only what follows the span, so the lines keep their numbers.
function acceptedText(name,line){
 const text=lineText(name,line);
 const length=Array.from(text).length;
 return review.findings.filter(item=>item.decidable!==false&&decisions.items[item.id]==='accepted'&&typeof item.replacement==='string'
  &&isMarked(item)&&item.document===name&&item.line<=line&&line<=item.end_line)
  .map(item=>({from:item.line===line?item.start:0,to:item.end_line===line?item.end:length,insert:item.line===line?item.replacement:''}))
  .sort((a,b)=>b.from-a.from).reduce((value,edit)=>segment(value,0,edit.from)+edit.insert+segment(value,edit.to),text);
}
function shownLine(name,line,skip){
 if(mode==='markup')return quoteMarkup(name,line,skip);
 return esc(segment(mode==='accepted'?acceptedText(name,line):lineText(name,line),skip));
}
const HEADING=/^#+\s+/;
// A table whose source Word table was found keeps that table's merged cells. Its lines stay below it,
// open when a comment is anchored on them, since a finding cites a line and not a cell.
function tableMarkup(piece,name,lines){
 const structure=piece.native?.table_structure;
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
 const [first,last]=piece.lines;
 const marked=mode==='markup'&&review.findings.some(item=>anchorsOf(item).some(mark=>mark.document===name&&mark.line<=last&&first<=mark.end_line));
 return `<div class="table-scroll"><table class="source-table"><colgroup>${columns}</colgroup><tbody>${rows}</tbody></table></div><details class="table-source"${marked?' open':''}><summary>${marked?'Exact source text with comment anchors':'Exact source text'}</summary>${lines}</details>`;
}
// Which lines a model wrote. The engine's Read stage has a model read every page image, and each map
// row's source says whose text the piece is: the converter's (text), read again from the page image
// because the converter garbled it (ai-reconstructed, which keeps the converter's reading in original),
// or written by the model (ai). A figure description is the model's account of the image. A page the
// converter returned no text from is one of the lost pages, and the engine names the document and
// lines its transcription became. In a manuscript no model read the pages of, such as an application's
// own source, the model that wrote those pieces is the one the application named, and no page image
// stands behind them.
const wasRead=()=>Boolean(paper.ai_read?.read);
const pieceModel=()=>(wasRead()&&paper.ai_read.reader_model)||paper.ai_read?.ai_model||'a model';
const lostPages=()=>(paper.ai_read?.lost_pages||[]).filter(row=>Number.isInteger(row.page));
const fromLostPage=piece=>lostPages().some(row=>(row.added||[]).some(added=>added.document===(piece.document||paper.main)
 &&added.lines?.[0]<=piece.lines[0]&&piece.lines[1]<=added.lines?.[1]));
const modelWritten=piece=>piece.kind==='figure-description'||piece.source==='ai'||piece.source==='ai-reconstructed';
// A piece the reader read again as several keeps the converter's whole reading in each, with which part
// it is. Prose is never typed by the reader: a prose part is a slice of the converter's own characters
// that the engine cut where the reader said.
const PROSE_KINDS=['paragraph','footnote','heading','title'];
const rereadPart=piece=>Number.isInteger(piece.original?.part)&&Number.isInteger(piece.original?.of)?piece.original:null;
const cutProse=piece=>piece.source==='ai-reconstructed'&&PROSE_KINDS.includes(piece.kind)&&Boolean(rereadPart(piece));
// Debris the converter read as pieces of their own leaves the document when the reader folds it into
// the piece it is part of, and each one's whole reading is kept on that piece.
function absorbedMarkup(piece){
 const rows=Array.isArray(piece.original?.absorbed)?piece.original.absorbed:[];
 if(!rows.length)return '';
 const one=rows.length===1;
 return `<details class="converter-reading"><summary>${one?'One piece':`${rows.length} pieces`} the converter read separately, folded into this one</summary>${rows.map(row=>`<pre>${esc(row.text)}</pre>`).join('')}</details>`;
}
function provenanceMarkup(piece){
 if(!modelWritten(piece))return '';
 const by=esc(pieceModel());
 const page=Number.isInteger(piece.page)&&piece.page>0?`page ${piece.page}`:'its page';
 const folded=absorbedMarkup(piece);
 if(piece.kind==='figure-description')return `<p class="provenance">AI description of the figure image by ${by}, not the authors' words</p>`+folded;
 const part=rereadPart(piece);
 const split=part&&part.of>1?`. It is part ${part.part} of ${part.of} of what the converter read as one ${esc(part.kind)}`:'';
 const reading=piece.source==='ai-reconstructed'?piece.original?.latex||piece.original?.text||'':'';
 const label=wasRead()?"The converter's reading":'The text it replaced';
 const parts=part&&part.of>1?`${label}, ${part.of===2?'both parts':`all ${part.of} parts`}`:label;
 const replaced=reading?`<details class="converter-reading"><summary>${parts}</summary><pre>${esc(reading)}</pre></details>`:'';
 if(cutProse(piece))return `<p class="provenance">The converter's text, cut by ${by}${wasRead()?` after reading the image of ${page}`:''}. Every character in it is the converter's${split}</p>`+replaced+folded;
 if(!wasRead())return `<p class="provenance">Written by ${by}. No page image was read here, so there is no page to compare it with${split}</p>`+replaced+folded;
 if(piece.source==='ai-reconstructed')return `<p class="provenance">Read from the image of ${page} by ${by}, because the converter garbled it${split}</p>`+replaced+folded;
 return `<p class="provenance">Written by ${by} from the image of ${page}, ${fromLostPage(piece)?'a page the converter returned no text from':'because the converter missed it'}</p>`+folded;
}
// What the model that read the pages left for whoever reads the manuscript, such as a table the
// converter dropped. It is that model's own account, so it is shown as such and never as the paper.
// The engine writes a note only when a read is sealed, with its whitespace folded to single spaces,
// so it is shown as written.
function readerNoteMarkup(){
 const note=paper.ai_read?.note||'';
 if(!note)return '';
 return `<aside class="reader-note" role="note"><p><strong>A note from ${esc(pieceModel())}, the model that read the pages.</strong> It is that model's account of what it found, not the authors' text and not a review finding.</p><blockquote>${esc(note)}</blockquote></aside>`;
}
// The pages that came only from the model, each linked to the first line its transcription became.
function lostPagesMarkup(){
 const pages=lostPages();
 if(!pages.length)return '';
 const links=pages.map(row=>{
  const first=(row.added||[]).find(added=>Number.isInteger(added.lines?.[0]));
  return first?lineLink(first.document,first.lines[0],String(row.page)):String(row.page);
 });
 const one=pages.length===1;
 return `<p class="lost-pages" role="note">${one?'Page':'Pages'} ${links.join(', ')} came only from ${esc(pieceModel())}. The converter returned no text from ${one?'it':'them'}, so every line shown for ${one?'it':'them'} was written by the model from the page image.</p>`;
}
function pieceMarkup(piece,name,newSection){
 const [first,last]=piece.lines;
 const numbers=Array.from({length:last-first+1},(_,k)=>first+k);
 const line=(number,skip=0)=>`<span class="line" id="${esc(lineId(name,number))}">${shownLine(name,number,skip)}</span>`;
 if(piece.kind==='heading')return `<section class="source-block${modelWritten(piece)?' model-written':''}"><h2>${numbers.map(number=>line(number,Array.from(lineText(name,number).match(HEADING)?.[0]||'').length)).join(' ')}</h2>${provenanceMarkup(piece)}</section>`;
 // A piece of a Scaffold draft says whether its source can be edited in place.
 const native=piece.native?(piece.native.editable&&piece.native.file?`Editable source · ${esc(piece.native.file)}`:'Protected source region'):'';
 const page=Number.isInteger(piece.page)&&piece.page>0?`<button class="page-preview" data-page-document="${esc(name)}" data-page-line="${first}">Original page ${piece.page}</button>${native?' · '+native:''}`
  :native||(name===paper.main?'Page anchor unavailable':'Supplement text');
 const where=first===last?`line ${first}`:`lines ${first} to ${last}`;
 const tableLines=()=>`<p class="table-text">${numbers.map(number=>line(number)).join('\n')}</p>`;
 const content=piece.kind==='table'?tableMarkup(piece,name,tableLines())||tableLines()
  :`<p class="${piece.kind==='reference'?'refs':''}">${numbers.map(number=>line(number)).join('<br>')}</p>`;
 return `<section class="source-block${modelWritten(piece)?' model-written':''}">${newSection&&piece.section?`<h2>${esc(piece.section)}</h2>`:''}<div class="source-link">${page} <span class="muted">· ${esc(where)}</span></div>${provenanceMarkup(piece)}${content}</section>`;
}
// The main document first, then each supplement under its own title, with a link to its file.
function manuscript(){
 const nav=[],parts=[readerNoteMarkup(),lostPagesMarkup()];
 for(const name of Object.keys(paper.documents)){
  if(name!==paper.main){
   const asset=paper.assets.find(item=>item.document===name&&item.path);
   const link=asset?` <a class="source-link" href="${esc(withDraft('/'+(asset.preview||asset.path)))}" target="_blank" rel="noopener">Supplement file</a>`:'';
   parts.push(`<h2 class="document-title" id="${esc(lineId(name,0))}">${esc(asset?.label||name)}${link}</h2>`);
   nav.push(`<a href="#${esc(lineId(name,0))}">${esc(asset?.label||name)}</a>`);
  }
  let previous;
  for(const piece of paper.pieces.filter(row=>(row.document||paper.main)===name).sort((a,b)=>a.lines[0]-b.lines[0])){
   const newSection=piece.section!==previous;previous=piece.section;
   if(newSection&&piece.section)nav.push(`<a href="#${esc(lineId(name,piece.lines[0]))}">${esc(piece.section)}</a>`);
   parts.push(pieceMarkup(piece,name,newSection));
  }
 }
 $('#manuscript').innerHTML=parts.join('');
 const assets=paper.assets.filter(item=>item.path).map(item=>`<a href="${esc(withDraft('/'+(item.preview||item.path)))}" target="_blank" rel="noopener">${esc(item.label)}</a>`);
 $('#outline').innerHTML=nav.join('')+'<h3>Source files</h3>'+assets.join('');
 $('#manuscript').querySelectorAll('[data-page-line]').forEach(button=>button.addEventListener('click',()=>showPage(pieceAt(button.dataset.pageDocument,Number(button.dataset.pageLine)))));
 applySearch();
}
// The box of a passage on its page, as shares of the page image. A box is in PDF points from the
// top left corner of the page as the converter read it, and the manifest gives that page's size.
// A page printed turned is rendered turned, so its box is turned the same way. A page whose size
// was not recorded gets no box, because a box placed against a guessed size is in the wrong place.
function boxStyle(bbox,size){
 if(!Array.isArray(bbox)||bbox.length!==4||!bbox.every(Number.isFinite)||!size)return null;
 const [width,height,turn]=[size.width,size.height,((size.rotation||0)%360+360)%360];
 if(!(width>0&&height>0)||turn%90)return null;
 const [x0,y0,x1,y1]=bbox;
 if(!(x1>x0&&y1>y0))return null;
 // Each quarter turn clockwise moves a point (x, y) of a page of height h to (h - y, x).
 const shown=[[x0,y0],[x1,y1]].map(([x,y])=>({0:[x,y],90:[height-y,x],180:[width-x,height-y],270:[y,width-x]})[turn]);
 const [across,down]=turn%180?[height,width]:[width,height];
 const [left,right]=[Math.min(shown[0][0],shown[1][0]),Math.max(shown[0][0],shown[1][0])];
 const [top,bottom]=[Math.min(shown[0][1],shown[1][1]),Math.max(shown[0][1],shown[1][1])];
 const share=(value,total)=>`${(100*value/total).toFixed(3)}%`;
 return `left:${share(left,across)};top:${share(top,down)};width:${share(right-left,across)};height:${share(bottom-top,down)}`;
}
// The original page of a passage, with the passage's box on it and, from a card, the quote.
function showPage(row){
 if(!row||!Number.isInteger(row.page))return;
 const image=$('#page-image'),box=$('#page-box');
 const style=boxStyle(row.bbox,(paper.pages||[]).find(item=>item.page===row.page));
 box.hidden=!style;
 if(style)box.setAttribute('style',style);
 image.src=withDraft(`/pages/${row.page}.png`);image.alt=`Original manuscript page ${row.page}`;
 $('#page-title').textContent=`Original page ${row.page}`;
 $('#page-quote').textContent=row.quote||'';$('#page-quote').hidden=!row.quote;
 $('#page-dialog').showModal();
}
const pageButton=(row,id,index)=>Number.isInteger(row.page)&&row.page>0
 ?` <button class="page-preview" data-page-card="${esc(id)}" data-page-member="${index}">Show on page ${esc(row.page)}</button>`:'';
// The further lines a card or a member cites. A run card lists them with their document. A
// finding lists line numbers in its own document.
const evidenceRows=item=>Array.isArray(item.evidence)?item.evidence:(item.evidence_lines||[]).map(line=>({document:item.document,line}));
const evidenceLinks=rows=>rows.filter(row=>row&&Number.isInteger(row.line)).map(row=>lineLink(row.document||paper.main,row.line)).join(' ');
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
// The issue ledger: one row per problem raised on this draft or an earlier one, under the id it keeps on every
// draft. A problem an engine review raised is its own row, and nothing matches it to another review's rows.
const PROBLEM_STATUS={open:'Open',fixed:'Fixed',declined:'Declined by the author',thrown_out:'Thrown out by the code check',
 not_applicable:'Copyedit, with no scientific status'};
const AUTHOR_STATUS={open:'open',addressed:'addressed by the author',declined:'declined by the author'};
// The author's decisions on a problem, the latest first, each naming the draft it was made on. A decision made after
// a fix check found the problem not fixed sits above the one it follows, and every earlier one stays in view.
function authorDecisions(row){
 // A problem brought in from an engine run has no wording to accept, only the decisions on the issue.
 const wording=row.wording?`<p>Wording ${esc(row.wording)} on draft ${esc(row.raised_on)}</p>`:'';
 if(!row.decisions.length)return wording+(row.status==='not_applicable'?'':'<p class="muted">The author has not decided on this problem.</p>');
 return wording+[...row.decisions].reverse().map(decision=>{
  const said=[decision.note&&`Note: ${esc(decision.note)}`,decision.rationale&&`Rationale: ${esc(decision.rationale)}`].filter(Boolean);
  return `<p><strong>Author's decision on draft ${esc(decision.draft)}</strong><br>Issue ${esc(AUTHOR_STATUS[decision.status]||decision.status)}${said.map(text=>'<br>'+text).join('')}</p>`;
 }).join('');
}
// One engine fix check of a later draft. Its verdict and basis are printed as the engine names them, and the
// quote is the passage of the checked draft the verdict rests on. A check that did not reach the problem says why.
// The lane is the checker's seat. What was wrong with the check as a whole is on every entry it wrote, so no
// verdict from an incomplete check, or from one that read the converter's text, reads as one from a clean check.
function fixCheckWarnings(check){
 return [check.check_incomplete&&`This check was incomplete: ${check.check_incomplete}`,
  check.read_failed&&`The reader did not read the pages of draft ${check.draft}, so this check read the converter's text: ${check.read_failed}`]
  .filter(Boolean).map(text=>`<p class="error">${esc(text)}</p>`).join('');
}
function fixCheck(check){
 const lane=check.lane?`, ${check.verdict?'checked by':'dealt to'} ${esc(check.lane)}`:'';
 const warnings=fixCheckWarnings(check);
 if(!check.verdict)return `<p class="muted"><strong>Not checked on draft ${esc(check.draft)} on ${esc(check.date)}${lane}</strong><br>${esc(check.reason)}</p>${warnings}`;
 const said=[check.basis&&`Basis: ${esc(check.basis)}`,check.reason&&`Reason: ${esc(check.reason)}`,
  check.note&&`Checker's note: ${esc(check.note)}`,
  check.searches.length&&`Searched the draft for: ${check.searches.map(esc).join(', ')}`].filter(Boolean);
 const evidence=check.evidence;
 const where=evidence&&[Number.isInteger(evidence.page)&&`page ${esc(evidence.page)} of its PDF`,evidence.section&&`section ${esc(evidence.section)}`].filter(Boolean);
 const quoted=evidence?`<p class="muted">From draft ${esc(check.draft)}${where.length?', '+where.join(', '):''}</p><blockquote>${esc(evidence.quote)}</blockquote>`
  :check.old_evidence.map(span=>`<p class="muted">${span.present?'Still in':'No longer in'} draft ${esc(check.draft)} word for word</p><blockquote>${esc(span.quote)}</blockquote>`).join('');
 return `<p><strong>Fix check of draft ${esc(check.draft)} on ${esc(check.date)}${lane}: ${esc(check.verdict)}</strong>${said.map(text=>'<br>'+text).join('')}</p>${warnings}${quoted}`;
}
// The latest verdict leads, after a later check that did not reach the problem. Every earlier check stays below it.
function fixChecks(row){
 const checks=row.fix_checks;
 if(!checks.length)return '<p class="muted">No later draft has been checked for this problem.</p>';
 const verdict=checks.findLastIndex(check=>check.verdict);
 const shown=[...new Set([checks.length-1,verdict].filter(index=>index>=0))];
 const earlier=checks.filter((_,index)=>!shown.includes(index)).reverse();
 return shown.map(index=>fixCheck(checks[index])).join('')
  +(earlier.length?`<details><summary>Earlier fix checks (${earlier.length})</summary>${earlier.map(fixCheck).join('')}</details>`:'');
}
// A carried finding still stands on this draft while the passage on its line has the fingerprint it was found on.
function history(){
 $('#history-details').hidden=!ledger.length;
 if(ledger.length&&!review.findings.length)$('#history-details').open=true;
 $('#history-ledger').innerHTML=ledger.map(row=>{
  const finding=row.finding||{};
  const current=pieceAt(finding.document,finding.line);
  const location=current&&finding.fingerprint&&current.fingerprint===finding.fingerprint?`<p>${lineLink(finding.document,finding.line,'View unchanged passage in this draft')}</p>`:'';
  const top=`<p><span class="badge">${esc(row.id)}</span> ${esc(PROBLEM_STATUS[row.status]||row.status)}</p>`;
  const raised=`<p>Raised on draft ${esc(row.raised_on)} by review ${esc(row.review_id)}. Its quotes are from that draft.</p>`;
  const quotes=row.evidence.map(span=>`<blockquote>${esc(span.quote)}</blockquote>`).join('');
  // A finding an earlier run's code check threw out is carried to say what the code showed, never as an open question.
  if(row.status==='thrown_out')return `<div class="cross-check thrown-out-item">${top}<p class="thrown-out-mark" role="note">${esc(THROWN_OUT)}</p><p><strong>${esc(row.title||'Finding')}</strong></p><p>${esc(row.statement||'')}</p>${quotes}${codeEvidence(finding,'Code that contradicts it')}${finding.note?`<p><strong>Code check note</strong><br>${esc(finding.note)}</p>`:''}${raised}</div>`;
  return `<div class="cross-check">${top}<p><strong>${esc(categoryLabel(row.category))}: ${esc(row.title||'Earlier problem')}</strong>${row.severity?' · '+esc(row.severity):''}</p><p>${esc(row.statement||'')}</p>${quotes}${location}${raised}${authorDecisions(row)}${row.status==='not_applicable'?'':fixChecks(row)}</div>`;
 }).join('');
}
// A run's cards are the editor's issues. Every review is a fresh panel, so a card says nothing about an earlier round.
const categoryLabel=name=>name?String(name).charAt(0).toUpperCase()+String(name).slice(1).replaceAll('-',' '):'No category';
const isRunCard=item=>Boolean(review.run&&Array.isArray(item.members));
const plural=(count,noun)=>`${count} ${noun}${count===1?'':'s'}`;
function issueBadges(item){
 const badges=[item.group!=='ledger'&&item.source_id&&`<span class="badge">Issue ${esc(item.source_id)}</span>`,
  Number.isInteger(item.raised_by)&&`<span class="badge">Raised by ${esc(plural(item.raised_by,'reviewer'))}</span>`,
  item.escalate&&'<span class="badge escalated">Escalated</span>'];
 return `<div class="run-badges">${badges.filter(Boolean).join('')}</div>`;
}
function issueNotes(item){
 const notes=[item.rebuttal_quote&&`<p><strong>Manuscript text the editor weighed against the computed finding</strong></p><blockquote>${esc(item.rebuttal_quote)}</blockquote>${Number.isInteger(item.rebuttal_line)?`<p>${lineLink(item.rebuttal_document||paper.main,item.rebuttal_line,'Go to passage')}</p>`:''}`,
  (item.audits||[]).length&&`<p class="muted">Specialist reports: ${item.audits.map(esc).join(', ')}</p>`].filter(Boolean);
 return notes.length?`<div class="cross-check">${notes.join('')}</div>`:'';
}
// A data file a reviewer fetched: whole, or only its first bytes when it was over the engine's cap.
// `changed` is the engine's own words for a file that changed after the snapshot listed it.
function dataRead(data){
 if(!data||!Number.isInteger(data.bytes)||!Number.isInteger(data.stored_bytes))return '';
 const read=data.partial===true?`only the first ${data.stored_bytes} of ${plural(data.bytes,'byte')} read`:`read whole, ${plural(data.bytes,'byte')}`;
 return read+(typeof data.changed==='string'&&data.changed?`, ${data.changed}`:'');
}
// A code-checked finding quotes the run's code snapshot as well as the paper: the file, its lines
// and the text the engine found there. Line numbers count lines of the snapshot file. Code that
// is a data file says how much of the file the review read.
function codeEvidence(member,label='Code checked'){
 const code=member.code_evidence;
 if(!code||typeof code.path!=='string'||!Number.isInteger(code.start_line)||!Number.isInteger(code.end_line))return '';
 const lines=code.start_line===code.end_line?`line ${code.start_line}`:`lines ${code.start_line} to ${code.end_line}`;
 const data=dataRead(member.code_data);
 return `<div class="cross-check code-evidence"><p><strong>${esc(label)}</strong><br><code>${esc(code.path)}</code>, ${lines} of the run's code snapshot${data?`<br>A data file, ${esc(data)}`:''}</p>${typeof code.text==='string'?`<pre>${esc(code.text)}</pre>`:''}</div>`;
}
// Each member is a reviewer's finding behind the issue, with its own passage on the manuscript.
function memberItem(item,member,index){
 const ruling=(review.run.escalation_rulings||[]).find(row=>row.finding_uid===member.finding_uid);
 const facts=[member.slot,member.track&&`${member.track} track`,member.kind,member.severity].filter(Boolean).map(esc).join(' · ');
 const badges=[member.basis&&`<span class="badge basis" title="${esc(member.basis_reason||'')}">Basis: ${esc(member.basis)}</span>`,
  member.escalate&&'<span class="badge escalated">Escalated</span>'].filter(Boolean).join('');
 const wording=member.kind==='edit'&&typeof member.replacement==='string'?`<p class="muted">Suggested wording</p><blockquote>${esc(member.replacement)}</blockquote>`:'';
 const links=(member.source_urls||[]).filter(url=>typeof url==='string'&&url.startsWith('https://')).map(url=>`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(url)}</a>`).join('<br>');
 // A member quoting the same span as an earlier one links to that earlier member's mark.
 const shared=isMarked(member)?item.members.findIndex(other=>isMarked(other)&&spanKey(other)===spanKey(member)):index;
 const where=member.placement==='anchored'?`<a href="#anchor-${esc(item.id)}-${shared+1}">Go to passage</a>`:'Unplaced: the quote is not found once in its passage';
 const evidence=evidenceLinks(evidenceRows(member));
 return `<li class="member"><p class="muted">${facts}</p>${badges?`<div class="run-badges">${badges}</div>`:''}${member.basis_reason?`<p class="muted">${esc(member.basis_reason)}</p>`:''}${member.title&&member.title!==item.title?`<p><strong>${esc(member.title)}</strong></p>`:''}${member.comment&&member.comment!==item.comment?`<p class="comment-text">${esc(member.comment)}</p>`:''}${member.quote?`<blockquote>${esc(member.quote)}</blockquote>`:''}${codeEvidence(member)}${wording}${member.counterevidence?`<div class="cross-check"><p><strong>Counterevidence checked</strong><br>${esc(member.counterevidence)}</p></div>`:''}${ruling?`<div class="cross-check ruling"><p><strong>Escalation ruling</strong><br>${esc(ruling.ruling)}</p></div>`:''}${links?`<p class="muted">Sources cited: ${links}</p>`:''}<div class="evidence">${where}${pageButton(member,item.id,index)}${evidence?`<br>Evidence: ${evidence}`:''}</div></li>`;
}
function memberList(item){
 if(!item.members.length)return '';
 return `<details class="members" open><summary>Evidence: ${esc(plural(item.members.length,'finding'))}</summary><ol>${item.members.map((member,index)=>memberItem(item,member,index)).join('')}</ol></details>`;
}
// A review written with no findings in it: the reviewers raised none, the guard quarantined
// what they raised, or the code check threw it out.
function runStatus(run){
 if(run.status!=='complete-without-findings')return `Status ${run.status}`;
 const quarantined=run.quarantined_findings_count||0;
 const thrown=run.code_check?run.code_check.counts.contradicted:0;
 if(quarantined&&thrown)return `Status ${run.status}: the guard quarantined ${quarantined} and the code check threw out ${thrown}`;
 if(thrown)return `Status ${run.status}: the code check threw out all ${thrown}`;
 return quarantined?`Status ${run.status}: the guard quarantined all ${quarantined}`
  :`Status ${run.status}: the reviewers raised none`;
}
// A token count with a comma every three digits, because a session's spend runs to millions.
function count(value){return String(value).replace(/\B(?=(\d{3})+(?!\d))/g,',');}
const TOKEN_PARTS=[['uncached input','tokens_input_uncached'],['cache write','tokens_cache_write'],
 ['cache read','tokens_cache_read'],['output','tokens_output']];
// Since engine 3d96d92 an agent row says what the session spent, every call added up with cache reads
// included, and its widest single call. A row without them keeps the one total it always had.
function spendFacts(row){
 if(!Number.isFinite(row.tokens_cumulative))return [Number.isFinite(row.tokens)&&`${count(row.tokens)} tokens`];
 if(!row.tokens_cumulative)return ['0 tokens spent'];
 const parts=TOKEN_PARTS.filter(([,key])=>Number.isFinite(row[key])).map(([name,key])=>`${name} ${count(row[key])}`);
 return [`${count(row.tokens_cumulative)} tokens spent${parts.length?` (${parts.join(', ')})`:''}`,
  Number.isFinite(row.tokens_peak_context)&&`peak context ${count(row.tokens_peak_context)} tokens`];
}
function agentFacts(row){
 const tasks=(row.labels||[]).filter(label=>label!==row.slot);
 const raises=['core','specialist'].includes(row.role)||row.findings>0||row.none_found;
 // The engine says `in process` for the recorder it ran itself, which has no model asked and none ran.
 const inProcess=row.ending==='in process';
 const models=inProcess?['in process, no model']
  :[`model asked ${row.assigned_model||'not recorded'}`,`model ran ${row.model||'not recorded'}`];
 // The engine's own word for how the agent ended goes beside the state, when it says more.
 const ended=row.ending&&!inProcess&&row.ending!==row.state?row.ending:'';
 const facts=[row.slot,row.track&&`${row.track} track`,row.role==='citation-worker'&&'citation worker, writes no findings',...models,
  Number.isInteger(row.attempt)&&`attempt ${row.attempt}`,
  Number.isInteger(row.tool_calls)&&`${row.tool_calls} tool calls`,...spendFacts(row),
  ended?`${row.state||'state not recorded'} (${ended})`:row.state,
  tasks.length&&`tasks ${tasks.join(', ')}`,
  raises&&(row.none_found?'reported no findings':`${row.findings||0} findings`)].filter(Boolean).map(esc).join(' · ');
 return row.detail&&!inProcess?`${facts}<br><span class="muted">${esc(row.detail)}</span>`:facts;
}
// What the two token figures mean, shown once under the agents of a run that has them.
const TOKENS_NOTE='Tokens spent is every call added up, cache reads included, and is what the run cost. Peak context is the'
 +' largest single call, and is the figure that compares with a run from before engine 0.10.0.';
// The agents of a run whose rows say what each session spent in all.
function spentRows(run){return (run.agents||[]).filter(row=>Number.isFinite(row.tokens_cumulative));}
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
 const where=[row.section&&esc(row.section),Number.isInteger(row.line)&&lineLink(row.document||paper.main,row.line,'Go to passage'),
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
// Which code the run was reviewed against and how much of it a reviewer opened. A run given no
// code says nothing about it, as REVIEW.md does. A local folder is named by its own name, as
// REVIEW.md names it, and a repository URL is shown whole.
function codeReviewed(code){
 if(!code||code.reviewed!==true)return '';
 const source=typeof code.source==='string'&&code.source?(code.kind==='folder'?code.source.split(/[\\/]/).filter(Boolean).pop()||'':code.source):'';
 const commit=typeof code.commit==='string'&&code.commit?` at ${code.commit.slice(0,12)}${code.dirty===true?' with uncommitted changes':''}`:'';
 const counts=[Number.isInteger(code.opened)&&Number.isInteger(code.files_in_snapshot)&&`${code.opened} of ${plural(code.files_in_snapshot,'file')} opened`,
  code.searches>0&&`${code.searches} ${code.searches===1?'search':'searches'}`,code.files_skipped>0&&`${plural(code.files_skipped,'path')} left out of the snapshot`,
  code.truncated&&`the snapshot stopped early: ${code.truncated}`].filter(Boolean);
 // The engine lists the data files the code ships and copies one in only when a reviewer reads it.
 const data=code.data_listed>0?[`${code.data_fetched} of ${plural(code.data_listed,'data file')} fetched`,
  code.data_partial>0&&`${code.data_partial} only in part`,code.data_refused>0&&`${code.data_refused} refused`].filter(Boolean):[];
 const cut=code.source_cut>0?`<p class="unverified">${esc(`${plural(code.source_cut,'program source file')} did not fit in the snapshot, so it is not the whole of the code, and no finding may say the code never does something.`)}</p>`:'';
 const opened=(code.files_opened||[]).filter(path=>typeof path==='string');
 const fetched=code.data.filter(row=>row&&typeof row.path==='string');
 return `<div class="code-reviewed"><p><strong>Code reviewed</strong><br><code>${esc(source||'the code this run was given')}</code>${esc(commit)}${counts.length?`<br>${esc(counts.join(', '))}`:''}${data.length?`<br>${esc(data.join(', '))}`:''}</p>${cut}${opened.length?`<details><summary>Files opened (${opened.length})</summary><ul>${opened.map(path=>`<li><code>${esc(path)}</code></li>`).join('')}</ul></details>`:''}${fetched.length?`<details><summary>Data files fetched (${fetched.length})</summary><ul>${fetched.map(row=>`<li><code>${esc(row.path)}</code>, ${esc(dataRead(row))}</li>`).join('')}</ul></details>`:''}</div>`;
}
// What the run's code check did with the findings that rest on how a number was computed.
// A run given no code has no code check. A check that answered only some of the claims it was handed
// is incomplete, and a silent one filed no report at all. The run panel says which, and why, above its comments.
function codeCheckCounts(check){
 if(!check)return '';
 const counts=check.counts||{};
 const missed=check.not_checked>0?`, ${check.not_checked} handed to it and not checked`:'';
 const over=check.over_cap>0?`, ${check.over_cap} over its cap${check.cap===null?'':` of ${check.cap}`} left unchecked`:'';
 const state=check.silent?', silent':check.incomplete?', incomplete':'';
 return `<p class="count">${esc(`Code check${state}: ${check.checked} checked, ${counts.confirmed??0} confirmed, ${counts.contradicted??0} thrown out, ${counts['not-shown']??0} not shown in the code${missed}${over}`)}</p>`;
}
// Why a run's code check left claims unread against the code, in the engine's words.
function codeCheckIncomplete(check){
 if(!check||!(check.incomplete||check.silent))return '';
 const opening=check.silent?'The code check filed no report, so every finding it was handed stands as its reviewer filed it'
  :'The code check is incomplete, so a finding it did not reach stands as its reviewer filed it';
 return `${opening}: ${check.incomplete_reason||`${plural(check.not_checked,'claim')} not read against the code.`}`;
}
// A reader that failed leaves the manuscript sealed as converted, and the run goes on from the converter's text.
function readerFailed(read){
 if(!read||!read.reader_failed)return '';
 return `The reader did not read the pages of this manuscript, so the reviewers read the converter's text: ${read.reason||'the reader gave no reason.'}`;
}
// A finding the code check threw out is in no issue and takes no decision. It is shown with the
// code that disproved it, marked as thrown out, apart from every open issue.
const THROWN_OUT='Thrown out by the code check. This is not an open issue: the code does not do what this finding said.';
function thrownOutItem(item){
 const facts=[item.slot,item.track&&`${item.track} track`,item.severity].filter(Boolean).map(esc).join(' · ');
 const where=Number.isInteger(item.line)?`<p>${lineLink(item.document||paper.main,item.line,'Go to passage')}</p>`:'';
 return `<div class="thrown-out-item" id="thrown-out-${esc(item.id)}"><p class="muted">${facts}</p><p class="thrown-out-mark" role="note">${esc(THROWN_OUT)}</p><h4>${esc(item.title||'Finding')}</h4>${item.comment?`<p class="comment-text">${esc(item.comment)}</p>`:''}${item.quote?`<blockquote>${esc(item.quote)}</blockquote>`:''}${where}${item.assumed_method?`<p><strong>What the finding took the code to do</strong><br>${esc(item.assumed_method)}</p>`:''}${codeEvidence(item,'Code that contradicts it')}${item.note?`<p><strong>Code check note</strong><br>${esc(item.note)}</p>`:''}</div>`;
}
function thrownOut(check){
 const items=check?check.thrown_out:[];
 if(!items.length)return '';
 return `<details class="thrown-out" id="thrown-out" open><summary>Thrown out: the code does not do what the finding said (${items.length})</summary>${items.map(thrownOutItem).join('')}</details>`;
}
function runPanel(){
 const run=review.run;
 $('#run-panel').hidden=!run;
 for(const name of RUN_FILTERS)$('#filter-'+name).hidden=!run;
 for(const name of WORKSPACE_FILTERS)$('#filter-'+name).hidden=Boolean(run);
 if(filter!=='all'&&!(run?RUN_FILTERS:WORKSPACE_FILTERS).includes(filter)){
  filter='all';document.querySelectorAll('[data-filter]').forEach(item=>item.setAttribute('aria-pressed',item.dataset.filter==='all'));
 }
 if(!run){$('#run-panel').innerHTML='';return;}
 const facts=[run.arm&&`Arm ${run.arm}`,run.reviewer_count&&`${run.reviewer_count} reviewers`,run.status&&runStatus(run),
  run.issues_source==='editor'&&'Issues grouped by the editor',run.issues_source==='server'&&'Issues written by the server, one per finding, with no editor',
  Number.isInteger(run.escalated_count)&&`${run.escalated_count} escalated`,run.review_guard_status&&`Guard ${run.review_guard_status}`,
  run.quarantined_findings_count?`${run.quarantined_findings_count} quarantined`:'',
  Number.isFinite(run.wall_seconds)&&`${Math.round(run.wall_seconds/60)} min`,
  Number.isFinite(run.tokens_total)&&`${count(run.tokens_total)} tokens${spentRows(run).length?' spent':''}`].filter(Boolean);
 // Why a run is not publishable is shown once, above its comments.
 const warnings=[run.cause,run.note,...(run.problems||[]),(run.missing_stages||[]).length&&`Stages that did not report: ${run.missing_stages.join(', ')}`,
  readerFailed(run.read),codeCheckIncomplete(run.code_check)].filter(Boolean);
 const unverified=unverifiedNote(run.models_unverified);
 const verdict=run.verdict;
 const verdictHtml=verdict?`<details open><summary>Editor's verdict</summary><p><strong>Significance</strong><br>${esc(verdict.significance)}</p><p><strong>Strength of evidence</strong><br>${esc(verdict.strength_of_evidence)}</p>${verdict.reasoning?`<p><strong>Reasoning</strong><br>${esc(verdict.reasoning)}</p>`:''}<p class="muted">Basis: ${esc(verdict.basis||'unstated')}. ${esc(verdict.limitation||'')}</p></details>`:'';
 const audits=Object.entries(run.audits||{});
 const auditHtml=audits.length?`<details><summary>Specialist reports (${audits.length})</summary>${audits.map(([track,text])=>`<details class="audit"><summary>${esc(track)}</summary><pre>${esc(text)}</pre></details>`).join('')}</details>`:'';
 const reviewers=run.agents||[],tracks=Object.entries(run.findings_by_track||{});
 const tokensNote=spentRows(run).length?`<p class="muted">${esc(TOKENS_NOTE)}</p>`:'';
 const reviewerHtml=reviewers.length||tracks.length?`<details><summary>Agents (${reviewers.length})</summary><ul>${reviewers.map(row=>`<li>${agentFacts(row)}</li>`).join('')}</ul>${tokensNote}${tracks.length?`<p class="muted">Findings by track: ${tracks.map(([track,count])=>`${esc(track)} ${esc(count)}`).join(' · ')}</p>`:''}</details>`:'';
 $('#run-panel').innerHTML=`<p class="count">${facts.map(esc).join(' · ')}</p>${warnings.map(text=>`<p class="error">${esc(text)}</p>`).join('')}${unverified?`<p class="unverified">${esc(unverified)}</p>`:''}${verdictHtml}${codeReviewed(run.code)}${codeCheckCounts(run.code_check)}${citationPanel(run.citations)}${auditHtml}${reviewerHtml}${(run.limitations||[]).map(text=>`<p class="muted">${esc(text)}</p>`).join('')}`;
}
// A run card with no engine id is numbered by its place, so it takes no decision. The server refuses one too.
const NO_ENGINE_ID='This card has no engine id, so a decision on it could land on another card. Re-run the review to decide on it.';
function card(item){
 const decidable=item.decidable!==false;
 const wording=decidable?decisions.items[item.id]||'proposed':'no decision';
 const annotation=decidable?pendingResponses.get(responseKey(item.id))||decisions.annotations?.[item.id]||{}:{};
 const issueStatus=annotation.issue_status||'open';
 const run=isRunCard(item);
 const anchored=run?anchorsOf(item).length:item.placement==='anchored';
 const source=run&&!item.members.length?'':anchored&&Number.isInteger(item.line)?lineLink(item.document||paper.main,item.line,'Go to passage')+(run?'':pageButton(item,item.id,-1))
  :run?'No finding behind this issue is placed on the manuscript text':'Unplaced comment: source anchor needs review';
 const evidence=evidenceLinks(evidenceRows(item));
 const actions=item.kind==='edit'?`<button data-action="accepted" ${wording!=='proposed'?'disabled':''}>Accept wording</button><button data-action="rejected" ${wording!=='proposed'?'disabled':''}>Decline wording</button>`:`<button data-action="noted" ${wording!=='proposed'?'disabled':''}>Mark for follow-up</button>`;
 const number=item.number?`${esc(item.number)}. `:'';
 const top=run?`<span class="category run ${esc(item.group)}">${esc(categoryLabel(item.severity||'unspecified'))} · ${esc(categoryLabel(item.category))}</span>`
  :`<span class="category ${esc(categoryOf(item))}">${esc(categoryOf(item))} · ${esc(item.kind)} · ${esc(item.severity||'unspecified')}</span>`;
 const details=run?issueBadges(item):'';
 const notes=run?issueNotes(item)+memberList(item):item.counterevidence?`<div class="cross-check"><p><strong>Counterevidence checked</strong><br>${esc(item.counterevidence)}</p></div>`:'';
 const decide=decidable?`<div class="actions">${actions}${wording!=='proposed'?'<button data-action="proposed">Undo wording decision</button>':''}</div><div class="author-response"><label>Author comment<textarea data-field="comment" maxlength="4000">${esc(annotation.author_comment||'')}</textarea></label><label>Issue status<select data-field="issue"><option value="open" ${issueStatus==='open'?'selected':''}>Open</option><option value="addressed" ${issueStatus==='addressed'?'selected':''}>Addressed by author</option><option value="declined" ${issueStatus==='declined'?'selected':''}>Declined by author</option></select></label><label>Rationale for status<textarea data-field="rationale" maxlength="2000">${esc(annotation.rationale||'')}</textarea></label><button data-save-response>Save author response</button><p class="muted">Addressed and declined record the author's assessment. Neither verifies the scientific issue. A declined issue is not checked again on a later draft.</p></div>${annotation.history?.length?`<details><summary>Author response history (${annotation.history.length})</summary><ol>${annotation.history.map(row=>`<li>${esc(row.at)} · ${esc(row.issue_status)} · ${esc(row.rationale||'No rationale')}</li>`).join('')}</ol></details>`:''}`
  :`<p class="muted no-engine-id" role="note">${esc(NO_ENGINE_ID)}</p>`;
 return `<article class="finding" id="note-${esc(item.id)}" data-id="${esc(item.id)}"><div class="card-top">${top}<span>${esc(wording)}</span></div>${details}<h3>${number}${esc(item.title||(run?'Review issue':'Review finding'))}</h3><p class="comment-text">${esc(item.comment||item.text||'')}</p>${notes}${source||evidence?`<div class="evidence">${source}${source&&evidence?'<br>':''}${evidence?`Evidence: ${evidence}`:''}</div>`:''}${externalFinding(item)}${decide}</article>`;
}
// Saved decisions that match no card that takes one: an earlier viewer's per-finding keys, a
// numbered card's place, or an issue this run no longer holds. They are counted once and left in the file.
function staleNote(){
 const live=new Set(review.findings.filter(item=>item.decidable!==false).map(item=>item.id));
 const stale=new Set([...Object.keys(decisions.items||{}),...Object.keys(decisions.annotations||{})].filter(id=>!live.has(id)));
 if(!stale.size)return '';
 return `<p class="stale-decisions muted" role="note">${esc(`${plural(stale.size,'saved decision')} no longer ${stale.size===1?'matches':'match'} a card in this review. The decisions file is left as it is.`)}</p>`;
}
function grouped(items){
 const groups={required:[],suggestion:[],ledger:[]};
 for(const item of items)(groups[item.group]||groups.ledger).push(item);
 return groups;
}
function runCount(){
 const groups=grouped(review.findings);
 const thrown=review.run.code_check?review.run.code_check.thrown_out.length:0;
 const thrownText=thrown?` · ${thrown} thrown out by the code check`:'';
 if(review.run.findings_source==='none')return 'No findings'+thrownText;
 if(review.run.findings_source!=='issues')return `${plural(groups.ledger.length,'finding')}, not grouped into issues`+thrownText;
 return [`${groups.required.length} required`,`${plural(groups.suggestion.length,'suggestion')}`,
  groups.ledger.length&&`${plural(groups.ledger.length,'finding')} no issue holds`].filter(Boolean).join(' · ')+thrownText;
}
// A run's review: the required changes in rank order, the suggestions under their categories,
// then any finding no issue holds.
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
 const loose=run.findings_source==='issues'?'Findings no issue holds':'Findings recorded before any issues were written';
 const sections=[groups.required.length&&`<h3 class="issue-group">Required changes (${groups.required.length})</h3>${groups.required.map(card).join('')}`,
  groups.suggestion.length&&`<h3 class="issue-group">Suggestions (${groups.suggestion.length})</h3>${suggestions.join('')}`,
  groups.ledger.length&&`<h3 class="issue-group">${loose} (${groups.ledger.length})</h3>${groups.ledger.map(card).join('')}`,
  filter==='all'&&thrownOut(run.code_check)].filter(Boolean);
 const empty=review.findings.length||run.publishable!==false?'<div class="empty">No comments in this view.</div>':'';
 return banner+(sections.join('')||empty);
}
function cards(){
 const openEarlier=ledger.filter(row=>row.status==='open').length;
 $('#finding-count').textContent=(review.run?runCount():review.findings.length+' new')+(openEarlier?' · '+plural(openEarlier,'earlier problem')+' open':'');$('#review-summary').textContent=review.summary||'';
 runPanel();
 const raw=review.raw_response||{};
 $('#handoff-details').hidden=!(raw.source_cards||[]).length&&!raw.domain_profile&&!raw.result_map&&!(raw.result_comparisons||[]).length;
 $('#handoff-ledger').innerHTML='';
 if(raw.domain_profile)$('#handoff-ledger').innerHTML+=`<p><strong>Selected domain guidance</strong>: ${(raw.domain_profile.selected||[]).map(item=>esc(item.name)).join(', ')||'Shared methods only'}</p><p>${esc(raw.domain_profile.limitation)}</p>`;
 $('#handoff-ledger').innerHTML+=(raw.source_cards||[]).map(card=>externalCard(card)).join('');
 if(raw.result_map){
  const map=raw.result_map;
  $('#handoff-ledger').innerHTML+=`<details><summary>Claims, figures and tables (${map.nodes.length} passages)</summary><p>${esc(map.limitation)}</p><p>Figure pixels require separate inspection.</p>${map.edges.map(edge=>`<p>${lineLink(edge.document,edge.from)} cites ${esc(edge.quote)}: ${edge.to.length?edge.to.map(target=>lineLink(target.document,target.line)).join(', '):'Target not extracted'}</p>`).join('')}${map.checks.map(check=>`<p>${esc(check.reason)} ${check.lines.map(line=>lineLink(check.document,line)).join(', ')}</p>`).join('')}</details>`;
 }
 for(const comparison of raw.result_comparisons||[]){
  $('#handoff-ledger').innerHTML+=`<details><summary>Quantity comparison: ${esc(comparison.status.replaceAll('_',' '))}</summary><p>${esc(comparison.limitation)}</p>${comparison.observations.map(obs=>`<p>${lineLink(obs.document,obs.line)}: ${esc(obs.value)} (${esc(obs.metric)})</p><blockquote>${esc(obs.quote)}</blockquote>`).join('')}<p>Context labels are investigator assessments.</p></details>`;
 }
 $('#comments').innerHTML=staleNote()+(review.run?runCards():review.findings.filter(item=>filter==='all'||filter===categoryOf(item)||(filter==='questions'&&item.kind!=='edit')).map(card).join('')||'<div class="empty">No comments in this view.</div>');
 $('#comments').querySelectorAll('[data-action]').forEach(button=>button.addEventListener('click',()=>saveFinding(button.closest('article'),button.dataset.action)));
 $('#comments').querySelectorAll('[data-save-response]').forEach(button=>button.addEventListener('click',()=>saveFinding(button.closest('article'),decisions.items[button.closest('article').dataset.id]||'proposed')));
 $('#comments').querySelectorAll('[data-page-card]').forEach(button=>button.addEventListener('click',()=>{
  const item=review.findings.find(row=>row.id===button.dataset.pageCard),index=Number(button.dataset.pageMember);
  showPage(index<0?item:item?.members?.[index]);
 }));
 $('#comments').querySelectorAll('[data-field]').forEach(input=>input.addEventListener('input',()=>{
  const card=input.closest('article');
  pendingResponses.set(responseKey(card.dataset.id),{...(decisions.annotations?.[card.dataset.id]||{}),author_comment:card.querySelector('[data-field=comment]').value,issue_status:card.querySelector('[data-field=issue]').value,rationale:card.querySelector('[data-field=rationale]').value});
  $('#save-status').textContent='Author response has unsaved changes.';
 }));
}
async function saveFinding(card,status){
 const issueStatus=card.querySelector('[data-field=issue]').value;
 const rationale=card.querySelector('[data-field=rationale]').value;
 if(issueStatus!=='open'&&!rationale.trim()){error('Addressed and declined issues require a rationale.');return;}
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
  ||!review.findings.some(item=>item.kind==='edit'&&item.decidable!==false&&decisions.items[item.id]==='accepted');
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
  state=await api(requestedDraft()?'/api/revisions?draft='+encodeURIComponent(requestedDraft()):'/api/revisions');
  paper=await api(withDraft('/api/paper'));ledger=await api(withDraft('/api/ledger'));
  $('#source-title').textContent=paper.title;document.title='Review · '+paper.title;
  const written=paper.pieces.filter(modelWritten).length;
  $('#summary-counts').textContent=`${state.native?'Native source':paper.statistics.pdf_pages+' pages'} · ${paper.statistics.reference_entries} references · ${plural(paper.pieces.length,'passage')}${written?` · ${written} ${wasRead()?'written or read again':'written'} by ${pieceModel()}`:''}`;
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
 }catch(e){error(e.message);}
}
$('#draft-select').addEventListener('change',event=>setDraftLink(event.target.value));
$('#review-select').addEventListener('change',event=>loadReview(event.target.value).catch(e=>error(e.message)));
$('#search').addEventListener('input',applySearch);
// A link into a collapsed section, such as the thrown-out findings, opens it, so the target is visible.
window.addEventListener('hashchange',()=>{const target=document.getElementById(decodeURIComponent(location.hash.slice(1)));const box=target?.closest('details');if(box)box.open=true;});
document.querySelectorAll('[data-mode]').forEach(button=>button.addEventListener('click',()=>{mode=button.dataset.mode;document.querySelectorAll('[data-mode]').forEach(item=>item.setAttribute('aria-pressed',item===button));manuscript();}));
document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{filter=button.dataset.filter;document.querySelectorAll('[data-filter]').forEach(item=>item.setAttribute('aria-pressed',item===button));cards();}));
$('#close-page').addEventListener('click',()=>$('#page-dialog').close());
$('#export').addEventListener('click',async()=>{try{const value=await api(withDraft('/api/export?review='+encodeURIComponent(review.id)));const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const anchor=document.createElement('a');anchor.href=url;anchor.download=paper.id+'-'+review.id+'-review.json';anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){error(e.message);}});
$('#build-revision').addEventListener('click',async()=>{const id=prompt('New revision ID. Use lowercase letters, numbers, underscores, or hyphens.');if(!id)return;try{$('#build-revision').disabled=true;$('#save-status').textContent='Compiling and verifying the new revision.';const value=await api(withDraft('/api/revisions'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision_id:id,review_id:review.id,decision_revision:decisions.revision,expected_head:state.head})});setDraftLink(value.head.revision_id);}catch(e){error(e.message);$('#build-revision').disabled=false;}});
$('#checkout-draft').addEventListener('click',async()=>{if(!confirm(`Make ${state.selected} the active draft? Existing revisions remain available.`))return;try{const value=await api(withDraft('/api/checkout'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision_id:state.selected,expected_head:state.head})});setDraftLink(value.revision_id);}catch(e){error(e.message);}});
start();
