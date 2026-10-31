// Shared Mermaid boot for all planning documents: render, then fit each SVG to one A4 box.
const MERMAID_CFG = {
  startOnLoad: false, theme: 'base', securityLevel: 'loose',
  themeVariables: {
    fontFamily: '"Helvetica Neue",Helvetica,Arial,sans-serif', fontSize: '13px',
    primaryColor: '#eef3ff', primaryTextColor: '#12161d', primaryBorderColor: '#1d4ed8',
    lineColor: '#6b7280', secondaryColor: '#f5f7fa', tertiaryColor: '#fbfcfd',
    noteBkgColor: '#fff8ec', noteBorderColor: '#b45309', noteTextColor: '#12161d',
    git0: '#1d4ed8', git1: '#8a4408', git2: '#5925a5', git3: '#04635a', git4: '#b42318',
    gitBranchLabel0: '#ffffff', gitBranchLabel1: '#ffffff', gitBranchLabel2: '#ffffff',
    gitBranchLabel3: '#ffffff', gitBranchLabel4: '#ffffff'
  },
  flowchart: { curve: 'basis', nodeSpacing: 32, rankSpacing: 38, useMaxWidth: true },
  sequence: { useMaxWidth: true, wrap: true, width: 150 },
  gantt: { useMaxWidth: true, fontSize: 10, barHeight: 14, sectionFontSize: 11 },
  gitGraph: { useMaxWidth: true, showBranches: true, showCommitLabel: true, rotateCommitLabel: true }
};
const MAX_W = 620, MAX_H = 690;
(async () => {
  mermaid.initialize(MERMAID_CFG);
  await mermaid.run({ querySelector: 'figure .mermaid' });
  document.querySelectorAll('figure .mermaid svg').forEach(svg => {
    const vb = svg.viewBox && svg.viewBox.baseVal;
    if (!vb || !vb.width || !vb.height) return;
    const s = Math.min(MAX_W / vb.width, MAX_H / vb.height, 1);
    svg.removeAttribute('width'); svg.removeAttribute('height');
    svg.style.maxWidth = 'none';
    svg.style.width = (vb.width * s) + 'px'; svg.style.height = (vb.height * s) + 'px';
  });
  await Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; })));
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  window.__docReady = true;
})();
