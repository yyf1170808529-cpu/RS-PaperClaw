'use strict';
(function(root) {
  function mount(doc, navigator, makePrompt) {
    const node=doc.getElementById('daily-prompt-data');
    if(!node) return;
    const data=JSON.parse(node.textContent);
    const papers=new Map(data.papers.map(p=>[p.paper_id,p]));
    for(const button of doc.querySelectorAll('[data-prompt-paper]')) {
      const paper=papers.get(button.dataset.promptPaper);
      if(!paper) continue;
      const text=makePrompt(data.prompt_template,paper);
      const feedback=doc.createElement('span');
      feedback.setAttribute('role','status');
      feedback.setAttribute('aria-live','polite');
      const panelHost=button.closest?.('article')?.querySelector('[data-paper-panels]')||button.parentNode;
      panelHost.append(feedback);
      let fallback;
      button.addEventListener('click',async()=>{
        if(!text) {feedback.textContent='此资源暂不提供论文精读 Prompt';return;}
        try {
          await navigator.clipboard.writeText(text);
          feedback.textContent='已复制';
        } catch {
          if(!fallback) {
            fallback=doc.createElement('details');
            const summary=doc.createElement('summary');summary.textContent='展开 Prompt，长按复制';
            const area=doc.createElement('textarea');
            area.readOnly=true;area.rows=10;area.value=text;
            area.setAttribute('aria-label','论文分析 Prompt：'+paper.title);
            fallback.append(summary,area);panelHost.append(fallback);
          }
          fallback.open=true;
          feedback.textContent='请在文本框中长按全选复制';
        }
      });
    }
  }
  if(typeof module!=='undefined') module.exports={mount};
  else {root.MaritimeDailyPrompt={mount};if(!root.document.getElementById('daily-reading-data'))mount(root.document,root.navigator,root.MaritimePrompt.makePrompt);}
})(globalThis);
