import * as duckdb from 'https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.30.0/+esm';

const $ = selector => document.querySelector(selector);
const notice = $('#notice');
const total = $('#total');
const count = $('#map-count');
const detail = $('#detail');
const chips = [...document.querySelectorAll('[data-band]')];
const map = new maplibregl.Map({container:'map',style:'https://tiles.openfreemap.org/styles/bright',center:[7.438,51.493],zoom:11});
map.addControl(new maplibregl.NavigationControl(), 'top-right');
map.on('error', e => console.error('MapLibre tile/style error',e.error));
window.opencommMap = map; // Public map only; useful for inspecting rendering.
let conn, mapReady=false, band='all', dataReady=false;
const empty={type:'FeatureCollection',features:[]};
map.on('load',()=>{
  map.addSource('observations',{type:'geojson',data:empty});
  map.addLayer({id:'measured',type:'circle',source:'observations',paint:{
    'circle-color':['case',['>=',['get','rsrp_dbm'],-85],'#117e72',['>=',['get','rsrp_dbm'],-105],'#3b9eae','#d79b57'],
    'circle-radius':['interpolate',['linear'],['zoom'],9,3,13,6],
    'circle-opacity':0.76,'circle-stroke-color':'#fff','circle-stroke-width':0.9
  }});
  map.on('mouseenter','measured',()=>{map.getCanvas().style.cursor='pointer'});
  map.on('mouseleave','measured',()=>{map.getCanvas().style.cursor='' });
  mapReady=true;
  if(dataReady) void refresh();
});
map.on('click','measured',e=>{
  const f=e.features?.[0]; if(!f)return;
  const p=f.properties;
  $('#detail-value').textContent=Number(p.rsrp_dbm).toFixed(1);
  $('#detail-dot').className='dot '+(p.rsrp_dbm>=-85?'high':p.rsrp_dbm>=-105?'mid':'low');
  $('#detail-extra').hidden=true;$('#detail-more').setAttribute('aria-expanded','false');
  $('#detail-time').textContent=p.measured_at || 'Not recorded';
  $('#detail-radio').textContent=p.radio || 'Not recorded';
  $('#detail-row').textContent=p.source_record_id || 'Not recorded';
  detail.hidden=false;
});
$('#detail-close').addEventListener('click',()=>{detail.hidden=true});
$('#detail-more').addEventListener('click',()=>{const opened=$('#detail-extra').hidden;$('#detail-extra').hidden=!opened;$('#detail-more').setAttribute('aria-expanded',String(opened));$('#detail-more').textContent=opened?'Hide details ⌃':'Source details ⌄'});
$('#reset').addEventListener('click',()=>{
  if(window.matchMedia('(prefers-reduced-motion: reduce)').matches)map.jumpTo({center:[7.438,51.493],zoom:11});
  else map.flyTo({center:[7.438,51.493],zoom:11,duration:850,essential:false});
  detail.hidden=true;
});
for(const chip of chips)chip.addEventListener('click',()=>{
  band=chip.dataset.band;
  for(const button of chips){const active=button===chip;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active))}
  detail.hidden=true;
  void refresh().catch(showError);
});
function showError(error){notice.classList.add('error');notice.textContent='Could not read local data. Reload the page or try a modern browser.';console.error(error)}
async function refresh(){
  if(!conn||!mapReady)return;
  const predicate={all:'TRUE',high:'rsrp_dbm >= -85',mid:'rsrp_dbm >= -105 AND rsrp_dbm < -85',low:'rsrp_dbm < -105'}[band];
  // band is selected only from this closed set; no external text enters SQL.
  const result=await conn.query(`SELECT source,source_record_id,knowledge_grade,country_code,radio,lon,lat,rsrp_dbm,measured_at FROM observations WHERE ${predicate} AND lon BETWEEN -180 AND 180 AND lat BETWEEN -90 AND 90 ORDER BY source_record_id LIMIT 2000`);
  const rows=result.toArray().map(row=>row.toJSON());
  const features=rows.map(r=>({type:'Feature',geometry:{type:'Point',coordinates:[r.lon,r.lat]},properties:{source:r.source,source_record_id:r.source_record_id,knowledge_grade:r.knowledge_grade,country_code:r.country_code,radio:r.radio,rsrp_dbm:r.rsrp_dbm,measured_at:r.measured_at?String(r.measured_at):''}}));
  map.getSource('observations').setData({type:'FeatureCollection',features});
  count.textContent=rows.length?`${rows.length.toLocaleString()} points shown · max 2,000`:'No points in this band';
}
async function boot(){
  const bundle=await duckdb.selectBundle(duckdb.getJsDelivrBundles());
  const workerURL=URL.createObjectURL(new Blob([`importScripts(${JSON.stringify(bundle.mainWorker)});`],{type:'text/javascript'}));
  const worker=new Worker(workerURL);
  const db=new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(),worker);
  await db.instantiate(bundle.mainModule,bundle.pthreadWorker);
  URL.revokeObjectURL(workerURL);
  const response=await fetch(new URL('./assets/observations.parquet',import.meta.url));
  if(!response.ok)throw new Error(`Parquet fetch HTTP ${response.status}`);
  await db.registerFileBuffer('observations.parquet',new Uint8Array(await response.arrayBuffer()));
  conn=await db.connect();
  await conn.query("CREATE VIEW observations AS SELECT * FROM read_parquet('observations.parquet')");
  const result=await conn.query('SELECT count(*) AS n FROM observations');
  const n=Number(result.toArray()[0].n);
  total.textContent=n.toLocaleString();
  dataReady=true;
  notice.textContent=n?'Measured RF · DoNext H-Bahn · no inferred coverage':'No licensed observations loaded yet';
  await refresh();
}
boot().catch(showError);
