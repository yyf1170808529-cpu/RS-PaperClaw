'use strict';
(function(root) {
  const KEY='rs-paperclaw-maritime-daily-reading-v1';
  const beijingDate=(now=new Date())=>new Date(now.getTime()+8*3600000).toISOString().slice(0,10);
  const normalize=value=>{let id=String(value||'').trim().replace(/^https?:\/\/(?:www\.)?arxiv.org\/(?:abs|pdf)\//i,'').replace(/^arxiv:/i,'').replace(/\.pdf$/i,'');if(/^\d{4}\.\d{4,5}v\d+$/i.test(id))id=id.replace(/v\d+$/i,'');return id.replace(/^https?:\/\/(?:dx\.)?doi.org\//i,'doi:').replace(/^(10\.\d{4,9}\/)/,'doi:$1').toLowerCase();};
  function identities(batch) {
    const aliases=batch.aliases||{}, canonical=value=>{
      let id=normalize(value);const seen=new Set();
      while(!seen.has(id)){seen.add(id);const next=aliases[id]||aliases['arxiv:'+id];if(!next)break;id=normalize(next);}
      return id;
    };
    return new Set(batch.payload.papers.flatMap(p=>[p.paper_id,p.arxiv_id,p.arxiv_url,p.doi].filter(Boolean).map(canonical)));
  }
  const batchId=batch=>batch.payload.date+':'+batch.payload.papers.map(p=>normalize(p.paper_id)).sort().join('|');
  function valid(batch) {
    const p=batch?.payload;
    return Boolean(p&&/^\d{4}-\d{2}-\d{2}$/.test(p.date)&&p.publication_status==='complete'&&p.papers?.length===5&&
      new Set(p.papers.map(p=>normalize(p.paper_id))).size===5&&
      p.papers.every(p=>p.paper_id&&p.title&&p.abstract&&p.abstract_zh&&Number.isFinite(p.ai_score))&&typeof batch.prompt_template==='string');
  }
  function create(storage, initial, today=()=>beijingDate()) {
    function read() {
      const raw=storage.getItem(KEY);
      if(raw){const saved=JSON.parse(raw);if(saved.schema_version!==1||!valid(saved.batch)||!Array.isArray(saved.shown))throw Error('阅读进度格式异常，原数据未覆盖。');return saved;}
      if(!valid(initial))throw Error('尚无完整五篇精选，暂不初始化阅读进度。');
      const state={schema_version:1,batch:initial,completed:false,completed_date:null,shown:[batchId(initial)]};write(state);return state;
    }
    function write(state){storage.setItem(KEY,JSON.stringify(state));return state;}
    function complete(value=true){const state=read();state.completed=value;state.completed_date=value?today():null;return write(state);}
    function advance(next) {
      const state=read();
      if(!state.completed||!state.completed_date||today()<=state.completed_date||!valid(next)||
        next.payload.date<=state.batch.payload.date||next.payload.date>today()||state.shown.includes(batchId(next)))return state;
      const combined={...state.batch.aliases,...next.aliases};
      const current=identities({...state.batch,aliases:combined});
      if([...identities({...next,aliases:combined})].some(id=>current.has(id)))return state;
      return write({...state,batch:next,completed:false,completed_date:null,shown:[...state.shown,batchId(next)]});
    }
    return {read,complete,advance};
  }
  function mount(win) {
    const doc=win.document,node=doc.getElementById('daily-reading-data');if(!node)return;
    const error=text=>{doc.getElementById('reading-error').textContent=text;};
    try {
      const initial=JSON.parse(node.textContent),progress=create(win.localStorage,initial),favorites=win.MaritimeFavorites.create(win.localStorage);
      const message=text=>{doc.getElementById('favorite-message').textContent=text;};
      win.MaritimeFavorites.toolbar(doc.getElementById('daily-favorites'),favorites,message);
      let rendered='';
      const el=(tag,text)=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
      const link=(text,url)=>{const a=el('a',text);a.href=/^https?:\/\//i.test(url||'')?url:'#';return a;};
      function controls(state) {
        doc.getElementById('reading-date').textContent='每日阅读 '+beijingDate();
        doc.getElementById('reading-batch-date').textContent='当前批次：'+state.batch.payload.date+' 精选';
        doc.getElementById('reading-status').textContent=state.completed?'':'本批尚未标记阅读完成';
        const button=doc.getElementById('reading-complete');button.textContent=state.completed?'已阅读完成 · 明日更新':'✓ 本批五篇已阅读完成';button.disabled=state.completed;
        doc.getElementById('reading-undo').hidden=!state.completed;
      }
      function render(state) {
        controls(state);const batch=state.batch,id=batchId(batch);if(rendered===id)return;
        const papers=batch.payload.papers,holder=doc.getElementById('reading-papers');holder.replaceChildren();
        favorites.configure(papers,batch.aliases||{});
        for(const p of papers) {
          const article=el('article');article.append(el('h2',p.title));
          const authors=Array.isArray(p.authors)?p.authors:[];
          article.append(el('p','作者：'+(authors.slice(0,5).join('、')||'待核实')));
          if(authors.length>5){const d=el('details');d.append(el('summary','查看全部作者'),el('p',authors.join('、')));article.append(d);}
          const verified=p.affiliation_verified&&p.affiliation_source&&authors[0]&&p.first_author?.trim().toLowerCase()===authors[0].trim().toLowerCase();
          const affiliation=verified&&p.first_author_affiliations?.[0];
          article.append(el('p','第一作者单位：'+(affiliation||'待核实')+(affiliation?'（'+p.affiliation_source+'）':'')),el('p',p.source||''),el('p',(p.level||'')+' · AI相关分 '+p.ai_score+'/100 '+(p.selection_source||'')),el('p',p.reason||''));
          const abstracts=el('details'),english=el('p',p.abstract);english.lang='en';abstracts.append(el('summary','查看摘要（中文 / English）'),el('p',p.abstract_zh),english);article.append(abstracts);
          const actions=el('div');actions.className='paper-actions';
          const prompt=el('button','Prompt');prompt.type='button';prompt.dataset.promptPaper=p.paper_id;
          const favorite=el('span');favorite.dataset.favoriteInline='1';favorite.dataset.favoritePaper=p.paper_id;
          actions.append(link('原文',p.original_url||p.arxiv_url),el('span','·'),link('阅读与笔记',p.reading_url),el('span','·'),prompt,el('span','·'),favorite);
          const panels=el('div');panels.className='paper-panels';panels.dataset.paperPanels=p.paper_id;article.append(actions,panels);holder.append(article);
          win.MaritimeFavorites.mount(favorite,p,favorites,message,{inline:true,panelHost:panels});
        }
        doc.getElementById('daily-prompt-data').textContent=JSON.stringify({prompt_template:batch.prompt_template,papers:papers.map(p=>({...p,authors:Array.isArray(p.authors)?p.authors:[]}))});
        win.MaritimeDailyPrompt.mount(doc,win.navigator,win.MaritimePrompt.makePrompt);
        rendered=id;
      }
      const prefix=win.location.pathname.includes('/maritime-data/mobile/')?'../../':'';
      async function check() {
        try {
          const state=progress.read();render(state);
          if(!state.completed||beijingDate()<=state.completed_date)return;
          // Do not replace an editor while the user is writing a favorite note.
          if(doc.activeElement?.tagName==='TEXTAREA'||doc.querySelector('.paper-panels details[open]'))return;
          const response=await win.fetch(prefix+'maritime-data/mobile/latest.json',{cache:'no-store'});if(!response.ok)return;
          render(progress.advance({payload:await response.json(),aliases:initial.aliases,prompt_template:initial.prompt_template}));
        }catch(e){error('阅读进度暂未更新：'+e.message+'；当前批次已保留。');}
      }
      doc.getElementById('reading-complete').addEventListener('click',()=>{try{render(progress.complete());}catch(e){error('无法保存阅读进度：'+e.message);}});
      doc.getElementById('reading-undo').addEventListener('click',()=>{try{render(progress.complete(false));}catch(e){error('无法保存阅读进度：'+e.message);}});
      win.addEventListener('storage',event=>{if(event.key===KEY)try{render(progress.read());}catch(e){error(e.message);}});
      render(progress.read());check();win.setInterval(check,60000);
      doc.addEventListener('visibilitychange',()=>{if(!doc.hidden)check();});
    }catch(e){error('阅读进度暂不可用：'+e.message+'；原收藏和笔记未修改。');}
  }
  if(typeof module!=='undefined')module.exports={KEY,beijingDate,valid,batchId,identities,create,mount};
  else {root.MaritimeDailyReading={mount};mount(root);}
})(globalThis);
