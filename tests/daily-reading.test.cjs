const test=require('node:test'),assert=require('node:assert/strict');
const {create,KEY,beijingDate,valid}=require('../docs/maritime_daily_reading.js');
function batch(date,start=0){return {payload:{date,publication_status:'complete',papers:Array.from({length:5},(_,i)=>({paper_id:`2610.${10000+start+i}`,title:'Paper '+i,abstract:'English',abstract_zh:'中文摘要',ai_score:80}))},aliases:{},prompt_template:'{{title}}'};}
function setup(){const map=new Map([['favorites','private note']]);const storage={getItem:k=>map.get(k)||null,setItem:(k,v)=>map.set(k,v)};let day='2026-10-24';return {map,storage,day:d=>{day=d;},progress:create(storage,batch(day),()=>day)};}
test('unfinished snapshot survives reload, cloud changes and Beijing midnight without touching notes',()=>{
  const s=setup(),first=s.progress.read();s.day('2026-10-25');
  assert.deepEqual(s.progress.advance(batch('2026-10-25',10)),first);
  assert.deepEqual(create(s.storage,batch('2026-10-25',10)).read(),first);
  assert.equal(s.map.get('favorites'),'private note');
  assert.equal(beijingDate(new Date('2026-10-24T16:00:00Z')),'2026-10-25');
});
test('completion stays same day; undo persists; next day only complete disjoint newer batch switches once',()=>{
  const s=setup();s.progress.complete();
  assert.equal(s.progress.advance(batch('2026-10-25',10)).batch.payload.date,'2026-10-24');
  s.progress.complete(false);s.day('2026-10-25');
  assert.equal(s.progress.advance(batch('2026-10-25',10)).batch.payload.date,'2026-10-24');
  s.day('2026-10-24');s.progress.complete();s.day('2026-10-25');
  const incomplete=batch('2026-10-25',10);incomplete.payload.publication_status='partial';
  assert.equal(s.progress.advance(incomplete).batch.payload.date,'2026-10-24');
  assert.equal(s.progress.advance(batch('2026-10-25',3)).batch.payload.date,'2026-10-24');
  const next=s.progress.advance(batch('2026-10-25',10));assert.equal(next.batch.payload.date,'2026-10-25');assert.equal(next.completed,false);assert.equal(next.shown.length,2);
  assert.deepEqual(s.progress.advance(batch('2026-10-25',10)),next);
});
test('DOI/arxiv aliases cannot disguise overlap; corrupt progress preserved; storage errors explicit',()=>{
  const s=setup();s.progress.read();s.progress.complete();s.day('2026-10-25');
  const next=batch('2026-10-25',10);next.payload.papers[0].doi='10.1234/abc';next.aliases['doi:10.1234/abc']='2610.10000';
  assert.equal(s.progress.advance(next).batch.payload.date,'2026-10-24');
  s.map.set(KEY,'broken');assert.throws(()=>s.progress.read());assert.equal(s.map.get(KEY),'broken');
  assert.throws(()=>create({getItem:()=>null,setItem:()=>{throw Error('quota');}},batch('2026-10-24')).read(),/quota/);
  assert.equal(valid({...next,payload:{...next.payload,papers:next.payload.papers.slice(1)}}),false);
});
test('daily DOM pins content and prompt, keeps favorites/notes, marks and undoes without replacing articles',async()=>{
  const vm=require('node:vm'),fs=require('node:fs');
  class Element {
    constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.style={};this.handlers={};this.textContent='';this.value='';}
    append(...nodes){for(const n of nodes){n.parentNode=this;this.children.push(n);}}
    replaceChildren(...nodes){this.children=[];this.append(...nodes);}
    setAttribute(k,v){this[k]=v;}addEventListener(k,fn){this.handlers[k]=fn;}
    click(){return this.handlers.click?.();}
    closest(tag){let n=this;while(n&&n.tagName!==tag.toUpperCase())n=n.parentNode;return n;}
    querySelector(s){return walk(this).find(n=>s==='[data-paper-panels]'&&n.dataset.paperPanels);}
  }
  const walk=n=>[n,...n.children.flatMap(walk)],nodes=new Map();
  for(const id of ['daily-reading-data','daily-prompt-data','daily-favorites','favorite-message','reading-date','reading-batch-date','reading-status','reading-papers','reading-complete','reading-undo','reading-error'])nodes.set(id,new Element('div'));
  const first=batch('2026-10-24');first.payload.papers.forEach(p=>Object.assign(p,{authors:['Alice'],original_url:'https://arxiv.org/abs/'+p.paper_id,reading_url:'https://example.org/maritime.html?paper='+p.paper_id,resource_type:'preprint'}));
  nodes.get('daily-reading-data').textContent=JSON.stringify(first);
  let now='2026-10-24T12:00:00Z',latest=batch('2026-10-25',10),tick,copied='';const storage=new Map();
  const doc={getElementById:id=>nodes.get(id),createElement:tag=>new Element(tag),addEventListener(){},querySelector:()=>null,querySelectorAll:s=>walk(nodes.get('reading-papers')).filter(n=>s==='[data-prompt-paper]'&&n.dataset.promptPaper)};
  const context=vm.createContext({document:doc,Date:class extends Date{constructor(...args){super(...(args.length?args:[now]));}},
    localStorage:{get length(){return storage.size;},key:i=>[...storage.keys()][i],getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},
    navigator:{clipboard:{writeText:async text=>{copied=text;}}},location:{pathname:'/RS-PaperClaw/maritime-daily.html'},addEventListener(){},setInterval:fn=>{tick=fn;},fetch:async url=>({ok:true,json:async()=>url.includes('content-corrections')?{records:{}}:url.includes('reading-index')?{batches:[{date:latest.payload.date}]}:latest.payload})});
  for(const file of ['maritime_favorites.js','maritime_prompt.js','maritime_daily_prompt.js','maritime_daily_reading.js'])vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../docs',file),'utf8'),context);
  await new Promise(setImmediate);
  const articles=nodes.get('reading-papers').children;assert.equal(articles.length,5);
  const find=text=>walk(nodes.get('reading-papers')).find(n=>n.textContent===text);
  await find('Prompt').click();assert.ok(copied.includes('Paper 0'));
  find('☆收藏').click();const editor=walk(articles[0]).find(n=>n.tagName==='TEXTAREA');editor.value='中文 **笔记**';editor.handlers.input();find('保存笔记').click();
  assert.ok([...storage.values()].some(v=>v.includes('中文 **笔记**')));
  now='2026-10-25T00:00:00Z';await tick();assert.equal(nodes.get('reading-papers').children[0],articles[0]);assert.equal(nodes.get('reading-date').textContent,'每日阅读 2026-10-25');
  nodes.get('reading-complete').click();assert.equal(nodes.get('reading-complete').textContent,'已阅读完成 · 明日更新');
  await tick();assert.equal(nodes.get('reading-papers').children[0],articles[0]);
  nodes.get('reading-undo').click();assert.equal(JSON.parse(storage.get(KEY)).completed,false);
  nodes.get('reading-complete').click();now='2026-10-26T00:00:00Z';await tick();
  assert.equal(nodes.get('reading-error').textContent,'');assert.equal(JSON.parse(storage.get(KEY)).batch.payload.date,'2026-10-25');assert.equal(nodes.get('reading-papers').children.length,5);
  assert.ok([...storage.values()].some(v=>v.includes('中文 **笔记**')));
});

test('unread medical correction preserves completion and other snapshots; delayed replacement restores five',()=>{
 const s=setup();const first=s.progress.read();s.progress.correct({'2610.10000':{reason:'medical',replacement:null}});
 let state=s.progress.read();assert.equal(state.completed,false);assert.equal(state.batch.payload.papers.length,4);assert.equal(state.pending_corrections.length,1);
 s.progress.correct({'2610.10000':{reason:'medical',replacement:{...batch('2026-10-24',20).payload.papers[0]}}});
 state=s.progress.read();assert.equal(state.batch.payload.papers.length,5);assert.equal(state.completed,false);assert.equal(state.batch.payload.papers[0].paper_id,first.batch.payload.papers[1].paper_id);assert.equal(s.map.get('favorites'),'private note');
});
