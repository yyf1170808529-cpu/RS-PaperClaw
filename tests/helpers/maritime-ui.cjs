const vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const ROOT=path.join(__dirname,'../..');
function hub(initial){return {storage:initial||new Map(),listeners:new Set()};}
async function setupUI(saved,dataset,search='',options={}) {
  class Element {
    constructor(tag){this.tag=tag;this.children=[];this.value='';this.textContent='';this.handlers={};this.style={};this.dataset={};}
    append(...items){for(const item of items){item.parentNode=this;this.children.push(item);}}
    replaceChildren(...items){this.children=items;}
    addEventListener(name,fn){this.handlers[name]=fn;}
    setAttribute(name,value){this[name]=value;}
    click(){return this.handlers.click?.();}
    focus(){} select(){}
    closest(tag){let node=this;while(node&&node.tag!==tag)node=node.parentNode;return node;}
    querySelector(selector){return this.children.find(n=>selector==='[data-paper-panels]'&&n.dataset.paperPanels);}
  }
  const nodes=new Map(['date','topic','level','sort','search','summary','report','message','papers','export','import','window','quality','bucket','language','favorite-tools','favorites-status','favorite-message'].map(id=>[id,new Element(id)]));
  const shared=options.hub||hub();const storage=shared.storage;
  if(saved!==undefined)storage.set('rs-paperclaw-maritime-readings-v1',saved);
  const eventHandlers=new Map();shared.listeners.add((key)=>eventHandlers.get('storage')?.({key}));
  let copied='';const downloaded=[],holders=[],fetched=[];
  const p=(id,topics,score,date,level)=>({arxiv_id:id,title:'Visual fusion',abstract:'Matching methods',authors:['Alice'],published:date,arxiv_url:`https://arxiv.org/abs/${id}`,pdf_url:`https://arxiv.org/pdf/${id}`,assessment:{topics,score,level,reasons:['cross-modal'],applications:['通用计算机视觉']}});
  dataset=dataset||{papers:[p('2610.00001',['A','C'],22,'2026-10-10','high'),p('2610.00002',['D'],12,'2026-10-11','transfer')],topics:{A:'Fusion',D:'Methods'},days:{'2026-10-10':{candidate_ids:['2610.00001']}},prompt_template:'{{title}}\n{{abstract}}\n{{authors}}'};
  for(const p of dataset.papers)p.assessment&&(p.assessment.applications=['通用计算机视觉']);
  if(options.daily){
    nodes.set('daily-favorites',new Element('div'));
    const data=new Element('script');data.textContent=JSON.stringify(dataset);nodes.set('daily-favorites-data',data);
    for(const p of dataset.papers){
      const el=new Element('div');el.dataset.favoritePaper=p.paper_id;holders.push(el);
      if(options.inline){
        const article=new Element('article'),actions=new Element('div'),panels=new Element('div');
        el.dataset.favoriteInline='1';panels.dataset.paperPanels=p.paper_id;
        actions.append(el);article.append(actions,panels);nodes.get('papers').append(article);
      }else nodes.get('papers').append(el);
    }
  }
  const context=vm.createContext({console,Date,Set,Map,JSON,Object,Error,Promise,URLSearchParams,
    document:{getElementById:id=>nodes.get(id),createElement:tag=>new Element(tag),querySelectorAll:()=>holders},
    localStorage:{get length(){return storage.size;},key:i=>[...storage.keys()][i],getItem:key=>storage.get(key)??null,setItem:(key,value)=>{storage.set(key,value);for(const fn of shared.listeners)fn(key);}},
    addEventListener:(name,fn)=>eventHandlers.set(name,fn),
    navigator:{clipboard:{writeText:async text=>{copied=text;}}},location:{search,pathname:options.daily?'/RS-PaperClaw/maritime-daily.html':'/RS-PaperClaw/maritime.html'},
    fetch:async url=>{fetched.push(url);return options.fetch?options.fetch(url):{ok:true,json:async()=>dataset};},
    URL:{createObjectURL:blob=>{downloaded.push(blob.parts[0]);return 'blob:test';},revokeObjectURL(){}},
    Blob:class{constructor(parts){this.parts=parts;}},setTimeout:fn=>fn(),setInterval:options.setInterval,
  });
  if(!options.oldSource)vm.runInContext(fs.readFileSync(path.join(ROOT,'docs/maritime_favorites.js'),'utf8'),context);
  if(!options.daily){
    vm.runInContext(fs.readFileSync(path.join(ROOT,'docs/maritime_prompt.js'),'utf8'),context);
    vm.runInContext(options.oldSource||fs.readFileSync(path.join(ROOT,'docs/maritime.js'),'utf8'),context);
  }
  await new Promise(resolve=>setImmediate(resolve));
  const walk=element=>[element,...element.children.flatMap(walk)];
  return {nodes,storage,context,shared,downloaded,fetched,copied:()=>copied,find:label=>walk(nodes.get('papers')).find(e=>e.textContent===label),elements:()=>walk(nodes.get('papers')),events:eventHandlers};
}
module.exports={setupUI,hub};
