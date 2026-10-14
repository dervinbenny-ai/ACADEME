(() => {
 'use strict';
 function decorate(root=document){
   root.querySelectorAll('table[data-sortable]').forEach(table=>{
     if(table.dataset.enhanced)return;table.dataset.enhanced='true';
     const heads=[...table.querySelectorAll('thead th')];
     table.querySelectorAll('tbody td[colspan]').forEach(cell=>{if(cell.parentElement.parentElement.children.length===1){const copy=cell.textContent.trim(),empty=Academe.el('div',{class:'empty-state'}),icon=Academe.el('span',{class:'empty-icon'});icon.append(Academe.el('i',{class:'bi bi-inbox'}));empty.append(icon,Academe.el('h3',{},'No matching records'),Academe.el('p',{},copy));cell.replaceChildren(empty);}});
     table.querySelectorAll('tbody tr').forEach(row=>[...row.cells].forEach((cell,i)=>{
       cell.dataset.label=heads[i]?.textContent.trim()||'';
       if(table.closest('.card-table')&&!cell.hasAttribute('colspan')){const content=Academe.el('div',{class:'cell-content'});content.append(...cell.childNodes);cell.append(content);}
     }));
     heads.forEach((head,index)=>{
       const label=head.textContent.trim();if(['Action','Actions','Decision'].includes(label))return;
       const button=Academe.el('button',{type:'button',class:'sort-button','aria-label':'Sort displayed rows by '+label},label);button.append(Academe.el('i',{class:'bi bi-arrow-down-up','aria-hidden':'true'}));head.replaceChildren(button);
       button.addEventListener('click',()=>{
         const direction=head.getAttribute('aria-sort')==='ascending'?-1:1;heads.forEach(h=>h.removeAttribute('aria-sort'));head.setAttribute('aria-sort',direction===1?'ascending':'descending');
         const rows=[...table.tBodies[0].rows];if(rows.some(r=>r.cells.length!==heads.length))return;
         rows.sort((a,b)=>{const x=a.cells[index].dataset.sort||a.cells[index].textContent.trim(),y=b.cells[index].dataset.sort||b.cells[index].textContent.trim();return direction*x.localeCompare(y,undefined,{numeric:true,sensitivity:'base'});});rows.forEach(row=>table.tBodies[0].append(row));
       });
     });
   });
 }
 decorate();
 const liveForms=[...document.querySelectorAll('form[data-live-filter]')];
 liveForms.forEach(form=>{
   const panel=form.closest('.panel'),status=Academe.el('div',{class:'search-status',role:'status','aria-live':'polite'});form.after(status);
   let timer,controller,sequence=0;
   const chips=Academe.el('div',{class:'filter-chips','aria-label':'Filter by status'}),picker=form.querySelector('select[name=status]');
   if(picker){form.after(chips);[...picker.options].forEach(option=>{
     const button=Academe.el('button',{type:'button',class:'filter-chip','aria-pressed':String(option.selected)},option.value?option.textContent.replaceAll('_',' ').toLowerCase().replace(/^./,c=>c.toUpperCase()):'All');
     button.addEventListener('click',()=>{picker.value=option.value;picker.dispatchEvent(new Event('change',{bubbles:true}));});button.dataset.value=option.value;chips.append(button);
   });}
   const update=async()=>{
     const version=++sequence;controller?.abort();controller=new AbortController();
     const url=new URL(form.action||location.href);url.search=new URLSearchParams(new FormData(form)).toString();url.searchParams.delete('page');
     status.textContent='Searching...';panel.setAttribute('aria-busy','true');chips.querySelectorAll('button').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.value===picker?.value)));
     try{const response=await fetch(url,{signal:controller.signal,headers:{'X-Requested-With':'Academe'}});if(!response.ok||response.redirected)throw new Error('Could not load results. Refresh or sign in again.');
       const doc=new DOMParser().parseFromString(await response.text(),'text/html');if(version!==sequence)return;
       const nextForm=[...doc.querySelectorAll('form[data-live-filter]')][liveForms.indexOf(form)],nextPanel=nextForm?.closest('.panel');if(!nextPanel)throw new Error('Results unavailable. Use the Filter button to retry.');
       panel.querySelectorAll('.table-wrap,.pagination-bar,.empty-state').forEach(node=>node.remove());
       nextPanel.querySelectorAll('.table-wrap,.pagination-bar,.empty-state').forEach(node=>panel.append(document.importNode(node,true)));decorate(panel);
       history.replaceState(null,'',url);const count=[...panel.querySelectorAll('tbody tr')].filter(row=>!row.querySelector('td[colspan]')).length;status.textContent=count?`${count} displayed row${count===1?'':'s'}. Sort headings apply to this page.`:'No matching records.';
     }catch(error){if(error.name!=='AbortError'&&version===sequence)status.textContent=error.message;}finally{if(version===sequence)panel.removeAttribute('aria-busy');}
   };
   const schedule=()=>{clearTimeout(timer);controller?.abort();sequence++;status.textContent='Searching...';timer=setTimeout(update,300);};
   form.addEventListener('input',schedule);form.addEventListener('change',schedule);form.addEventListener('submit',event=>{event.preventDefault();clearTimeout(timer);update();});
 });
 const report=document.querySelector('[data-report-form]');if(report){
   const chosen=Academe.el('div',{class:'selected-columns','aria-label':'Selected report columns'});report.querySelector('details')?.after(chosen);
   const update=()=>{chosen.replaceChildren(...[...report.querySelectorAll('[name=columns]:checked')].map(input=>Academe.el('span',{},input.parentElement.textContent.trim())));};report.addEventListener('change',update);update();
   report.addEventListener('submit',async event=>{
     const button=event.submitter;if(button?.name!=='format')return;event.preventDefault();const text=button.textContent;button.disabled=true;button.textContent=button.value==='pdf'?'Generating PDF...':button.value==='xlsx'?'Generating Excel...':'Generating CSV...';
     try{const params=new URLSearchParams(new FormData(report));params.set('format',button.value);const response=await fetch(location.pathname+'?'+params,{headers:{Accept:'application/octet-stream'}});if(!response.ok||!response.headers.get('content-disposition')?.includes('attachment'))throw new Error('Report could not be generated. Refresh and try again.');const blob=await response.blob(),url=URL.createObjectURL(blob);const link=Academe.el('a',{href:url,download:response.headers.get('content-disposition').match(/filename="?([^";]+)/)?.[1]||'academic-report.'+button.value});document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);Academe.toast('Report ready. Your download has started.','success');}
     catch(error){Academe.toast(error.message,'danger');}finally{button.disabled=false;button.textContent=text;}
   });
 }
})();
