const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {filterPapers,makePrompt,validateBackup,readingFor} = require('../docs/maritime.js');
const p = (id, topics, score, date, level='transfer') => ({arxiv_id:id,title:'Visual fusion',abstract:'Matching methods',authors:['Alice'],published:date,
  arxiv_url:`https://arxiv.org/abs/${id}`,pdf_url:`https://arxiv.org/pdf/${id}`,assessment:{topics,score,level,reasons:['cross-modal']}});
const papers = [p('2610.00001',['A','C'],22,'2026-10-10','high'),p('2610.00002',['D'],12,'2026-10-11'),p('2610.00003',[],0,'2026-10-11','excluded')];
test('filters topics, date membership, level, authors, reasons and sorting',()=>{
  const days={'2026-10-10':{candidate_ids:['2610.00001']}};
  assert.equal(filterPapers(papers,{topic:'C'},days).length,1);
  assert.equal(filterPapers(papers,{date:'2026-10-10'},days).length,1);
  assert.equal(filterPapers(papers,{level:'excluded'},days).length,1);
  assert.equal(filterPapers(papers,{search:'alice'},days).length,2);
  assert.equal(filterPapers(papers,{search:'cross-modal'},days).length,2);
  assert.equal(filterPapers(papers,{sort:'date'},days)[0].arxiv_id,'2610.00002');
  assert.equal(filterPapers(papers,{sort:'score'},days)[0].arxiv_id,'2610.00001');
  const tagged=papers.map((p,i)=>({...p,recommendation:{bucket:i===0?'water':'land'}}));
  assert.equal(filterPapers(tagged,{bucket:'water'},days).length,1);
});
test('prompt contains exact metadata and PDF evidence limitations',()=>{
  const template=fs.readFileSync(path.join(__dirname,'../skills/rs-paper-pipeline/scripts/prompts/maritime_analysis.md'),'utf8');
  const paper={...papers[0],abstract:'Literal {{title}} inside abstract'};
  const prompt=makePrompt(template,paper);
  for(const value of [paper.title,paper.abstract,paper.arxiv_url,paper.pdf_url,'Alice','需上传全文核实','Q/K/V']) assert.ok(prompt.includes(value));
  assert.ok(!prompt.includes('{{authors}}'));
  assert.ok(makePrompt(template,{...paper,open_access_url:'https://example.org/official.pdf'}).includes('PDF：https://example.org/official.pdf'));
});
test('analysis JSON backup round trip, Unicode, exact Markdown, reading override',()=>{
  const record={analysis:'# 分析\n\n$x$\n<script>alert(1)</script>',state:'值得精读',updated_at:'2026-10-12'};
  const backup={schema_version:1,readings:{'2610.00001':record}};
  const readings=validateBackup(JSON.parse(JSON.stringify(backup)));
  assert.deepEqual(readings['2610.00001'],record);
  assert.deepEqual(readingFor({...papers[0],reading:{analysis:'old'}},readings),record);
  assert.throws(()=>validateBackup({schema_version:2,readings:{}}));
  assert.throws(()=>validateBackup({schema_version:1,readings:{'bad':record}}));
  assert.throws(()=>validateBackup({schema_version:1,readings:{'2610.00001':{...record,state:'invalid'}}}));
});
test('untrusted text and Markdown use safe text nodes, no HTML execution',()=>{
  const source=fs.readFileSync(path.join(__dirname,'../docs/maritime.js'),'utf8');
  assert.ok(!source.includes('innerHTML'));
  assert.ok(source.includes('preview.textContent = editor.value'));
  assert.ok(source.includes('navigator.clipboard.writeText(prompt)'));
});

// Exercise the actual event wiring with a lightweight DOM adapter, no browser dependency.
async function setupUI(saved) {
  const vm = require('node:vm');
  class Element {
    constructor(tag) {this.tag=tag;this.children=[];this.value='';this.textContent='';this.handlers={};}
    append(...items) {this.children.push(...items);}
    replaceChildren(...items) {this.children=items;}
    addEventListener(name,handler) {this.handlers[name]=handler;}
    setAttribute() {}
    click() {return this.handlers.click?.();}
    focus() {}
    select() {}
  }
  const nodes=new Map(['date','topic','level','sort','search','summary','report','message','papers','export','import'].map(id=>[id,new Element(id)]));
  const storage=new Map(saved ? [['rs-paperclaw-maritime-readings-v1',saved]] : []);
  const downloaded=[];let copied='';
  const dataset={papers:papers.slice(0,2),topics:{A:'Fusion',D:'Methods'},days:{'2026-10-10':{candidate_ids:['2610.00001'],candidate_count:1,selected_count:1,high_count:1,topic_counts:{A:1}}},prompt_template:'{{title}}\n{{abstract}}\n{{authors}}'};
  for(const p of dataset.papers) p.assessment.applications=['通用计算机视觉'];
  const context=vm.createContext({console,Date,Set,JSON,Object,Error,Promise,
    document:{getElementById:id=>nodes.get(id),createElement:tag=>new Element(tag)},
    localStorage:{getItem:key=>storage.get(key),setItem:(key,value)=>storage.set(key,value)},
    navigator:{clipboard:{writeText:async text=>{copied=text;}}},
    fetch:async()=>({ok:true,json:async()=>dataset}),
    URL:{createObjectURL:blob=>{downloaded.push(blob.parts[0]);return 'blob:test';},revokeObjectURL(){}},
    Blob:class{constructor(parts){this.parts=parts;}},setTimeout:fn=>fn(),
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../docs/maritime.js'),'utf8'),context);
  await new Promise(resolve=>setImmediate(resolve));
  const walk=element=>[element,...element.children.flatMap(walk)];
  return {nodes,storage,downloaded,copied:()=>copied,find:(label)=>walk(nodes.get('papers')).find(e=>e.textContent===label),
    elements:()=>walk(nodes.get('papers'))};
}
test('UI copies exact prompt, saves analysis and state, exports and restores JSON',async()=>{
  const app=await setupUI();
  assert.equal(app.nodes.get('papers').children.length,2);
  assert.equal(app.find('原始论文').href,papers[0].pdf_url);
  assert.equal(app.find('ChatGPT 网页').href,'https://chatgpt.com/');
  assert.equal(app.find('准备 PDF 全文与本地精读命令'),undefined);
  await app.find('复制分析 Prompt').click();
  assert.equal(app.copied(),'Visual fusion\nMatching methods\nAlice');
  const editor=app.elements().find(e=>e.tag==='textarea' && !e.readOnly);
  const analysis='# 核心方法\n\n<script>never execute</script>\n$x$';editor.value=analysis;
  app.find('保存分析').click();
  assert.ok(app.elements().some(e=>e.tag==='pre' && e.textContent===analysis));
  const state=app.elements().find(e=>e.tag==='select');state.value='已精读';state.handlers.change();
  app.nodes.get('export').click();
  const backup=JSON.parse(app.downloaded.at(-1));
  assert.equal(backup.readings['2610.00001'].analysis,analysis);
  assert.equal(backup.readings['2610.00001'].state,'已精读');
  const other=await setupUI();
  await other.nodes.get('import').handlers.change({target:{files:[{text:async()=>JSON.stringify(backup)}],value:'backup'}});
  assert.ok(other.elements().some(e=>e.tag==='pre' && e.textContent===analysis));
  assert.equal(other.elements().find(e=>e.tag==='select').value,'已精读');
  other.nodes.get('date').value='2026-10-10';other.nodes.get('date').handlers.input();
  assert.equal(other.nodes.get('papers').children.length,1);
});
test('corrupt storage is preserved and recoverable; invalid import is atomic',async()=>{
  const app=await setupUI('corrupt-json');
  app.find('保存分析').click();
  assert.equal(app.storage.get('rs-paperclaw-maritime-readings-v1'),'corrupt-json');
  app.nodes.get('export').click();
  assert.equal(app.downloaded.at(-1),'corrupt-json');
  await app.nodes.get('import').handlers.change({target:{files:[{text:async()=>'{"schema_version":2}'}],value:'bad'}});
  assert.equal(app.storage.get('rs-paperclaw-maritime-readings-v1'),'corrupt-json');
});

test('V2 JIF/CAS union filters only verified published journals and supports DOI backup',()=>{
  const formal={...papers[0],paper_id:'doi:10.1234/a',arxiv_id:null,venue_type:'journal',publication_status:'published',quality:{cas_one:false,jcr_q1:true,both:false,high_journal:true,status:'verified'}};
  assert.equal(filterPapers([formal],{quality:'high_journal'},{}).length,1);
  assert.equal(filterPapers([formal],{quality:'jcr_q1'},{}).length,1);
  assert.equal(filterPapers([formal],{quality:'cas_one'},{}).length,0);
  assert.equal(filterPapers([formal],{quality:'both'},{}).length,0);
  assert.equal(filterPapers([{...formal,publication_status:'unknown'}],{quality:'high_journal'},{}).length,0);
  assert.ok(validateBackup({schema_version:1,readings:{'doi:10.1234/a':{analysis:'# 正文',state:'已浏览'}}})['doi:10.1234/a']);
});
test('V2 windows and independent recommendation ranking reduce low priority papers',()=>{
  const low={...papers[0],recommendation:{low_priority:true,direct_relevance:1,maritime:false,method_transfer_signal:true,section:'candidate'}};
  const maritime={...papers[1],recommendation:{low_priority:false,direct_relevance:3,maritime:true,method_transfer_signal:false,section:'preprints'}};
  assert.equal(filterPapers([low,maritime],{sort:'score'}, {})[0].arxiv_id,maritime.arxiv_id);
  assert.equal(filterPapers([low,maritime],{window:'7',today:'2026-10-12'}, {}).length,2);
  assert.equal(filterPapers([low,maritime],{window:'1',today:'2026-10-12'}, {}).length,0);
  assert.equal(filterPapers([low,maritime],{section:'candidate'}, {}).length,1);
});
