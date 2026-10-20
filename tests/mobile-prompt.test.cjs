const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const {makePrompt}=require('../docs/maritime_prompt.js');
const desktop=require('../docs/maritime.js');
const {mount}=require('../docs/maritime_daily_prompt.js');
const template=fs.readFileSync(path.join(__dirname,'../skills/rs-paper-pipeline/scripts/prompts/maritime_analysis.md'),'utf8');
const papers=[{paper_id:'2610.01750',title:'FFBL-Coop',authors:['Alice','Bob'],published:'2026-10-02',arxiv_url:'https://arxiv.org/abs/2610.01750',pdf_url:'https://arxiv.org/pdf/2610.01750',doi:'10.1234/a',original_url:'https://doi.org/10.1234/a',venue:'Verified venue',abstract:'Complete English abstract\nSecond paragraph.'},
  {paper_id:'2610.09700',title:'SNAP',authors:['Carol'],published:'2026-10-13',abstract:'A different complete abstract',original_url:'https://arxiv.org/abs/2610.09700'}];

function ui(data,clipboard){
  class Element{
    constructor(tag){this.tag=tag;this.children=[];this.dataset={};this.handlers={};}
    append(...nodes){for(const n of nodes){n.parentNode=this;this.children.push(n);}}
    setAttribute(key,value){this[key]=value;}
    addEventListener(name,fn){this.handlers[name]=fn;}
    click(){return this.handlers.click();}
  }
  const parents=data.papers.map(()=>new Element('p'));
  const buttons=data.papers.map((p,i)=>{const b=new Element('button');b.dataset.promptPaper=p.paper_id;parents[i].append(b);return b;});
  const doc={getElementById:()=>({textContent:JSON.stringify(data)}),querySelectorAll:()=>buttons,createElement:tag=>new Element(tag)};
  mount(doc,{clipboard},makePrompt);return {parents,buttons};
}

test('mobile and desktop use the identical function and unchanged full template with PDF',async()=>{
  assert.equal(makePrompt,desktop.makePrompt);
  let copied='';const app=ui({papers,prompt_template:template},{writeText:async text=>{copied=text;}});
  assert.ok(!app.parents[0].children.some(n=>n.tag==='details'));
  await app.buttons[0].click();
  assert.equal(copied,desktop.makePrompt(template,papers[0]));
  for(const value of [papers[0].title,'Alice, Bob',papers[0].published,papers[0].arxiv_url,papers[0].pdf_url,papers[0].doi,papers[0].original_url,papers[0].venue,papers[0].abstract,'Q/K/V','13.'])assert.ok(copied.includes(value),value);
  assert.equal(app.parents[0].children.find(n=>n.role==='status').textContent,'已复制');
  assert.ok(!copied.includes('SNAP'));
});

test('no PDF retains desktop short fulltext request and each button copies its own paper',async()=>{
  let copied='';const app=ui({papers,prompt_template:template},{writeText:async text=>{copied=text;}});
  await app.buttons[1].click();
  assert.equal(copied,desktop.makePrompt(template,papers[1]));
  assert.ok(copied.includes('SNAP'));assert.ok(copied.includes(papers[1].abstract));assert.ok(copied.includes('上传 PDF'));
  assert.ok(!copied.includes('13.'));assert.ok(!copied.includes('FFBL-Coop'));
});

test('unavailable clipboard or denied permission expands a readonly manual copy box',async()=>{
  for(const clipboard of [undefined,{writeText:async()=>{throw Error('denied');}}]){
    const app=ui({papers,prompt_template:template},clipboard);
    await app.buttons[0].click();await app.buttons[0].click();
    const details=app.parents[0].children.filter(n=>n.tag==='details');
    assert.equal(details.length,1);assert.equal(details[0].open,true);
    const area=details[0].children.find(n=>n.tag==='textarea');
    assert.equal(area.readOnly,true);assert.equal(area.value,desktop.makePrompt(template,papers[0]));
    await app.buttons[1].click();
    const short=app.parents[1].children.find(n=>n.tag==='details').children.find(n=>n.tag==='textarea');
    assert.equal(short.value,desktop.makePrompt(template,papers[1]));assert.ok(!short.value.includes('13.'));
  }
});

test('current generated mobile HTML has per-paper buttons and self-contained matching metadata',async()=>{
  const html=fs.readFileSync(path.join(__dirname,'../docs/maritime-daily.html'),'utf8');
  const data=JSON.parse(html.match(/<script id="daily-prompt-data" type="application\/json">(.*?)<\/script>/s)[1]);
  assert.equal(data.prompt_template.replace(/\r\n/g,'\n'),template.replace(/\r\n/g,'\n'));
  const ids=[...html.matchAll(/data-prompt-paper="([^"]+)"/g)].map(m=>m[1]);
  assert.equal(ids.length,data.papers.length);assert.equal(ids.length,5);
  assert.deepEqual(ids,data.papers.map(p=>p.paper_id));
  let copied='';const app=ui(data,{writeText:async text=>{copied=text;}});
  for(let i=0;i<ids.length;i++){
    await app.buttons[i].click();assert.ok(copied.includes(data.papers[i].title));
    assert.ok(copied.includes(data.papers[i].abstract));assert.ok(data.papers[i].authors.length>0);
  }
});
