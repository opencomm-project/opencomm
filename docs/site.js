import * as duckdb from 'https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.30.0/+esm';

const notice = document.querySelector('#notice');
const total = document.querySelector('#total');
const count = document.querySelector('#map-count');
const grade = document.querySelector('#grade');
const country = document.querySelector('#country');
const map = new maplibregl.Map({container:'map',style:'https://demotiles.maplibre.org/style.json',center:[23,42],zoom:3});
map.addControl(new maplibregl.NavigationControl(), 'top-right');
let conn;
let mapReady = false;
let requested = false;
map.on('load', () => {
  map.addSource('observations', {type:'geojson',data:{type:'FeatureCollection',features:[]}});
  map.addLayer({id:'inventory',type:'circle',source:'observations',filter:['==',['get','knowledge_grade'],'inferred_inventory'],paint:{'circle-color':'#f3ba7e','circle-radius':6,'circle-stroke-color':'#09151c','circle-stroke-width':1}});
  map.addLayer({id:'measured',type:'circle',source:'observations',filter:['==',['get','knowledge_grade'],'measured_rf'],paint:{'circle-color':'#a4f1c5','circle-radius':6,'circle-stroke-color':'#09151c','circle-stroke-width':1}});
  mapReady = true;
  if(requested) void refresh();
});
map.on('click', ['inventory','measured'], e => {
  const f=e.features?.[0];
  if(!f) return;
  const p=f.properties;
  const kind=p.knowledge_grade==='measured_rf'?'Measured RF':'Inferred inventory';
  // Text content, not HTML: source labels come from external data.
  const node=document.createElement('div');
  node.textContent=`${kind} · ${p.source} · ${p.country_code}`;
  new maplibregl.Popup().setLngLat(f.geometry.coordinates).setDOMContent(node).addTo(map);
});
const safe = value => value === 'all' ? null : value;
async function refresh(){
  if (!conn || !mapReady) {requested=true;return;}
  requested=false;
  const g=safe(grade.value), c=safe(country.value);
  // Values are from closed select menus; SQL parameter binding avoids interpolation.
  const stmt=await conn.prepare(`SELECT source,knowledge_grade,country_code,lon,lat FROM observations
    WHERE (?::VARCHAR IS NULL OR knowledge_grade=?) AND (?::VARCHAR IS NULL OR country_code=?)
    AND lon BETWEEN -180 AND 180 AND lat BETWEEN -90 AND 90 LIMIT 2000`);
  let result;
  try {result=await stmt.query(g,g,c,c)} finally {await stmt.close()}
  const rows=result.toArray().map(row=>row.toJSON());
  map.getSource('observations').setData({type:'FeatureCollection',features:rows.map(r=>({type:'Feature',geometry:{type:'Point',coordinates:[r.lon,r.lat]},properties:{source:r.source,knowledge_grade:r.knowledge_grade,country_code:r.country_code}}))});
  count.textContent=rows.length===0?'No observations in this view':`${rows.length} shown (max 2,000)`;
}
for(const input of [grade,country]) input.addEventListener('change',()=>{refresh().catch(showError)});
function showError(error){notice.classList.add('error');notice.textContent='Local query failed. Reload the page or try a modern browser. No network data was changed.';console.error(error)}
async function boot(){
  const bundle=await duckdb.selectBundle(duckdb.getJsDelivrBundles());
  const workerURL=URL.createObjectURL(new Blob([`importScripts(${JSON.stringify(bundle.mainWorker)});`],{type:'text/javascript'}));
  const worker=new Worker(workerURL);
  const db=new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(),worker);
  await db.instantiate(bundle.mainModule,bundle.pthreadWorker);
  URL.revokeObjectURL(workerURL);
  const response=await fetch(new URL('./assets/observations.parquet',import.meta.url));
  if(!response.ok) throw new Error(`Parquet fetch HTTP ${response.status}`);
  await db.registerFileBuffer('observations.parquet',new Uint8Array(await response.arrayBuffer()));
  conn=await db.connect();
  await conn.query("CREATE VIEW observations AS SELECT * FROM read_parquet('observations.parquet')");
  const result=await conn.query('SELECT count(*) AS n FROM observations');
  const n=Number(result.toArray()[0].n);
  total.textContent=n.toLocaleString();
  notice.textContent=n===0?'No licensed observations loaded yet. The map is intentionally empty.':'Showing licensed observations with explicit evidence grades.';
  await refresh();
}
boot().catch(showError);
