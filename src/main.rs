#![windows_subsystem = "windows"]
use std::env;
use std::sync::Arc;
use tao::event::{Event, WindowEvent};
use tao::event_loop::{ControlFlow, EventLoop};
use tao::window::WindowBuilder;
use std::io::{self, Read, IsTerminal};
use wry::WebViewBuilder;
#[cfg(windows)]
use wry::WebViewBuilderExtWindows;

const HTML: &str = r#"<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#000;color:#fff;font-family:system-ui,sans-serif;height:100vh;overflow:hidden;position:relative}
#v{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#000}
.controls{position:absolute;left:0;right:0;bottom:0;padding:12px;background:linear-gradient(transparent,rgba(0,0,0,0.85));transition:opacity 0.3s;opacity:1;z-index:10}
.controls.hide{opacity:0;pointer-events:none}
.row{display:flex;align-items:center;gap:10px}
button,label{background:transparent;border:none;color:#fff;cursor:pointer;display:flex;align-items:center;padding:4px}
svg{width:20px;height:20px;fill:#fff}
#tl{flex:1;height:6px;background:rgba(128,128,128,0.35);border-radius:3px;cursor:pointer;position:relative}
#fill{height:100%;background:rgb(116,192,252);border-radius:3px;width:0}
.volwrap{position:relative;display:flex;align-items:center;gap:4px}
.vol{display:none;position:absolute;bottom:30px;left:50%;transform:translateX(-50%);writing-mode:vertical-lr;direction:rtl;width:6px;height:90px;appearance:none;-webkit-appearance:none;background:rgba(128,128,128,0.35);border-radius:3px;cursor:pointer;z-index:15}
.volwrap:hover .vol{display:block}
.vol::-webkit-slider-runnable-track{width:6px;height:100%;background:rgba(128,128,128,0.35);border-radius:3px}
.vol::-webkit-slider-thumb{appearance:none;-webkit-appearance:none;width:14px;height:14px;border-radius:50%;background:rgb(116,192,252);margin-left:-4px;border:none}
.vol::-moz-range-track{width:6px;height:100%;background:rgba(128,128,128,0.35);border-radius:3px}
.vol::-moz-range-progress{width:6px;height:100%;background:rgb(116,192,252);border-radius:3px}
.vol::-moz-range-thumb{width:14px;height:14px;border-radius:50%;background:rgb(116,192,252);border:none}
.time{font-size:13px;min-width:90px;text-align:center;cursor:pointer;user-select:none}

.speedwrap{position:relative}
#speedmenu{display:none;position:absolute;bottom:36px;right:0;background:#222;padding:4px;border-radius:6px;min-width:70px}
#speedmenu button{display:block;width:100%;text-align:left;padding:6px;font-size:13px}
#speedmenu button.active{background:#fff;color:#000}
.dnd{position:absolute;inset:0;display:none;align-items:center;justify-content:center;background:rgba(0,0,0,0.4);font-size:18px;z-index:20}
.dnd.show{display:flex}
.brandmark{display:flex;align-items:center;opacity:.85;margin-right:2px}
.brandmark svg{width:22px;height:22px;filter:drop-shadow(0 1px 2px rgba(0,0,0,.8))}
.speedwrap{position:relative;display:flex;align-items:center;gap:4px}
.spdind{position:fixed;top:12px;right:12px;background:rgba(0,0,0,.6);color:#fff;padding:8px 14px;border-radius:8px;font-size:22px;font-weight:600;opacity:0;transition:opacity .4s;pointer-events:none;z-index:21;white-space:nowrap}
.spdind.show{opacity:1}

.volind{position:fixed;top:12px;right:12px;background:rgba(0,0,0,.6);color:#fff;padding:8px 14px;border-radius:8px;font-size:22px;font-weight:600;opacity:0;transition:opacity .4s;pointer-events:none;z-index:20}

/* Settings menu */
.settingswrap{position:relative;display:flex;align-items:center;gap:4px}
#settingsbtn{opacity:0;transition:opacity 0.2s;background:rgba(0,0,0,0.3);border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center}
.controls:hover #settingsbtn,#settingsbtn:hover{opacity:1}
#settingsmenu{display:none;position:absolute;bottom:36px;right:0;background:#222;padding:8px;border-radius:8px;min-width:220px;max-width:300px;z-index:20;box-shadow:0 4px 20px rgba(0,0,0,0.5)}
#settingsmenu.show{display:block}
.settings-section{padding:8px 0;border-bottom:1px solid #333}
.settings-section:last-child{border-bottom:none}
.settings-section h4{font-size:11px;text-transform:uppercase;color:#888;margin:0 0 8px;padding:0 4px;letter-spacing:0.5px}
.settings-section button{display:flex;align-items:center;gap:8px;width:100%;text-align:left;padding:8px 12px;font-size:13px;border-radius:4px;background:transparent;color:#fff;cursor:pointer;transition:background 0.15s}
.settings-section button:hover{background:#333}
.settings-section button.active{background:rgb(116,192,252);color:#000}
.settings-section button.disabled{opacity:0.4;cursor:not-allowed}
.settings-section button .track-info{font-size:11px;color:#aaa;margin-left:auto}
.settings-section button .sync-controls{display:flex;align-items:center;gap:6px;margin-top:6px;padding-top:6px;border-top:1px solid #333;font-size:12px}
.settings-section button .sync-controls input{width:50px;padding:2px 6px;background:#111;border:1px solid #333;border-radius:3px;color:#fff;font-size:11px}
.settings-section button .sync-controls input:focus{outline:none;border-color:rgb(116,192,252)}
.settings-section button .sync-controls label{display:flex;align-items:center;gap:4px;color:#aaa;cursor:pointer}
.settings-divider{height:1px;background:#333;margin:4px 0}
#subtitle-menu,#audio-menu{max-height:200px;overflow-y:auto}
.subtitle-sync{display:none;padding:8px;background:#1a1a1a;border-radius:4px;margin-top:4px}
.subtitle-sync.show{display:block}
.subtitle-sync label{display:block;margin-bottom:4px;color:#aaa;font-size:12px}
.subtitle-sync input[type="number"]{width:80px;padding:4px 8px;background:#111;border:1px solid #333;border-radius:3px;color:#fff;font-size:13px}
.subtitle-sync input[type="number"]:focus{outline:none;border-color:rgb(116,192,252)}
.subtitle-sync .sync-btns{display:flex;gap:6px;margin-top:8px}
.subtitle-sync .sync-btns button{flex:1;padding:6px;background:#333;border:none;border-radius:3px;color:#fff;font-size:12px;cursor:pointer}
.subtitle-sync .sync-btns button:hover{background:rgb(116,192,252);color:#000}
.subtitle-sync .sync-btns button:disabled{opacity:0.5;cursor:not-allowed}
.track-item{display:flex;align-items:center;gap:8px;padding:8px 12px;border-radius:4px;cursor:pointer;transition:background 0.15s}
.track-item:hover{background:#333}
.track-item.active{background:rgb(116,192,252);color:#000}
.track-item .track-lang{font-weight:500}
.track-item .track-label{color:#aaa;font-size:12px}
.track-item .track-default{color:rgb(116,192,252);font-size:11px;margin-left:auto}
.external-track-btn{width:100%;text-align:left;padding:8px 12px;font-size:13px;background:#333;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-top:8px;display:flex;align-items:center;gap:8px}
.external-track-btn:hover{background:rgb(116,192,252);color:#000}
.external-track-btn svg{width:16px;height:16px}
.no-tracks{padding:12px;color:#888;font-size:13px;text-align:center}

</style></head><body>
<video id="v" crossorigin="anonymous"></video>
<input type="file" id="f" accept="video/*" style="display:none">
<input type="file" id="subtitle-file" accept=".srt,.vtt,.ass,.ssa" style="display:none" multiple>
<input type="file" id="audio-file" accept="audio/*" style="display:none" multiple>
<div class="controls" id="ctl">
  <div class="row">
    <div class="brandmark"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640"><path fill="rgb(116, 192, 252)" d="M128 128C92.7 128 64 156.7 64 192L64 448C64 483.3 92.7 512 128 512L384 512C419.3 512 448 483.3 448 448L448 192C448 156.7 419.3 128 384 128L128 128zM496 400L569.5 458.8C573.7 462.2 578.9 464 584.3 464C597.4 464 608 453.4 608 440.3L608 199.7C608 186.6 597.4 176 578.9 176 573.7 177.8 569.5 181.2L496 240L496 400z"/></svg></div>
    <button id="play"></button>
    <span class="time" id="cur">00:00:00</span>
    <div id="tl"><div id="fill"></div></div>
    <span class="time" id="end">00:00:00</span>
    <span id="spd"></span>
    <div class="volwrap">
      <button id="volbtn"></button>
      <input type="range" class="vol" id="vol" min="0" max="2" step="0.01" value="1">
<div class="volind" id="volind">100%</div>
<div class="spdind" id="spdind">1x</div>
    </div>
    <div class="speedwrap">
      <button id="speedbtn"></button>
      <div id="speedmenu">
        <button data-s="0.5">0.5x</button><button data-s="0.7">0.7x</button><button data-s="1">1x</button><button data-s="1.3">1.3x</button><button data-s="1.5">1.5x</button><button data-s="1.6">1.6x</button><button data-s="1.7">1.7x</button><button data-s="1.8">1.8x</button><button data-s="1.9">1.9x</button><button data-s="2">2x</button>
      </div>
    </div>
    <div class="settingswrap">
      <button id="settingsbtn" title="Settings"></button>
      <div id="settingsmenu">
        <div class="settings-section">
          <h4>Subtitles</h4>
          <div id="subtitle-menu"></div>
          <button class="external-track-btn" id="load-subtitle-btn">
            <svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
            Load subtitle file
          </button>
        </div>
        <div class="settings-section">
          <h4>Audio Tracks</h4>
          <div id="audio-menu"></div>
          <button class="external-track-btn" id="load-audio-btn">
            <svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
            Load audio file
          </button>
        </div>
      </div>
    </div>
    <label for="f" id="open"></label>
    <button id="fsbtn"></button>
  </div>
</div>
<div class="dnd" id="dnd">Drop video here</div>
<script>
const v=document.getElementById("v");
const play=document.getElementById("play");
const tl=document.getElementById("tl");
const fill=document.getElementById("fill");
const vol=document.getElementById("vol");
const cur=document.getElementById("cur");
const end=document.getElementById("end");
const spd=document.getElementById("spd");
const ctl=document.getElementById("ctl");
const speedbtn=document.getElementById("speedbtn");
const speedmenu=document.getElementById("speedmenu");
const settingsbtn=document.getElementById("settingsbtn");
const settingsmenu=document.getElementById("settingsmenu");
const subtitleMenu=document.getElementById("subtitle-menu");
const audioMenu=document.getElementById("audio-menu");
const loadSubtitleBtn=document.getElementById("load-subtitle-btn");
const loadAudioBtn=document.getElementById("load-audio-btn");
const subtitleFileInput=document.getElementById("subtitle-file");
const audioFileInput=document.getElementById("audio-file");
const dnd=document.getElementById("dnd");
const spdind=document.getElementById("spdind");
const fsbtn=document.getElementById("fsbtn");
const PLAY='<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
const PAUSE='<svg viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>';
const CLOCK='<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z"/></svg>';
const FOLDER='<svg viewBox="0 0 24 24"><path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>';
const VOLUME='<svg viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>';
const MUTE='<svg viewBox="0 0 24 24"><path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/></svg>';
const SETTINGS='<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>';
const FS='<svg viewBox="0 0 24 24"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg>';
const FS_EXIT='<svg viewBox="0 0 24 24"><path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/></svg>';
let speed=1,showRemaining=false,timer=null,volTimer=null,spdTimer=null,isMuted=false,prevVol=1,hudReady=false;
let currentSubtitleTrack=null,currentAudioTrack=null,subtitleOffset=0,externalSubtitles=[],externalAudioTracks=[];
function fmt(s){if(!isFinite(s))return "00:00:00";s=Math.max(0,Math.floor(s));const h=Math.floor(s/3600),m=Math.floor((s%3600)/60),sec=s%60;return String(h).padStart(2,"0")+":"+String(m).padStart(2,"0")+":"+String(sec).padStart(2,"0");}
function upd(){if(v.duration){fill.style.width=(v.currentTime/v.duration*100)+"%";cur.textContent=fmt(v.currentTime);end.textContent=showRemaining?"-"+fmt(v.duration-v.currentTime):fmt(v.duration);}}
function toggle(){v.paused?v.play():v.pause();}
function showCtl(){ctl.classList.remove("hide");clearTimeout(timer);if(!v.paused)timer=setTimeout(()=>ctl.classList.add("hide"),3000);}
function setVideoName(n){if(n){const b=n.split(/[\\\\/]/).pop();document.title="PVP | "+(b||n);}}
play.innerHTML=PLAY;speedbtn.innerHTML=CLOCK;document.getElementById("open").innerHTML=FOLDER;document.getElementById("volbtn").innerHTML=VOLUME;settingsbtn.innerHTML=SETTINGS;fsbtn.innerHTML=FS;
play.onclick=toggle;v.onclick=toggle;v.onplay=()=>{play.innerHTML=PAUSE;ensureAudio();if(audioCtx&&audioCtx.state==="suspended")audioCtx.resume();};v.onpause=()=>play.innerHTML=PLAY;v.ontimeupdate=upd;
tl.onclick=e=>{const r=tl.getBoundingClientRect();if(v.duration)v.currentTime=(e.clientX-r.left)/r.width*v.duration;};
end.onclick=()=>{showRemaining=!showRemaining;if(v.duration)upd();}
const SPEEDS=[0.5,0.7,1,1.3,1.5,1.6,1.7,1.8,1.9,2];
function applySpeed(val){let idx=SPEEDS.reduce((b,cur,i)=>Math.abs(cur-val)<Math.abs(SPEEDS[b]-val)?i:b,0);speed=SPEEDS[idx];v.playbackRate=speed;spd.textContent=speed!==1?speed.toFixed(1)+'x':'';const vi=document.getElementById("volind");if(hudReady){vi.style.opacity=0;clearTimeout(volTimer);}spdind.textContent=speed.toFixed(1)+'x';if(hudReady)spdind.classList.add("show");clearTimeout(spdTimer);spdTimer=setTimeout(()=>spdind.classList.remove("show"),900);document.querySelectorAll('#speedmenu button').forEach(function(x){x.classList.remove('active');if(+x.dataset.s===speed)x.classList.add('active');});}

let audioCtx=null,gainNode=null,sourceNode=null;
function ensureAudio(){if(audioCtx)return;try{audioCtx=new (window.AudioContext||window.webkitAudioContext)();sourceNode=audioCtx.createMediaElementSource(v);gainNode=audioCtx.createGain();sourceNode.connect(gainNode);gainNode.connect(audioCtx.destination);}catch(e){audioCtx=null;}}
function applyVolume(val){val=Math.max(0,Math.min(2,val));ensureAudio();if(gainNode)gainNode.gain.value=val;try{v.volume=Math.min(1,val);}catch(e){}vol.value=val;const pct=(val/2*100);vol.style.background="linear-gradient(to top, rgb(116,192,252) "+pct+"%, rgba(128,128,128,0.35) "+pct+"%)";const ind=document.getElementById("volind");ind.textContent=Math.round(val*100)+"%";spdind.classList.remove("show");clearTimeout(spdTimer);if(hudReady){ind.style.opacity=1;clearTimeout(volTimer);volTimer=setTimeout(()=>ind.style.opacity=0,900);}if(val>0){if(isMuted){isMuted=false;document.getElementById("volbtn").innerHTML=VOLUME;}prevVol=val;}else if(val===0){document.getElementById("volbtn").innerHTML=MUTE;isMuted=true;}}
vol.oninput=()=>applyVolume(+vol.value);
function setMute(m){isMuted=m;if(m){prevVol=+vol.value||prevVol;applyVolume(0);document.getElementById("volbtn").innerHTML=MUTE;}else{applyVolume(prevVol||1);document.getElementById("volbtn").innerHTML=VOLUME;}}
document.getElementById("volbtn").onclick=e=>{e.stopPropagation();setMute(!isMuted);}
speedbtn.onclick=e=>{e.stopPropagation();speedmenu.style.display=speedmenu.style.display==="block"?"none":"block";};
document.querySelectorAll('#speedmenu button').forEach(function(b){b.onclick=function(){applySpeed(+b.dataset.s);document.querySelectorAll('#speedmenu button').forEach(function(x){x.classList.remove('active');});b.classList.add('active');speedmenu.style.display='none';};});
let isFs=false;fsbtn.onclick=e=>{e.stopPropagation();if(window.chrome&&window.chrome.webview)window.chrome.webview.postMessage("fullscreen");isFs=!isFs;fsbtn.innerHTML=isFs?FS_EXIT:FS;};
document.addEventListener("fullscreenchange",()=>{fsbtn.innerHTML=document.fullscreenElement?FS_EXIT:FS;});
document.addEventListener("click",e=>{if(!settingsmenu.contains(e.target)&&e.target!==settingsbtn){settingsmenu.classList.remove("show");}speedmenu.style.display="none";});

settingsbtn.onclick=e=>{e.stopPropagation();settingsmenu.classList.toggle("show");};

// Subtitle handling
function parseSRT(content){const tracks=[];const blocks=content.trim().split(/\n\s*\n/);blocks.forEach((block,i)=>{const lines=block.trim().split('\n');if(lines.length>=3){const timeMatch=lines[1].match(/(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})/);if(timeMatch){const start=parseTime(timeMatch[1]);const end=parseTime(timeMatch[2]);const text=lines.slice(2).join('\n');tracks.push({index:i,start,end,text});}}});return tracks;}
function parseVTT(content){const tracks=[];const lines=content.split('\n');let i=0;while(i<lines.length){const line=lines[i].trim();const timeMatch=line.match(/(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})/);if(timeMatch){const start=parseTime(timeMatch[1].replace('.',','));const end=parseTime(timeMatch[2].replace('.',','));i++;let text='';while(i<lines.length&&lines[i].trim()){text+=lines[i]+'\n';i++;}tracks.push({index:tracks.length,start,end,text:text.trim()});}i++;}return tracks;}
function parseTime(t){const parts=t.split(/[:,]/);return(+parts[0])*3600+(+parts[1])*60+(+parts[2])+(+parts[3])/1000;}
function formatSRT(tracks){return tracks.map((t,i)=>`${i+1}\n${fmtTime(t.start)} --> ${fmtTime(t.end)}\n${t.text}\n`).join('\n');}
function fmtTime(s){const h=Math.floor(s/3600).toString().padStart(2,'0');const m=Math.floor((s%3600)/60).toString().padStart(2,'0');const sec=Math.floor(s%60).toString().padStart(2,'0');const ms=Math.floor((s%1)*1000).toString().padStart(3,'0');return `${h}:${m}:${sec},${ms}`;}

function renderSubtitleMenu(){
  subtitleMenu.innerHTML='';
  let hasTracks=false;
  // Internal text tracks
  if(v.textTracks&&v.textTracks.length>0){
    hasTracks=true;
    for(let i=0;i<v.textTracks.length;i++){
      const track=v.textTracks[i];
      const item=document.createElement('div');
      item.className='track-item'+(track.mode==='showing'?' active':'');
      item.innerHTML=`<span class="track-lang">${track.language||'Und'}</span><span class="track-label">${track.label||'Track '+(i+1)}</span>${track.default?'<span class="track-default">Default</span>':''}`;
      item.onclick=()=>selectSubtitleTrack(i);
      subtitleMenu.appendChild(item);
    }
  }
  // External subtitles
  externalSubtitles.forEach((sub,idx)=>{
    hasTracks=true;
    const item=document.createElement('div');
    item.className='track-item'+(currentSubtitleTrack===sub?' active':'');
    item.innerHTML=`<span class="track-lang">${sub.lang||'Ext'}</span><span class="track-label">${sub.name||'External '+ (idx+1)}</span><span class="track-default">External</span>`;
    item.onclick=()=>selectExternalSubtitle(sub);
    subtitleMenu.appendChild(item);
  });
  if(!hasTracks){
    subtitleMenu.innerHTML='<div class="no-tracks">No subtitle tracks available</div>';
  }
  // Add sync controls if external subtitle selected
  if(currentSubtitleTrack&&externalSubtitles.includes(currentSubtitleTrack)){
    addSubtitleSyncControls();
  }
}

function addSubtitleSyncControls(){
  const existing=document.querySelector('.subtitle-sync');
  if(existing)existing.remove();
  const syncDiv=document.createElement('div');
  syncDiv.className='subtitle-sync show';
  syncDiv.innerHTML=`
    <label>Sync offset: <input type="number" id="subtitle-offset" value="${subtitleOffset}" step="0.1" min="-60" max="60"> seconds</label>
    <div class="sync-btns">
      <button id="sync-subtitle-btn">Apply Sync</button>
      <button id="reset-subtitle-btn">Reset</button>
    </div>
  `;
  subtitleMenu.appendChild(syncDiv);
  document.getElementById('sync-subtitle-btn').onclick=()=>{
    subtitleOffset=parseFloat(document.getElementById('subtitle-offset').value)||0;
    applySubtitleSync();
  };
  document.getElementById('reset-subtitle-btn').onclick=()=>{
    subtitleOffset=0;
    document.getElementById('subtitle-offset').value=0;
    applySubtitleSync();
  };
}

function applySubtitleSync(){
  if(currentSubtitleTrack&&externalSubtitles.includes(currentSubtitleTrack)){
    currentSubtitleTrack.offset=subtitleOffset;
    // Re-render cues with offset
    renderExternalSubtitles();
  }
}

function renderExternalSubtitles(){
  // Remove existing external track
  for(let i=v.textTracks.length-1;i>=0;i--){
    const track=v.textTracks[i];
    if(track.kind==='subtitles'&&track.label&&track.label.startsWith('External:')){
      v.removeTextTrack(track);
    }
  }
  if(currentSubtitleTrack&&externalSubtitles.includes(currentSubtitleTrack)){
    const track=v.addTextTrack('subtitles',currentSubtitleTrack.name,'External:'+currentSubtitleTrack.lang);
    track.mode='showing';
    currentSubtitleTrack.cues.forEach(cue=>{
      track.addCue(new VTTCue(cue.start+subtitleOffset,cue.end+subtitleOffset,cue.text));
    });
  }
}

function selectSubtitleTrack(index){
  for(let i=0;i<v.textTracks.length;i++){
    v.textTracks[i].mode=i===index?'showing':'hidden';
  }
  currentSubtitleTrack=v.textTracks[index]||null;
  subtitleOffset=0;
  renderSubtitleMenu();
}

function selectExternalSubtitle(sub){
  currentSubtitleTrack=sub;
  renderExternalSubtitles();
  renderSubtitleMenu();
}

function loadExternalSubtitle(file){
  const reader=new FileReader();
  reader.onload=e=>{
    let tracks=[];
    const ext=file.name.split('.').pop().toLowerCase();
    if(ext==='srt')tracks=parseSRT(e.target.result);
    else if(ext==='vtt')tracks=parseVTT(e.target.result);
    else{alert('Unsupported subtitle format');return;}
    const sub={name:file.name,lang:file.name.split('.').slice(0,-1).join('.').split(/[-_]/).pop()||'Ext',cues:tracks,offset:0};
    externalSubtitles.push(sub);
    selectExternalSubtitle(sub);
  };
  reader.readAsText(file);
}

loadSubtitleBtn.onclick=()=>subtitleFileInput.click();
subtitleFileInput.onchange=e=>{
  Array.from(e.target.files).forEach(loadExternalSubtitle);
  e.target.value='';
};

// Audio track handling
function renderAudioMenu(){
  audioMenu.innerHTML='';
  let hasTracks=false;
  if(v.audioTracks&&v.audioTracks.length>0){
    hasTracks=true;
    for(let i=0;i<v.audioTracks.length;i++){
      const track=v.audioTracks[i];
      const item=document.createElement('div');
      item.className='track-item'+(track.enabled?' active':'');
      item.innerHTML=`<span class="track-lang">${track.language||'Und'}</span><span class="track-label">${track.label||'Track '+(i+1)}</span>${track.kind==='main'?'<span class="track-default">Main</span>':''}`;
      item.onclick=()=>selectAudioTrack(i);
      audioMenu.appendChild(item);
    }
  }
  externalAudioTracks.forEach((aud,idx)=>{
    hasTracks=true;
    const item=document.createElement('div');
    item.className='track-item'+(currentAudioTrack===aud?' active':'');
    item.innerHTML=`<span class="track-lang">${aud.lang||'Ext'}</span><span class="track-label">${aud.name||'External '+ (idx+1)}</span><span class="track-default">External</span>`;
    item.onclick=()=>selectExternalAudio(aud);
    audioMenu.appendChild(item);
  });
  if(!hasTracks){
    audioMenu.innerHTML='<div class="no-tracks">No audio tracks available</div>';
  }
}

function selectAudioTrack(index){
  if(v.audioTracks){
    for(let i=0;i<v.audioTracks.length;i++){
      v.audioTracks[i].enabled=i===index;
    }
    currentAudioTrack=v.audioTracks[index]||null;
  }
  renderAudioMenu();
}

function selectExternalAudio(aud){
  // For external audio, we'd need to swap the video source or use audio context
  // This is a placeholder for the UI - actual implementation would require more complex handling
  currentAudioTrack=aud;
  alert('External audio track selection: '+aud.name+'\n(Full implementation requires video reloading with new audio)');
  renderAudioMenu();
}

function loadExternalAudio(file){
  const reader=new FileReader();
  reader.onload=e=>{
    const aud={name:file.name,lang:file.name.split('.').slice(0,-1).join('.').split(/[-_]/).pop()||'Ext',blob:e.target.result,url:URL.createObjectURL(file)};
    externalAudioTracks.push(aud);
    selectExternalAudio(aud);
  };
  reader.readAsArrayBuffer(file);
}

loadAudioBtn.onclick=()=>audioFileInput.click();
audioFileInput.onchange=e=>{
  Array.from(e.target.files).forEach(loadExternalAudio);
  e.target.value='';
};

// Initialize menus when video metadata loads
v.addEventListener('loadedmetadata',()=>{
  renderSubtitleMenu();
  renderAudioMenu();
});

// Also update when text tracks change
v.addEventListener('loadstart',()=>{
  externalSubtitles=[];
  externalAudioTracks=[];
  currentSubtitleTrack=null;
  currentAudioTrack=null;
  subtitleOffset=0;
});

document.getElementById("f").onchange=e=>{const f=e.target.files[0];if(f){v.src=URL.createObjectURL(f);v.muted=true;v.play().then(()=>v.muted=false).catch(()=>{});setVideoName(f.name);}};
["mousemove","mousedown","wheel"].forEach(ev=>document.addEventListener(ev,showCtl));document.addEventListener("keydown",e=>{showCtl();if(e.code==="Space"){e.preventDefault();toggle();}else if(e.code==="KeyF"){e.preventDefault();if(window.chrome&&window.chrome.webview)window.chrome.webview.postMessage("fullscreen");isFs=!isFs;fsbtn.innerHTML=isFs?FS_EXIT:FS;}else if(e.code==="ArrowUp"){e.preventDefault();applyVolume(Math.min(2,+vol.value+0.1));}else if(e.code==="ArrowDown"){e.preventDefault();applyVolume(Math.max(0,+vol.value-0.1));}else if(e.code==="ArrowLeft"){e.preventDefault();if(v.duration)v.currentTime=Math.max(0,v.currentTime-10);upd();}else if(e.code==="ArrowRight"){e.preventDefault();if(v.duration)v.currentTime=Math.min(v.duration,v.currentTime+10);upd();}else if(e.code==="KeyM"){e.preventDefault();setMute(!isMuted);}else if(e.code==="BracketLeft"){e.preventDefault();let i=SPEEDS.indexOf(speed);if(i>0)applySpeed(SPEEDS[i-1]);}else if(e.code==="BracketRight"){e.preventDefault();let i=SPEEDS.indexOf(speed);if(i<SPEEDS.length-1)applySpeed(SPEEDS[i+1]);}});
showCtl();
["dragenter","dragover"].forEach(ev=>document.addEventListener(ev,e=>{e.preventDefault();dnd.classList.add("show");}));
["dragleave","drop"].forEach(ev=>document.addEventListener(ev,e=>{e.preventDefault();dnd.classList.remove("show");}));
document.addEventListener("drop",e=>{const f=e.dataTransfer.files[0];if(f&&f.type.startsWith("video/")){v.src=URL.createObjectURL(f);v.muted=true;v.play().then(()=>v.muted=false).catch(()=>{});setVideoName(f.name);}});
document.addEventListener("wheel",e=>{e.preventDefault();applyVolume(Math.max(0,Math.min(2,+vol.value+(e.deltaY<0?0.05:-0.05))));showCtl();});
showCtl();applyVolume(1);applySpeed(1);hudReady=true;
let rc=0;document.addEventListener("contextmenu",e=>{e.preventDefault();const n=Date.now();if(n-rc<400){if(window.chrome&&window.chrome.webview)window.chrome.webview.postMessage("fullscreen");isFs=!isFs;fsbtn.innerHTML=isFs?FS_EXIT:FS;rc=0;}else{rc=n;setTimeout(()=>rc=0,400);}});
const p=new URLSearchParams(location.search);if(p.get("src")){try{let s=p.get("src");if(/^[a-zA-Z]:[\\\\/]/.test(s))s="file:///"+s.replace(/\\\\/g,"/").replace(/ /g,"%20");v.src=s;v.play();setVideoName(p.get("src"));}catch(e){}}
</script></body></html>"#;

fn main() {
    let src = env::args().nth(1);
    use std::sync::Mutex;
    let current_video: Arc<Mutex<Option<std::path::PathBuf>>> = Arc::new(Mutex::new(src.as_ref().map(std::path::PathBuf::from)));
    // Serve the selected file over localhost so the media pipeline can play it
    // (file:// and custom schemes are not reliably playable).
    let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    let cv = current_video.clone();
    std::thread::spawn(move || {
        use std::io::{Read, Write};
        for mut stream in listener.incoming().flatten() {
            let mut buf = [0u8; 8192];
            let n = stream.read(&mut buf).unwrap_or(0);
            let req = String::from_utf8_lossy(&buf[..n]).to_string();
            let path = cv.lock().ok().and_then(|g| g.clone());
            if let Some(p) = path {
                if let Ok(data) = std::fs::read(&p) {
                    let total = data.len();
                    let mime = match p.extension().and_then(|e| e.to_str()).map(|s| s.to_lowercase()).as_deref() {
                        Some("mp4") | Some("m4v") => "video/mp4",
                        Some("webm") => "video/webm",
                        Some("ogg") | Some("ogv") => "video/ogg",
                        Some("mkv") => "video/x-matroska",
                        Some("avi") => "video/x-msvideo",
                        Some("mov") => "video/quicktime",
                        _ => "application/octet-stream",
                    };
                    // Parse Range header.
                    let range = req.lines().find(|l| l.to_lowercase().starts_with("range:")).map(|l| l.to_string());
                    let (status, body, cr) = if let Some(rh) = range {
                        let spec = rh.split(':').nth(1).unwrap_or("").trim();
                        let spec = spec.strip_prefix("bytes=").unwrap_or(spec);
                        let mut parts = spec.split('-');
                        let start: usize = parts.next().unwrap_or("0").trim().parse().unwrap_or(0);
                        let end: usize = parts.next().map(|s| s.trim()).filter(|s| !s.is_empty()).and_then(|s| s.parse().ok()).unwrap_or(total.saturating_sub(1)).min(total.saturating_sub(1));
                        if start <= end && start < total {
                            (206, data[start..=end].to_vec(), Some(format!("bytes {}-{}/{}", start, end, total)))
                        } else {
                            (200, data.clone(), None)
                        }
                    } else {
                        (200, data.clone(), None)
                    };
                    let mut resp = format!("HTTP/1.1 {} {}\r\nContent-Type: {}\r\nAccept-Ranges: bytes\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\nConnection: close\r\n", status, if status==206 {"Partial Content"} else {"OK"}, mime, body.len());
                    if let Some(cr) = cr { resp.push_str(&format!("Content-Range: {}\r\n", cr)); }
                    resp.push_str("\r\n");
                    let _ = stream.write_all(resp.as_bytes());
                    let _ = stream.write_all(&body);
                } else {
                    let _ = stream.write_all(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n");
                }
            } else {
                let _ = stream.write_all(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n");
            }
            let _ = stream.flush();
        }
    });
    // Render the logo SVG into a window icon at runtime.
    let icon = (|| {
        let opts = usvg::Options::default();
        let tree = usvg::Tree::from_str(include_str!("../assets/logo.svg"), &opts).ok()?;
        let w = 64u32;
        let h = 64u32;
        let mut pixmap = tiny_skia::Pixmap::new(w, h)?;
        let scale = (w as f32 / tree.size().width()).min(h as f32 / tree.size().height());
        let ts = tiny_skia::Transform::from_scale(scale, scale);
        resvg::render(&tree, ts, &mut pixmap.as_mut());
        tao::window::Icon::from_rgba(pixmap.data().to_vec(), w, h).ok()
    })();
    let event_loop = EventLoop::new();
    let window = Arc::new(WindowBuilder::new()
        .with_title("PVP")
        .with_inner_size(tao::dpi::LogicalSize::new(960.0, 540.0))
        .with_window_icon(icon)
        .build(&event_loop)
        .unwrap());
    let mut html = HTML.to_string();
    let mut s = String::new();
    let stdin_piped = !io::stdin().is_terminal();
    if stdin_piped && io::stdin().lock().read_to_string(&mut s).is_ok() && !s.is_empty() {
        html = html.replace("const v=document.getElementById(\"v\");", "const v=document.getElementById(\"v\");v.src=URL.createObjectURL(new Blob([s],{type:\"video/mp4\"}));setVideoName(\"stdin\");");
    } else if let Some(path) = &src {
        let file_url = format!("http://127.0.0.1:{}/video", port);
        html = html.replace("const v=document.getElementById(\"v\");", &format!("const v=document.getElementById(\"v\");v.src=\"{}\";setVideoName(\"{}\");v.addEventListener('loadeddata',()=>{{if(window.chrome&&window.chrome.webview)window.chrome.webview.postMessage('loaded');}});v.addEventListener('error',()=>{{if(window.chrome&&window.chrome.webview)window.chrome.webview.postMessage('error:'+((v.error&&v.error.message)||'unknown'));}});v.muted=true;v.play().then(()=>{{v.muted=false;}}).catch(()=>{{}});", file_url, path.replace("\\", "\\\\")));
    }
    let w = window.clone();
    let w2 = window.clone();
    let _cv = current_video.clone();
    // WebView2 cannot write next to the exe when installed in Program Files,
    // so keep its profile in a per-user writable location.
    let data_dir = std::env::var("LOCALAPPDATA")
        .map(|d| std::path::PathBuf::from(d).join("PVP").join("WebView2"))
        .unwrap_or_else(|_| std::env::temp_dir().join("PVP-WebView2"));
    let _ = std::fs::create_dir_all(&data_dir);
    // Write the HTML to a file so the page origin becomes file://, allowing
    // the video element to load local file:// sources (custom schemes are
    // not reliably playable by the media pipeline).
    let mut web_context = wry::WebContext::new(Some(data_dir));
    let _webview = WebViewBuilder::new_with_web_context(&mut web_context)
        .with_html(html)
        .with_devtools(true)
        .with_ipc_handler(move |req| {
            let body = req.body();
            if body == "loaded" || body.starts_with("error:") || body == "ping" {
                let _ = std::fs::write("C:\\Users\\Public\\pvp_video_status.txt", body);
            }
            if body == "fullscreen" {
                let _ = std::fs::write("C:\\Users\\Public\\pvp_fs.txt", "received");
                if w2.fullscreen().is_some() {
                    w2.set_fullscreen(None);
                } else {
                    w2.set_fullscreen(Some(tao::window::Fullscreen::Borderless(None)));
                }
            }
        })
        .with_document_title_changed_handler(move |title| {
            w.set_title(&title);
        })
        .build(&*window)
        .unwrap();
    event_loop.run(move |event, _, control_flow| {
        *control_flow = ControlFlow::Wait;
        if let Event::WindowEvent { event: WindowEvent::CloseRequested, .. } = event {
            *control_flow = ControlFlow::Exit;
        }
    });
}





