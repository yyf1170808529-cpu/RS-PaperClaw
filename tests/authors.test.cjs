const test=require('node:test'),assert=require('node:assert/strict');
const {label}=require('../docs/maritime_authors.js');
test('authors show first and only explicitly verified correspondence without losing full order',()=>{
 const p={authors:['First','Second','Third','Last']};assert.equal(label(p),'First');
 p.corresponding_authors=['Last'];assert.equal(label(p),'First');
 p.corresponding_author_verified=true;p.corresponding_author_source='OpenAlex explicit flag';assert.equal(label(p),'First · Corresponding: Last');
 p.corresponding_authors=['First','Second','Third','Last'];assert.equal(label(p),'First（通讯作者） · Corresponding: Second、Third 等');assert.deepEqual(p.authors,['First','Second','Third','Last']);
});
const {setupUI}=require('./helpers/maritime-ui.cjs');
test('desktop card uses compact verified authors and preserves metadata for prompt',async()=>{
 const p={paper_id:'2610.12345',arxiv_id:'2610.12345',title:'Visual matching',authors:['First','Second','Correspondent'],corresponding_authors:['Correspondent'],corresponding_author_verified:true,corresponding_author_source:'Official',published:'2026-11-05',abstract:'Matching',assessment:{topics:[],score:20,level:'high',reasons:[]}};
 const app=await setupUI(undefined,{papers:[p],days:{},topics:{},prompt_template:'{{authors}}'});
 assert.ok(app.elements().some(e=>e.textContent==='First · Corresponding: Correspondent · 2026-11-05'));
 assert.deepEqual(p.authors,['First','Second','Correspondent']);
});
