'use strict';
const STATES = ['待读', '已浏览', '值得精读', '已精读', '值得复现'];
const LEVELS = {high: '高度相关', transfer: '方法可借鉴', general: '一般相关', excluded: '不相关'};
const STORAGE = 'rs-paperclaw-maritime-readings-v1';
const paperId = paper => paper.paper_id || paper.arxiv_id;
const SECTIONS = {maritime:'海事重点推荐',methods:'跨领域高水平方法',preprints:'arXiv',candidate:'一般候选库'};

function sourceLabel(paper) {
  if(paper.publication_status==='published' && paper.venue) return paper.venue;
  return paper.arxiv_id ? 'arXiv' : paper.venue||'其他来源';
}

function compareRecommendation(a,b) {
  if (!a.recommendation || !b.recommendation) return b.assessment.score-a.assessment.score;
  const vector = p => {const r=p.recommendation,q=p.quality||{};return [r.low_priority?0:1,r.direct_relevance,r.maritime?1:0,q.high_journal||q.high_conference?1:0,r.method_transfer_signal?1:0];};
  const av=vector(a),bv=vector(b);
  for(let i=0;i<av.length;i++) if(av[i]!==bv[i]) return bv[i]-av[i];
  return (b.publication_date||b.published).localeCompare(a.publication_date||a.published) || b.assessment.score-a.assessment.score;
}

function filterPapers(papers, filters, days) {
  const ids = filters.date ? new Set(days[filters.date]?.candidate_ids || days[filters.date]?.all_ids || []) : null;
  const search = (filters.search || '').toLowerCase();
  const end = filters.today || new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Shanghai'});
  const start = !filters.date && filters.window && filters.window!=='history' ? new Date(new Date(`${end}T00:00:00Z`).getTime()-(Number(filters.window)-1)*86400000).toISOString().slice(0,10) : '';
  return papers.filter(p => (!ids || ids.has(paperId(p))) &&
    (!start || ((p.publication_date||p.published)>=start && (p.publication_date||p.published)<=end)) &&
    (!filters.section || p.recommendation?.section===filters.section) &&
    (!filters.bucket || p.recommendation?.bucket===filters.bucket) &&
    (!filters.quality || (filters.quality==='unverified' ? p.quality?.status==='unverified' : p.venue_type==='journal' && p.publication_status==='published' && p.quality?.[filters.quality])) &&
    (!filters.topic || p.assessment.topics.includes(filters.topic)) &&
    (filters.level ? p.assessment.level === filters.level : p.assessment.level !== 'excluded') &&
    `${p.title} ${p.abstract} ${p.authors.join(' ')} ${p.venue||''} ${p.doi||''} ${p.assessment.reasons.join(' ')}`.toLowerCase().includes(search))
    .sort((a, b) => filters.sort === 'date' ? b.published.localeCompare(a.published) || b.assessment.score - a.assessment.score :
      compareRecommendation(a,b) || b.published.localeCompare(a.published) || paperId(a).localeCompare(paperId(b)));
}

function makePrompt(template, paper) {
  const values = {...paper, pdf_url: paper.open_access_url || paper.pdf_url, authors: paper.authors.join(', ')};
  return template.replace(/\{\{(title|authors|published|arxiv_url|pdf_url|abstract|doi|original_url|venue)\}\}/g, (_, key) => values[key]||'暂未获取');
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

function readingFor(paper, readings) {
  return readings[paperId(paper)] || paper.reading || {analysis: '', state: '待读'};
}

if (typeof module !== 'undefined') module.exports = {filterPapers, makePrompt, validateBackup, readingFor, STATES,compareRecommendation,paperId,sourceLabel};

if (typeof document !== 'undefined') {
  const $ = id => document.getElementById(id);
  let data, readings = Object.create(null), brokenStorage = null;
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
      localStorage.setItem(STORAGE, JSON.stringify({schema_version: 1, readings: next}));
      readings = next;
      message('已保存到本浏览器。请导出 JSON 备份以防浏览器数据被清除。');
      return true;
    } catch (error) { message(`保存失败：${error.message}。请复制文本或导出 Markdown。`); return false; }
  }
  function render() {
    const filters = Object.fromEntries(['date', 'topic', 'level', 'sort', 'search','window','quality','section','bucket','language'].map(id => [id, $(id)?.value||'']));
    let papers = filterPapers(data.papers, filters, data.days);
    let quotaSummary='';
    if(filters.window && filters.window!=='history') {
      const quotas=data.recommendation_policy?.quotas||{water:12,land:6,general:2};
      const counts={};papers=papers.filter(p=>{const s=p.recommendation?.bucket;if(!(s in quotas))return false;counts[s]=(counts[s]||0)+1;return counts[s]<=quotas[s];});
      const labels={water:'水路',land:'陆上强相关',general:'通用高水平'};
      quotaSummary=' ｜ 目标60%/30%/10%；'+Object.entries(quotas).map(([k,n])=>`${labels[k]} ${Math.min(counts[k]||0,n)}/${n}`).join('，')+'；不足不补位';
    }
    const day = data.days[filters.date];
    $('summary').textContent = day ? `候选 ${day.candidate_count} / 入选 ${day.selected_count} / 高度相关 ${day.high_count} / 主专题 ${Object.entries(day.topic_counts).map(([k,v]) => `${k}:${v}`).join(' ')} / 当前 ${papers.length}` : `当前 ${papers.length} 篇 / 候选库 ${data.papers.length} 篇`;
    $('summary').textContent += quotaSummary;
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
      article.append(node('h2', paper.title), node('p', `${paper.authors.join(', ')} · ${paper.published}`, 'muted'),
        node('p', `${LEVELS[assessment.level]} ${assessment.score} · 主专题 ${assessment.primary_topic || '无'} · ${assessment.topics.join('/')} · ${assessment.applications.join('、')}`, 'muted'));
      const source=sourceLabel(paper);
      article.append(node('p', source==='arXiv' ? source : `${SECTIONS[paper.recommendation?.section]||'一般候选库'} · ${source}`),
        node('p', `第一作者：${paper.first_author||paper.authors[0]||'暂未获取'} ｜单位：${paper.affiliation_verified ? paper.first_author_affiliations.join('; ') : '暂未获取'}`, 'muted'));
      if(paper.venue_type==='journal') article.append(node('p', `中科院大类（${quality.cas_year||2025}）：${paper.cas_partition ? paper.cas_partition+'区':'待核验'} ｜ JCR JIF：${quality.jcr_records?.map(r=>`${r.year} ${r.category} ${r.quartile}`).join('；')||'待核验'} ｜ DOI：${paper.doi||'暂未获取'}`, 'muted'));
      else if(paper.doi) article.append(node('p',`DOI：${paper.doi}`,'muted'));
      const proof=node('details');proof.append(node('summary','发表/分区证据与推荐理由'),node('pre',JSON.stringify({publication:paper.publication_evidence,cas:quality.cas_records,jcr:quality.jcr_records,reasons:paper.recommendation?.reasons},null,2),'analysis'));article.append(proof);
      const links = node('div', undefined, 'actions');
      for (const [text, href] of [['原始论文', paper.open_access_url||paper.pdf_url||paper.original_url||paper.arxiv_url||''], ['ChatGPT 网页', 'https://chatgpt.com/'], ['DeepSeek 网页', 'https://chat.deepseek.com/']]) {
        if(!/^https?:\/\//.test(href)) continue;
        const link = node('a', text); link.href = href; link.target = '_blank'; link.rel = 'noreferrer'; links.append(link);
      }
      const prompt = makePrompt(data.prompt_template, paper);
      const fallback = node('details'); fallback.append(node('summary', '查看 / 手动复制分析 Prompt'));
      const promptText = node('textarea'); promptText.value = prompt; promptText.readOnly = true; promptText.setAttribute('aria-label', '论文分析 Prompt'); fallback.append(promptText);
      links.append(button('复制分析 Prompt', async () => {
        try { await navigator.clipboard.writeText(prompt); message('Prompt 已复制。请粘贴到 ChatGPT 或 DeepSeek；如果无法读取 PDF 链接，再手动上传 PDF。'); }
        catch { fallback.open = true; promptText.focus(); promptText.select(); message('剪贴板不可用，请从展开区域手动复制 Prompt。'); }
      }));
      const stateLabel = node('label', '阅读状态'); const state = node('select');
      for (const name of STATES) { const option = node('option', name); option.value = name; state.append(option); }
      state.value = reading.state;
      state.addEventListener('change', () => { if (!persist(id, {...readingFor(paper, readings), state: state.value})) state.value = readingFor(paper, readings).state; });
      stateLabel.append(state); links.append(stateLabel); article.append(links);
      const details = node('details'); details.append(node('summary', '中英文摘要与评分理由'));
      const translation=paper.translation||{};
      const chinese=translation.zh && ['manual','machine'].includes(translation.status) ? translation.zh : '';
      if(filters.language!=='en') details.append(node('p', chinese ? `中文（${translation.status==='manual'?'人工修订':'机器翻译'}）：\n${chinese}` : '中文暂不可用；英文原文仍保留。','abstract'));
      if(filters.language!=='zh' || !chinese) details.append(node('p',`English：\n${paper.abstract||'英文摘要暂未获取'}`,'abstract'));
      const abstractTools=node('div',undefined,'actions');
      for(const [label,text]of [['复制英文摘要',paper.abstract],['复制中文摘要',chinese]]) if(text) abstractTools.append(button(label,async()=>{try{await navigator.clipboard.writeText(text);message('摘要已复制');}catch{message('剪贴板不可用，请选择摘要手动复制');}}));
      details.append(abstractTools,node('p',assessment.reasons.join('；')));
      article.append(details, fallback);
      const analysis = node('details'); analysis.append(node('summary', reading.analysis ? '查看 / 编辑已有分析' : '粘贴论文分析'));
      const preview = node('pre', reading.analysis || '尚未保存分析', 'analysis');
      const editor = node('textarea'); editor.value = reading.analysis; editor.placeholder = '将 ChatGPT 或 DeepSeek 返回的 Markdown 粘贴到这里'; editor.setAttribute('aria-label', `${paper.title} 分析 Markdown`);
      const tools = node('div', undefined, 'actions');
      tools.append(button('保存分析', () => { if (persist(id, {analysis: editor.value, state: state.value})) preview.textContent = editor.value; }),
        button('导出 Markdown', () => download(`${id.replaceAll('/', '_').replaceAll(':','_')}-analysis.md`, editor.value, 'text/markdown;charset=utf-8')));
      analysis.append(preview, editor, tools); article.append(analysis); $('papers').append(article);
    }
  }
  async function init() {
    try {
      const response = await fetch('maritime-data/library.json', {cache: 'no-cache'});
      if (!response.ok) throw new Error(`数据 HTTP ${response.status}；请先运行 maritime --action site`);
      data = await response.json();
      try { const saved = localStorage.getItem(STORAGE); if (saved) { brokenStorage = saved; readings = validateBackup(JSON.parse(saved)); brokenStorage = null; } }
      catch (error) { message(`本地数据无法读取：${error.message}。原始存储未覆盖，请先备份。`); $('export').textContent = '导出备份（本地数据异常，请检查）'; }
      for (const [key, name] of Object.entries(data.topics)) { const option = node('option', `${key}. ${name}`); option.value = key; $('topic').append(option); }
      for (const date of Object.keys(data.days).sort().reverse()) { const option = node('option', date); option.value = date; $('date').append(option); }
      for (const [old,canonical] of Object.entries(data.aliases||{})) if(readings[old]&&!readings[canonical]) readings[canonical]=readings[old];
      for (const id of ['date','topic','level','sort','search','window','quality','section','bucket','language']) $(id)?.addEventListener('input', render);
      if(data.source_runs?.length) {const last=data.source_runs.at(-1);const run=last.run_id?data.source_runs.filter(r=>r.run_id===last.run_id):[last];message(`最近来源任务：${run.some(r=>r.status!=='success')?'检索不完整':'指定来源检索成功'}；${run.map(r=>`${r.source}${r.journal?' / '+r.journal:''}: ${r.status}`).join('；')}。已成功的数据仍保留。`);}
      $('export').addEventListener('click', () => {
        if (brokenStorage !== null) { download('maritime-readings-recovery.json', brokenStorage, 'application/json'); return; }
        const all = {...Object.fromEntries(data.papers.filter(p => p.reading).map(p => [paperId(p),p.reading])), ...readings};
        download('maritime-readings.json', JSON.stringify({schema_version: 1, readings: all}, null, 2), 'application/json');
      });
      $('import').addEventListener('change', async event => {
        try {
          const file = event.target.files[0]; if (!file) return;
          const imported = validateBackup(JSON.parse(await file.text()));
          const next = {...readings, ...imported};
          localStorage.setItem(STORAGE, JSON.stringify({schema_version: 1, readings: next}));
          readings = next; brokenStorage = null; $('export').textContent = '导出 JSON 备份'; render(); message('备份已合并到本浏览器；同一 ID 以导入记录为准。未知论文记录保留，之后检索到该论文即可显示。');
        } catch (error) { message(`导入失败：${error.message}，未修改现有记录。`); }
        event.target.value = '';
      });
      render();
    } catch (error) { message(`加载失败：${error.message}。请使用本地 HTTP 服务或 GitHub Pages 打开。`); }
  }
  init();
}
