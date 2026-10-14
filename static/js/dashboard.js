(() => {
 'use strict';
 const hour = new Date().getHours(), greeting = hour<12?'Good morning':hour<17?'Good afternoon':'Good evening';
 document.querySelectorAll('[data-greeting]').forEach(el=>el.textContent=greeting);
 document.querySelectorAll('[data-today]').forEach(el=>{el.textContent=new Date().toLocaleDateString(undefined,{day:'numeric',month:'short',year:'numeric'});el.dateTime=new Date().toISOString().slice(0,10);});
 const deadlines=()=>document.querySelectorAll('[data-deadline]').forEach(el=>{
   const deadline=new Date(el.dataset.deadline).getTime();if(!Number.isFinite(deadline))return;
   const diff=deadline-Date.now(),hours=Math.ceil(diff/3600000);
   el.classList.toggle('urgent',hours<24);el.classList.toggle('soon',hours>=24&&hours<=72);
   el.textContent=diff<=0?(el.dataset.allowLate==='true'?'Late submission allowed':'Deadline passed'):hours<24?`${hours}h remaining`:`${Math.floor(hours/24)}d ${hours%24}h remaining`;
   el.title=new Date(deadline).toLocaleString();
 }); deadlines();setInterval(()=>{if(!document.hidden)deadlines();},60000);
 const categories={personal:['name','dob','gender','blood_group'],academic:['register_number','roll_number','department','class','semester','batch','admission_year','cgpa','backlogs'],contact:['email','phone','address','emergency_contact'],placement:['skills','resume','linkedin','portfolio','certifications','placement_status'],internship:['internship_company','internship_role','start_date','end_date','duration','stipend','skills_learned','certificate']};
 const tabs=[...document.querySelectorAll('[data-profile-tab]')];
 const choose = button => {
   const category=button.dataset.profileTab;let shown=0;
   tabs.forEach(tab=>{tab.setAttribute('aria-selected',String(tab===button));tab.tabIndex=tab===button?0:-1;});
   const panel=document.getElementById('profile-details');panel?.setAttribute('aria-labelledby',button.id);
   document.querySelectorAll('[data-profile-key]').forEach(row=>{row.hidden=category!=='all' && (category==='documents'?row.dataset.document!=='true':!categories[category]?.includes(row.dataset.profileKey));if(!row.hidden)shown++;});
   const empty=document.getElementById('profile-empty');if(empty)empty.hidden=shown>0;
 };
 tabs.forEach((tab,index)=>{tab.addEventListener('click',()=>choose(tab));tab.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;choose(tabs[next]);tabs[next].focus();});});
 document.querySelectorAll('.completion-ring').forEach(ring=>{const n=Number(ring.style.getPropertyValue('--completion'));ring.style.setProperty('--accent',n<=40?'var(--red-500)':n<=70?'var(--amber-500)':n<=90?'var(--blue-600)':'var(--emerald-500)');});
})();
