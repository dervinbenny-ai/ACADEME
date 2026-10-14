(() => {
 'use strict';
 const dialog=document.getElementById('confirm-dialog');if(!dialog)return;
 let pending=null,submitter=null;
 document.addEventListener('submit',event=>{
   const form=event.target, message=event.submitter?.dataset.confirmAction||form.dataset.confirm;
   if(!message||form.dataset.confirmed==='yes'||event.defaultPrevented)return;
   event.preventDefault();pending=form;submitter=event.submitter;
   document.getElementById('confirm-message').textContent=message;dialog.showModal();document.getElementById('confirm-cancel').focus();
 },true);
 document.getElementById('confirm-cancel').addEventListener('click',()=>dialog.close());
 document.getElementById('confirm-accept').addEventListener('click',()=>{
   dialog.close();if(!pending)return;const form=pending,button=submitter;
   form.dataset.confirmed='yes';form.requestSubmit(button);delete form.dataset.confirmed;
 });
 document.querySelectorAll('dialog').forEach(modal=>modal.addEventListener('click',event=>{if(event.target!==modal)return;const rect=modal.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)modal.close();}));
})();
