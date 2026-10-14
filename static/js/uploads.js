(() => {
 'use strict';
 document.querySelectorAll('input[type=file]').forEach(input=>{
   let zone=input.closest('.upload-zone');if(!zone){zone=Academe.el('div',{class:'upload-zone'});input.parentNode.insertBefore(zone,input);zone.append(Academe.el('i',{class:'bi bi-cloud-arrow-up','aria-hidden':'true'}),input);}
   const hint=Academe.el('span',{class:'upload-hint'},'Drop your file here, or use Browse. Your teacher will review submitted documents.');zone.append(hint);
   const preview=Academe.el('div',{class:'upload-preview',hidden:''});zone.append(preview);
   const update=()=>{preview.replaceChildren();const file=input.files[0];preview.hidden=!file;if(!file)return;const info=Academe.el('div');info.append(Academe.el('strong',{},file.name),Academe.el('small',{},(file.size/1024/1024).toFixed(2)+' MB · Ready to submit'));const clear=Academe.el('button',{type:'button','aria-label':'Remove selected file'},'×');clear.addEventListener('click',()=>{input.value='';update();input.focus();});preview.append(Academe.el('i',{class:'bi bi-file-earmark'}),info,clear);};
   input.addEventListener('change',update);zone.addEventListener('dragover',event=>{event.preventDefault();zone.classList.add('drag-over');});zone.addEventListener('dragleave',()=>zone.classList.remove('drag-over'));
   zone.addEventListener('drop',event=>{event.preventDefault();zone.classList.remove('drag-over');const files=event.dataTransfer?.files;if(!files?.length)return;try{const transfer=new DataTransfer();for(const file of [...files].slice(0,input.multiple?files.length:1))transfer.items.add(file);input.files=transfer.files;input.dispatchEvent(new Event('change',{bubbles:true}));}catch{Academe.toast('Use Browse to choose the file.');}});update();
 });
 document.querySelectorAll('form[enctype="multipart/form-data"]').forEach(form=>{
  let status;
  form.addEventListener('submit',event=>{
   if(form.dataset.uploading){event.preventDefault();return;}
   const skipValidation=form.noValidate||event.submitter?.formNoValidate;
   if(event.defaultPrevented||(!skipValidation&&!form.checkValidity())||!form.querySelector('input[type=file]'))return;
   event.preventDefault();const data=new FormData(form);if(event.submitter?.name)data.append(event.submitter.name,event.submitter.value);
   const buttons=[...form.querySelectorAll('button[type=submit],button:not([type])')],progress=Academe.el('progress',{max:'100',value:'0','aria-label':'Upload progress'});
   if(!status)status=Academe.el('div',{role:'status',class:'search-status','data-upload-status':''});
   status.textContent='Uploading...';form.append(progress,status);progress.style.width='100%';form.dataset.uploading='true';buttons.forEach(button=>button.disabled=true);
   // Buttons and fields named "action" shadow form.action in the DOM.
   const xhr=new XMLHttpRequest();xhr.open('POST',form.getAttribute('action')||location.href);xhr.timeout=120000;xhr.setRequestHeader('X-CSRFToken',Academe.csrf());
   xhr.upload.onprogress=event=>{if(event.lengthComputable){const percentage=Math.round(event.loaded/event.total*100);progress.value=percentage;status.textContent=percentage===100?'Upload received. Processing your document...':`Uploading ${percentage}%`;}};
   const reset=()=>{delete form.dataset.uploading;buttons.forEach(button=>button.disabled=false);progress.remove();};
   xhr.onload=()=>{reset();if(xhr.status>=200&&xhr.status<300){const doc=new DOMParser().parseFromString(xhr.responseText,'text/html'),success=doc.querySelector('.toast-stack .success');try{if(success)sessionStorage.setItem('academe-flash',success.querySelector('span')?.textContent||'Submission saved.');}catch{}status.textContent='Complete. Opening your updated record...';location.assign(xhr.responseURL||location.href);}else{const doc=new DOMParser().parseFromString(xhr.responseText,'text/html'),reason=doc.querySelector('.error-panel p')?.textContent?.trim();status.textContent=`${reason||'Could not save the upload.'} Your selected file is still available. Check the form and retry.`;}};
   xhr.onerror=()=>{reset();status.textContent='Connection interrupted. Check your saved submissions before retrying.';};xhr.ontimeout=()=>{reset();status.textContent='The upload timed out. Check your saved submissions before retrying.';};xhr.send(data);
  });
 });
})();
