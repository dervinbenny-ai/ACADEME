(() => {
 'use strict';
 const dialog=document.getElementById('command-dialog'),input=document.getElementById('command-search'),results=document.getElementById('command-results');if(!dialog)return;
 const nav=[...document.querySelectorAll('.sidebar nav a')].map(a=>({label:a.querySelector('span').textContent,url:a.getAttribute('href'),kind:'Page',icon:a.querySelector('i').className.replace('bi bi-','')}));
 let timer,controller,sequence=0;
 const row=item=>{const a=Academe.el('a',{href:item.url});const text=Academe.el('div');text.append(Academe.el('strong',{},item.label),Academe.el('small',{},item.kind));a.append(Academe.el('i',{class:'bi bi-'+(item.icon||'arrow-up-right')}),text);return a;};
 const render=items=>{results.replaceChildren(...items.map(row));if(!items.length)results.append(Academe.el('div',{class:'command-state'},'No matching records. Try a different name or request.'));};
 const open=()=>{dialog.showModal();input.value='';render(nav.slice(0,7));input.focus();};
 document.querySelectorAll('[data-command-open]').forEach(button=>button.addEventListener('click',open));
 document.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();if(dialog.open)dialog.close();else open();}});
 dialog.addEventListener('close',()=>{clearTimeout(timer);controller?.abort();sequence++;});
 input.addEventListener('input',()=>{
   clearTimeout(timer);controller?.abort();const q=input.value.trim(),version=++sequence;
   if(q.length<2){render(nav.filter(item=>item.label.toLowerCase().includes(q.toLowerCase())).slice(0,7));return;}
   results.replaceChildren(Academe.el('div',{class:'command-state'},'Searching your workspace...'));
   timer=setTimeout(async()=>{controller=new AbortController();try{
     const response=await fetch('/api/workspace/search?q='+encodeURIComponent(q),{signal:controller.signal,headers:{Accept:'application/json'}});
     if(!response.ok||!response.headers.get('content-type')?.includes('application/json'))throw new Error('Search is unavailable. Please refresh or sign in again.');
     const data=await response.json();if(version!==sequence)return;render([...nav.filter(item=>item.label.toLowerCase().includes(q.toLowerCase())),...data.items]);
   }catch(error){if(error.name!=='AbortError'&&version===sequence)results.replaceChildren(Academe.el('div',{class:'command-state'},error.message));}},300);
 });
})();
