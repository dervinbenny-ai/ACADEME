(() => {
 'use strict';
 const toggle=document.getElementById('notification-toggle'),popover=document.getElementById('notification-popover'),feed=document.getElementById('notification-feed');if(!toggle)return;
 let newest=null,busy=false;
 const counts=count=>document.querySelectorAll('[data-unread-count]').forEach(el=>{el.textContent=count;if(el.classList.contains('nav-count')||el.parentElement===toggle)el.hidden=!count;});
 const read=async id=>{
   const response=await fetch('/api/workspace/notifications/read',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':Academe.csrf()},body:JSON.stringify(id?{id}: {})});
   if(!response.ok)throw new Error('Could not update notifications. Refresh and try again.');await load();
 };
 const load=async()=>{
   if(busy)return;busy=true;
   try{const response=await fetch('/api/workspace/notifications',{headers:{Accept:'application/json'}});if(!response.ok||!response.headers.get('content-type')?.includes('application/json'))throw new Error('Sign in again to view notifications.');const data=await response.json();counts(data.unread);
     if(newest!==null&&data.latest_id>newest&&data.items.some(item=>!item.read&&item.id>newest))Academe.toast('You have a new workspace notification.');newest=data.latest_id;
     feed.replaceChildren();if(!data.items.length)feed.append(Academe.el('div',{class:'empty-state'},'You’re all caught up. New updates will appear here.'));
     for(const item of data.items){const row=Academe.el('div',{class:'notification-row'+(item.read?'':' unread')});const icon=Academe.el('span',{class:'stat-icon'});icon.append(Academe.el('i',{class:'bi bi-bell'}));const body=Academe.el('div');const link=Academe.el('a',{href:item.link});link.append(Academe.el('strong',{},item.title));body.append(link,Academe.el('p',{},item.body),Academe.el('small',{},new Date(item.created_at).toLocaleString()));
       if(!item.read){const button=Academe.el('button',{type:'button',class:'text-button'},'Mark read');button.addEventListener('click',async()=>{button.disabled=true;try{await read(item.id);}catch(error){Academe.toast(error.message,'danger');button.disabled=false;}});body.append(button);}row.append(icon,body);feed.append(row);
     }
   }catch(error){if(!popover.hidden)feed.replaceChildren(Academe.el('div',{class:'command-state'},error.message));}finally{busy=false;}
 };
 toggle.addEventListener('click',()=>{popover.hidden=!popover.hidden;toggle.setAttribute('aria-expanded',String(!popover.hidden));if(!popover.hidden)load();});
 document.getElementById('mark-all-notifications').addEventListener('click',async event=>{event.currentTarget.disabled=true;try{await read();}catch(error){Academe.toast(error.message,'danger');}finally{document.getElementById('mark-all-notifications').disabled=false;}});
 document.addEventListener('click',event=>{if(!event.target.closest('.notification-menu')){popover.hidden=true;toggle.setAttribute('aria-expanded','false');}});
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!popover.hidden){popover.hidden=true;toggle.setAttribute('aria-expanded','false');toggle.focus();}});
 load();setInterval(()=>{if(!document.hidden)load();},60000);
})();
