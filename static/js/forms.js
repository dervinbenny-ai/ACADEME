(() => {
 'use strict';
 document.querySelectorAll('.password-toggle').forEach(button=>button.addEventListener('click',()=>{
   const input=button.parentElement.querySelector('input');if(!input)return;const show=input.type==='password';input.type=show?'text':'password';button.setAttribute('aria-label',show?'Hide password':'Show password');button.setAttribute('aria-pressed',String(show));button.querySelector('i').className=show?'bi bi-eye-slash':'bi bi-eye';
 }));
 document.querySelectorAll('textarea[maxlength],input[maxlength]').forEach(input=>{
   const counter=Academe.el('small',{class:'char-count'});const update=()=>counter.textContent=`${input.value.length} / ${input.maxLength}`;input.after(counter);input.addEventListener('input',update);update();
 });
 document.addEventListener('invalid',event=>{
   const input=event.target,wrap=input.closest('.field,.floating-field');if(!wrap)return;
   wrap.classList.add('is-invalid');input.setAttribute('aria-invalid','true');let error=wrap.querySelector('.field-error');
   if(!error){error=Academe.el('span',{class:'field-error',id:(input.id||input.name)+'-error'});wrap.append(error);}
   error.textContent=input.validationMessage;input.setAttribute('aria-describedby',error.id);
 },true);
 document.addEventListener('input',event=>{
   const input=event.target;if(!input.validity||!input.validity.valid)return;const wrap=input.closest('.field,.floating-field');if(!wrap)return;
   wrap.classList.remove('is-invalid');input.removeAttribute('aria-invalid');const error=wrap.querySelector('.field-error');if(error&&input.getAttribute('aria-describedby')===error.id)input.removeAttribute('aria-describedby');error?.remove();
 });
 const reset = () => document.querySelectorAll('form[data-busy]').forEach(form=>{
   delete form.dataset.busy;form.removeAttribute('aria-busy');form.querySelectorAll('[data-original-html]').forEach(button=>{button.disabled=false;button.innerHTML=button.dataset.originalHtml;delete button.dataset.originalHtml;});
 });
 document.addEventListener('submit',event=>{
   const form=event.target;if(form.dataset.busy==='true'){event.preventDefault();return;}
   if(form.method.toLowerCase()==='get'||event.defaultPrevented)return;
   queueMicrotask(()=>{
     if(event.defaultPrevented)return;form.dataset.busy='true';form.setAttribute('aria-busy','true');
     const button=event.submitter;if(!button)return;
     // Keep the clicked name/value in the native form payload. Disable only after serialization.
     setTimeout(()=>{button.dataset.originalHtml=button.innerHTML;button.disabled=true;button.replaceChildren(Academe.el('span',{class:'loading-spinner','aria-hidden':'true'}),document.createTextNode(' Working...'));},0);
   });
 });
 window.addEventListener('pageshow',reset);
 // Native error pages navigate normally; back/forward restoration resets controls.
})();
