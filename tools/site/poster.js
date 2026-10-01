'use strict';
(()=>{
const trigger=document.querySelector('.poster-preview'),dialog=document.querySelector('#poster-dialog');
if(!trigger||!dialog)return;
const stage=dialog.querySelector('.poster-stage'),img=stage.querySelector('img');let scale=1;
function fit(){const w=Math.max(240,stage.clientWidth-32);img.style.width=(w*scale)+'px';img.style.height='auto';}
function close(){dialog.close();trigger.focus({preventScroll:true});}
trigger.addEventListener('click',()=>{dialog.showModal();scale=1;fit();stage.scrollTop=0;stage.scrollLeft=0;});
dialog.querySelectorAll('[data-poster-action]').forEach(b=>b.addEventListener('click',()=>{const a=b.dataset.posterAction;if(a==='close'){close();return;}scale=a==='fit'?1:Math.max(.5,Math.min(4,scale*(a==='in'?1.4:1/1.4)));fit();}));
dialog.addEventListener('keydown',e=>{if(e.key==='+'||e.key==='='){scale=Math.min(4,scale*1.4);fit();e.preventDefault();}if(e.key==='-'){scale=Math.max(.5,scale/1.4);fit();e.preventDefault();}if(e.key==='0'){scale=1;fit();e.preventDefault();}});
dialog.addEventListener('close',()=>trigger.focus({preventScroll:true}));
dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)close();}});
window.addEventListener('resize',()=>{if(dialog.open)fit();});
})();
