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
let observations=[], mapReady=false, band='all', dataReady=false, view='measured', predictionData=null, predictionMetrics=null;
const operatorFilter=$('#operator-filter'), technologyFilter=$('#technology-filter');
const empty={type:'FeatureCollection',features:[]};
map.on('load',()=>{
  map.addSource('observations',{type:'geojson',data:empty});
  map.addLayer({id:'measured',type:'circle',source:'observations',paint:{
    'circle-color':['case',['>=',['get','rsrp_dbm'],-85],'#117e72',['>=',['get','rsrp_dbm'],-105],'#3b9eae','#d79b57'],
    'circle-radius':['interpolate',['linear'],['zoom'],9,3,13,6],
    'circle-opacity':0.76,'circle-stroke-color':'#fff','circle-stroke-width':0.9
  }});
  map.addSource('predictions',{type:'geojson',data:empty});
  map.addLayer({id:'prediction-hexes',type:'fill',source:'predictions',layout:{visibility:'none'},paint:{
    'fill-color':['case',['>=',['get','predicted_rsrp_dbm'],-85],'#117e72',['>=',['get','predicted_rsrp_dbm'],-105],'#3b9eae','#d79b57'],
    'fill-opacity':['interpolate',['linear'],['get','uncertainty_db'],5,.8,20,.5,40,.25],
    'fill-outline-color':'#244349'
  }});
  map.on('mouseenter','prediction-hexes',()=>{map.getCanvas().style.cursor='pointer'});
  map.on('mouseleave','prediction-hexes',()=>{map.getCanvas().style.cursor='' });
  map.on('mouseenter','measured',()=>{map.getCanvas().style.cursor='pointer'});
  map.on('mouseleave','measured',()=>{map.getCanvas().style.cursor='' });
  mapReady=true;
  if(predictionData)map.getSource('predictions').setData(predictionData);
  if(dataReady) void refresh();
});
map.on('click','measured',e=>{
  const f=e.features?.[0]; if(!f)return;
  const p=f.properties;
  $('#detail-value').textContent=Number(p.rsrp_dbm).toFixed(1);
  $('#detail-dot').className='dot '+(p.rsrp_dbm>=-85?'high':p.rsrp_dbm>=-105?'mid':'low');
  $('#detail-extra').hidden=true;$('#detail-more').setAttribute('aria-expanded','false');$('#detail-more').textContent='Source details ⌄';
  $('#detail-time').textContent=p.measured_at || 'Not recorded';
  $('#detail-radio').textContent=p.radio || 'Not recorded';
  $('#detail-operator').textContent=p.operator_name ? `Anonymized ${p.operator_name}` : 'Not recorded';
  $('#detail-network').textContent=p.network_label || 'Not recorded';
  $('#detail-row').textContent=p.source_record_id || 'Not recorded';
  detail.hidden=false;
});
map.on('click','prediction-hexes',e=>{
  if(view!=='predicted')return;
  const p=e.features?.[0]?.properties;if(!p)return;
  $('#prediction-value').textContent=Number(p.predicted_rsrp_dbm).toFixed(1);
  $('#prediction-dot').className='dot '+(p.predicted_rsrp_dbm>=-85?'high':p.predicted_rsrp_dbm>=-105?'mid':'low');
  $('#prediction-uncertainty').textContent=`Heuristic uncertainty ±${Number(p.uncertainty_db).toFixed(1)} dB · ${p.distance_m} m from closest route sample`;
  $('#prediction-detail').hidden=false;
});
$('#prediction-close').addEventListener('click',()=>{$('#prediction-detail').hidden=true});
function setView(next){
  if(next==='predicted'&&!predictionData){notice.textContent='Prediction layer is loading or unavailable';return}
  if(!mapReady)return
  view=next;detail.hidden=true;$('#prediction-detail').hidden=true;
  map.setLayoutProperty('measured','visibility',view==='measured'?'visible':'none');
  map.setLayoutProperty('prediction-hexes','visibility',view==='predicted'?'visible':'none');
  $('#measured-toolbar').hidden=view==='predicted';$('#measured-legend').hidden=view==='predicted';
  $('#model-metrics').hidden=view==='measured';$('#prediction-legend').hidden=view==='measured';
  $('#view-note').textContent=view==='measured'?'Real sampled signal readings, not coverage.':'Exploratory model, not measured coverage.';
  for(const [id,selected] of [['view-measured',view==='measured'],['view-predicted',view==='predicted']]){$('#'+id).classList.toggle('selected',selected);$('#'+id).setAttribute('aria-pressed',String(selected))}
  count.textContent=view==='predicted'?`${predictionData.features.length} predicted hexes · code C · NR/5G signal · route corridor only`:count.textContent;
  if(view==='measured')void refresh().catch(showError);
  map.resize();
}
$('#view-measured').addEventListener('click',()=>setView('measured'));
$('#view-predicted').addEventListener('click',()=>setView('predicted'));
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
for(const selector of [operatorFilter,technologyFilter])selector.addEventListener('change',()=>{detail.hidden=true;void refresh().catch(showError)});
function showError(error){notice.classList.add('error');notice.textContent='Measurement data is temporarily unavailable.';console.error('Measured data load/render failure:',error)}
function refresh(){
  if(!dataReady||!mapReady||view!=='measured')return;
  const rows=[];
  for(const r of observations){
    if(operatorFilter.value!=='all'&&r[1]!==operatorFilter.value)continue;
    if(technologyFilter.value==='nr'&&!r[2].startsWith('NR '))continue;
    if(technologyFilter.value==='lte'&&!r[2].startsWith('LTE '))continue;
    if(band==='high'&&r[6]<-85||band==='mid'&&(r[6]<-105||r[6]>=-85)||band==='low'&&r[6]>=-105)continue;
    rows.push(r);if(rows.length>=2000)break;
  }
  const features=rows.map(r=>({type:'Feature',geometry:{type:'Point',coordinates:[r[4],r[5]]},properties:{source_record_id:r[0],operator_name:r[1],radio:r[2],network_label:r[3],rsrp_dbm:r[6],measured_at:r[7]}}));
  map.getSource('observations').setData({type:'FeatureCollection',features});
  const label=[operatorFilter.value==='all'?'all operator codes':`code ${operatorFilter.value}`,technologyFilter.value==='all'?'all signal types':technologyFilter.value==='nr'?'NR / 5G':'LTE / 4G'].join(' · ');
  count.textContent=rows.length?`${rows.length.toLocaleString()} points shown · ${label}${rows.length===2000?' · capped at 2,000':''}`:`No points · ${label}`;
}
async function boot(){
  const response=await fetch(new URL('./assets/observations.json',import.meta.url));
  if(!response.ok)throw new Error(`JSON fetch HTTP ${response.status}`);
  observations=await response.json();
  if(!Array.isArray(observations)||observations.length!==10148)throw new Error('Unexpected observation extract length');
  total.textContent=observations.length.toLocaleString();
  dataReady=true;
  notice.classList.remove('error');notice.textContent='Measured RF · DoNext H-Bahn · no inferred coverage';
  refresh();
  try{
    const [hexResponse,metricsResponse]=await Promise.all([fetch(new URL('./assets/predicted-rsrp.geojson',import.meta.url)),fetch(new URL('./assets/model-metrics.json',import.meta.url))]);
    if(!hexResponse.ok||!metricsResponse.ok)throw new Error('Prediction assets unavailable');
    predictionData=await hexResponse.json();predictionMetrics=await metricsResponse.json();
    if(mapReady)map.getSource('predictions').setData(predictionData);
    $('#model-score').textContent=`Holdout MAE ${predictionMetrics.holdout_mae_db} dB (${predictionMetrics.holdout_n.toLocaleString()} held-out points); spatial 5-fold CV MAE ${predictionMetrics.cv_weighted_mae_db} dB (folds: ${predictionMetrics.cv_folds.map(f=>f.mae_db).join(', ')} dB).`;
  }catch(error){$('#view-predicted').disabled=true;console.warn('Model layer unavailable',error)}
}
boot().catch(showError);
