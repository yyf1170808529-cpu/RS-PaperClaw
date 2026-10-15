'use strict';
const STATES = ['待读', '已浏览', '值得精读', '已精读', '值得复现'];
const LEVELS = {high: '高度相关', transfer: '方法可借鉴', general: '一般相关', excluded: '不相关'};
const STORAGE = 'rs-paperclaw-maritime-readings-v1';
const paperId = paper => paper.paper_id || paper.arxiv_id;
const INVALID = new Set(['deleted','withdrawn','invalid']);
const RESOURCE_TYPES = new Set(['dataset','software','other']);
function recommendable(p) {
  const b=p.recommendation?.bucket,q=p.quality||{};
  return p.recommendation_status!=='candidate' && !INVALID.has(p.validity?.status) && !RESOURCE_TYPES.has(p.resource_type) && p.resource_type!=='unknown' && p.assessment?.level!=='excluded' &&
    (b==='water' ? p.resource_type==='journal_article' && q.high_journal : ['land','general'].includes(b) && p.assessment.level==='high' && !p.recommendation.low_priority && ((p.resource_type==='journal_article' && q.high_journal) || (p.resource_type==='conference_paper' && q.ccf_a) || (p.resource_type==='preprint' && p.publication_status!=='published')));
}
function recommendationSummary(papers) {
  const counts={water:0,land:0,general:0},seen=new Set();
  for(const p of papers) if(!seen.has(paperId(p)) && recommendable(p)) {seen.add(paperId(p));counts[p.recommendation.bucket]++;}
  return `水路 ${counts.water} 篇 · 陆上 ${counts.land} 篇 · 通用方法 ${counts.general} 篇`;
}
const SECTIONS = {maritime:'海事重点推荐',methods:'跨领域高水平方法',preprints:'arXiv',candidate:'一般候选库'};

function updateStatus(data) {
  const last=data.source_runs?.at(-1);
  if(!last) return {text:'尚无更新记录',details:''};
  const run=last.run_id?data.source_runs.filter(r=>r.run_id===last.run_id):[last];
  const good=run.filter(r=>['success','incomplete'].includes(r.status)).length;
  const complete=run.every(r=>r.status==='success');
  const summary=data.update_summary?.run_id===last.run_id?data.update_summary:null;
  const noNew=summary ? summary.added===0 : complete && run.every(r=>r.candidate_count===0);
  let text=complete?'最近更新成功':good?'最近更新部分完成，部分来源未成功，其余数据已保存':'最近更新失败，请查看日志';
  if(complete && noNew) text+='（本次没有新论文）';
  const groups={};
  for(const r of run) {
    const name=r.source||'unknown';
    const group=groups[name] ||= {success:0,failed:0,incomplete:0,limited:0};
    if(r.status==='success') group.success++;
    else if(r.status==='incomplete') group.incomplete++;
    else if(/429|rate.?limit|budget_exhausted|额度/i.test(r.error||'')) group.limited++;
    else group.failed++;
  }
  const details=Object.entries(groups).map(([name,g])=>`${name}：成功${g.success}，失败${g.failed}，限流${g.limited}，截断${g.incomplete}`).join('；');
  return {text,details,complete,noNew};
}

function sourceLabel(paper) {
  const q=paper.quality||{};
  if(paper.venue_type==='journal') return `${paper.venue||'期刊'} · ${q.one_type||'待核验'} · IF ${q.jif==null?'暂无':Number.isInteger(q.jif)?q.jif.toFixed(1):q.jif}`;
  if(paper.venue_type==='conference' && paper.publication_status==='published') return `${q.conference_name||paper.venue}${q.ccf_a?' · CCF A':['B','C'].includes(q.ccf_grade)?' · CCF '+q.ccf_grade:''}`;
  if(paper.publication_status==='published' && paper.venue) return paper.venue;
  return paper.arxiv_id ? 'arXiv' : paper.venue||'其他来源';
}

function compareRecommendation(a,b) {
  if(Boolean(a.ai_demoted)!==Boolean(b.ai_demoted)) return a.ai_demoted?1:-1;
  if(typeof a.ai_score==='number' || typeof b.ai_score==='number') {
    const difference=(b.ai_score??-1)-(a.ai_score??-1);if(difference)return difference;
  }
  if (!a.recommendation || !b.recommendation) return b.assessment.score-a.assessment.score;
  const vector = p => {const r=p.recommendation,q=p.quality||{};return [r.low_priority?0:1,q.ccf_a?1:0,q.high_journal||q.high_conference?1:0,r.direct_relevance,r.maritime?1:0,r.method_transfer_signal?1:0];};
  const av=vector(a),bv=vector(b);
  for(let i=0;i<av.length;i++) if(av[i]!==bv[i]) return bv[i]-av[i];
  return (b.publication_date||b.published).localeCompare(a.publication_date||a.published) || b.assessment.score-a.assessment.score;
}

function filterPapers(papers, filters, days) {
  if(filters.window==='favorites') {
    const saved=filters.favorites||new Set(),search=(filters.search||'').toLowerCase();
    return papers.filter(p=>saved.has(paperId(p)) && `${paperId(p)} ${p.title} ${p.authors.join(' ')} ${p.abstract||''}`.toLowerCase().includes(search))
      .sort((a,b)=>(b.publication_date||b.published||'').localeCompare(a.publication_date||a.published||''));
  }
  const ids = filters.date ? new Set((filters.window && filters.window!=='history' ? days[filters.date]?.paper_ids : null) || days[filters.date]?.candidate_ids || days[filters.date]?.all_ids || []) : null;
  const search = (filters.search || '').toLowerCase();
  const end = filters.today || new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Shanghai'});
  const start = !filters.date && ['7','14','1'].includes(filters.window) && !filters.backendView ? new Date(new Date(`${end}T00:00:00Z`).getTime()-(Number(filters.window)-1)*86400000).toISOString().slice(0,10) : '';
  return papers.filter(p => !INVALID.has(p.validity?.status) && !RESOURCE_TYPES.has(p.resource_type) && p.resource_type!=='unknown' && (!ids || ids.has(paperId(p))) &&
    (!start || ((p.publication_date||p.published)>=start && (p.publication_date||p.published)<=end)) &&
    (filters.window!=='today' || p.discovery_date===end) &&
    (!filters.section || p.recommendation?.section===filters.section) &&
    (!filters.bucket || (filters.window==='history' ? (p.application_bucket || ({maritime:'water',traffic:'land',general:'general'}[p.recommendation?.application])) : p.recommendation?.bucket)===filters.bucket) &&
    (!filters.quality || (filters.quality==='unverified' ? p.quality?.status==='unverified' : p.venue_type==='journal' && p.publication_status==='published' && p.quality?.[filters.quality])) &&
    (!filters.topic || p.assessment.topics.includes(filters.topic)) &&
    (filters.level ? p.assessment.level === filters.level : p.assessment.level !== 'excluded') &&
    `${paperId(p)} ${p.title} ${p.abstract} ${p.authors.join(' ')} ${p.venue||''} ${p.doi||''} ${p.assessment.reasons.join(' ')}`.toLowerCase().includes(search))
    .sort((a, b) => filters.sort === 'date' ? b.published.localeCompare(a.published) || b.assessment.score - a.assessment.score :
      compareRecommendation(a,b) || b.published.localeCompare(a.published) || paperId(a).localeCompare(paperId(b)));
}

function makePrompt(template, paper) {
  if(RESOURCE_TYPES.has(paper.resource_type) || paper.resource_type==='unknown' || INVALID.has(paper.validity?.status)) return '';
  const pdf = (paper.oa_evidence || /\.pdf(?:[?#]|$)/i.test(paper.open_access_url||'') ? paper.open_access_url : '') || paper.pdf_url;
  let text=template;
  if(!/^https?:\/\//.test(pdf||'')) text=text.split('<!-- FULLTEXT -->')[0];
  const values = {...paper, pdf_url: pdf, authors: paper.authors.join(', ')};
  return text.replace('<!-- FULLTEXT -->','').replace(/\{\{(title|authors|published|arxiv_url|pdf_url|abstract|doi|original_url|venue)\}\}/g, (_, key) => values[key]||'暂未获取');
}

function validateBackup(backup) {
  if (!backup || backup.schema_version !== 1 || !backup.readings || typeof backup.readings !== 'object' || Array.isArray(backup.readings))
    throw new Error('需要 schema_version=1 和 readings 对象');
  const readings = Object.create(null);
  for (const [id, record] of Object.entries(backup.readings)) {
    if (!/^(?:\d{4}\.\d{4,5}|[a-zA-Z.-]+\/\d{7}|doi:10\.\d{4,9}\/\S+|openalex:W\d+)$/.test(id) || !record ||
        typeof record.analysis !== 'string' || !STATES.includes(record.state) ||
        (record.updated_at !== undefined && typeof record.updated_at !== 'string')) throw new Error(`无效记录: ${id}`);
    readings[id] = {analysis: record.analysis, state: record.state, updated_at: record.updated_at || new Date().toISOString()};
  }
  return readings;
}

function validateFavorites(backup, aliases={}) {
  if(backup.favorites===undefined) return null;
  if(!Array.isArray(backup.favorites)) throw new Error('收藏列表格式错误');
  const result=new Set();
  for(const raw of backup.favorites) {
    if(typeof raw!=='string' || !/^(?:\d{4}\.\d{4,5}|[a-zA-Z.-]+\/\d{7}|doi:10\.\d{4,9}\/\S+|openalex:W\d+)$/.test(raw)) throw new Error(`无效收藏ID: ${raw}`);
    result.add(aliases[raw]||raw);
  }
  return result;
}

function readingFor(paper, readings) {
  return readings[paperId(paper)] || paper.reading || {analysis: '', state: '待读'};
}

if (typeof module !== 'undefined') module.exports = {filterPapers, makePrompt, validateBackup, validateFavorites, readingFor, STATES,compareRecommendation,paperId,sourceLabel,recommendationSummary,recommendable,updateStatus};

if (typeof document !== 'undefined') {
  const $ = id => document.getElementById(id);
  let data, readings = Object.create(null), favorites = new Set(), brokenStorage = null;
  const message = text => { $('message').textContent = text; };
  function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  }
  function button(text, handler) {
    const element = node('button', text);
    element.addEventListener('click', handler);
    return element;
  }
  function download(filename, text, type) {
    const url = URL.createObjectURL(new Blob([text], {type}));
    const anchor = node('a'); anchor.href = url; anchor.download = filename;
    anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function persist(id, record) {
    if (brokenStorage !== null) { message('本地存储格式异常，请先导出原始备份，再导入有效 JSON 恢复。'); return false; }
    const next = {...readings, [id]: {...record, updated_at: new Date().toISOString()}};
    try {
      localStorage.setItem(STORAGE, JSON.stringify({schema_version: 1, readings: next, favorites:[...favorites]}));
      readings = next;
      message('已保存到本浏览器。请导出 JSON 备份以防浏览器数据被清除。');
      return true;
    } catch (error) { message(`保存失败：${error.message}。请复制文本或导出 Markdown。`); return false; }
  }
  function toggleFavorite(id) {
    if(brokenStorage!==null) { message('本地存储异常，请先导出备份。'); return false; }
    const next=new Set(favorites);
    if(next.has(id)) next.delete(id); else next.add(id);
    try { localStorage.setItem(STORAGE,JSON.stringify({schema_version:1,readings,favorites:[...next]}));favorites=next;message(next.has(id)?'已加入我的收藏':'已取消收藏');return true; }
    catch(error) { message(`收藏保存失败：${error.message}`);return false; }
  }
  function render() {
    const filters = Object.fromEntries(['date', 'topic', 'level', 'sort', 'search','window','quality','section','bucket','language'].map(id => [id, $(id)?.value||'']));
    const view=filters.date ? data.days[filters.date]?.recommendation_view : data.recommendation_views?.[filters.window];
    filters.backendView=!!view;filters.favorites=favorites;
    let papers = filterPapers(data.papers, filters, data.days);
    if(view && filters.window!=='history' && filters.window!=='today') {
      const ids=new Set(view.paper_ids);papers=papers.filter(p=>ids.has(paperId(p)) && recommendable(p));
    } else if(filters.window && !['history','today','favorites'].includes(filters.window)) {
      const quotas=data.recommendation_policy?.quotas||{water:10,land:6,general:4};
      const counts={};papers=papers.filter(p=>{const s=p.recommendation?.bucket;if(!(s in quotas) || !recommendable(p))return false;counts[s]=(counts[s]||0)+1;return counts[s]<=quotas[s];});
    }
    const day = data.days[filters.date];
    $('summary').textContent = filters.window==='history' ? `当前 ${papers.length} 篇 / 总收录 ${data.papers.length} 条` : filters.window==='favorites' ? `我的收藏 ${papers.length} 篇` : recommendationSummary(papers);
    $('report').hidden = !day;
    if (day) $('report').href = `maritime-data/reports/${filters.date.slice(0,7).replace('-', '')}/${filters.date.replaceAll('-', '')}.md`;
    $('papers').replaceChildren();
    if (!papers.length) $('papers').append(node('p', Object.keys(data.days).length ?
      '当前范围没有入选论文。可调整筛选条件；在线检索失败请查看 CLI 日志。' :
      '尚未完成成功的在线检索。请运行 maritime --days 7；若请求失败，查看 papers/maritime/logs/errors.jsonl。'));
    for (const paper of papers) {
      const article = node('article');
      const assessment = paper.assessment;
      const reading = readingFor(paper, readings);
      const id=paperId(paper),quality=paper.quality||{};
      article.id='paper-'+encodeURIComponent(id);
      article.append(node('h2', paper.title), node('p', `${paper.authors.join(', ')} · ${paper.published}`, 'muted'),
        node('p', `规则分 ${assessment.score}（${LEVELS[assessment.level]}） · ${paper.recommendation_status==='direct'||paper.recommendation_status==='direct_rule'?'直接相关':paper.recommendation_status==='transfer'?'方法值得关注':'普通候选'}${typeof paper.ai_score==='number'?` · AI相关分 ${paper.ai_score}/100`:' · AI待评估'} · 主专题 ${assessment.primary_topic || '无'} · ${assessment.topics.join('/')} · ${assessment.applications.join('、')}`, 'muted'));
      const source=sourceLabel(paper);
      article.append(node('p', source),
        node('p', `第一作者：${paper.first_author||paper.authors[0]||'暂未获取'} ｜单位：${paper.affiliation_verified ? paper.first_author_affiliations.join('; ') : '暂未获取'}`, 'muted'));
      if(paper.doi) article.append(node('p',`DOI：${paper.doi}`,'muted'));
      const links = node('div', undefined, 'actions');
      const favoriteButton=button(favorites.has(id)?'取消收藏':'收藏',()=>{if(toggleFavorite(id)){favoriteButton.textContent=favorites.has(id)?'取消收藏':'收藏';if($('window').value==='favorites')render();}});
      links.append(favoriteButton);
      for (const [text, href] of [['原始论文', paper.open_access_url||paper.pdf_url||paper.original_url||paper.arxiv_url||''], ['ChatGPT 网页', 'https://chatgpt.com/'], ['DeepSeek 网页', 'https://chat.deepseek.com/'], [paper.venue_type==='journal' ? '期刊 DOI' : 'DOI 原文', paper.doi ? 'https://doi.org/'+paper.doi : ''], ['arXiv 页面', paper.arxiv_url||''], ['arXiv PDF', paper.arxiv_id ? 'https://arxiv.org/pdf/'+paper.arxiv_id : '']]) {
        if(!/^https?:\/\//.test(href)) continue;
        const link = node('a', text); link.href = href; link.target = '_blank'; link.rel = 'noreferrer'; links.append(link);
      }
      const prompt = makePrompt(data.prompt_template, paper);
      const fallback = node('details');
      if(prompt) { fallback.append(node('summary', '查看 / 手动复制分析 Prompt'));
      const promptText = node('textarea'); promptText.value = prompt; promptText.readOnly = true; promptText.setAttribute('aria-label', '论文分析 Prompt'); fallback.append(promptText);
      links.append(button('复制分析 Prompt', async () => {
        try { await navigator.clipboard.writeText(prompt); message('Prompt 已复制。请粘贴到 ChatGPT 或 DeepSeek；如果无法读取 PDF 链接，再手动上传 PDF。'); }
        catch { fallback.open = true; promptText.focus(); promptText.select(); message('剪贴板不可用，请从展开区域手动复制 Prompt。'); }
      }));
      }
      const stateLabel = node('label', '阅读状态'); const state = node('select');
      for (const name of STATES) { const option = node('option', name); option.value = name; state.append(option); }
      state.value = reading.state;
      state.addEventListener('change', () => { if (!persist(id, {...readingFor(paper, readings), state: state.value})) state.value = readingFor(paper, readings).state; });
      stateLabel.append(state); links.append(stateLabel); article.append(links);
      const details = node('details'); details.append(node('summary', '中英文摘要与评分理由'));
      const translation=paper.translation||{};
      const chinese=paper.display_abstract_zh!==undefined ? paper.display_abstract_zh : translation.zh && ['manual','machine'].includes(translation.status) ? translation.zh : '';
      const chineseSource=translation.status==='manual'?'人工修订':paper.selected_translation?.status==='deepseek' && paper.display_abstract_zh===paper.selected_translation.zh?'DeepSeek 翻译':'机器翻译';
      if(filters.language!=='en') details.append(node('p', chinese ? `中文（${chineseSource}）：\n${chinese}` : '中文暂不可用；英文原文仍保留。','abstract'));
      if(filters.language!=='zh' || !chinese) details.append(node('p',`English：\n${paper.abstract||'英文摘要暂未获取'}`,'abstract'));
      const abstractTools=node('div',undefined,'actions');
      for(const [label,text]of [['复制英文摘要',paper.abstract],['复制中文摘要',chinese]]) if(text) abstractTools.append(button(label,async()=>{try{await navigator.clipboard.writeText(text);message('摘要已复制');}catch{message('剪贴板不可用，请选择摘要手动复制');}}));
      details.append(abstractTools,node('p',assessment.reasons.join('；')));
      const license=paper.abstract_source?.license_url;
      if(/^https?:\/\//.test(license||'')) {const link=node('a','摘要来源与许可');link.href=license;link.target='_blank';link.rel='noreferrer';details.append(link);}
      article.append(details); if(prompt) article.append(fallback);
      const analysis = node('details'); analysis.append(node('summary', reading.analysis ? '查看 / 编辑已有分析' : '粘贴论文分析'));
      const preview = node('pre', reading.analysis || '尚未保存分析', 'analysis');
      const editor = node('textarea'); editor.value = reading.analysis; editor.placeholder = '将 ChatGPT 或 DeepSeek 返回的 Markdown 粘贴到这里'; editor.setAttribute('aria-label', `${paper.title} 分析 Markdown`);
      const tools = node('div', undefined, 'actions');
      tools.append(button('保存分析', () => { if (persist(id, {analysis: editor.value, state: state.value})) preview.textContent = editor.value; }),
        button('导出 Markdown', () => download(`${id.replaceAll('/', '_').replaceAll(':','_')}-analysis.md`, editor.value, 'text/markdown;charset=utf-8')));
      analysis.append(preview, editor, tools);
      const alternateReadings=[...(paper.merge_conflicts||[]).filter(c=>c.field==='reading'), ...Object.entries(data.aliases||{}).filter(([old,current])=>current===id && readings[old] && JSON.stringify(readings[old])!==JSON.stringify(reading)).map(([old])=>({from:old,value:readings[old]}))];
      if(alternateReadings.length) {
        const alternatives=node('details');alternatives.append(node('summary','合并前的阅读记录（已安全保留）'));
        for(const c of alternateReadings) alternatives.append(node('p',c.from||'旧记录'),node('pre',c.value.analysis||c.value.state||''));
        analysis.append(alternatives);
      }
      article.append(analysis); $('papers').append(article);
    }
  }
  async function init() {
    try {
      const response = await fetch('maritime-data/library.json', {cache: 'no-cache'});
      if (!response.ok) throw new Error(`数据 HTTP ${response.status}；请先运行 maritime --action site`);
      data = await response.json();
      const selected=typeof location!=='undefined' ? new URLSearchParams(location.search).get('paper') : null;
      if(selected) { $('window').value='history'; $('search').value=data.aliases?.[selected]||selected; }
      try { const saved = localStorage.getItem(STORAGE); if (saved) { brokenStorage = saved; const backup=JSON.parse(saved);readings = validateBackup(backup);favorites=validateFavorites(backup,data.aliases)||new Set();brokenStorage = null; } }
      catch (error) { message(`本地数据无法读取：${error.message}。原始存储未覆盖，请先备份。`); $('export').textContent = '导出备份（本地数据异常，请检查）'; }
      for (const [key, name] of Object.entries(data.topics)) { const option = node('option', `${key}. ${name}`); option.value = key; $('topic').append(option); }
      for (const date of Object.keys(data.days).sort().reverse()) { const option = node('option', date); option.value = date; $('date').append(option); }
      for (const [old,canonical] of Object.entries(data.aliases||{})) if(readings[old]&&!readings[canonical]) readings[canonical]=readings[old];
      for (const id of ['date','topic','level','sort','search','window','quality','section','bucket','language']) $(id)?.addEventListener('input', render);
      const status=updateStatus(data);message(status.text);
      if($('update-detail-text')) $('update-detail-text').textContent=status.details;
      if($('update-details')) $('update-details').hidden=!status.details;
      $('export').addEventListener('click', () => {
        if (brokenStorage !== null) { download('maritime-readings-recovery.json', brokenStorage, 'application/json'); return; }
        const all = {...Object.fromEntries(data.papers.filter(p => p.reading).map(p => [paperId(p),p.reading])), ...readings};
        download('maritime-readings.json', JSON.stringify({schema_version: 1, readings: all, favorites:[...favorites]}, null, 2), 'application/json');
      });
      $('import').addEventListener('change', async event => {
        try {
          const file = event.target.files[0]; if (!file) return;
          const backup=JSON.parse(await file.text());
          const imported = validateBackup(backup);
          const importedFavorites=validateFavorites(backup,data.aliases);
          const next = {...readings, ...imported};
          const nextFavorites=importedFavorites===null?favorites:new Set([...favorites,...importedFavorites]);
          localStorage.setItem(STORAGE, JSON.stringify({schema_version: 1, readings: next, favorites:[...nextFavorites]}));
          readings = next;favorites=nextFavorites; brokenStorage = null; $('export').textContent = '导出 JSON 备份'; render(); message('备份已合并到本浏览器；同一 ID 以导入记录为准。未知论文记录保留，之后检索到该论文即可显示。');
        } catch (error) { message(`导入失败：${error.message}，未修改现有记录。`); }
        event.target.value = '';
      });
      render();
    } catch (error) { message(`加载失败：${error.message}。请使用本地 HTTP 服务或 GitHub Pages 打开。`); }
  }
  init();
}
