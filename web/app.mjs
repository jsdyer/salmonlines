import {metrics,presets,unpack,matching,yearsFor,continuousRuns,csv} from './model.mjs';

const $ = id => document.getElementById(id);
const elem = (type,text) => { const node=document.createElement(type); if(text!==undefined) node.textContent=text; return node; };
const number = new Intl.NumberFormat('en-CA',{maximumFractionDigits:3});
const svgNS='http://www.w3.org/2000/svg';
const svgNode=(type,attrs,text) => {
  const node=document.createElementNS(svgNS,type);
  for (const [key,val] of Object.entries(attrs)) node.setAttribute(key,val);
  if(text!==undefined) node.textContent=text;
  return node;
};
const colours=['#1d5850','#a43e29'];
let index=[], byId=new Map(), source, selected, comparison, active=[], years=[], version=0;
const cache=new Map();
const view=new URLSearchParams(location.hash.slice(1));
const metricPosition=()=>1+metrics.findIndex(item=>item.key===$('metric').value);

async function json(name) {
  const response=await fetch('./data/'+name+'.json');
  if(!response.ok) throw new Error('Snapshot unavailable');
  return response.json();
}
async function history(item) {
  const shard=Number(item.id.split('-')[0])%source.shards;
  if(!cache.has(shard)) cache.set(shard,json('observations-'+shard).catch(error=>{cache.delete(shard);throw error;}));
  const data=await cache.get(shard);
  if(!data[item.id]) throw new Error('Series missing');
  return new Map(data[item.id].map(row=>[row[0],row]));
}
function filterList() {
  const matches=matching(index,$('search').value,$('species').value,$('area').value);
  $('matches').textContent=matches.length ? number.format(matches.length)+' matches'+(matches.length>45?' · first 45 shown':'') : 'No matching populations. Try another river, species or subdistrict.';
  $('results').replaceChildren(...matches.slice(0,45).map(item=>{
    const button=elem('button',item.name);
    button.setAttribute('aria-pressed',String(selected?.id===item.id));
    button.append(elem('small',item.water+' · '+(item.area||'Unlisted area')+' · '+item.id));
    button.onclick=()=>choose(item.id);
    return button;
  }));
}
function comparisonOptions() {
  const area=selected.area;
  const items=matching(index,$('compare-search').value,selected.species).filter(item=>item.id!==selected.id);
  // The source publishes subdistricts, which are a coarse way to find neighbours.
  items.sort((a,b)=>Number(b.area===area)-Number(a.area===area));
  const options=items.slice(0,70);
  if(comparison && !options.includes(comparison)) options.unshift(comparison);
  $('compare').replaceChildren(new Option('Single population',''),...options.map(item=>new Option(item.name+' · '+item.id,item.id)));
  $('compare').value=comparison?.id||'';
  $('compare-count').textContent=number.format(items.length)+' same-species matches. Same-subdistrict records appear first. Type a waterbody or ID to narrow the list.';
}
function choose(id, second='', metric) {
  selected=byId.get(id)||byId.get(presets.adams.id)||index[0];
  comparison=byId.get(second);
  if(comparison===selected||comparison?.species!==selected.species) comparison=null;
  if(metric && metrics.some(m=>m.key===metric)) $('metric').value=metric;
  $('compare-search').value='';
  comparisonOptions();
  filterList();
  update();
}
function urlForView() {
  const params=new URLSearchParams({series:selected.id,measure:$('metric').value,period:$('period').value});
  if(comparison) params.set('compare',comparison.id);
  const url=new URL(location.href);
  url.hash=params.toString();
  return url;
}
function renderChart() {
  const pos=metricPosition();
  const points=active.map(({records})=>years.map(year=>[year,records.get(year)?.[pos]??null]));
  const vals=points.flat().map(point=>point[1]).filter(value=>value!==null);
  const plot=$('plot');plot.replaceChildren();
  if(!vals.length) {
    plot.append(elem('p','No numerical estimates for this measure and period. Try another measure or inspect the annual source records below.'));
    return;
  }
  const width=670,height=244,left=64,right=19,top=22,bottom=39;
  const maximum=Math.max(...vals,1);
  const x=year=>left+(years.length===1?.5:(year-years[0])/(years.length-1))*(width-left-right);
  const y=value=>height-bottom-value/maximum*(height-top-bottom);
  const chart=svgNode('svg',{viewBox:'0 0 '+width+' '+height,role:'img','aria-label':$('metric').selectedOptions[0].text+' by analysis year. Exact estimates available in the records table.'});
  for(let i=0;i<5;i++) {
    const value=maximum*i/4;
    chart.append(svgNode('line',{x1:left,x2:width-right,y1:y(value),y2:y(value),stroke:'#dbe1d8'}));
    const tick=new Intl.NumberFormat('en-CA',{notation:'compact',maximumFractionDigits:2}).format(value);
    chart.append(svgNode('text',{x:left-9,y:y(value)+4,'text-anchor':'end',fill:'#48625b','font-size':13},tick));
  }
  const yearTicks=new Set(Array.from({length:Math.min(6,years.length)},(_,i)=>years[Math.round(i*(years.length-1)/Math.max(1,Math.min(6,years.length)-1))]));
  for(const year of yearTicks) chart.append(svgNode('text',{x:x(year),y:height-12,'text-anchor':'middle',fill:'#48625b','font-size':13},year));
  points.forEach((values,i)=>{
    for(const segment of continuousRuns(values)) {
      const coords=segment.map(([year,value])=>x(year)+','+y(value)).join(' ');
      chart.append(svgNode('polyline',{points:coords,fill:'none',stroke:colours[i],'stroke-width':2.2,'stroke-dasharray':i?'6 3':'none'}));
      for(const [year,value] of segment) {
        const mark=svgNode('circle',{cx:x(year),cy:y(value),r:3.1,fill:i?'#fffdf7':colours[i],stroke:colours[i],'stroke-width':1.6});
        mark.append(svgNode('title',{},active[i].item.name+' · '+year+' · '+number.format(value)));
        chart.append(mark);
      }
    }
  });
  plot.append(chart);
}
function yearRows() {
  const pos=metricPosition();
  return [...years].reverse().flatMap(year=>active.map(({item,records})=>{
    const row=records.get(year);
    return {item,year,value:row?.[pos]??null,presence:row?(source.presence[row[5]]||'Unspecified'):'No source row',method:row?(source.methods[row[6]]||''):'',hasRow:!!row};
  }));
}
function display() {
  const pos=metricPosition();
  years=yearsFor(active.map(s=>Array.from(s.records.values())),$('period').value,source.years[1]);
  $('location').textContent=selected.water+' · '+selected.species;
  $('title').textContent=selected.name;
  $('identity').textContent='Population '+selected.id.split('-')[0]+' · Waterbody '+selected.id.split('-')[1]+' · DFO subdistrict '+(selected.area||'unknown')+(selected.run?' · Run '+selected.run:'');
  $('definition').textContent=metrics[pos-1].note;
  $('legend').replaceChildren(...active.map(({item},i)=>{const n=elem('span',item.name);n.className='key'+(i?' second':'');return n;}));
  $('river-reading').replaceChildren(...active.map(({item,records}) => {
    const values = years.filter(year => Number.isFinite(records.get(year)?.[pos]));
    const measure = metrics[pos-1].name.toLowerCase();
    if (!values.length) return elem('p', item.name + ' has no numerical estimate for ' + measure + ' in the selected years. Open the source records below to check inspections and adult presence.');
    const last = values.at(-1);
    const previous = values.at(-2);
    let reading = item.name + ' · ' + metrics[pos-1].name + '. DFO’s latest estimate in this view is ' + number.format(records.get(last)[pos]) + ' fish in ' + last + '.';
    if (previous !== undefined) reading += ' Its preceding published estimate was ' + number.format(records.get(previous)[pos]) + ' in ' + previous + '.';
    return elem('p', reading);
  }));
  renderChart();
  $('coverage').textContent=active.map(({item,records})=>number.format(years.filter(year=>records.get(year)?.[pos]!=null).length)+' of '+years.length+' years have numerical estimates for '+item.name).join('. ')+'.';
  $('table-head').replaceChildren();
  const headers=elem('tr');for(const h of ['Year','Population','Estimate','Adult presence','Survey methods']) headers.append(elem('th',h));$('table-head').append(headers);
  $('table-body').replaceChildren(...yearRows().map(row=>{
    const tr=elem('tr');
    for(const val of [row.year,row.item.name,row.value===null?'—':number.format(row.value),row.presence,row.method||'—']) tr.append(elem('td',val));
    return tr;
  }));
  const showCrossing = selected.id === '46982-62';
  $('crossing-note').hidden = !showCrossing;
  if (showCrossing) {
    const lastYear = Math.max(...active[0].records.keys());
    $('crossing-years').textContent = lastYear < 2016
      ? 'The latest published year for this population is ' + lastYear + ', before the 2016 repair.'
      : 'The latest published year for this population is ' + lastYear + '.';
  }
  $('water').hidden=selected.water!=='YORKSON CREEK'||selected.area!=='29B';
}
async function update() {
  const token=++version;
  $('status').textContent='Loading selected history…';$('status').hidden=false;$('history').hidden=true;
  $('action-status').value='';
  try {
    const next=await Promise.all([selected,comparison].filter(Boolean).map(async item=>({item,records:await history(item)})));
    if(token!==version) return;
    active=next;
    display();
    $('status').hidden=true;$('history').hidden=false;
    window.history.replaceState(null,'',urlForView());
  } catch {
    if(token===version) $('status').textContent='This history could not load. Select the population again to retry, or use the DFO source below.';
  }
}
async function start() {
  [source,index]=await Promise.all([json('source'),json('index')]);
  index=index.map(unpack);
  byId=new Map(index.map(item=>[item.id,item]));
  for(const [id,prop] of [['species','species'],['area','area']]) {
    const values=[...new Set(index.map(item=>item[prop]).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'en',{numeric:true}));
    for(const val of values) $(id).add(new Option(val,val));
    $(id).onchange=filterList;
  }
  $('search').oninput=filterList;
  for(const metric of metrics) $('metric').add(new Option(metric.name,metric.key));
  $('metric').onchange=update;$('period').onchange=update;
  $('compare-search').oninput=comparisonOptions;
  $('compare').onchange=()=>{comparison=byId.get($('compare').value)||null;update();};
  for(const button of document.querySelectorAll('[data-preset]')) {
    button.onclick=()=>{
      const preset=presets[button.dataset.preset];
      $('search').value=byId.get(preset.id).water;$('species').value='';$('area').value='';$('period').value='all';choose(preset.id,'',preset.metric);
    };
  }
  $('share').onclick=async()=>{
    const url=urlForView().href;
    try {await navigator.clipboard.writeText(url);$('action-status').value='View link copied.';}
    catch {$('action-status').value=url;}
  };
  $('export').onclick=()=>{
    const rows=[['analysis_year','population_id','waterbody_id','population','measure','estimate','source_row','adult_presence','enumeration_methods','source_edition']];
    for(const r of yearRows()) rows.push([r.year,...r.item.id.split('-'),r.item.name,source.measures[metricPosition()-1],r.value,r.hasRow,r.presence,r.method,source.edition]);
    const url=URL.createObjectURL(new Blob([csv(rows)],{type:'text/csv;charset=utf-8'}));
    const a=elem('a');a.href=url;a.download='salmon-lines-'+selected.id+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  $('raw').href=source.url;$('raw').hidden=false;
  $('provenance').textContent=number.format(source.rows)+' annual records across '+number.format(source.populations)+' DFO populations in the all-areas Pacific release, including BC, Yukon and transboundary waters. Analysis years '+source.years.join('–')+'. DFO edition '+source.edition+' · '+(source.retrieved ? 'Snapshot retrieved '+source.retrieved : 'Retrieval date unrecorded')+' · Site built '+source.build_date+'.';
  if(['25','10'].includes(view.get('period'))) $('period').value=view.get('period');
  choose(view.get('series')||presets.adams.id,view.get('compare'),view.get('measure')||'adult');
}
start().catch(()=>{$('status').textContent='The population index could not load. Reload to retry or download the original data from DFO below.';});
