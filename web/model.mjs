export const metrics = [
  {key:'adult', name:'Natural adult spawners', note:'Adults spawning naturally. DFO records early-maturing jacks separately.'},
  {key:'natural', name:'Total natural spawners', note:'DFO’s reported total for naturally spawning adults and jacks. An unreported total stays blank even when an adult estimate exists.'},
  {key:'river', name:'Total return to river', note:'DFO’s wider freshwater return estimate can include natural spawners, hatchery broodstock, other removals and unspecified returns.'},
  {key:'legacy', name:'Unspecified returns', note:'Historical estimates where the age group or accounting basis is uncertain. Use this measure to explore older records without mixing definitions.'},
];
export const presets = {
  chilliwack:{id:'46982-62',metric:'legacy'},
  adams:{id:'46239-220',metric:'adult'},
  yorkson:{id:'47959-26',metric:'legacy'},
  nathan:{id:'47988-31',metric:'legacy'}
};
export function unpack(row) {
  const [id,name,water,species,area,run]=row;
  return {id,name,water,species,area,run,search:[name,water,id,area].join(' ').toLocaleLowerCase()};
}
export function matching(items, query, species='', area='') {
  const words=query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  return items.filter(item=>(!species || item.species===species) && (!area || item.area===area) && words.every(word=>item.search.includes(word)));
}
export function yearsFor(histories, period, lastSourceYear) {
  const records=histories.flat();
  const lo=period==='all' ? Math.min(...records.map(r=>r[0])) : lastSourceYear-Number(period)+1;
  const hi=period==='all' ? Math.max(...records.map(r=>r[0])) : lastSourceYear;
  return Array.from({length:hi-lo+1},(_,i)=>lo+i);
}
export function continuousRuns(points) {
  const runs=[];
  let previous=null;
  for (const [year,value] of points) {
    if (value===null) { previous=null; continue; }
    if (previous!==year-1) runs.push([]);
    runs.at(-1).push([year,value]);
    previous=year;
  }
  return runs;
}
export function csv(rows) {
  return rows.map(row=>row.map(value=>'"'+String(value??'').replaceAll('"','""')+'"').join(',')).join('\r\n')+'\r\n';
}
