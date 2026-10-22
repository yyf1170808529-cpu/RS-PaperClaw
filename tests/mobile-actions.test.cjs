const {test}=require('node:test'),assert=require('node:assert/strict');
const {setupUI}=require('./helpers/maritime-ui.cjs');
const fs=require('node:fs'),path=require('node:path');
const walk=n=>[n,...n.children.flatMap(walk)];
const p={paper_id:'2610.12871',title:'ROSETTA',original_url:'https://arxiv.org/abs/2610.12871'};

test('inline favorites keep only their button in the action row and notes below',async()=>{
  const app=await setupUI(undefined,{papers:[p]},'',{daily:true,inline:true});
  const article=app.nodes.get('papers').children[0],actions=article.children[0],panels=article.children[1];
  const button=walk(actions).find(n=>n.tag==='button');
  assert.equal(button.textContent,'☆收藏');assert.ok(!walk(actions).some(n=>n.tag==='textarea'));
  await button.click();assert.equal(button.textContent,'★已收藏');
  const detail=panels.children.find(n=>n.tag==='details');assert.equal(detail.open,true);
  walk(detail).find(n=>n.textContent==='暂不填写').click();
  assert.equal(detail.open,false);assert.equal(button.textContent,'★已收藏');
  await button.click();const editor=walk(detail).find(n=>n.tag==='textarea');
  editor.value='中文收藏笔记 **保留**';editor.handlers.input();walk(detail).find(n=>n.textContent==='保存笔记').click();
  const store=app.context.MaritimeFavorites.create(app.context.localStorage);store.configure([p]);
  assert.equal(store.get(p.paper_id).note,'中文收藏笔记 **保留**');
});

test('actual generated action rows include all four controls in one nowrap flex container',()=>{
  const html=fs.readFileSync(path.join(__dirname,'../docs/maritime-daily.html'),'utf8');
  const actions=[...html.matchAll(/<div class="paper-actions">(.*?)<\/div>/g)].map(m=>m[1]);
  assert.equal(actions.length,5);
  for(const row of actions){
    for(const text of ['原文','阅读与笔记','Prompt','data-favorite-inline="1"'])assert.ok(row.includes(text));
    assert.ok(!row.includes('<textarea'));assert.ok(!row.includes('<details'));
  }
  assert.match(html,/\.paper-actions\{display:flex;[^}]*flex-wrap:nowrap/);
  assert.ok(html.includes('@media(max-width:360px)'));
  assert.equal((html.match(/第一作者单位：/g)||[]).length,5);
  assert.equal((html.match(/<p>作者：/g)||[]).length,5);
});
