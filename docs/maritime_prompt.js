'use strict';
(function(root) {
  // Shared verbatim with the full library: the template remains the source of the 13 sections.
  const RESOURCE_TYPES = new Set(['dataset','software','other']);
  const INVALID = new Set(['deleted','withdrawn','invalid']);
  function makePrompt(template, paper) {
    if(RESOURCE_TYPES.has(paper.resource_type) || paper.resource_type==='unknown' || INVALID.has(paper.validity?.status)) return '';
    const pdf = (paper.oa_evidence || /\.pdf(?:[?#]|$)/i.test(paper.open_access_url||'') ? paper.open_access_url : '') || paper.pdf_url;
    let text=template;
    if(!/^https?:\/\//.test(pdf||'')) text=text.split('<!-- FULLTEXT -->')[0];
    const values = {...paper, pdf_url: pdf, authors: paper.authors.join(', ')};
    return text.replace('<!-- FULLTEXT -->','').replace(/\{\{(title|authors|published|arxiv_url|pdf_url|abstract|doi|original_url|venue)\}\}/g, (_, key) => values[key]||'暂未获取');
  }
  const api={makePrompt};
  if(typeof module!=='undefined') module.exports=api;
  else root.MaritimePrompt=api;
})(globalThis);
