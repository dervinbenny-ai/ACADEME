(() => {
 'use strict';
 const source=document.getElementById('analytics-data');if(!source||!window.Chart)return;
 const list=[],palette=['#8170d6','#67afa4','#78a0d2','#dcaf71','#b58bc7','#8caf99'];
 JSON.parse(source.textContent).forEach((data,index)=>{
   const canvas=document.getElementById('analytics-'+index);if(!canvas)return;
   if(!data.values.length||data.values.every(n=>!n)){const state=Academe.el('div',{class:'empty-state'},'Insights will appear when records are available.');canvas.replaceWith(state);return;}
   const donut=[2,4,5].includes(index),css=getComputedStyle(document.documentElement),muted=css.getPropertyValue('--text-muted').trim(),border=css.getPropertyValue('--border-light').trim();
   list.push(new Chart(canvas,{type:donut?'doughnut':'bar',data:{labels:data.labels.map(x=>x.replaceAll('_',' ')),datasets:[{label:'Records',data:data.values,backgroundColor:palette,borderWidth:donut?3:0,borderColor:css.getPropertyValue('--surface').trim(),borderRadius:donut?3:6,maxBarThickness:44}]},options:{maintainAspectRatio:false,cutout:'74%',animation:Academe.reduced()?false:{duration:650},plugins:{legend:{display:donut,position:'bottom',labels:{usePointStyle:true,pointStyle:'circle',boxWidth:7,boxHeight:7,padding:17,color:muted,font:{family:'Inter',size:10}}},tooltip:{backgroundColor:'#15213b',padding:12,cornerRadius:8}},scales:donut?{}:{y:{beginAtZero:true,border:{display:false},ticks:{precision:0,color:muted,font:{size:10}},grid:{color:border}},x:{border:{display:false},grid:{display:false},ticks:{color:muted,font:{size:10}}}}}}));
 });
 document.addEventListener('academe:theme',()=>{const css=getComputedStyle(document.documentElement);list.forEach(chart=>{chart.data.datasets[0].borderColor=css.getPropertyValue('--surface').trim();chart.options.plugins.legend.labels.color=css.getPropertyValue('--text-muted').trim();if(chart.config.type==='bar'){for(const axis of ['x','y'])chart.options.scales[axis].ticks.color=css.getPropertyValue('--text-muted').trim();chart.options.scales.y.grid.color=css.getPropertyValue('--border-light').trim();}chart.update('none');});});
})();
