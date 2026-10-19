const {test}=require('node:test'),assert=require('node:assert/strict');
const {setupUI,hub}=require('./helpers/maritime-ui.cjs');
const F=require('../docs/maritime_favorites.js');
const ff={paper_id:'2610.01750',title:'FFBL-Coop: Association-Decoupled Cooperative 3D Multi-Object Tracking',original_url:'https://arxiv.org/abs/2610.01750'};
const snap={paper_id:'2610.09700',title:'What Makes Synthetic Hard Negatives Work in Vision-Language Pretraining?',original_url:'https://arxiv.org/abs/2610.09700'};
const walk=n=>[n,...n.children.flatMap(walk)],find=(n,text)=>walk(n).find(x=>x.textContent===text);
const dataset=()=>({papers:[ff,snap].map(p=>({...p,authors:[],abstract:'',published:'2026-10-01',assessment:{score:0,level:'excluded',topics:[],reasons:[]},resource_type:'preprint'})),topics:{},aliases:{},days:{'2026-10-15':{recommendation_view:{paper_ids:[]}}},prompt_template:'{{title}}'});
const storageApi=map=>({get length(){return map.size;},key:i=>[...map.keys()][i],getItem:k=>map.get(k)??null,setItem:(k,v)=>map.set(k,v)});

test('daily → library favorites → daily preserves empty note, ignores all filters and survives reopening',async()=>{
  const shared=hub();const daily=await setupUI(undefined,{papers:[ff,snap],aliases:{}},'',{hub:shared,daily:true});
  find(daily.nodes.get('papers').children[0],'收藏').click();
  find(daily.nodes.get('papers').children[0],'暂不填写').click();
  const full=await setupUI(undefined,dataset(),'',{hub:shared});
  for(const [id,v] of Object.entries({date:'2026-10-15',quality:'cas_one',bucket:'water',level:'high',search:'no-match',window:'favorites'}))full.nodes.get(id).value=v;
  full.nodes.get('window').handlers.input();
  assert.equal(full.nodes.get('summary').textContent,'本浏览器收藏 1 篇');
  assert.ok(full.find(ff.title));
  const reopened=await setupUI(undefined,{papers:[ff,snap],aliases:{}},'',{hub:shared,daily:true});
  assert.equal(find(reopened.nodes.get('papers').children[0],'已收藏').textContent,'已收藏');
  assert.equal(reopened.fetched.length,0);
});

test('note edits synchronize in both pages and export all snapshots without loading library on daily',async()=>{
  const shared=hub();const daily=await setupUI(undefined,{papers:[ff,snap],aliases:{}},'',{hub:shared,daily:true});
  for(const holder of daily.nodes.get('papers').children)find(holder,'收藏').click();
  const holder=daily.nodes.get('papers').children[1],editor=walk(holder).find(n=>n.tag==='textarea');
  const note='中文笔记 **困难负样本**\n- 尝试视觉–AIS\n<script>不得执行</script>';
  editor.value=note;editor.handlers.input();find(holder,'保存笔记').click();
  const full=await setupUI(undefined,dataset(),'',{hub:shared});full.nodes.get('window').value='favorites';full.nodes.get('window').handlers.input();
  const edit=full.elements().find(n=>n.tag==='textarea'&&n['aria-label']?.includes(snap.title)&&n['aria-label'].startsWith('收藏笔记'));
  assert.equal(edit.value,note);edit.value=note+'\n完整库补记';edit.handlers.input();
  const article=full.nodes.get('papers').children.find(n=>walk(n).includes(edit));find(article,'保存笔记').click();
  assert.equal(editor.value,note+'\n完整库补记');
  daily.nodes.get('daily-favorites').children[0].click();const md=daily.downloaded.at(-1);
  for(const value of [ff.title,ff.original_url,snap.title,snap.original_url,note+'\n完整库补记'])assert.ok(md.includes(value));
  assert.equal(daily.fetched.length,0);
  assert.ok(!require('fs').readFileSync(require('path').join(__dirname,'../docs/maritime_favorites.js'),'utf8').includes('innerHTML'));
});

test('combined JSON preserves independent favorite notes, readings, and restores on daily',async()=>{
  const old={schema_version:1,readings:{[ff.paper_id]:{state:'已精读',analysis:'# 完整分析'}},favorites:[ff.paper_id]};
  const full=await setupUI(JSON.stringify(old),dataset());full.nodes.get('window').value='favorites';full.nodes.get('window').handlers.input();
  full.nodes.get('export').click();const backup=JSON.parse(full.downloaded.at(-1));
  assert.equal(backup.readings[ff.paper_id].analysis,'# 完整分析');
  const daily=await setupUI(undefined,{papers:[ff,snap]},'',{daily:true});
  const label=daily.nodes.get('daily-favorites').children[2],input=label.children[0];
  await input.handlers.change({target:{files:[{text:async()=>JSON.stringify(backup)}],value:'backup'}});
  assert.ok(find(daily.nodes.get('papers').children[0],'已收藏'));
  assert.equal(backup.favorites_v2.favorite_records[0].title,ff.title);
});

test('bad readings do not block migrating valid favorites; malformed legacy remains recoverable',async()=>{
  const old=JSON.stringify({schema_version:1,readings:{[ff.paper_id]:{state:'待读'}},favorites:['invalid',ff.paper_id]});
  const full=await setupUI(old,dataset());full.nodes.get('window').value='favorites';full.nodes.get('window').handlers.input();
  assert.equal(full.nodes.get('summary').textContent,'本浏览器收藏 1 篇');assert.equal(full.storage.get(F.LEGACY),old);
  const map=new Map([[F.LEGACY,'{broken JSON']]);const store=F.create(storageApi(map),{});store.configure([snap]);store.add(snap);
  assert.equal(store.list().length,1);assert.equal(store.backup().recovery[F.LEGACY],'{broken JSON');
  store.configure([snap]);assert.equal(store.list().length,1);
  await full.nodes.get('import').handlers.change({target:{files:[{text:async()=>JSON.stringify({schema_version:1,readings:{}})}],value:'repair'}});
  assert.ok([...full.storage].some(([k,v])=>k.includes(':legacy-recovery:')&&v===old));
});

test('alias notes merge without destruction; missing library papers remain visible and exportable',async()=>{
  const old='doi:10.1234/snap';const map=new Map();const store=F.create(storageApi(map),{});store.configure();
  store.add({...snap,paper_id:old});store.note({paper_id:old},'DOI笔记');store.add(snap);store.note(snap,'arXiv笔记');
  store.configure([snap],{[old]:snap.paper_id});assert.equal(store.list().length,1);
  const row=store.list()[0];assert.ok([row.note,...row.note_history].includes('DOI笔记'));assert.ok([row.note,...row.note_history].includes('arXiv笔记'));
  const full=await setupUI(undefined,{papers:[],topics:{},days:{},aliases:{[old]:snap.paper_id},prompt_template:''},'',{hub:hub(map)});
  full.nodes.get('window').value='favorites';full.nodes.get('window').handlers.input();
  assert.equal(full.nodes.get('summary').textContent,'本浏览器收藏 1 篇');assert.ok(full.find(snap.title));assert.ok(full.nodes.get('favorites-status').textContent.includes('1 篇暂未匹配'));
});

test('separate stale tabs cannot overwrite another paper; cancellation retains notes across migration',()=>{
  const map=new Map([[F.LEGACY,JSON.stringify({schema_version:1,readings:{},favorites:[ff.paper_id]})]]);
  const a=F.create(storageApi(map),{}),b=F.create(storageApi(map),{});a.configure([ff,snap]);b.configure([ff,snap]);
  a.note(ff,'保留笔记');b.add(snap);b.note(snap,'另篇笔记');a.remove(ff.paper_id);
  a.configure([ff,snap]);assert.equal(a.list().length,1);assert.equal(a.get(ff.paper_id).note,'保留笔记');
  a.add(ff);assert.equal(b.get(ff.paper_id).note,'保留笔记');assert.equal(a.get(snap.paper_id).note,'另篇笔记');
});

test('favorites work before large library download completes and after network failure; plain text includes all notes',async()=>{
  const shared=hub();const daily=await setupUI(undefined,{papers:[ff,snap]},'',{hub:shared,daily:true});
  for(const holder of daily.nodes.get('papers').children)find(holder,'收藏').click();
  for(const fetch of [()=>new Promise(()=>{}),async()=>{throw Error('offline');}]){
    const full=await setupUI(undefined,dataset(),'?view=favorites',{hub:shared,fetch});
    assert.equal(full.nodes.get('summary').textContent,'本浏览器收藏 2 篇');
    assert.ok(full.find(ff.title));assert.ok(full.find(snap.title));
    await find(full.nodes.get('favorite-tools'),'复制全部收藏文本').click();
    assert.ok(full.copied().includes(ff.title));assert.ok(full.copied().includes(snap.original_url));
    assert.ok(!full.copied().includes('## '));
    find(full.nodes.get('favorite-tools'),'导出 TXT').click();assert.equal(full.downloaded.at(-1),full.copied());
  }
});

test('lightweight same-day digest revision check preserves an unsaved favorite note',async()=>{
  let check;
  const daily=await setupUI(undefined,{date:'2026-10-19',revision:'old',papers:[ff]},'',{
    daily:true,setInterval:fn=>{check=fn;},
    fetch:async()=>({ok:true,json:async()=>({published_date:'2026-10-19',published_revision:'new'})})
  });
  const holder=daily.nodes.get('papers').children[0];find(holder,'收藏').click();
  const editor=walk(holder).find(n=>n.tag==='textarea');editor.value='尚未保存 **中文笔记**';editor.handlers.input();
  await check();
  const link=find(daily.nodes.get('daily-favorites'),'有新日报，保存笔记后点击查看');
  assert.equal(link.hidden,false);assert.ok(link.href.includes('update=new'));
  assert.equal(editor.value,'尚未保存 **中文笔记**');
  assert.deepEqual(daily.fetched,['maritime-data/mobile/publication-status.json']);
});
