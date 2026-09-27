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
let observations=[], mapReady=false, band='all', dataReady=false, view='measured', predictionData=null, predictionMetrics=null, centerData=null, sectorData=null, israelData=null, region='germany';
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
  map.addSource('israel-cells',{type:'geojson',data:empty});
  map.addLayer({id:'israel-cells-layer',type:'circle',source:'israel-cells',layout:{visibility:'none'},paint:{'circle-color':'#69459c','circle-radius':['interpolate',['linear'],['zoom'],6,3,11,5],'circle-opacity':.67,'circle-stroke-color':'#ffffff','circle-stroke-width':.7}});
  map.on('mouseenter','israel-cells-layer',()=>{map.getCanvas().style.cursor='pointer'});
  map.on('mouseleave','israel-cells-layer',()=>{map.getCanvas().style.cursor='' });
  map.addSource('sector-paths',{type:'geojson',data:empty});
  map.addLayer({id:'sector-path-layer',type:'line',source:'sector-paths',layout:{visibility:'none'},paint:{'line-color':'#b0465d','line-width':['interpolate',['linear'],['zoom'],10,1.5,13,3],'line-opacity':.72,'line-dasharray':[2,1]}});
  map.addSource('reception-centers',{type:'geojson',data:empty});
  map.addLayer({id:'center-halos',type:'circle',source:'reception-centers',layout:{visibility:'none'},paint:{'circle-radius':['interpolate',['linear'],['zoom'],9,8,13,13],'circle-color':'#ffffff','circle-opacity':.9,'circle-stroke-color':'#5a3d80','circle-stroke-width':2}});
  map.addLayer({id:'center-diamonds',type:'symbol',source:'reception-centers',layout:{visibility:'none','text-field':'◇','text-size':22,'text-allow-overlap':true},paint:{'text-color':'#5a3d80'}});
  map.on('mouseenter','center-halos',()=>{map.getCanvas().style.cursor='pointer'});
  map.on('mouseleave','center-halos',()=>{map.getCanvas().style.cursor='' });
  map.on('mouseenter','prediction-hexes',()=>{map.getCanvas().style.cursor='pointer'});
  map.on('mouseleave','prediction-hexes',()=>{map.getCanvas().style.cursor='' });
  map.on('mouseenter','measured',()=>{map.getCanvas().style.cursor='pointer'});
  map.on('mouseleave','measured',()=>{map.getCanvas().style.cursor='' });
  mapReady=true;
  if(predictionData)map.getSource('predictions').setData(predictionData);
  if(centerData)map.getSource('reception-centers').setData(centerData);
  if(sectorData)map.getSource('sector-paths').setData(sectorData);
  if(israelData)refreshIsrael();
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
  if(view!=='predicted'||region!=='germany')return;
  const p=e.features?.[0]?.properties;if(!p)return;
  $('#prediction-value').textContent=Number(p.predicted_rsrp_dbm).toFixed(1);
  $('#prediction-dot').className='dot '+(p.predicted_rsrp_dbm>=-85?'high':p.predicted_rsrp_dbm>=-105?'mid':'low');
  $('#prediction-uncertainty').textContent=`Heuristic uncertainty ±${Number(p.uncertainty_db).toFixed(1)} dB · ${p.distance_m} m from closest route sample`;
  $('#prediction-detail').hidden=false;
});
map.on('click','center-halos',e=>{
  if(view!=='centers'||region!=='germany')return;
  const p=e.features?.[0]?.properties;if(!p)return;
  $('#center-count').textContent=Number(p.sample_count).toLocaleString();
  $('#center-mno').textContent=p.mno_code;
  $('#center-index').textContent=p.cell_index;
  $('#center-identifiers').textContent=`${p.physical_cellid} / ${p.earfcn}`;
  $('#center-detail').hidden=false;
});
map.on('click','israel-cells-layer',e=>{
  if(region!=='israel')return;
  const p=e.features?.[0]?.properties;if(!p)return;
  $('#israel-detail-radio').textContent=p.radio;
  $('#israel-detail-network').textContent=`425 / ${p.mnc}`;
  $('#israel-detail-id').textContent=`${p.area} / ${p.cell}`;
  $('#israel-detail-samples').textContent=Number(p.samples).toLocaleString();
  $('#israel-detail').hidden=false;
});
$('#israel-close').addEventListener('click',()=>{$('#israel-detail').hidden=true});
function refreshIsrael(){
  if(!mapReady||!israelData)return;
  const radio=$('#israel-radio').value,mnc=$('#israel-network').value;
  const selected=israelData.filter(r=>(radio==='all'||r[2]===radio)&&(mnc==='all'||r[3]===mnc));
  // Deterministic, bounded view from the full local inventory, not a claim that only 3,000 exist.
  const step=Math.max(1,Math.ceil(selected.length/3000));
  const sampled=selected.filter((_,i)=>i%step===0).slice(0,3000);
  map.getSource('israel-cells').setData({type:'FeatureCollection',features:sampled.map(r=>({type:'Feature',geometry:{type:'Point',coordinates:[r[0],r[1]]},properties:{knowledge_grade:'inferred_inventory',radio:r[2],mnc:r[3],area:r[4],cell:r[5],samples:r[6]}}))});
  if(region==='israel')count.textContent=`${sampled.length.toLocaleString()} shown of ${selected.length.toLocaleString()} matching cells · ${israelData.length.toLocaleString()} total extract`;
}
function setRegion(next){
  if(next==='israel'&&!israelData){notice.textContent='Israel inventory is loading or unavailable';return}
  region=next;detail.hidden=true;$('#prediction-detail').hidden=true;$('#center-detail').hidden=true;$('#israel-detail').hidden=true;
  $('#area-germany').classList.toggle('selected',next==='germany');$('#area-germany').setAttribute('aria-pressed',String(next==='germany'));
  $('#area-israel').classList.toggle('selected',next==='israel');$('#area-israel').setAttribute('aria-pressed',String(next==='israel'));
  $('#germany-views').hidden=next==='israel';$('#israel-controls').hidden=next!=='israel';$('#israel-credit').hidden=next!=='israel';
  $('#measured-toolbar').hidden=next!=='germany'||view!=='measured';
  for(const [id,active] of [['measured',next==='germany'&&view==='measured'],['prediction-hexes',next==='germany'&&view==='predicted'],['center-halos',next==='germany'&&view==='centers'],['center-diamonds',next==='germany'&&view==='centers'],['sector-path-layer',next==='germany'&&view==='sector'],['israel-cells-layer',next==='israel']])map.setLayoutProperty(id,'visibility',active?'visible':'none');
  for(const [id,active] of [['measured-legend',next==='germany'&&view==='measured'],['prediction-legend',next==='germany'&&view==='predicted'],['center-legend',next==='germany'&&view==='centers'],['israel-legend',next==='israel'],['center-note',next==='germany'&&view==='centers'],['sector-legend',next==='germany'&&view==='sector'],['model-metrics',next==='germany'&&view==='predicted']])$('#'+id).hidden=!active;
  $('#region-title').innerHTML=next==='israel'?'Cells, <em>not coverage.</em>':'Signal, <em>at a glance.</em>';
  $('#region-eyebrow').textContent=next==='israel'?'ISRAEL · INFERRED CELL INVENTORY':'DORTMUND · REAL RF MEASUREMENTS';
  $('#region-description').textContent=next==='israel'?'Estimated cell positions from OpenCellID, not measured RF, tower sites or coverage.':'One sampled rail route. Each dot is a measured signal reading, not a coverage prediction.';
  $('#total').textContent=next==='israel'?israelData.length.toLocaleString():observations.length.toLocaleString();
  $('#total-label').textContent=next==='israel'?'source cell records':'source measurements';
  $('#map').setAttribute('aria-label',next==='israel'?'Map of inferred OpenCellID Israel cell positions, not measured signal or tower sites':'Map of sampled RF measurements along the Dortmund H-Bahn route');
  $('#sector-credit').hidden=next==='israel'||view!=='sector';
  $('#map-scope').textContent=next==='israel'?'Israel · inferred inventory':view==='measured'?'Dortmund · measured RF':view==='centers'?'Dortmund · reception centers':view==='sector'?'Dortmund · sector paths':'Dortmund · model prediction';
  if(next==='israel'){map.jumpTo({center:[34.92,31.8],zoom:7});refreshIsrael();notice.textContent='Inferred inventory · OpenCellID Israel · no measured RF'}
  else{map.jumpTo({center:[7.438,51.493],zoom:11});notice.textContent='Measured RF · DoNext H-Bahn · no inferred coverage';setView(view)}
  map.resize();
}
function toggleControls(force){
  const open=typeof force==='boolean'?force:!$('#map-controls').classList.contains('open');
  $('#map-controls').classList.toggle('open',open);
  $('#map-layer-toggle').setAttribute('aria-expanded',String(open));
  $('#map-layer-toggle').textContent=open?'× Close controls':'☷ Layers & filters';
  map.resize();
}
$('#map-layer-toggle').addEventListener('click',()=>toggleControls());
$('#area-germany').addEventListener('click',()=>{setRegion('germany');toggleControls(false)});
$('#area-israel').addEventListener('click',()=>{setRegion('israel');toggleControls(false)});
for(const id of ['israel-radio','israel-network'])$('#'+id).addEventListener('change',()=>{$('#israel-detail').hidden=true;refreshIsrael()});
$('#center-close').addEventListener('click',()=>{$('#center-detail').hidden=true});
$('#prediction-close').addEventListener('click',()=>{$('#prediction-detail').hidden=true});
function setView(next){
  if(next==='predicted'&&!predictionData){notice.textContent='Prediction layer is loading or unavailable';return}
  if(next==='centers'&&!centerData){notice.textContent='Reception centers are loading or unavailable';return}
  if(next==='sector'&&!sectorData){notice.textContent='Sector research paths are loading or unavailable';return}
  if(!mapReady)return;
  view=next;detail.hidden=true;$('#prediction-detail').hidden=true;$('#center-detail').hidden=true;
  map.setLayoutProperty('measured','visibility',view==='measured'?'visible':'none');
  map.setLayoutProperty('prediction-hexes','visibility',view==='predicted'?'visible':'none');
  for(const layer of ['center-halos','center-diamonds'])map.setLayoutProperty(layer,'visibility',view==='centers'?'visible':'none');
  map.setLayoutProperty('sector-path-layer','visibility',view==='sector'?'visible':'none');
  $('#measured-toolbar').hidden=view!=='measured';$('#measured-legend').hidden=view!=='measured';
  $('#model-metrics').hidden=view!=='predicted';$('#prediction-legend').hidden=view!=='predicted';
  $('#center-note').hidden=view!=='centers';$('#center-legend').hidden=view!=='centers';
  $('#sector-legend').hidden=view!=='sector';$('#sector-credit').hidden=view!=='sector';
  $('#view-note').textContent={measured:'Real sampled signal readings, not coverage.',predicted:'Exploratory model, not measured coverage.',centers:'Grouped receiver positions, not towers.',sector:'Directional route-path research, not coverage; clutter worsened pooled CV.'}[view];
  for(const [id,selected] of [['view-measured',view==='measured'],['view-predicted',view==='predicted'],['view-centers',view==='centers'],['view-sector',view==='sector']]){$('#'+id).classList.toggle('selected',selected);$('#'+id).setAttribute('aria-pressed',String(selected))}
  if(view==='predicted')count.textContent=`${predictionData.features.length} predicted hexes · code C · NR/5G signal · route corridor only`;
  if(view==='sector')count.textContent=`${sectorData.features.length} route-sector paths · not coverage · clutter CV 6.77 vs baseline 6.51 dB`;
  if(view==='centers')count.textContent=`${centerData.features.length} estimated reception centers · NOT towers`;
  if(view==='measured')refresh();
  $('#map').setAttribute('aria-label',view==='sector'?'Dortmund route-bound sector research paths from receiver-derived centers to observed endpoints; not signal coverage':view==='centers'?'Map of estimated reception centers, not physical tower sites':view==='predicted'?'Map of route-adjacent model-predicted RF, not measured or validated coverage':'Map of sampled RF measurements along the Dortmund H-Bahn route');
  $('#map-scope').textContent=view==='measured'?'Dortmund · measured RF':view==='centers'?'Dortmund · reception centers':view==='sector'?'Dortmund · sector paths':'Dortmund · model prediction';
  map.resize();
}
$('#view-measured').addEventListener('click',()=>setView('measured'));
$('#view-predicted').addEventListener('click',()=>setView('predicted'));
$('#view-centers').addEventListener('click',()=>setView('centers'));
$('#view-sector').addEventListener('click',()=>setView('sector'));
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
    const response=await fetch(new URL('./assets/israel-inventory.json',import.meta.url));
    if(!response.ok)throw new Error(`Israel inventory HTTP ${response.status}`);
    israelData=await response.json();
    if(!Array.isArray(israelData)||israelData.length!==29567)throw new Error('Unexpected inventory extract length');
    const codes=[...new Set(israelData.map(r=>r[3]))].sort((a,b)=>Number(a)-Number(b));
    for(const code of codes){const option=document.createElement('option');option.value=code;option.textContent=`MNC ${code}`;$('#israel-network').append(option)}
  }catch(error){$('#area-israel').disabled=true;console.warn('Israel inventory unavailable',error)}
  try{
    const response=await fetch(new URL('./assets/reception-centers.geojson',import.meta.url));
    if(!response.ok)throw new Error(`Centers HTTP ${response.status}`);
    centerData=await response.json();
    if(mapReady)map.getSource('reception-centers').setData(centerData);
  }catch(error){$('#view-centers').disabled=true;console.warn('Reception centers unavailable',error)}
  try{
    const response=await fetch(new URL('./assets/sector-paths.geojson',import.meta.url));
    if(!response.ok)throw new Error(`Sector paths HTTP ${response.status}`);
    sectorData=await response.json();
    if(mapReady)map.getSource('sector-paths').setData(sectorData);
  }catch(error){$('#view-sector').disabled=true;console.warn('Sector research layer unavailable',error)}
  try{
    const [hexResponse,metricsResponse]=await Promise.all([fetch(new URL('./assets/predicted-rsrp.geojson',import.meta.url)),fetch(new URL('./assets/model-metrics.json',import.meta.url))]);
    if(!hexResponse.ok||!metricsResponse.ok)throw new Error('Prediction assets unavailable');
    predictionData=await hexResponse.json();predictionMetrics=await metricsResponse.json();
    if(mapReady)map.getSource('predictions').setData(predictionData);
    $('#model-score').textContent=`Holdout MAE ${predictionMetrics.holdout_mae_db} dB (${predictionMetrics.holdout_n.toLocaleString()} held-out points); spatial 5-fold CV MAE ${predictionMetrics.cv_weighted_mae_db} dB (folds: ${predictionMetrics.cv_folds.map(f=>f.mae_db).join(', ')} dB).`;
  }catch(error){$('#view-predicted').disabled=true;console.warn('Model layer unavailable',error)}
}
boot().catch(showError);
