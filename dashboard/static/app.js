// ── Tabs ─────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
  });
});

// ── WebSocket ────────────────────────────────
let ws = null, reconnectTimer = null;

function connect() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onopen = () => { clearTimeout(reconnectTimer); };
  ws.onmessage = e => handleMessage(JSON.parse(e.data));
  ws.onclose = () => { reconnectTimer = setTimeout(connect, 3000); };
  ws.onerror = () => ws.close();
}

function handleMessage(m) {
  const h = { tick:onTick, signal:onSignal, signal_result:onSignalResult, log:onLog, status:onStatus, history:onHistory, new_period:onNewPeriod };
  if (h[m.type]) h[m.type](m.data);
  else if (m.type === 'error') onLog({level:'ERROR', msg:m.data.msg, ts:''});
}

// ── Charts ───────────────────────────────────
const mono = "'JetBrains Mono',monospace";
const gridColor = 'rgba(35,35,40,0.6)';

const baseScales = {
  x: { type:'time', time:{unit:'minute',displayFormats:{minute:'HH:mm'}}, grid:{color:gridColor,drawBorder:false}, ticks:{color:'#5a5a64',maxTicksLimit:6,font:{family:mono,size:10}}, border:{display:false} },
  y: { grid:{color:gridColor,drawBorder:false}, ticks:{color:'#5a5a64',font:{family:mono,size:10}}, border:{display:false} }
};

const priceChart = new Chart(document.getElementById('priceChart'), {
  type:'line',
  data:{datasets:[{
    data:[], borderColor:'#f7931a', backgroundColor:'rgba(247,147,26,0.04)',
    borderWidth:1.5, pointRadius:0, pointHitRadius:6, fill:true, tension:0.2
  }]},
  options:{responsive:true, maintainAspectRatio:false, animation:false, scales:baseScales, plugins:{legend:{display:false},tooltip:{mode:'index',intersect:false,backgroundColor:'#19191d',titleColor:'#f0f0f0',bodyColor:'#9898a0',borderColor:'#232328',borderWidth:1}}}
});

const oddsChart = new Chart(document.getElementById('oddsChart'), {
  type:'line',
  data:{datasets:[
    {label:'UP', data:[], borderColor:'#00dc82', borderWidth:1.5, pointRadius:0, pointHitRadius:6, tension:0.2},
    {label:'DOWN', data:[], borderColor:'#ff3b5c', borderWidth:1.5, pointRadius:0, pointHitRadius:6, tension:0.2}
  ]},
  options:{responsive:true, maintainAspectRatio:false, animation:false,
    scales:{...baseScales, y:{...baseScales.y, min:0, max:1, ticks:{...baseScales.y.ticks, callback:v=>(v*100)+'%'}}},
    plugins:{legend:{labels:{color:'#9898a0',font:{family:mono,size:10},usePointStyle:true,pointStyle:'line',padding:16,boxWidth:20}},tooltip:{mode:'index',intersect:false,backgroundColor:'#19191d',titleColor:'#f0f0f0',bodyColor:'#9898a0',borderColor:'#232328',borderWidth:1}}}
});

const MAX_PTS = 200;
function push(c,i,x,y){const d=c.data.datasets[i].data;d.push({x,y});if(d.length>MAX_PTS)d.shift();c.update('none');}

// ── Audit Pie ────────────────────────────────
const auditPie = new Chart(document.getElementById('auditPie'), {
  type:'doughnut',
  data:{labels:['WIN','LOSS'],datasets:[{data:[0,0],backgroundColor:['#00dc82','#ff3b5c'],borderWidth:0,borderRadius:4}]},
  options:{responsive:true,maintainAspectRatio:true,cutout:'72%',plugins:{legend:{display:false},tooltip:{enabled:true,backgroundColor:'#19191d',titleColor:'#f0f0f0',bodyColor:'#9898a0',borderColor:'#232328',borderWidth:1}},animation:{duration:300}}
});

// ── State ────────────────────────────────────
let signalCount=0, positionCount=0, auditW=0, auditL=0, lastPrice=null;

// ── Handlers ─────────────────────────────────
function onTick(d){
  const ts=d.ts*1000;
  push(priceChart,0,ts,d.price);
  push(oddsChart,0,ts,d.up_odds);
  push(oddsChart,1,ts,d.down_odds);

  // Hero price
  const el=document.getElementById('sPrice');
  el.textContent='$'+d.price.toLocaleString(undefined,{minimumFractionDigits:2});
  el.classList.remove('flash-up','flash-down');
  void el.offsetWidth;
  if(lastPrice!==null){
    el.classList.add(d.price>=lastPrice?'flash-up':'flash-down');
  }
  lastPrice=d.price;

  // Hero pulse
  const hero=document.getElementById('hero');
  hero.classList.remove('pulse');
  void hero.offsetWidth;
  hero.classList.add('pulse');
  setTimeout(()=>hero.classList.remove('pulse'),800);

  // Change
  const ch=document.getElementById('sChange');
  ch.textContent=(d.change_bps>=0?'+':'')+d.change_bps.toFixed(1)+' bp';
  ch.className='value '+(d.change_bps>0?'down':d.change_bps<0?'up':'');

  // Odds
  document.getElementById('sUp').textContent=(d.up_odds*100).toFixed(1)+'%';
  document.getElementById('sDown').textContent=(d.down_odds*100).toFixed(1)+'%';

  // Win rate & P/L
  updateStatsBar();
}

function updateStatsBar(){
  const total=auditW+auditL;
  document.getElementById('sWinRate').textContent=total>0?((auditW/total)*100).toFixed(0)+'%':'--';
  const pnl=auditW-auditL;
  const pnlEl=document.getElementById('sPnl');
  pnlEl.textContent=total>0?(pnl>=0?'+':'')+pnl:'--';
  pnlEl.className='stat-value '+(pnl>0?'green':pnl<0?'red':'');
}

function onSignal(d){
  signalCount++; positionCount++;
  document.getElementById('sSignals').textContent=signalCount;
  document.getElementById('sPositions').textContent=positionCount;
  const tr=document.createElement('tr');
  tr.innerHTML=`<td>${d.ts}</td><td class="${d.side==='YES'?'c-up':'c-down'}">${d.side}</td><td>${d.reason}</td>`;
  document.getElementById('signalsBody').prepend(tr);
}

function onSignalResult(d){
  if(d.result==='WIN') auditW++; else auditL++;
  updateAudit();
  updateStatsBar();
  const tr=document.createElement('tr');
  const sc=d.side==='YES'?'c-up':'c-down', rc=d.result==='WIN'?'c-up':'c-down';
  tr.innerHTML=`<td>${d.ts}</td><td class="${sc}">${d.side}</td><td class="${rc}">${d.result}</td>`
    +`<td>$${d.start_price.toLocaleString(undefined,{minimumFractionDigits:2})}</td>`
    +`<td>$${d.end_price.toLocaleString(undefined,{minimumFractionDigits:2})}</td>`
    +`<td>${d.change_bps>=0?'+':''}${d.change_bps} bp</td><td>${d.reason}</td>`;
  document.getElementById('auditBody').prepend(tr);
}

function updateAudit(){
  const t=auditW+auditL, r=t>0?((auditW/t)*100).toFixed(1):'--';
  document.getElementById('auditRate').textContent=t>0?r+'%':'--';
  document.getElementById('auditWins').textContent=auditW;
  document.getElementById('auditLosses').textContent=auditL;
  document.getElementById('auditTotal').textContent=t;
  auditPie.data.datasets[0].data=[auditW,auditL];
  auditPie.update();
}

function onLog(d){
  const body=document.getElementById('logBody');
  const div=document.createElement('div');
  div.className='log-line';
  const ts=d.ts?`<span class="ts">[${d.ts}]</span> `:'';
  div.innerHTML=`${ts}<span class="lv lv-${d.level}">[${d.level}]</span> <span class="msg">${d.msg.replace(/&/g,'&amp;').replace(/</g,'&lt;')}</span>`;
  body.appendChild(div);
  body.scrollTop=body.scrollHeight;
  while(body.children.length>500) body.removeChild(body.firstChild);
}

function onStatus(d){
  const b=document.getElementById('badge');
  if(d.running){
    b.textContent=d.dry_run?'DRY RUN':'LIVE';
    b.className='status '+(d.dry_run?'dry':'running');
    document.getElementById('btnStart').disabled=true;
    document.getElementById('btnStop').disabled=false;
  }else{
    b.textContent='STOPPED';
    b.className='status stopped';
    document.getElementById('btnStart').disabled=false;
    document.getElementById('btnStop').disabled=true;
  }
}

function onHistory(d){
  if(d.prices) d.prices.forEach(p=>push(priceChart,0,p.ts*1000,p.price));
  if(d.odds) d.odds.forEach(o=>{push(oddsChart,0,o.ts*1000,o.up_odds);push(oddsChart,1,o.ts*1000,o.down_odds);});
  if(d.logs) d.logs.forEach(l=>onLog(l));
  if(d.signals){
    d.signals.forEach(s=>{
      signalCount++;
      const tr=document.createElement('tr');
      tr.innerHTML=`<td>${s.ts}</td><td class="${s.side==='YES'?'c-up':'c-down'}">${s.side}</td><td>${s.reason}</td>`;
      document.getElementById('signalsBody').appendChild(tr);
    });
    document.getElementById('sSignals').textContent=signalCount;
  }
  if(d.signal_audit) d.signal_audit.forEach(a=>onSignalResult(a));
  if(d.running!==undefined) onStatus({running:d.running,dry_run:d.dry_run});
}

function onNewPeriod(d){
  priceChart.data.datasets[0].data=[];
  oddsChart.data.datasets[0].data=[];
  oddsChart.data.datasets[1].data=[];
  priceChart.update('none'); oddsChart.update('none');
  signalCount=0; lastPrice=null;
  document.getElementById('sSignals').textContent='0';
  document.getElementById('signalsBody').innerHTML='';
  onLog({level:'INFO',msg:`--- NEW PERIOD: ${d.slug} ---`,ts:''});
}

function doStart(){if(ws&&ws.readyState===1) ws.send(JSON.stringify({action:'start',dry_run:document.getElementById('dryRun').checked}));}
function doStop(){if(ws&&ws.readyState===1) ws.send(JSON.stringify({action:'stop'}));}
function clearLog(){document.getElementById('logBody').innerHTML='';}

connect();
