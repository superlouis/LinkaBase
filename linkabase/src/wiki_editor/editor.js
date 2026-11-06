import MarkdownIt from 'markdown-it';
import Turndown from 'turndown';
import {gfm} from 'turndown-plugin-gfm';
import DOMPurify from 'dompurify';
const md=new MarkdownIt({html:false,linkify:true,breaks:false});
const td=new Turndown({headingStyle:'atx',codeBlockStyle:'fenced',bulletListMarker:'-'});td.use(gfm);
let eventSequence=0;
// Event deduplication only: no secure-context API or authentication role.
const eventId=()=>Date.now().toString(36)+'-'+(++eventSequence)+'-'+Math.random().toString(36).slice(2);
const send=(type,extra={})=>parent.postMessage({isStreamlitMessage:true,type,...extra},'*');
let args,original='',changed=false,mode='visual',revision;
const $=id=>document.getElementById(id);
function source(){return changed?(mode==='source'?$('source').value:td.turndown($('paper').innerHTML)):original;}
function status(){ $('status').textContent=changed?'Unsaved changes':'No unsaved changes'; }
let previewing=false;
function switchMode(next){previewing=false;$('preview').hidden=true;$('previewToggle').setAttribute('aria-pressed','false');$('help').textContent=next==='source'?'Markdown source · Write Markdown directly. Preview shows the rendered document.':'Visual editor · Select text to format it. Use the toolbar for headings, lists, links, images, and tables.';const text=source();mode=next;$('source').value=text;$('paper').innerHTML=DOMPurify.sanitize(md.render(text));$('source').hidden=next!=='source';$('paper').hidden=next!=='visual';$('toolbar').hidden=next!=='visual';$('mode').value=next;}
window.addEventListener('message',e=>{if(e.source!==parent||e.data.type!=='streamlit:render')return;args=e.data.args;
for(const [k,v]of Object.entries(args.colors))document.documentElement.style.setProperty('--'+k,v);
if(revision!==args.revision){revision=args.revision;original=args.content;changed=false;mode=/^(---\s*$)|\[\[|\$\$|<\w+/m.test(original)?'source':'visual';switchMode(mode);status();}
send('streamlit:setFrameHeight',{height:620});});
function dirty(){changed=true;status();}
$('paper').addEventListener('input',dirty);$('source').addEventListener('input',dirty);
$('paper').addEventListener('paste',e=>{e.preventDefault();document.execCommand('insertText',false,e.clipboardData.getData('text/plain'));dirty();});
$('previewToggle').onclick=()=>{previewing=!previewing;$('preview').innerHTML=DOMPurify.sanitize(md.render(source()));$('preview').hidden=!previewing;$('paper').hidden=previewing||mode!=='visual';$('source').hidden=previewing||mode!=='source';$('toolbar').hidden=previewing||mode!=='visual';$('previewToggle').setAttribute('aria-pressed',String(previewing));};
$('mode').onchange=e=>switchMode(e.target.value);
for(const b of document.querySelectorAll('#toolbar button'))b.addEventListener('mousedown',e=>e.preventDefault());
for(const b of document.querySelectorAll('[data-cmd]')){b.onmousedown=e=>e.preventDefault();b.onclick=()=>{document.execCommand(b.dataset.cmd,false,b.dataset.value||null);dirty();};}
$('heading').onchange=e=>{document.execCommand('formatBlock',false,e.target.value);dirty();};
$('link').onclick=()=>{const url=prompt('Link address (https://…)');if(url&&/^https?:\/\//i.test(url)){document.execCommand('createLink',false,url);dirty();}};
$('image').onclick=()=>{const url=prompt('Image address (https://…)');if(url&&/^https?:\/\//i.test(url)){document.execCommand('insertImage',false,url);dirty();}};
$('table').onclick=()=>{document.execCommand('insertHTML',false,'<table><thead><tr><th>Heading</th><th>Heading</th></tr></thead><tbody><tr><td>Text</td><td>Text</td></tr></tbody></table><p><br></p>');dirty();};
function action(action){send('streamlit:setComponentValue',{value:{action,content:source(),nonce:eventId()}});}
$('save').onclick=()=>action('save');$('cancel').onclick=()=>{if(!changed||confirm('Discard unsaved changes?'))action('cancel');};
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='s'){e.preventDefault();action('save');}});
send('streamlit:componentReady',{apiVersion:1});
