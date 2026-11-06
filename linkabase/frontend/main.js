import React from 'react';
import {createRoot} from 'react-dom/client';
import {Excalidraw,exportToBlob} from '@excalidraw/excalidraw';
import '@excalidraw/excalidraw/index.css';
window.EXCALIDRAW_ASSET_PATH='/studio-assets/';

const incoming=new URLSearchParams(location.hash.slice(1)).get('token');
if(incoming){sessionStorage.setItem('linkabaseToken',incoming);history.replaceState(null,'',location.pathname);}
const token=sessionStorage.getItem('linkabaseToken')||'';
const headers={Authorization:'Bearer '+token};
const status=document.querySelector('#status'),button=document.querySelector('#save');
async function boot(){
try {

const id=location.pathname.split('/').pop();let response=await fetch('/api/drawings/'+id,{headers});if(!response.ok)throw Error('Cannot load drawing');let {scene,version,writable}=await response.json();let api,dirty=false;
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
createRoot(document.querySelector('#root')).render(React.createElement(Excalidraw,{initialData:scene,viewModeEnabled:!writable,excalidrawAPI:a=>{api=a;button.disabled=!writable;status.textContent=writable?'Ready • Save changes before closing':'Read-only drawing';},onChange:()=>{if(writable)dirty=true;}}));
button.onclick=async()=>{button.disabled=true;status.textContent='Saving…';try{const elements=api.getSceneElements(),files=api.getFiles();const appState={viewBackgroundColor:api.getAppState().viewBackgroundColor};let preview=null;
if(elements.length){const blob=await exportToBlob({elements,files,appState,mimeType:'image/png',maxWidthOrHeight:1800});preview=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=reject;r.readAsDataURL(blob);});}
const result=await fetch('/api/drawings/'+id,{method:'PUT',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify({scene:{type:'excalidraw',version:2,source:'linkabase',elements,appState,files},preview,version})});if(!result.ok)throw Error(await result.text());version=(await result.json()).version;dirty=false;status.textContent='Saved ✓ Preview will update in Streamlit';}catch(e){status.textContent='Save failed: '+e.message;}finally{button.disabled=!writable;}};
}catch(e){status.textContent='Editor failed to load: '+e.message;}

}
boot();
