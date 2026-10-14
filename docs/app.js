const STATUS={G:'G 양호',A:'A 경계',R:'R 위험',B:'B 보류'};
const fmt=n=>new Intl.NumberFormat('ko-KR',{maximumFractionDigits:2}).format(n);

function countsText(counts){return ['G','A','R','B'].filter(k=>counts[k]).map(k=>`${k}${counts[k]}`).join(' · ')}

function renderReferenceChart(score){
  const svg=document.querySelector('#reference-chart'),w=800,h=300,l=54,r=72,t=20,b=36,plot=h-t-b;
  const bands=[
    {from:70,to:100,color:'#562724',label:'1 위기'},
    {from:55,to:70,color:'#5a421e',label:'2 위험'},
    {from:35,to:55,color:'#5d542a',label:'3 주의'},
    {from:20,to:35,color:'#274056',label:'4 안전'},
    {from:0,to:20,color:'#21364a',label:'5 매우 안전'}
  ];
  const y=v=>t+plot*(1-v/100);
  svg.innerHTML=bands.map(x=>`<rect x="${l}" y="${y(x.to)}" width="${w-l-r}" height="${y(x.from)-y(x.to)}" fill="${x.color}"/><text x="${w-r+8}" y="${(y(x.to)+y(x.from))/2+4}" class="chart-label">${x.label}</text>`).join('')+
    [0,20,35,55,70,100].map(v=>`<line x1="${l}" y1="${y(v)}" x2="${w-r}" y2="${y(v)}" class="chart-grid"/><text x="8" y="${y(v)+4}" class="chart-label">${v}</text>`).join('')+
    `<line x1="${l+24}" y1="${y(score)}" x2="${l+170}" y2="${y(score)}" class="score-line"/><circle cx="${l+24}" cy="${y(score)}" r="7" class="score-dot"/><text x="${l+40}" y="${y(score)-10}" class="score-text">${score} — 기산일</text>`;
}

function priceCard(title,data){
  return `<article class="price-card"><div class="price-head"><h3>${title}</h3><span>${data.direction}</span></div><div class="price-table">${data.items.map(([a,b,c])=>`<div><b>${a}</b><span>${b}</span><em>${c}</em></div>`).join('')}</div><p>${data.verdict}</p></article>`;
}

function boardRow(item){return `<div class="board-row"><span class="num">${item.number}</span><b>${item.title}</b><span class="status ${item.status.toLowerCase()}">${STATUS[item.status]}</span><p>${item.summary}</p></div>`}

function detailCard(item){
  return `<details class="detail-card ${item.status}" id="${item.id}"><summary><span class="num">${item.number}</span><div><h3>${item.title}</h3><p>${item.summary}</p></div><span class="status ${item.status.toLowerCase()}">${STATUS[item.status]}</span></summary><div class="detail-body"><p class="description">${item.description}</p><div class="check-table"><div class="check-head"><b>확인할 체크 요소</b><b>기록된 상태 · 근거 날짜</b></div>${item.checks.map(([a,b])=>`<div><b>□ ${a}</b><span>${b}</span></div>`).join('')}</div><p class="verdict"><b>판정</b> ${item.verdict}</p><div class="conditions"><span><b>완화</b> ${item.ease}</span><span><b>강화</b> ${item.escalate}</span></div></div></details>`;
}

function verticalBars(el,data,suffix='%'){
  const max=Math.max(...data.values.map(v=>Math.abs(v)),1);
  el.innerHTML=data.labels.map((label,i)=>{const v=data.values[i],height=Math.max(5,Math.abs(v)/max*120);return `<div class="vbar-item"><span class="vvalue">${v>0?'+':''}${v}${suffix}</span><div class="vbar-track"><i class="${v<0?'negative':''}" style="height:${height}px"></i></div><b>${label}</b></div>`}).join('');
}

function horizontalBars(el,data){
  const max=Math.max(...data.values.map(v=>Math.abs(v)),1);
  el.innerHTML=data.labels.map((label,i)=>{const v=data.values[i],width=Math.abs(v)/max*100;return `<div class="hbar-item"><b>${label}</b><div class="hbar-track"><i class="${v<0?'negative':''}" style="width:${width}%"></i></div><span>${v>0?'+':''}${v}%</span></div>`}).join('');
}

function dualLineChart(el,data){
  const w=760,h=210,l=52,r=52,t=18,b=34,innerW=w-l-r,innerH=h-t-b;
  const extent=a=>[Math.min(...a),Math.max(...a)];
  const [rMin,rMax]=extent(data.rate),[sMin,sMax]=extent(data.sox);
  const x=i=>l+innerW*(i/(data.labels.length-1));
  const y=(v,min,max)=>t+innerH*(1-(v-min)/(max-min||1));
  const ratePts=data.rate.map((v,i)=>`${x(i)},${y(v,rMin,rMax)}`).join(' ');
  const soxPts=data.sox.map((v,i)=>`${x(i)},${y(v,sMin,sMax)}`).join(' ');
  el.innerHTML=[0,.5,1].map(p=>`<line x1="${l}" y1="${t+innerH*p}" x2="${w-r}" y2="${t+innerH*p}" class="chart-grid"/>`).join('')+
    `<polyline points="${ratePts}" class="line rate-line"/><polyline points="${soxPts}" class="line sox-line"/>`+
    data.labels.map((v,i)=>`<text x="${x(i)}" y="${h-10}" text-anchor="middle" class="chart-label">${v}</text>`).join('')+
    `<text x="${l}" y="12" class="rate-text">미 10Y ${data.rate.at(-1)}%</text><text x="${w-r-110}" y="12" class="sox-text">SOX ${data.sox.at(-1)}</text>`;
}

function koreaCard(k){return `<article class="korea-card"><div class="card-title"><h3>${k.title}</h3><span class="status ${k.status.toLowerCase()}">${STATUS[k.status]}</span></div><p class="muted">${k.note}</p><div class="check-table">${k.checks.map(([a,b])=>`<div><b>□ ${a}</b><span>${b}</span></div>`).join('')}</div><p class="verdict"><b>판정</b> ${k.verdict}</p></article>`}

function autoCard(item){
  const value=item.value==null?'값 없음':`${fmt(item.value)}${item.unit?' '+item.unit:''}`;
  return `<article class="auto-card ${item.status}"><div class="card-title"><h3>${item.title}</h3><span class="status ${item.status.toLowerCase()}">${STATUS[item.status]}</span></div><p>${item.reason}</p><small><b>대리변수</b> ${item.proxy}</small><small><b>한계</b> ${item.limitation}</small><div class="auto-meta"><span>${value}</span><span>${item.observed_at||'관측일 없음'}</span><a href="${item.source_url}" target="_blank" rel="noreferrer">근거 ↗</a></div></article>`;
}

function renderChecklist(d){
  const s=d.summary;
  document.querySelector('#level').textContent=s.level;
  document.querySelector('#level-label').textContent=s.label;
  document.querySelector('#score').textContent=s.overall;
  document.querySelector('#macro-score').textContent=s.macro.score;
  document.querySelector('#ai-score').textContent=s.ai.score;
  document.querySelector('#macro-counts').textContent=countsText(s.macro.counts);
  document.querySelector('#ai-counts').textContent=countsText(s.ai.counts);
  document.querySelector('#macro-bar').style.width=`${s.macro.score}%`;
  document.querySelector('#ai-bar').style.width=`${s.ai.score}%`;
  document.querySelector('#asof').textContent=`기준일 ${d.as_of} · 발행 ${d.published_at} · 체크리스트 ${d.version} · 22항목 · 확인률 100%`;
  renderReferenceChart(s.overall);
  document.querySelector('#macro-price').innerHTML=priceCard('매크로단 가격 반응',d.price_board.macro);
  document.querySelector('#ai-price').innerHTML=priceCard('AI단 가격 반응',d.price_board.ai);
  document.querySelector('#divergence').textContent=`⚠ 괴리 판독: ${d.price_board.divergence}`;
  const macro=d.items.filter(x=>x.axis==='macro'),ai=d.items.filter(x=>x.axis==='ai');
  document.querySelector('#macro-board').innerHTML=macro.map(boardRow).join('');
  document.querySelector('#ai-board').innerHTML=ai.map(boardRow).join('');
  document.querySelector('#macro-details').innerHTML=macro.map(detailCard).join('');
  document.querySelector('#ai-details').innerHTML=ai.map(detailCard).join('');
  document.querySelector('#korea-card').innerHTML=koreaCard(d.korea_discount);
  verticalBars(document.querySelector('#fedwatch-chart'),d.charts.fedwatch,'%');
  verticalBars(document.querySelector('#etf-chart'),d.charts.etf,'');
  horizontalBars(document.querySelector('#cds-chart'),d.charts.cds);
  dualLineChart(document.querySelector('#rate-sox-chart'),d.charts.rate_sox);
  document.querySelector('#rate-sox-note').textContent=d.charts.rate_sox.note;
  document.querySelector('#glossary').innerHTML=d.glossary.map(([term,meaning])=>`<div><b>${term}</b><span>${meaning}</span></div>`).join('');
}

function renderAutomatic(d){
  const s=d.summary;
  document.querySelector('#auto-overall').textContent=s.overall.score??'B';
  document.querySelector('#auto-macro').textContent=s.macro.score??'B';
  document.querySelector('#auto-ai').textContent=s.ai.score??'B';
  document.querySelector('#auto-coverage').textContent=`${s.overall.coverage}%`;
  document.querySelector('#auto-asof').textContent=`기준일 ${d.as_of} · 생성 ${d.generated_at} · B ${s.overall.counts.B}개`;
  document.querySelector('#auto-macro-cards').innerHTML=d.items.filter(x=>x.axis==='macro').map(autoCard).join('');
  document.querySelector('#auto-ai-cards').innerHTML=d.items.filter(x=>x.axis==='ai').map(autoCard).join('');
}

document.querySelectorAll('.tab').forEach(btn=>btn.addEventListener('click',()=>{
  document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x===btn));
  const original=btn.dataset.target==='original';
  document.querySelector('#original-view').hidden=!original;
  document.querySelector('#automatic-view').hidden=original;
}));

Promise.all([
  fetch('data/checklist.json').then(r=>{if(!r.ok)throw Error('원본 체크리스트 없음');return r.json()}),
  fetch('data/latest.json').then(r=>{if(!r.ok)throw Error('자동 데이터 없음');return r.json()})
]).then(([checklist,automatic])=>{renderChecklist(checklist);renderAutomatic(automatic)}).catch(err=>{
  document.querySelector('#asof').textContent=`데이터를 불러오지 못했습니다: ${err.message}`;
});

