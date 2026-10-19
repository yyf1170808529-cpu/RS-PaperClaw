'use strict';
(function (root) {
  const KEY='rs-paperclaw-maritime-favorites-v2', LEGACY='rs-paperclaw-maritime-readings-v1';
  const PREFIX=KEY+':paper:', VERSION='3.7.2';
  const validId=id=>/^(?:\d{4}\.\d{4,5}|[a-zA-Z.-]+\/\d{7}|doi:10\.\d{4,9}\/\S+|openalex:W\d+)$/.test(id);
  const safeUrl=value=>/^https?:\/\//i.test(value||'')?value:'';
  function normalize(value) {
    let id=String(value||'').trim().replace(/^https?:\/\/(?:www\.)?arxiv.org\/(?:abs|pdf)\//i,'').replace(/^arxiv:/i,'').replace(/\.pdf$/i,'');
    if(/^\d{4}\.\d{4,5}v\d+$/.test(id)) id=id.replace(/v\d+$/,'');
    id=id.replace(/^https?:\/\/(?:dx\.)?doi.org\//i,'doi:');
    if(/^10\.\d{4,9}\//.test(id)) id='doi:'+id;
    if(/^doi:/i.test(id)) id=id.toLowerCase();
    return id;
  }
  function create(storage, events=root) {
    let aliases={},catalog=new Map();const listeners=new Set(),warnings=new Set();
    const now=()=>new Date().toISOString();
    function canonical(raw) {
      let id=normalize(raw);const seen=new Set();
      while(aliases[id]&&!seen.has(id)){seen.add(id);id=normalize(aliases[id]);}
      return id;
    }
    const key=id=>PREFIX+encodeURIComponent(normalize(id));
    function meta() {
      const raw=storage.getItem(KEY);
      if(!raw)return {schema_version:2,seen:[],aliases:{}};
      try {const m=JSON.parse(raw);if(m.schema_version!==2||!Array.isArray(m.seen))throw Error();return m;}
      catch {throw Error('收藏索引格式异常；请先导出恢复备份，原数据未覆盖。');}
    }
    function entries() {
      const rows=[];
      for(let i=0;i<storage.length;i++){
        const name=storage.key(i);if(!name?.startsWith(PREFIX))continue;
        try {const p=JSON.parse(storage.getItem(name));if(!validId(p.paper_id)||typeof p.note!=='string'||typeof p.title!=='string'||(p.note_history!==undefined&&(!Array.isArray(p.note_history)||p.note_history.some(n=>typeof n!=='string')))||[p.created_at,p.updated_at].some(t=>t!==undefined&&typeof t!=='string'))throw Error();rows.push(p);}
        catch {warnings.add('存在无法解析的收藏记录，可从恢复备份取回原文。');}
      }
      return rows;
    }
    function merge(a,b) {
      const latest=(a.updated_at||'')>(b.updated_at||'')?a:b,other=latest===a?b:a;
      const history=[...(a.note_history||[]),...(b.note_history||[])];
      if(other.note && other.note!==latest.note)history.push(other.note);
      return {...other,...latest,paper_id:canonical(a.paper_id),title:latest.title||other.title,
        original_url:latest.original_url||other.original_url,reading_url:latest.reading_url||other.reading_url,
        created_at:[a.created_at,b.created_at].filter(Boolean).sort()[0],note_history:[...new Set(history)]};
    }
    function all(includeInactive=false) {
      const rows=new Map();
      for(const p of entries()) {const id=canonical(p.paper_id);rows.set(id,rows.has(id)?merge(rows.get(id),p):{...p,paper_id:id});}
      return [...rows.values()].filter(p=>includeInactive||p.active!==false).sort((a,b)=>(a.created_at||'').localeCompare(b.created_at||'')||a.paper_id.localeCompare(b.paper_id));
    }
    function snapshot(p) {
      const id=canonical(p.paper_id||p.arxiv_id);if(!validId(id))throw Error('无效论文ID：'+id);
      const original=safeUrl(p.doi?'https://doi.org/'+p.doi:p.original_url||p.arxiv_url)||
        (id.startsWith('doi:')?'https://doi.org/'+id.slice(4):/^\d{4}\./.test(id)?'https://arxiv.org/abs/'+id:'');
      return {paper_id:id,title:p.title||'',original_url:original,
        reading_url:safeUrl(p.reading_url)||'https://yyf1170808529-cpu.github.io/RS-PaperClaw/maritime.html?paper='+encodeURIComponent(id)};
    }
    function changed(){for(const fn of [...listeners])fn();}
    function save(p){const previous=get(p.paper_id);p={...p,updated_at:new Date(Math.max(Date.now(),Date.parse(previous?.updated_at)||0)+1).toISOString()};storage.setItem(key(p.paper_id),JSON.stringify(p));changed();return p;}
    function get(raw){return all(true).find(p=>p.paper_id===canonical(raw));}
    function add(p){const s=snapshot(p),old=get(s.paper_id);return save({...s,...old,title:old?.title||s.title,original_url:old?.original_url||s.original_url,reading_url:old?.reading_url||s.reading_url,paper_id:s.paper_id,note:old?.note||'',created_at:old?.created_at||now(),updated_at:now(),active:true});}
    function note(p,text,expected) {
      const old=get(p.paper_id)||add(p),history=[...(old.note_history||[])];
      if(expected!==undefined&&old.note!==expected&&old.note!==text&&old.note)history.push(old.note);
      return save({...old,note:text,note_history:[...new Set(history)],updated_at:now()});
    }
    function remove(id){const p=get(id);if(p)save({...p,active:false,updated_at:now()});}
    function configure(papers=[],mapping={}) {
      const m=meta();aliases={...m.aliases,...mapping};catalog=new Map(papers.map(p=>[canonical(p.paper_id||p.arxiv_id),p]));
      m.aliases=aliases;const seen=new Set(m.seen),raw=storage.getItem(LEGACY);
      if(raw){
        try {
          const legacy=JSON.parse(raw);
          if(Array.isArray(legacy.favorites))for(const value of legacy.favorites){
            const id=canonical(value);
            if(!validId(id)){warnings.add('旧收藏含无法解析的ID，原记录保留在恢复备份中。');continue;}
            if(!seen.has(String(value))&&!get(id))add(catalog.get(id)||{paper_id:id});
            seen.add(String(value));
          }
        }catch {warnings.add('旧阅读备份无法解析；新收藏仍可使用，原文可导出恢复。');}
      }
      m.seen=[...seen];storage.setItem(KEY,JSON.stringify(m));
      // Keep old alias entries intact; a canonical copy combines notes safely.
      for(const p of all(true)){
        const source=catalog.get(p.paper_id),s=source?snapshot(source):{};
        const next={...p,title:p.title||s.title||'',original_url:p.original_url||s.original_url||'',reading_url:p.reading_url||s.reading_url||''};
        if(storage.getItem(key(p.paper_id))!==JSON.stringify(next))storage.setItem(key(p.paper_id),JSON.stringify(next));
      }
      changed();
    }
    function backup(){const raw={};for(let i=0;i<storage.length;i++){const k=storage.key(i);if(k===KEY||k===LEGACY||k?.startsWith(KEY+':'))raw[k]=storage.getItem(k);}return {schema_version:2,favorite_records:all(true),recovery:raw};}
    function restore(value) {
      const data=value.favorites_v2||value;
      let rows=data.favorite_records;
      if(!rows&&Array.isArray(value.favorites))rows=value.favorites.map(id=>({paper_id:id,note:''}));
      if(!Array.isArray(rows))throw Error('备份中没有收藏记录');
      for(const row of rows){if(!row||!validId(canonical(row.paper_id))||(row.note!==undefined&&typeof row.note!=='string')||(row.note_history!==undefined&&(!Array.isArray(row.note_history)||row.note_history.some(n=>typeof n!=='string')))||[row.created_at,row.updated_at].some(t=>t!==undefined&&typeof t!=='string'))throw Error('收藏备份记录格式错误；未导入。');}
      for(const row of rows){const s=snapshot({...catalog.get(canonical(row.paper_id)),...row}),stamp=now();
        const incoming={...row,...s,note:row.note||'',created_at:row.created_at||stamp,updated_at:row.updated_at||stamp,active:row.active!==false};
        const old=get(s.paper_id);save(old?merge(old,incoming):incoming);
      }
      // Recovery payload is retained locally, never executed or uploaded.
      if(data.recovery)storage.setItem(KEY+':import-recovery',JSON.stringify(data.recovery));
      return all().length;
    }
    function markdown() {
      return '# 我的论文收藏\n\n'+all().map(p=>`## ${p.title||p.paper_id}\n\n原文：${safeUrl(p.original_url)||safeUrl(p.reading_url)||'暂未获取'}\n\n${p.note?'收藏笔记：\n\n'+p.note+'\n':'（未填写笔记）\n'}`).join('\n');
    }
    function plainText(){return '我的论文收藏\n\n'+all().map(p=>`${p.title||p.paper_id}\n原文：${safeUrl(p.original_url)||safeUrl(p.reading_url)||'暂未获取'}\n收藏笔记：${p.note||'（未填写）'}\n`).join('\n');}
    function refresh(){try{aliases={...aliases,...meta().aliases};changed();}catch(e){warnings.add(e.message);}}
    events?.addEventListener?.('storage',refresh);events?.addEventListener?.('pageshow',refresh);events?.addEventListener?.('focus',refresh);
    return {configure,list:all,get,add,note,remove,backup,restore,markdown,plainText,canonical,
      preserveLegacy(raw){storage.setItem(KEY+':legacy-recovery:'+now(),raw);},
      subscribe(fn){listeners.add(fn);return()=>listeners.delete(fn);},warnings:()=>[...warnings]};
  }
  function download(name,text,type='text/markdown;charset=utf-8') {
    const url=URL.createObjectURL(new Blob([text],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function mount(holder,paper,store,message=()=>{}) {
    const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
    const button=el('button'),panel=el('details'),summary=el('summary','收藏笔记'),editor=el('textarea');
    editor.setAttribute('aria-label','收藏笔记：'+(paper.title||paper.paper_id));editor.style.minHeight='100px';editor.placeholder='可留空，支持纯文本和 Markdown';
    const save=el('button','保存笔记'),close=el('button','暂不填写'),cancel=el('button','取消收藏（保留笔记）'),preview=el('pre');
    panel.append(summary,editor,save,close,cancel,preview);holder.append(button,panel);let dirty=false,base='';
    function update(){const p=store.get(paper.paper_id||paper.arxiv_id);button.textContent=p&&p.active!==false?'已收藏':'收藏';panel.hidden=!p;
      if(!dirty){base=p?.note||'';editor.value=base;}preview.textContent=p?.note||'';
      if(p?.note_history?.length)preview.textContent+='\n\n已保留的其他笔记版本：\n'+p.note_history.join('\n\n');}
    function action(fn){try{fn();update();}catch(e){message('收藏保存失败：'+e.message);}}
    button.addEventListener('click',()=>action(()=>{store.add(paper);panel.hidden=false;panel.open=true;message('已收藏；笔记可稍后填写。');}));
    editor.addEventListener('input',()=>{dirty=true;});
    save.addEventListener('click',()=>action(()=>{store.note(paper,editor.value,base);dirty=false;message('收藏笔记已保存到本浏览器。');}));
    close.addEventListener('click',()=>{panel.open=false;});
    cancel.addEventListener('click',()=>action(()=>{store.remove(paper.paper_id||paper.arxiv_id);panel.open=false;message('已取消收藏，笔记仍保留；再次收藏即可恢复。');}));
    const off=store.subscribe(()=>{if(holder.isConnected===false){off();return;}update();});update();
  }
  function toolbar(holder,store,message=()=>{}) {
    const button=document.createElement('button');button.textContent='导出全部收藏';
    button.addEventListener('click',()=>{try{download('我的论文收藏_'+new Date(Date.now()+8*60*60*1000).toISOString().slice(0,10)+'.md',store.markdown());}catch(e){message(e.message);}});
    const copy=document.createElement('button');copy.textContent='复制全部收藏文本';
    const text=document.createElement('textarea');text.hidden=true;text.readOnly=true;text.setAttribute('aria-label','全部收藏纯文本');
    copy.addEventListener('click',async()=>{text.value=store.plainText();text.hidden=false;try{await navigator.clipboard.writeText(text.value);message('全部收藏已复制为纯文本，可直接粘贴。');}catch{text.focus();text.select();message('请长按文本区域全选复制。');}});
    const txt=document.createElement('button');txt.textContent='导出 TXT';txt.addEventListener('click',()=>download('我的论文收藏_'+new Date(Date.now()+8*60*60*1000).toISOString().slice(0,10)+'.txt',store.plainText(),'text/plain;charset=utf-8'));
    const json=document.createElement('button');json.textContent='导出收藏 JSON / 恢复原始数据';json.addEventListener('click',()=>download('maritime-favorites.json',JSON.stringify(store.backup(),null,2),'application/json'));
    const label=document.createElement('label');label.textContent='恢复收藏 JSON ';const input=document.createElement('input');input.type='file';input.accept='.json';
    input.addEventListener('change',async event=>{try{const f=event.target.files[0];if(f){store.restore(JSON.parse(await f.text()));message('收藏和笔记已合并恢复。');}}catch(e){message(e.message);}event.target.value='';});label.append(input);holder.append(button,json,label,copy,txt,text);
    const link=document.createElement('a');link.textContent='查看我的收藏';link.href=(typeof location!=='undefined'&&location.pathname?.includes('/maritime-data/mobile/')?'../../':'')+'maritime.html?view=favorites&v=3.8';holder.append(link);
  }
  const api={VERSION,KEY,LEGACY,normalize,create,mount,toolbar,download};
  if(typeof module!=='undefined')module.exports=api;else root.MaritimeFavorites=api;
  if(typeof document!=='undefined'&&document.getElementById('daily-favorites')){
    const status=document.getElementById('favorite-message'),message=text=>{status.textContent=text;};
    try{
      const data=JSON.parse(document.getElementById('daily-favorites-data').textContent),store=create(localStorage);
      store.configure(data.papers,data.aliases);toolbar(document.getElementById('daily-favorites'),store,message);
      const papers=new Map(data.papers.map(p=>[p.paper_id,p]));
      for(const holder of document.querySelectorAll('[data-favorite-paper]'))mount(holder,papers.get(holder.dataset.favoritePaper),store,message);
      message(store.warnings().join(' '));
      if(data.date && typeof setInterval==='function'){
        const fresh=document.createElement('a');fresh.hidden=true;document.getElementById('daily-favorites').append(fresh);
        async function check(){
          try{
            const prefix=location.pathname.includes('/maritime-data/mobile/')?'../../':'';
            const response=await fetch(prefix+'maritime-data/mobile/publication-status.json',{cache:'no-cache'});
            if(!response.ok)return;
            const status=await response.json();
            if(status.published_date>data.date){fresh.textContent='有新日报，保存笔记后点击查看';fresh.href=prefix+'maritime-daily.html?v=3.8';fresh.hidden=false;}
          }catch{}
        }
        setInterval(check,300000); // Never reload a page containing an unsaved note.
      }
    }catch(e){message('收藏暂不可用：'+e.message+'；原数据未清空。');}
  }
})(typeof window!=='undefined'?window:globalThis);
