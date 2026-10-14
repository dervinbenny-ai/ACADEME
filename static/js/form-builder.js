(() => {
 'use strict';
 const form=document.getElementById('builder-form');if(!form)return;
 const {el,toast}=Academe;
 const library=JSON.parse(document.getElementById('field-library').textContent),fields=JSON.parse(document.getElementById('initial-fields').textContent);
 const area=document.getElementById('builder-fields'),settings=document.getElementById('field-settings'),status=document.getElementById('builder-status');
 const kinds=['text','textarea','number','decimal','date','email','phone','url','select','multiselect','radio','checkbox','file'];
 const icons={text:'input-cursor-text',textarea:'text-paragraph',number:'123',decimal:'123',date:'calendar3',email:'envelope',phone:'telephone',url:'link-45deg',select:'menu-button-wide',multiselect:'ui-checks',radio:'ui-radios',checkbox:'check-square',file:'file-earmark-arrow-up'};
 let selected=fields[0]||null,dragged=null,suggestions=[];
 const sync=()=>{document.getElementById('fields-json').value=JSON.stringify(fields);document.getElementById('field-count').textContent=fields.length+' FIELD'+(fields.length===1?'':'S');};
 const say=message=>{status.textContent=message;};
 function add(field){
   const existing=fields.find(f=>f.key===field.key);if(existing){selected=existing;render();say(field.label+' is already in the form.');return;}
   const value=structuredClone(field);value.required=value.required!==false;value.reuse=value.reuse||'auto';value.validation=value.validation||{};value.options=value.options||[];fields.push(value);selected=value;render();say(value.label+' added.');
   area.lastElementChild?.classList.add('field-enter');
 }
 function move(index,direction){const next=index+direction;if(next<0||next>=fields.length)return;[fields[index],fields[next]]=[fields[next],fields[index]];render();say('Field moved to position '+(next+1));area.children[next]?.querySelector('.field-select').focus();}
 function button(label,icon,action){const b=el('button',{type:'button','aria-label':label,title:label});b.append(el('i',{class:'bi bi-'+icon}));b.addEventListener('click',event=>{event.stopPropagation();action();});return b;}
 function render(){
   area.replaceChildren();
   if(!fields.length){const empty=el('div',{class:'builder-empty'});empty.append(el('i',{class:'bi bi-ui-checks-grid'}),el('strong',{},'Great requests start with the right fields.'),el('p',{},'Choose from the field library or ask the local assistant for a head start.'));area.append(empty);}
   fields.forEach((field,index)=>{
     field.required=field.required!==false;field.reuse=field.reuse||'auto';field.validation=field.validation||{};field.options=field.options||[];
     const box=el('article',{class:'builder-field'+(field===selected?' selected':''),'data-index':index,draggable:'true'}),head=el('div',{class:'builder-field-head'});
     head.append(el('i',{class:'bi bi-grip-vertical drag-handle','aria-hidden':'true'}));
     const choose=el('button',{type:'button',class:'field-select','aria-label':'Edit '+field.label});choose.style.cssText='text-align:left;flex:1;background:transparent;color:var(--text);font-weight:550;';choose.textContent=String(index+1).padStart(2,'0')+' · '+field.label;choose.addEventListener('click',()=>{selected=field;render();});head.append(choose);
     head.append(button('Move '+field.label+' up','arrow-up',()=>move(index,-1)),button('Move '+field.label+' down','arrow-down',()=>move(index,1)),button('Duplicate '+field.label,'copy',()=>{
       const copy=structuredClone(field);let n=1,key;do{const suffix='_copy_'+n++;key=field.key.slice(0,80-suffix.length)+suffix;}while(fields.some(f=>f.key===key));copy.key=key;copy.label=field.label.slice(0,113)+' (copy)';fields.splice(index+1,0,copy);selected=copy;render();say('Field duplicated.');
     }),button('Remove '+field.label,'x-lg',()=>{fields.splice(index,1);if(selected===field)selected=fields[Math.min(index,fields.length-1)]||null;render();say('Field removed.');}));
     const preview=el('div',{class:'field-preview'});preview.append(el('i',{class:'bi bi-'+(icons[field.type]||'input-cursor-text')}),document.createTextNode('  '+(field.placeholder||(['select','radio','multiselect'].includes(field.type)?(field.options||[]).join(' · ')||'Configure your choices':field.type==='file'?'Drop a document here':field.label))));
     const meta=el('div',{class:'field-meta'});meta.append(el('span',{},field.type),el('span',{},field.required?'Required':'Optional'),el('span',{},'Reuse: '+field.reuse));box.append(head,preview,meta);
     box.addEventListener('click',event=>{if(event.target.closest('button'))return;selected=field;render();});
     box.addEventListener('dragstart',event=>{if(event.target!==box)return;dragged=field;event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',field.key);box.classList.add('dragging');});
     box.addEventListener('dragover',event=>{if(!dragged||dragged===field)return;event.preventDefault();event.dataTransfer.dropEffect='move';box.classList.add('drag-target');});
     box.addEventListener('dragleave',()=>box.classList.remove('drag-target'));
     box.addEventListener('drop',event=>{event.preventDefault();if(!dragged||dragged===field)return;const source=fields.indexOf(dragged),target=fields.indexOf(field);fields.splice(source,1);fields.splice(target,0,dragged);selected=dragged;dragged=null;render();say('Field order updated.');});
     box.addEventListener('dragend',()=>{dragged=null;document.querySelectorAll('.dragging,.drag-target').forEach(node=>node.classList.remove('dragging','drag-target'));});area.append(box);
   });renderSettings();renderLibrary();sync();
 }
 function control(label,key,field,kind='input',choices=[]){
   const wrap=el('div',{class:'field'}),id='setting-'+key,input=el(kind,{id});wrap.append(el('label',{for:id},label));
   if(kind==='select'){choices.forEach(choice=>input.append(el('option',{value:choice},choice)));input.value=field[key]||choices[0];}
   else {input.value=key==='options'?(field.options||[]).join(', '):field[key]||'';if(key==='key'){input.pattern='[a-z][a-z0-9_]{0,79}';input.maxLength=80;}if(key==='label')input.maxLength=120;}
   input.addEventListener('input',()=>{
     field[key]=key==='options'?input.value.split(',').map(x=>x.trim()).filter(Boolean):input.value;sync();const box=area.children[fields.indexOf(field)];
     if(key==='label'){
       box.querySelector('.field-select').textContent=String(fields.indexOf(field)+1).padStart(2,'0')+' · '+field.label;
       const names=['Edit '+field.label,'Move '+field.label+' up','Move '+field.label+' down','Duplicate '+field.label,'Remove '+field.label];
       box.querySelectorAll('.builder-field-head button').forEach((b,i)=>{b.setAttribute('aria-label',names[i]);b.title=names[i];});
     }
     box.querySelector('.field-preview').textContent=field.placeholder||(['select','radio','multiselect'].includes(field.type)?(field.options||[]).join(' · ')||'Configure your choices':field.type==='file'?'Drop a document here':field.label);
     box.querySelector('.field-meta').children[0].textContent=field.type;box.querySelector('.field-meta').children[2].textContent='Reuse: '+field.reuse;
   });
   if(key==='type')input.addEventListener('change',()=>renderSettings());wrap.append(input);return wrap;
 }
 function renderSettings(){
   settings.replaceChildren();if(!selected){settings.append(el('p',{},'Select a field to configure its label, choices, and validation.'));return;}
   const field=selected;field.validation=field.validation||{};
   settings.append(control('Field label','label',field),control('Field key','key',field),control('Input type','type',field,'select',kinds),control('Existing profile information','reuse',field,'select',['auto','confirm','update']));
   const info=el('small',{class:'muted'},'Auto reuses known values. Confirm asks students to check them. Update permits a new value for teacher review.');settings.append(info);
   const label=el('label',{class:'check'}),check=el('input',{type:'checkbox'});check.checked=field.required!==false;check.addEventListener('change',()=>{field.required=check.checked;sync();area.children[fields.indexOf(field)].querySelector('.field-meta').children[1].textContent=check.checked?'Required':'Optional';});label.append(check,document.createTextNode('Required field'));settings.append(label);
   if(['select','multiselect','radio'].includes(field.type))settings.append(control('Choices (comma separated)','options',field));
   settings.append(control('Placeholder','placeholder',field),control('Helper text','help_text',field));
   if(['number','decimal'].includes(field.type)){
     const grid=el('div',{class:'form-grid'});for(const bound of ['min','max']){const wrap=el('div',{class:'field'}),inp=el('input',{type:'number',step:'any',id:'validation-'+bound});inp.value=field.validation[bound]??'';wrap.append(el('label',{for:inp.id},bound==='min'?'Minimum':'Maximum'),inp);inp.addEventListener('input',()=>{if(inp.value==='')delete field.validation[bound];else field.validation[bound]=Number(inp.value);sync();});grid.append(wrap);}settings.append(grid);
   }
 }
 function renderLibrary(){
   const query=document.getElementById('library-search').value.toLowerCase(),list=document.getElementById('library-list');list.replaceChildren();
   const categories=['PERSONAL','ACADEMIC','CONTACT','PLACEMENT','INTERNSHIP','DOCUMENTS','OTHER'];
   categories.forEach(category=>{
     const found=library.filter(field=>(category==='DOCUMENTS'?field.type==='file':field.category===category&&field.type!=='file')&&(field.label+' '+field.category).toLowerCase().includes(query));if(!found.length)return;
     list.append(el('div',{class:'library-category'},category==='OTHER'?'MORE FIELDS':category));
     found.forEach(field=>{const b=el('button',{type:'button'}),added=fields.some(f=>f.key===field.key);b.append(el('i',{class:'bi bi-'+(icons[field.type]||'input-cursor-text')}),el('span',{},field.label),el('i',{class:'bi bi-'+(added?'check2':'plus-lg')}));b.title=added?'Already added — click to edit':'Add '+field.label;b.addEventListener('click',()=>add(field));list.append(b);});
   });if(!list.children.length)list.append(el('p',{class:'table-note'},'No fields match. Try another term or add a custom field.'));
 }
 document.getElementById('library-search').addEventListener('input',renderLibrary);
 document.getElementById('add-custom').addEventListener('click',()=>{let n=1;while(fields.some(f=>f.key==='custom_'+n))n++;add({key:'custom_'+n,label:'Custom field',type:'text',required:true,reuse:'auto',options:[],validation:{}});document.getElementById('setting-label')?.focus();});
 async function suggest(){
   const prompt=document.getElementById('ai-prompt').value.trim(),button=document.getElementById('suggest-fields'),status=document.getElementById('suggestion-status'),list=document.getElementById('suggestion-list');
   if(!prompt){status.textContent='Describe the information you would like to collect.';document.getElementById('ai-prompt').focus();return;}
   button.disabled=true;document.getElementById('regenerate-suggestions').disabled=true;status.textContent='Finding relevant fields in the local library...';list.replaceChildren(el('div',{class:'skeleton block'}));
   try{const response=await fetch('/api/suggest',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':Academe.csrf()},body:JSON.stringify({prompt})});if(!response.ok||!response.headers.get('content-type')?.includes('application/json'))throw new Error('Suggestions are unavailable. You can keep building with the field library.');const data=await response.json();suggestions=data.fields;status.textContent=data.provider+' · '+data.message;if(!document.getElementById('title').value)document.getElementById('title').value=data.title;list.replaceChildren();
     suggestions.forEach((field,index)=>{const accept=el('button',{type:'button',class:'field-enter'},'+ '+field.label);accept.style.animationDelay=(Math.min(index,5)*40)+'ms';accept.addEventListener('click',()=>{add(field);accept.disabled=true;accept.textContent='✓ '+field.label+' added';});list.append(accept);});document.getElementById('suggestion-actions').hidden=!suggestions.length;
   }catch(error){status.textContent=error.message;list.replaceChildren();document.getElementById('suggestion-actions').hidden=true;}finally{button.disabled=false;document.getElementById('regenerate-suggestions').disabled=false;}
 }
 document.getElementById('suggest-fields').addEventListener('click',suggest);document.getElementById('regenerate-suggestions').addEventListener('click',suggest);
 document.getElementById('add-all-suggestions').addEventListener('click',()=>{suggestions.forEach(field=>{if(!fields.some(f=>f.key===field.key))fields.push(structuredClone(field));});selected=fields.at(-1)||null;render();document.querySelectorAll('#suggestion-list button').forEach(b=>b.disabled=true);say('Suggested fields added. Review each field before saving.');});
 const preview=document.getElementById('preview-dialog');
 document.getElementById('preview-form').addEventListener('click',()=>{
   const content=document.getElementById('preview-content');content.replaceChildren();if(!fields.length)content.append(el('p',{},'Add fields to see a preview.'));
   fields.forEach((field,index)=>{const wrap=el('div',{class:'field'}),id='preview-'+index;wrap.append(el('label',{for:id},field.label+(field.required?' *':'')));let input;
     if(['select','multiselect'].includes(field.type)){input=el('select',{id});if(field.type==='multiselect')input.multiple=true;else input.append(el('option',{},'Choose an option'));(field.options||[]).forEach(option=>input.append(el('option',{},option)));}
     else if(['radio','checkbox'].includes(field.type)){input=el('div',{id});const options=field.type==='checkbox'?['Yes']:(field.options||[]);options.forEach(option=>{const label=el('label',{class:'check'});label.append(el('input',{type:field.type,name:'preview-'+index}),document.createTextNode(option));input.append(label);});}
     else input=el(field.type==='textarea'?'textarea':'input',{id,type:({decimal:'number',phone:'tel'}[field.type]||field.type),placeholder:field.placeholder||field.label});
     wrap.append(input,el('small',{},(field.help_text?field.help_text+' · ':'')+'Existing information: '+field.reuse));content.append(wrap);
   });preview.showModal();
 });document.getElementById('close-preview').addEventListener('click',()=>preview.close());
 form.addEventListener('submit',event=>{
   sync();const keys=fields.map(f=>f.key),bad=fields.find(f=>!f.label?.trim()||!/^[a-z][a-z0-9_]{0,79}$/.test(f.key)||(['select','radio','multiselect'].includes(f.type)&&!(f.options||[]).length));
   let message=!fields.length?'Add at least one field before saving.':new Set(keys).size!==keys.length?'Every field needs a unique key.':bad?'Check the selected field’s label, key, and choices.':'';
   if(message){event.preventDefault();if(bad){selected=bad;render();document.getElementById('setting-label')?.focus();}say(message);toast(message,'danger');area.scrollIntoView({behavior:Academe.reduced()?'instant':'smooth',block:'center'});}
 });
 const picker=document.getElementById('class_id');function targets(){document.querySelectorAll('#target-list [data-class]').forEach(label=>{label.hidden=label.dataset.class!==picker.value;if(label.hidden)label.querySelector('input').checked=false;});}picker.addEventListener('change',targets);targets();render();
})();
