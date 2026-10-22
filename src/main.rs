#![windows_subsystem = "windows"]
use std::env;
use std::sync::{Arc, Mutex};
use tao::event::{Event, WindowEvent};
use tao::event_loop::{ControlFlow, EventLoop};
use tao::window::WindowBuilder;
use std::io::{self, Read, IsTerminal};
use wry::WebViewBuilder;
#[cfg(windows)]
use wry::WebViewBuilderExtWindows;

mod captions;

use captions::{
    current_language, event_to_js, json_str, probe, speech_models_installed, start_speech_op,
    CaptionProvider, LiveCaptionsProvider,
};

const HTML: &str = r####"<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>PVP+</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#000;color:#fff;font-family:system-ui,sans-serif;height:100vh;overflow:hidden;position:relative}
#v{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#000}
body:not(.fs) #v{top:32px}
.controls{position:absolute;left:0;right:0;bottom:0;padding:12px;background:linear-gradient(transparent,rgba(0,0,0,0.85));transition:opacity 0.3s;opacity:1;z-index:10}
.controls.hide{opacity:0;pointer-events:none}
.row{display:flex;align-items:center;gap:10px}
button,label{background:transparent;border:none;color:#fff;cursor:pointer;display:flex;align-items:center;padding:4px}
button svg, label svg{width:20px;height:20px;fill:#fff}
#fsbtn svg{width:17px;height:17px;fill:none}
#tl{flex:1;height:6px;background:rgba(128,128,128,0.35);border-radius:3px;cursor:pointer;position:relative}
#fill{height:100%;background:rgb(116,192,252);border-radius:3px;width:0}
#tl-preview{position:absolute;bottom:14px;width:160px;background:#101010;border:1px solid #3a3a3a;border-radius:6px;overflow:hidden;box-shadow:0 6px 18px rgba(0,0,0,0.55);pointer-events:none;z-index:16}
#tl-preview[hidden]{display:none}
#tl-preview video{display:block;width:160px;height:90px;object-fit:contain;background:#000}
#tl-prev-t{display:block;text-align:center;font-size:11px;color:#ddd;padding:3px 0 4px;background:#181818}
.volwrap{position:relative;display:flex;align-items:center;gap:4px}
.vol{position:absolute;bottom:30px;left:50%;transform:translateX(-50%);writing-mode:vertical-lr;direction:rtl;width:6px;height:100px;appearance:none;-webkit-appearance:none;background:rgba(128,128,128,0.35);border-radius:3px;cursor:pointer;z-index:15;opacity:0;transition:opacity 0.2s;pointer-events:none}
.volwrap:hover .vol{opacity:1;pointer-events:auto}
.volwrap::after{content:"";position:absolute;left:-8px;right:-8px;bottom:28px;height:106px}
.vol::-webkit-slider-runnable-track{width:6px;height:100%;background:rgba(128,128,128,0.35);border-radius:3px}
.vol::-webkit-slider-thumb{appearance:none;-webkit-appearance:none;width:14px;height:14px;border-radius:50%;background:rgb(116,192,252);margin-left:-4px;border:none}
.vol::-moz-range-track{width:6px;height:100%;background:rgba(128,128,128,0.35);border-radius:3px}
.vol::-moz-range-progress{width:6px;height:100%;background:rgb(116,192,252);border-radius:3px}
.vol::-moz-range-thumb{width:14px;height:14px;border-radius:50%;background:rgb(116,192,252);border:none}
.time{font-size:13px;min-width:90px;text-align:center;cursor:pointer;user-select:none}

.dnd{position:absolute;inset:0;display:none;align-items:center;justify-content:center;background:rgba(0,0,0,0.4);font-size:18px;z-index:20}
.dnd.show{display:flex}
.brandmark{display:flex;align-items:center;justify-content:center;opacity:.85;margin-right:2px;position:relative;width:24px;height:24px}
.brandmark .logo-icon{width:18px;height:18px;fill:rgb(116, 192, 252);filter:drop-shadow(0 1px 2px rgba(0,0,0,.8));transition:opacity 0.2s}
.brandmark:hover .logo-icon{opacity:0}
.brandmark:hover .settings-icon{opacity:1}
.brandmark .settings-icon{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:17px;height:17px;opacity:0;transition:opacity 0.2s;stroke:#fff;fill:none;pointer-events:none}
.spdind{position:fixed;top:44px;right:12px;background:rgba(0,0,0,.6);color:#fff;padding:8px 14px;border-radius:8px;font-size:22px;font-weight:600;opacity:0;transition:opacity .4s;pointer-events:none;z-index:21;white-space:nowrap}
.spdind.show{opacity:1}
.pl-toast{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(0,0,0,.78);color:#fff;padding:14px 22px;border-radius:10px;font-size:15px;opacity:0;transition:opacity .6s;pointer-events:none;z-index:30;white-space:nowrap}
.pl-toast.show{opacity:1}
.volind{position:fixed;top:44px;right:12px;background:rgba(0,0,0,.6);color:#fff;padding:8px 14px;border-radius:8px;font-size:22px;font-weight:600;opacity:0;transition:opacity .4s;pointer-events:none;z-index:20}

/* CC button */
.ccbtn{background:transparent;border:none;color:#fff;cursor:pointer;display:flex;align-items:center;padding:4px;border-radius:4px;transition:background 0.15s}
.ccbtn:hover{background:rgba(255,255,255,0.1)}
.ccbtn.active{background:rgba(116,192,252,0.2)}
.ccbtn svg{width:20px;height:20px;fill:none}
.ccbtn.active .ccb{fill:none;stroke:rgb(116,192,252)}
.ccbtn.active .ccg{fill:rgb(116,192,252);stroke:rgb(116,192,252)}

/* Control bar icons: little hover background like CC; selected state in primary color (white hover wash hidden while active) */
.row>button,.volwrap>button{border-radius:4px;transition:background 0.15s,color 0.15s}
.row>button:hover,.volwrap>button:hover{background:rgba(255,255,255,0.1)}
.row>button.active,.volwrap>button.active{background:rgba(116,192,252,0.2);color:rgb(116,192,252)}
.row>button.active:hover,.volwrap>button.active:hover{background:rgba(116,192,252,0.2);color:rgb(116,192,252)}
.row>button.active svg,.volwrap>button.active svg{fill:rgb(116,192,252);stroke:rgb(116,192,252)}

/* Settings menu - click to toggle */
.brandmark-wrap{position:relative}
#settingsmenu{display:none;position:absolute;bottom:44px;left:0;background:#222;padding:8px;border-radius:8px;min-width:240px;max-width:300px;max-height:calc(100vh - 130px);overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:#555 transparent;z-index:20;box-shadow:0 4px 20px rgba(0,0,0,0.5)}
#settingsmenu.show{display:block}
#settingsmenu::-webkit-scrollbar{width:8px}
#settingsmenu::-webkit-scrollbar-thumb{background:#555;border-radius:4px}
#settingsmenu::-webkit-scrollbar-track{background:transparent}
.settings-section{padding:8px 0;border-bottom:1px solid #333}
.settings-section:last-child{border-bottom:none}
.settings-section h4{font-size:11px;text-transform:uppercase;color:#888;margin:0 0 8px;letter-spacing:0.5px}
.settings-section button{display:flex;align-items:center;gap:8px;width:100%;text-align:left;padding:8px 12px;font-size:13px;border-radius:4px;background:transparent;color:#fff;cursor:pointer;transition:background 0.15s}
.settings-section button:hover{background:#333}
.settings-section button.active{background:rgb(116,192,252);color:#000}
.settings-section button.disabled{opacity:0.4;cursor:not-allowed}
.settings-section button .track-info{font-size:11px;color:#aaa;margin-left:auto}
.settings-section .sync-controls{display:flex;align-items:center;gap:6px;margin-top:6px;padding-top:6px;border-top:1px solid #333;font-size:12px}
.settings-section .sync-controls input{width:60px;padding:2px 6px;background:#111;border:1px solid #333;border-radius:3px;color:#fff;font-size:11px}
.settings-section .sync-controls input:focus{outline:none;border-color:rgb(116,192,252)}
.settings-section .sync-controls label{display:flex;align-items:center;gap:4px;color:#aaa;cursor:pointer}
.settings-section .speed-options{display:flex;flex-wrap:wrap;gap:4px}
.settings-section .speed-options button{width:auto;padding:4px 10px;font-size:12px;background:#333;border-radius:3px}
.settings-section .speed-options button.active{background:rgb(116,192,252);color:#000}
.settings-section .speed-options button:hover{background:#444}
.shortcut-row{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:4px 0;font-size:12.5px;color:#ccc}
.shortcut-row span:first-child{white-space:nowrap}
.shortcut-row span:last-child{display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end}
.shortcut-row kbd{background:#333;border:1px solid #4a4a4a;border-bottom-width:2px;border-radius:4px;padding:1px 6px;font-size:10.5px;color:#fff;font-family:inherit;white-space:nowrap}
#subtitle-menu,#subtitle-menu-set,#audio-menu{max-height:200px;overflow-y:auto}
.subtitle-sync{display:none;padding:8px;background:#1a1a1a;border-radius:4px;margin-top:4px}
.subtitle-sync.show{display:block}
.subtitle-sync label{display:block;margin-bottom:4px;color:#aaa;font-size:12px}
.subtitle-sync input[type="number"]{width:80px;padding:4px 8px;background:#111;border:1px solid #333;border-radius:3px;color:#fff;font-size:13px}
.subtitle-sync input[type="number"]:focus{outline:none;border-color:rgb(116,192,252)}
.subtitle-sync .sync-btns{display:flex;gap:6px;margin-top:8px}
.subtitle-sync .sync-btns button{flex:1;padding:6px;background:#333;border:none;border-radius:3px;color:#fff;font-size:12px;cursor:pointer}
.subtitle-sync .sync-btns button:hover{background:rgba(116,192,252,0.18);color:rgb(116,192,252)}
.subtitle-sync .sync-btns button:disabled{opacity:0.5;cursor:not-allowed}
.track-item{display:flex;align-items:center;gap:8px;padding:8px 12px;border-radius:4px;cursor:pointer;transition:background 0.15s}
.track-item:hover{background:#333}
.track-item.active{background:rgb(116,192,252);color:#000}
.track-item .track-lang{font-weight:500}
.track-item .track-label{color:#aaa;font-size:12px}
.track-item .track-default{color:rgb(116,192,252);font-size:11px;margin-left:auto}
.external-track-btn{width:100%;text-align:left;padding:8px 12px;font-size:13px;background:#333;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-top:8px;display:flex;align-items:center;gap:8px}
.external-track-btn:hover{background:rgba(116,192,252,0.18);color:rgb(116,192,252)}
.external-track-btn svg{width:16px;height:16px;stroke:#fff;fill:none;stroke-width:2}
.no-tracks{padding:12px;color:#888;font-size:13px;text-align:center}
.menu-icon{width:18px;height:18px;stroke:#fff;fill:none;stroke-width:2;flex-shrink:0}

/* Live Captions Overlay */
.live-captions-overlay{
    position:absolute;
    left:0;right:0;
    bottom:60px;
    padding:0 20px;
    pointer-events:none;
    z-index:15;
    transition:opacity 0.3s, transform 0.3s;
    opacity:1;
}
.live-captions-overlay.hidden{
    opacity:0;
    transform:translateY(20px);
}
.live-captions-overlay.top{
    bottom:auto;
    top:60px;
}
.live-captions-overlay.center{
    bottom:50%;
    top:auto;
    transform:translateY(50%);
}
.live-captions-overlay.center.hidden{
    transform:translateY(50%) translateY(20px);
}
.live-captions-overlay.mid{
    bottom:40%;
    top:auto;
    transform:translateY(50%);
}
.live-captions-overlay.mid.hidden{
    transform:translateY(50%) translateY(20px);
}
.live-caption-line{
    background:var(--lc-bg,rgba(18, 18, 18, 0.85));
    color:var(--lc-fg,rgb(116, 192, 252));
    font-family:var(--lc-family,system-ui, sans-serif);
    font-weight:var(--lc-weight,400);
    font-size:var(--lc-size,16px);
    text-shadow:var(--lc-shadow,none);
    line-height:1.3;
    padding:6px 12px;
    border-radius:6px;
    margin:3px 0;
    max-width:85%;
    margin-left:auto;
    margin-right:auto;
    text-align:center;
    box-shadow:var(--lc-boxshadow,none);
    white-space:pre-wrap;
    word-wrap:break-word;
}
.live-caption-line .lc-clip{
    max-height:calc(var(--lc-lines,3) * 1.3em);
    overflow:hidden;
    display:flex;
    flex-direction:column;
    justify-content:flex-end;
    transition:max-height .3s ease;
}
.live-caption-line .lc-inner{
    flex:0 0 auto;
    min-width:0;
    max-width:60%;
    margin-left:auto;
    margin-right:auto;
}
.live-caption-line.enter{
    animation:captionFadeIn 0.2s ease-out;
}
@keyframes captionFadeIn{
    from{opacity:0;transform:translateY(10px);}
    to{opacity:1;transform:translateY(0);}
}
.settings-section button.info-btn{background:transparent;border:none;cursor:pointer;padding:3px;border-radius:4px;display:flex;line-height:0;width:auto;min-width:0;gap:0;margin-left:6px;margin-right:-3px;flex-shrink:0}
.settings-section button.info-btn:hover{background:#333}
.settings-section button.info-btn svg{width:15px;height:15px;fill:none;stroke:#fff;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.lc-info-panel{background:#1a1a1a;border:1px solid #333;border-radius:6px;padding:10px 12px;margin:8px 0 4px;font-size:12.5px;line-height:1.5;color:#ccc;display:flex;flex-direction:column;gap:6px}
.lc-info-panel b{color:#fff}
.lc-info-panel kbd{background:#333;border:1px solid #444;border-radius:3px;padding:0 4px;font-size:11px}
.lc-info-panel[hidden]{display:none}
.live-captions-settings .setting-row{
    display:flex;
    align-items:center;
    gap:8px;
    margin:8px 0;
}
.live-captions-settings .setting-row label{
    min-width:100px;
    flex-shrink:0;
    font-size:12.5px;
    color:#ccc;
}
.live-captions-settings .setting-row input[type="range"]{
    flex:1;
    min-width:0;
}
.live-captions-settings .setting-row input[type="number"]{
    flex:none;
    width:52px;
    height:26px;
    box-sizing:border-box;
    background:#333;
    border:none;
    color:#fff;
    padding:4px 6px;
    border-radius:4px;
    font-size:12.5px;
    font-family:inherit;
    text-align:center;
}
.live-captions-settings .setting-row input[type="number"]::-webkit-inner-spin-button,
.live-captions-settings .setting-row input[type="number"]::-webkit-outer-spin-button{
    -webkit-appearance:none;
    margin:0;
}
.live-captions-settings .setting-row select{
    flex:1;
    min-width:0;
    height:26px;
    box-sizing:border-box;
    background-color:#333;
    border:none;
    color:#fff;
    padding:4px 26px 4px 8px;
    border-radius:4px;
    font-size:12.5px;
    font-family:inherit;
    -webkit-appearance:none;
    appearance:none;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23999999' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
    background-repeat:no-repeat;
    background-position:right 9px center;
    background-size:14px 14px;
}
/* Settings icon stays visible while menu is open */
.brandmark:has(~ #settingsmenu.show) .settings-icon{opacity:1}
.brandmark:has(~ #settingsmenu.show) .logo-icon{opacity:0}

/* Palette button in section headers */
.section-head{display:flex;justify-content:space-between;align-items:center}
.section-head span{white-space:nowrap}
.settings-section button.palette-btn,.cc-row .palette-btn{background:transparent;border:none;cursor:pointer;padding:3px;border-radius:4px;display:flex;line-height:0;width:auto;min-width:0;gap:0;margin-left:auto;margin-right:-3px;flex-shrink:0}
.settings-section button.palette-btn:hover,.cc-row .palette-btn:hover{background:#333}
.settings-section button.palette-btn svg,.cc-row .palette-btn svg{width:15px;height:15px;fill:none;stroke:#fff;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}

/* Custom subtitle overlay (fully stylable) */
#suboverlay{position:absolute;left:0;right:0;bottom:64px;display:flex;flex-direction:column;align-items:center;gap:4px;pointer-events:none;z-index:14;padding:0 60px;opacity:0;transition:opacity .15s;font-size:18px}
#suboverlay.show{opacity:1}
.sub-line{background:var(--sub-bg,rgba(0,0,0,.7));box-shadow:var(--sub-boxshadow,none);color:inherit;font-weight:inherit;font-size:inherit;font-family:inherit;line-height:1.35;padding:.15em .55em;border-radius:4px;max-width:88%;text-align:center;white-space:pre-wrap;word-wrap:break-word}

/* Subtitle style popup */
.style-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:29;display:none}
.style-backdrop.show{display:block}
.style-popup{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);width:350px;max-width:92vw;max-height:86vh;overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:#555 transparent;background:#222;border:1px solid #383838;border-radius:10px;z-index:30;display:none;box-shadow:0 8px 30px rgba(0,0,0,.6)}
.style-popup::-webkit-scrollbar{width:8px}
.style-popup::-webkit-scrollbar-thumb{background:#555;border-radius:4px}
.style-popup::-webkit-scrollbar-track{background:transparent}
.style-popup.show{display:block}
.style-head{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid #333;font-size:13px;font-weight:600;letter-spacing:.3px}
.style-head button{background:transparent;border:none;color:#aaa;font-size:16px;cursor:pointer;padding:2px 6px;line-height:1}
.style-head button:hover{color:#fff}
.style-body{padding:8px 14px}
.style-row{display:flex;align-items:center;gap:8px;margin:9px 0}
.style-row label{width:105px;font-size:12px;color:#ccc;flex-shrink:0}
.style-row select{flex:1;min-width:0;background:#333;border:none;color:#fff;padding:5px 6px;border-radius:4px;font-size:12px}
.style-row input[type=range]{flex:1;min-width:0;accent-color:rgb(116,192,252)}
.style-row input[type=color]{width:44px;height:26px;border:1px solid #444;border-radius:4px;background:#333;cursor:pointer;padding:1px}
.style-row span{width:38px;font-size:11px;color:#999;text-align:right;flex-shrink:0}
.style-foot{display:flex;gap:8px;padding:10px 14px;border-top:1px solid #333}
.style-foot button{flex:1;padding:7px;border:none;border-radius:5px;font-size:13px;cursor:pointer}
#st-reset{background:#333;color:#fff}
#st-reset:hover{background:#444}
#st-done{background:rgb(116,192,252);color:#000;font-weight:600}
#st-done:hover{filter:brightness(1.1)}

/* Custom titlebar */
#titlebar{position:fixed;top:0;left:0;right:0;height:32px;display:flex;align-items:center;background:#171717;border-bottom:1px solid #0d0d0d;-webkit-app-region:drag;z-index:60;user-select:none}
body.fs #titlebar{display:none}
body:not(.fs) #v{top:32px}
body:not(.fs) .dnd{top:32px}
#tb-brand{font-size:11px;font-weight:600;letter-spacing:.8px;color:#8ab4d8;padding-left:12px;white-space:nowrap;flex-shrink:0;display:flex;align-items:center;gap:6px}
#tb-logo{height:13px;width:auto;display:block;flex-shrink:0}
#tb-divider{width:1px;height:14px;background:#555;margin:0 8px;flex-shrink:0}
#tb-title{font-size:11px;color:#ccc;white-space:nowrap;overflow:hidden;flex:1;min-width:0}
#tb-title.error,.tb-err{color:#e81123}
.tb-pl{opacity:.7}
.tb-playic{width:9px;height:9px;fill:currentColor;opacity:.45;margin:0 5px;flex-shrink:0}
#tb-title .tb-inner{display:inline-block;white-space:nowrap;padding-right:32px}
#tb-title .tb-marquee{display:inline-flex;white-space:nowrap;animation:tbmq linear infinite}
#tb-title .tb-marquee:hover{animation:none}
@keyframes tbmq{from{transform:translateX(0)}to{transform:translateX(-50%)}}
#tb-btns{display:flex;height:100%;-webkit-app-region:no-drag;flex-shrink:0}
#tb-btns button{width:44px;height:100%;background:transparent;border:none;color:#bbb;display:flex;align-items:center;justify-content:center;cursor:pointer;padding:0}
#tb-btns button:hover{background:#2c2c2c;color:#fff}
#tb-btns button:active{background:#3a3a3a}
#tb-close:hover{background:#e81123!important;color:#fff!important}
#tb-btns svg{width:13px;height:13px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
#tb-update,#tb-playlist{color:rgb(116,192,252)}
#tb-update svg,#tb-playlist svg{stroke:rgb(116,192,252);width:16px;height:16px}
#tb-update:hover,#tb-playlist:hover{background:rgba(116,192,252,.15);color:rgb(116,192,252)}
#tb-btns #tb-donate{color:rgb(116,192,252)}
#tb-btns #tb-donate svg{fill:currentColor;stroke:none;width:15px;height:15px}
#tb-btns #tb-donate:hover{background:rgba(116,192,252,.15);color:rgb(116,192,252)}
[hidden]{display:none!important}

/* Floating menus: open, subtitle (cc), playlist */
.openmenu,.cc-menu,.pl-menu{position:fixed;background:#222;border:1px solid #383838;border-radius:8px;box-shadow:0 8px 28px rgba(0,0,0,.6);z-index:56}
.openmenu{width:196px;padding:5px}
.om-item{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:5px;cursor:pointer;font-size:13px;color:#eee}
.om-item:hover{background:rgba(116,192,252,.15);color:rgb(116,192,252)}
.om-item svg{width:17px;height:17px;fill:none;stroke:currentColor;stroke-width:1.8;flex-shrink:0}
.cc-menu{width:276px;padding:7px}
.cc-row{display:flex;align-items:center;gap:9px;padding:8px 9px;border-radius:5px;cursor:pointer;font-size:13px;color:#eee}
.cc-row:hover{background:rgba(116,192,252,.15);color:rgb(116,192,252)}
.cc-row>svg{width:17px;height:17px;fill:none;stroke:currentColor;stroke-width:1.8;flex-shrink:0}
.cc-row>span{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cc-row.disabled{opacity:.45;cursor:not-allowed}
.cc-row.disabled:hover{background:transparent;color:#eee}
.cc-sublist{margin:2px 0 6px;padding:4px;background:#1b1b1b;border-radius:6px}
.cc-sublist .track-item{padding:7px 10px;font-size:12.5px}
.cc-sublist .external-track-btn{background:#2b2b2b;font-size:12.5px}
.track-card{margin:6px 0 2px;padding:4px;background:#1b1b1b;border-radius:6px}
.track-card .track-item{padding:7px 10px;font-size:12.5px}
.track-card .no-tracks{padding:14px 12px}
.track-card .external-track-btn{background:#2b2b2b;font-size:12.5px;font-weight:600;margin-top:4px;border-radius:5px;transition:background 0.15s}
.track-card .external-track-btn:hover{background:#333}
.cc-live-state{font-size:10px;letter-spacing:.5px;color:#888;padding:2px 7px;border:1px solid #444;border-radius:9px;flex-shrink:0}
.cc-live-state.on{color:#000;background:rgb(116,192,252);border-color:rgb(116,192,252);font-weight:600}
.cc-row>span.cc-live-state{flex:0 0 auto}
.lc-toggle-btn{min-width:48px;padding:3px 10px;border-radius:9px;border:1px solid #444;background:#1b1b1b;color:#888;font-size:10px;letter-spacing:.5px;font-weight:600;cursor:pointer;font-family:inherit;margin-left:auto;flex-shrink:0}
.lc-toggle-btn:disabled{opacity:.45;cursor:not-allowed}
/* The generic `.settings-section button` rule (and its :hover) out-specify
   plain .lc-toggle-btn, so the toggle's real look lives in this (0,2,1)+
   block below — same idea as the lc-models buttons. */
.settings-section button.lc-toggle-btn{width:auto;flex:none;min-width:56px;justify-content:center;gap:0;padding:5px 14px;font-size:11px;border-radius:11px;background:#1b1b1b;color:#888;border:1px solid #444;letter-spacing:.5px;font-weight:600;text-align:center;transition:background .15s,color .15s,border-color .15s}
.settings-section button.lc-toggle-btn:hover{background:#333;border-color:#555;color:#ccc}
.settings-section button.lc-toggle-btn.on{color:#000;background:rgb(116,192,252);border-color:rgb(116,192,252)}
.settings-section button.lc-toggle-btn.on:hover{background:rgb(140,205,255);border-color:rgb(140,205,255);color:#000}
.settings-section button.lc-toggle-btn:disabled{opacity:.45;cursor:not-allowed}
.lc-models{display:flex;flex-direction:column;gap:4px;margin:6px 0 2px}
.lc-models-hint{font-size:11.5px;color:#8ab4d8;text-align:right;margin-left:auto}
.lc-models .lc-models-hint{text-align:left;margin:2px 0;font-style:italic}
.lc-model{display:flex;align-items:center;gap:8px;padding:6px 10px;background:#1b1b1b;border:1px solid #2b2b2b;border-radius:6px;font-size:12.5px;color:#ccc}
.lc-model.active{border-color:#2b2b2b;background:rgba(116,192,252,.12);color:rgb(116,192,252)}
.lc-model.missing{opacity:.8}
.lc-model-name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.lc-model-badge{flex:none;min-width:75px;text-align:center;font-size:10px;font-weight:700;letter-spacing:.6px;color:rgb(116,192,252);white-space:nowrap}
.lc-model button{width:auto;flex:none;font-family:inherit;font-size:11.5px;padding:4px 10px;border-radius:5px;cursor:pointer;border:1px solid #444;background:#2b2b2b;color:#fff;display:flex;align-items:center;gap:5px;transition:background 0.15s}
.lc-model button:hover{background:#383838}
.lc-model button:disabled{opacity:.5;cursor:default}
.lc-model .lc-model-dl{background:rgb(116,192,252);border-color:rgb(116,192,252);color:#000;font-weight:600}
.lc-model .lc-model-dl:hover{filter:brightness(1.08);background:rgb(116,192,252)}
.lc-model .lc-model-del{padding:4px 6px;color:#e06c75;border-color:#4a2c2c}
.lc-model .lc-model-del:hover{background:#3a2424}
.lc-model .lc-model-del svg{width:13px;height:13px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.lc-model-busy{font-size:11.5px;color:#8ab4d8;white-space:nowrap}
.lc-model-busy::before{content:"";display:inline-block;width:8px;height:8px;margin-right:6px;border:2px solid #8ab4d8;border-top-color:transparent;border-radius:50%;vertical-align:-1px;animation:lcspin .8s linear infinite}
@keyframes lcspin{to{transform:rotate(360deg)}}
.lc-lang-trigger{flex:1;min-width:0;display:flex;align-items:center;gap:6px;height:26px;padding:0 9px}
.settings-section button.lc-lang-trigger{width:auto;height:26px;padding:0 9px;gap:6px;background:#1b1b1b;border:1px solid #444;border-radius:5px;color:#eee;font-family:inherit;font-size:12.5px;cursor:pointer;text-align:left;transition:border-color 0.15s,background 0.15s}
.settings-section button.lc-lang-trigger:hover{border-color:#666;background:#222}
.lc-lang-trigger .lc-lang-name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.lc-lang-trigger .lc-chev{width:14px;height:14px;flex:none;fill:none;stroke:#999;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;transition:transform 0.18s ease}
.lc-lang-trigger[aria-expanded="true"] .lc-chev{transform:rotate(180deg)}
.lc-lang-dd{margin:6px 0 2px;background:#222;border:1px solid #383838;border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,0.5);padding:6px;max-height:280px;overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:#555 transparent}
.lc-lang-dd[hidden]{display:none}
.lc-lang-dd::-webkit-scrollbar{width:8px}
.lc-lang-dd::-webkit-scrollbar-thumb{background:#555;border-radius:4px}
.lc-lang-dd .lc-models{margin:0}
.lc-lang-dd .lc-models-hint{text-align:left;margin:2px 4px 6px;font-style:italic}
.pl-menu{top:36px;right:6px;width:300px;max-height:62vh;overflow-y:auto;padding:8px;scrollbar-width:thin;scrollbar-color:#555 transparent}
.pl-menu::-webkit-scrollbar{width:8px}
.pl-menu::-webkit-scrollbar-thumb{background:#555;border-radius:4px}
.pl-menu::-webkit-scrollbar-track{background:transparent}
.pl-head{display:flex;justify-content:space-between;align-items:center;padding:2px 4px 8px;border-bottom:1px solid #333;margin-bottom:6px}
.pl-head-btns{display:flex;gap:2px}
.pl-sort-wrap{position:relative;display:flex}
.pl-sort-menu{position:absolute;top:calc(100% + 6px);right:0;background:#222;border:1px solid #383838;border-radius:8px;box-shadow:0 8px 28px rgba(0,0,0,.6);z-index:60;min-width:170px;padding:5px}
.pl-sort-menu .om-item{padding:7px 10px;font-size:12.5px}
.pl-sort-menu .om-item.active{background:rgba(116,192,252,.15);color:rgb(116,192,252)}
.pl-sort-sep{height:1px;background:rgba(255,255,255,.12);margin:5px 8px}
.pl-head span{font-size:11px;text-transform:uppercase;color:#888;letter-spacing:.5px}
.pl-head button{background:transparent;border:none;padding:3px;border-radius:4px;display:flex;cursor:pointer;color:#ccc}
.pl-head button:hover{background:#333}
.pl-head button.on{color:rgb(116,192,252);background:rgba(116,192,252,.15)}
#sort-btn{font-size:11px;font-weight:500;letter-spacing:.5px;text-transform:uppercase;color:#888;padding:4px 8px;border-radius:4px}
#sort-btn:hover{background:#333;color:#ccc}
.pl-head button svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.pl-item{display:flex;align-items:center;gap:8px;padding:7px 8px;border-radius:5px;font-size:12.5px;color:#ddd;cursor:pointer;user-select:none;border:2px solid transparent}
.pl-item:hover{background:#2c2c2c}
.pl-item.cur{color:rgb(116,192,252);background:rgba(116,192,252,.12)}
.pl-item.drag-over{border-top-color:rgb(116,192,252)}
.pl-item .pl-grip{color:#666;cursor:grab;font-size:13px;line-height:1;flex-shrink:0;letter-spacing:-2px}
.pl-item .pl-name{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pl-item .pl-idx{color:#666;font-size:11px;width:18px;text-align:right;flex-shrink:0}
.pl-empty{color:#777;font-size:12.5px;text-align:center;padding:14px}

/* Version row in settings */
#ver-row{display:flex;align-items:center;padding:3px 4px 2px;gap:6px}
#ver-text{font-size:11.5px;color:#8ab4d8;letter-spacing:.4px;font-weight:600;flex:1}
#about-row{font-size:10.5px;color:#7f93a8;letter-spacing:.3px;padding:0 4px 8px}
button.upd-icon{background:transparent;border:none;padding:3px;border-radius:4px;display:flex;cursor:pointer;color:rgb(116,192,252)}
button.upd-icon:hover{background:rgba(116,192,252,.18)}
button.upd-icon svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
button.donate-icon{background:transparent;border:none;padding:3px;border-radius:4px;display:flex;cursor:pointer;color:rgb(116,192,252)}
button.donate-icon:hover{background:rgba(116,192,252,.18)}
button.donate-icon svg{width:15px;height:15px;fill:currentColor}
.donate-modal{position:fixed;inset:0;background:rgba(0,0,0,.55);display:none;align-items:center;justify-content:center;z-index:40}
.donate-modal.show{display:flex}
.donate-card{background:#222;border:1px solid #333;border-radius:12px;padding:18px 22px 16px;width:302px;max-width:92vw;display:flex;flex-direction:column;align-items:center;gap:10px;box-shadow:0 8px 30px rgba(0,0,0,.6);position:relative}
.donate-close{position:absolute;top:6px;right:6px;background:transparent;border:none;color:#aaa;font-size:17px;cursor:pointer;padding:2px 7px;border-radius:4px;display:flex;line-height:1}
.donate-close:hover{background:#333;color:#fff}
.donate-title{font-size:15px;font-weight:600;color:#fff;margin-top:2px}
.donate-upi-logo{height:26px;display:block}
.donate-ask{font-size:12.5px;color:#ccc;text-align:center;line-height:1.5}
.donate-ask b{color:rgb(116,192,252)}
.donate-qr{width:200px;height:200px;background:#fff;border-radius:8px;padding:6px;box-sizing:border-box}
.donate-upi-id{font-family:ui-monospace,Consolas,monospace;font-size:13.5px;color:#fff;background:#1b1b1b;border:1px dashed #444;padding:6px 14px;border-radius:6px;cursor:pointer;letter-spacing:.3px;display:flex;align-items:center;gap:6px;transition:background 0.15s}
.donate-upi-id:hover{background:#333;border-color:#666}
.donate-hint{font-size:11px;color:#888}

/* Update popup */
.upd-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:57;display:none}
.upd-backdrop.show{display:block}
.upd-popup{position:fixed;left:50%;top:44%;transform:translate(-50%,-50%);width:360px;max-width:92vw;background:#222;border:1px solid #383838;border-radius:10px;z-index:58;display:none;box-shadow:0 10px 36px rgba(0,0,0,.65)}
.upd-popup.show{display:block}
.upd-head{display:flex;justify-content:space-between;align-items:center;padding:11px 14px;border-bottom:1px solid #333;font-size:13.5px;font-weight:600}
.upd-head .upd-ic{color:rgb(116,192,252);display:flex;align-items:center;gap:8px}
.upd-head .upd-ic svg{width:17px;height:17px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.upd-head button{background:transparent;border:none;color:#aaa;font-size:16px;cursor:pointer;padding:2px 6px;line-height:1}
.upd-head button:hover{color:#fff}
.upd-body{padding:13px 15px;font-size:12.5px;color:#bbb}
.upd-vers{display:flex;align-items:center;gap:8px;font-size:14px;font-weight:600;color:#eee;margin-bottom:8px}
.upd-vers .to{color:rgb(116,192,252)}
.upd-vers svg{width:15px;height:15px;stroke:#888;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.upd-notes{max-height:150px;overflow-y:auto;background:#1a1a1a;border-radius:6px;padding:9px 11px;white-space:pre-wrap;color:#aaa;line-height:1.45;scrollbar-width:thin;scrollbar-color:#555 transparent}
.upd-notes::-webkit-scrollbar{width:8px}
.upd-notes::-webkit-scrollbar-thumb{background:#555;border-radius:4px}
.upd-bar{height:6px;background:#333;border-radius:3px;margin-top:11px;overflow:hidden}
.upd-bar-fill{height:100%;width:0%;background:rgb(116,192,252);border-radius:3px;transition:width .15s}
.upd-status{margin-top:10px;font-size:12px;color:#8ab4d8;min-height:15px}
.upd-foot{display:flex;gap:8px;padding:11px 14px;border-top:1px solid #333}
.upd-foot button{flex:1;padding:8px;border:none;border-radius:6px;font-size:13px;cursor:pointer}
#upd-later{background:#333;color:#fff}
#upd-later:hover{background:#444}
#upd-install{background:rgb(116,192,252);color:#000;font-weight:600}
#upd-install:hover{filter:brightness(1.08)}
#upd-install:disabled,#upd-later:disabled{opacity:.5;cursor:default}

</style></head><body>
<div id="titlebar">
  <span id="tb-brand"><svg id="tb-logo" viewBox="0 0 576 512" aria-hidden="true"><path fill="rgb(116,192,252)" d="M0 128C0 92.7 28.7 64 64 64l256 0c35.3 0 64 28.7 64 64l0 256c0 35.3-28.7 64-64 64L64 448c-35.3 0-64-28.7-64-64L0 128zM559.1 99.8c10.4 5.6 16.9 16.4 16.9 28.2l0 256c0 11.8-6.5 22.6-16.9 28.2s-23 5-32.9-1.6l-96-64L416 337.1l0-17.1 0-128 0-17.1 14.2-9.5 96-64c9.8-6.5 22.4-7.2 32.9-1.6z"/></svg>PVP+</span>
  <span id="tb-divider" style="display:none"></span>
  <span id="tb-title"></span>
  <div id="tb-btns">
    <button id="tb-playlist" title="Playlist" hidden><svg viewBox="0 0 24 24"><path d="M12 12H3"/><path d="M16 6H3"/><path d="M12 18H3"/><path d="m16 12 5 3-5 3v-6Z"/></svg></button>
    <button id="tb-update" title="Update available" hidden><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 8v8"/><path d="m8 12 4 4 4-4"/></svg></button>
    <button id="tb-donate" title="Donate (UPI)"><svg viewBox="0 0 576 512"><path d="M163.9 136.9c-29.4-29.8-29.4-78.2 0-108s77-29.8 106.4 0l17.7 18 17.7-18c29.4-29.8 77-29.8 106.4 0s29.4 78.2 0 108L310.5 240.1c-6.2 6.3-14.3 9.4-22.5 9.4s-16.3-3.1-22.5-9.4L163.9 136.9zM568.2 336.3c13.1 17.8 9.3 42.8-8.5 55.9L433.1 485.5c-23.4 17.2-51.6 26.5-80.7 26.5L192 512 32 512c-17.7 0-32-14.3-32-32l0-64c0-17.7 14.3-32 32-32l36.8 0 44.9-36c22.7-18.2 50.9-28 80-28l78.3 0 16 0 64 0c17.7 0 32 14.3 32 32s-14.3 32-32 32l-64 0-16 0c-8.8 0-16 7.2-16 16s7.2 16 16 16l120.6 0 119.7-88.2c17.8-13.1 42.8-9.3 55.9 8.5zM193.6 384c0 0 0 0 0 0l-.9 0c.3 0 .6 0 .9 0z"/></svg></button>
    <button id="tb-min" title="Minimize"><svg viewBox="0 0 24 24"><path d="M5 12h14"/></svg></button>
    <button id="tb-max" title="Maximize"><svg viewBox="0 0 24 24"><rect x="5" y="5" width="14" height="14" rx="1"/></svg></button>
    <button id="tb-close" title="Close"><svg viewBox="0 0 24 24"><path d="M6 6l12 12"/><path d="M18 6 6 18"/></svg></button>
  </div>
</div>
<video id="v"></video>
<div class="live-captions-overlay hidden" id="live-captions-overlay"></div>
<div id="suboverlay"></div>
<div id="tl-preview" hidden><video id="tl-prev-v" muted playsinline></video><span id="tl-prev-t"></span></div>
<input type="file" id="f" style="display:none">
<input type="file" id="folder-input" webkitdirectory multiple style="display:none">
<input type="file" id="subtitle-file" accept=".srt,.vtt,.ass,.ssa" style="display:none" multiple>
<input type="file" id="audio-file" accept="audio/*" style="display:none" multiple>
<div class="controls" id="ctl">
  <div class="row">
    <div class="brandmark-wrap">
      <div class="brandmark">
        <svg class="logo-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 576 512"><path fill="rgb(116, 192, 252)" d="M0 128C0 92.7 28.7 64 64 64l256 0c35.3 0 64 28.7 64 64l0 256c0 35.3-28.7 64-64 64L64 448c-35.3 0-64-28.7-64-64L0 128zM559.1 99.8c10.4 5.6 16.9 16.4 16.9 28.2l0 256c0 11.8-6.5 22.6-16.9 28.2s-23 5-32.9-1.6l-96-64L416 337.1l0-17.1 0-128 0-17.1 14.2-9.5 96-64c9.8-6.5 22.4-7.2 32.9-1.6z"/></svg>
        <svg class="settings-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/><circle cx="12" cy="12" r="3"/></svg>
      </div>
      <div id="settingsmenu">
        <div id="ver-row"><span id="ver-text">PVP+ v0.6.0</span><button class="upd-icon" id="ver-upd" title="Update available" hidden><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 8v8"/><path d="m8 12 4 4 4-4"/></svg></button><button class="donate-icon" id="ver-donate" title="Donate (UPI)"><svg viewBox="0 0 576 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M163.9 136.9c-29.4-29.8-29.4-78.2 0-108s77-29.8 106.4 0l17.7 18 17.7-18c29.4-29.8 77-29.8 106.4 0s29.4 78.2 0 108L310.5 240.1c-6.2 6.3-14.3 9.4-22.5 9.4s-16.3-3.1-22.5-9.4L163.9 136.9zM568.2 336.3c13.1 17.8 9.3 42.8-8.5 55.9L433.1 485.5c-23.4 17.2-51.6 26.5-80.7 26.5L192 512 32 512c-17.7 0-32-14.3-32-32l0-64c0-17.7 14.3-32 32-32l36.8 0 44.9-36c22.7-18.2 50.9-28 80-28l78.3 0 16 0 64 0c17.7 0 32 14.3 32 32s-14.3 32-32 32l-64 0-16 0c-8.8 0-16 7.2-16 16s7.2 16 16 16l120.6 0 119.7-88.2c17.8-13.1 42.8-9.3 55.9 8.5zM193.6 384c0 0 0 0 0 0l-.9 0c.3 0 .6 0 .9 0z"/></svg></button></div>
        <div id="about-row">Lightweight Rust video player &middot; ~3.8 MB &middot; MIT License</div>
        <div class="settings-section">
          <h4>Playback Speed</h4>
          <div class="speed-options" id="speedmenu"></div>
        </div>
        <div class="settings-section">
          <h4 class="section-head"><span>Subtitles</span><button class="palette-btn" id="pal-sub-set" title="Subtitle style"><svg viewBox="0 0 24 24"><path d="M12 22a1 1 0 0 1 0-20 10 9 0 0 1 10 9 5 5 0 0 1-5 5h-2.25a1.75 1.75 0 0 0-1.4 2.8l.3.4a1.75 1.75 0 0 1-1.4 2.8z"/><circle cx="13.5" cy="6.5" r=".5"/><circle cx="17.5" cy="10.5" r=".5"/><circle cx="6.5" cy="12.5" r=".5"/><circle cx="8.5" cy="7.5" r=".5"/></svg></button></h4>
          <div class="track-card">
            <div id="subtitle-menu-set"></div>
            <button class="external-track-btn" id="load-subtitle-btn-set">
              <svg class="menu-icon" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
              Add subtitle file
            </button>
          </div>
        </div>
        <div class="settings-section">
          <h4>Audio Tracks</h4>
          <div class="track-card">
            <div id="audio-menu"></div>
            <button class="external-track-btn" id="load-audio-btn">
              <svg class="menu-icon" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
              Add audio file
            </button>
          </div>
        </div>
        <div class="settings-section live-captions-settings">
          <h4 class="section-head"><span>Live Captions</span><button class="palette-btn" id="pal-cap" title="Live caption style"><svg viewBox="0 0 24 24"><path d="M12 22a1 1 0 0 1 0-20 10 9 0 0 1 10 9 5 5 0 0 1-5 5h-2.25a1.75 1.75 0 0 0-1.4 2.8l.3.4a1.75 1.75 0 0 1-1.4 2.8z"/><circle cx="13.5" cy="6.5" r=".5"/><circle cx="17.5" cy="10.5" r=".5"/><circle cx="6.5" cy="12.5" r=".5"/><circle cx="8.5" cy="7.5" r=".5"/></svg></button><button class="info-btn" id="lc-info" title="How Live Captions work"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg></button></h4>
          <div class="lc-info-panel" id="lc-info-panel" hidden>
            <div><b>How it works:</b> Live Captions (built into Windows) listens to the video's audio and turns speech into text, shown live inside the player. Keep the volume above 5% so it can hear.</div>
            <div><b>Turn on / off:</b> use the <b>Live subtitles</b> toggle below, or press <kbd>C</kbd>.</div>
            <div><b>Match the speaker's language:</b> open the <b>Language</b> menu below — installed models are marked <b>IN USE</b> or switchable with <b>Use</b>; missing ones show a <b>Download</b> button (accept the Windows permission prompt that appears). Delete a model you no longer need with the trash icon &mdash; the active one can't be deleted. Picking a new language lets Live Captions restart itself automatically.</div>
            <div><b>Style:</b> the palette icon edits the live captions look only; local subtitles have their own palette in the Subtitles section.</div>
            <div><b>If captions don't start:</b> open Live Captions once from the Start menu, then toggle it here again. Requires Windows 11 22H2 or later.</div>
          </div>
          <div class="setting-row">
            <label>Language</label>
            <button type="button" id="lc-lang-trigger" class="lc-lang-trigger" aria-expanded="false" aria-controls="lc-lang-dd">
              <span class="lc-lang-name" id="lc-lang-trigger-name">&hellip;</span>
              <svg class="lc-chev" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg>
            </button>
          </div>
          <div class="lc-lang-dd" id="lc-lang-dd" hidden>
            <div class="lc-models-hint" id="lc-models-hint"></div>
            <div class="lc-models" id="lc-models"><div class="lc-models-hint">Checking installed models&hellip;</div></div>
          </div>
          <div class="setting-row">
            <label>Position</label>
            <select id="live-captions-position">
              <option value="bottom" selected>Bottom</option>
              <option value="top">Top</option>
              <option value="center">Center</option>
              <option value="mid">60% Center</option>
            </select>
          </div>
          <div class="setting-row">
            <label>Max Lines</label>
            <input type="range" id="live-captions-max-lines" min="1" max="5" value="3">
            <input type="number" id="live-captions-max-lines-num" min="1" max="5" step="1" value="3" aria-label="Max lines value">
          </div>
          <div class="setting-row">
            <label>Live subtitles</label>
            <button id="live-captions-toggle" class="lc-toggle-btn" aria-pressed="false" disabled>OFF</button>
          </div>
        </div>
        <div class="settings-section">
          <h4>Keyboard &amp; Mouse</h4>
          <div class="shortcut-row"><span>Play / Pause</span><span><kbd>Space</kbd> <kbd>Click video</kbd></span></div>
          <div class="shortcut-row"><span>Fullscreen</span><span><kbd>F</kbd> <kbd>2&times; right-click</kbd></span></div>
          <div class="shortcut-row"><span>Seek &minus;10s / +10s</span><span><kbd>&larr;</kbd> <kbd>&rarr;</kbd></span></div>
          <div class="shortcut-row"><span>Volume up / down</span><span><kbd>&uarr;</kbd> <kbd>&darr;</kbd> <kbd>Wheel</kbd></span></div>
          <div class="shortcut-row"><span>Mute</span><span><kbd>M</kbd></span></div>
          <div class="shortcut-row"><span>Live captions</span><span><kbd>C</kbd></span></div>
          <div class="shortcut-row"><span>Speed down / up</span><span><kbd>[</kbd> <kbd>]</kbd></span></div>
          <div class="shortcut-row"><span>Maximize window</span><span><kbd>Double-click title</kbd></span></div>
          <div class="shortcut-row"><span>Close menus</span><span><kbd>Esc</kbd></span></div>
        </div>
      </div>
    </div>
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
<div class="pl-toast" id="pl-toast"></div>
    </div>
    <button class="ccbtn" id="ccbtn" title="Subtitles"></button>
    <button id="open" title="Open"></button>
    <button id="fsbtn"></button>
  </div>
</div>
<div class="dnd" id="dnd">Drop video, folder or subtitle here</div>
<div class="donate-modal" id="donate-modal">
  <div class="donate-card">
    <button class="donate-close" id="donate-close" title="Close">&#10005;</button>
    <div class="donate-title">Support PVP+</div>
    <img class="donate-upi-logo" src="data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiIHN0YW5kYWxvbmU9Im5vIj8+CjxzdmcKICAgeG1sbnM6ZGM9Imh0dHA6Ly9wdXJsLm9yZy9kYy9lbGVtZW50cy8xLjEvIgogICB4bWxuczpjYz0iaHR0cDovL2NyZWF0aXZlY29tbW9ucy5vcmcvbnMjIgogICB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiCiAgIHhtbG5zOnN2Zz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciCiAgIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICAgeG1sbnM6c29kaXBvZGk9Imh0dHA6Ly9zb2RpcG9kaS5zb3VyY2Vmb3JnZS5uZXQvRFREL3NvZGlwb2RpLTAuZHRkIgogICB4bWxuczppbmtzY2FwZT0iaHR0cDovL3d3dy5pbmtzY2FwZS5vcmcvbmFtZXNwYWNlcy9pbmtzY2FwZSIKICAgc29kaXBvZGk6ZG9jbmFtZT0iVVBJIExvZ28uc3ZnIgogICBpbmtzY2FwZTp2ZXJzaW9uPSIxLjAgKDQwMzVhNGZiNDksIDIwMjAtMDUtMDEpIgogICBpZD0ic3ZnMzQ3IgogICB2ZXJzaW9uPSIxLjEiCiAgIHZpZXdCb3g9IjAgMCAxMzAuNTQgNDYuMTE4IgogICBoZWlnaHQ9IjQ2LjExOG1tIgogICB3aWR0aD0iMTMwLjUzOTk5bW0iPgogIDxkZWZzCiAgICAgaWQ9ImRlZnMzNDEiPgogICAgPGNsaXBQYXRoCiAgICAgICBpZD0iY2xpcFBhdGgyOCIKICAgICAgIGNsaXBQYXRoVW5pdHM9InVzZXJTcGFjZU9uVXNlIj4KICAgICAgPHBhdGgKICAgICAgICAgaWQ9InBhdGgyNiIKICAgICAgICAgZD0iTSAwLDIxNiBIIDQzMiBWIDAgSCAwIFoiIC8+CiAgICA8L2NsaXBQYXRoPgogIDwvZGVmcz4KICA8c29kaXBvZGk6bmFtZWR2aWV3CiAgICAgaW5rc2NhcGU6d2luZG93LW1heGltaXplZD0iMCIKICAgICBpbmtzY2FwZTp3aW5kb3cteT0iMCIKICAgICBpbmtzY2FwZTp3aW5kb3cteD0iMTIyIgogICAgIGlua3NjYXBlOndpbmRvdy1oZWlnaHQ9IjEwMzAiCiAgICAgaW5rc2NhcGU6d2luZG93LXdpZHRoPSIxMzc1IgogICAgIHNob3dncmlkPSJmYWxzZSIKICAgICBpbmtzY2FwZTpkb2N1bWVudC1yb3RhdGlvbj0iMCIKICAgICBpbmtzY2FwZTpjdXJyZW50LWxheWVyPSJsYXllcjEiCiAgICAgaW5rc2NhcGU6ZG9jdW1lbnQtdW5pdHM9Im1tIgogICAgIGlua3NjYXBlOmN5PSI3MDQuNDMxNDgiCiAgICAgaW5rc2NhcGU6Y3g9Ii0yMDUuNzQ3MjYiCiAgICAgaW5rc2NhcGU6em9vbT0iMC41IgogICAgIGlua3NjYXBlOnBhZ2VzaGFkb3c9IjIiCiAgICAgaW5rc2NhcGU6cGFnZW9wYWNpdHk9IjAuMCIKICAgICBib3JkZXJvcGFjaXR5PSIxLjAiCiAgICAgYm9yZGVyY29sb3I9IiM2NjY2NjYiCiAgICAgcGFnZWNvbG9yPSIjZmZmZmZmIgogICAgIGlkPSJiYXNlIiAvPgogIDxtZXRhZGF0YQogICAgIGlkPSJtZXRhZGF0YTM0NCI+CiAgICA8cmRmOlJERj4KICAgICAgPGNjOldvcmsKICAgICAgICAgcmRmOmFib3V0PSIiPgogICAgICAgIDxkYzpmb3JtYXQ+aW1hZ2Uvc3ZnK3htbDwvZGM6Zm9ybWF0PgogICAgICAgIDxkYzp0eXBlCiAgICAgICAgICAgcmRmOnJlc291cmNlPSJodHRwOi8vcHVybC5vcmcvZGMvZGNtaXR5cGUvU3RpbGxJbWFnZSIgLz4KICAgICAgICA8ZGM6dGl0bGU+PC9kYzp0aXRsZT4KICAgICAgPC9jYzpXb3JrPgogICAgPC9yZGY6UkRGPgogIDwvbWV0YWRhdGE+CiAgPGcKICAgICBpZD0ibGF5ZXIxIgogICAgIGlua3NjYXBlOmdyb3VwbW9kZT0ibGF5ZXIiCiAgICAgaW5rc2NhcGU6bGFiZWw9IkxheWVyIDEiPgogICAgPGcKICAgICAgIGlkPSJnMjIiCiAgICAgICB0cmFuc2Zvcm09Im1hdHJpeCgwLjM1Mjc3Nzc3LDAsMCwtMC4zNTI3Nzc3NywtMTAuOTI2MzIxLDYxLjE1ODYzMykiPgogICAgICA8ZwogICAgICAgICBpZD0iZzI0IgogICAgICAgICBjbGlwLXBhdGg9InVybCgjY2xpcFBhdGgyOCkiPgogICAgICAgIDxnCiAgICAgICAgICAgaWQ9ImczMCIKICAgICAgICAgICB0cmFuc2Zvcm09InRyYW5zbGF0ZSgzMy45NzY2LDYxLjA2NzQpIj4KICAgICAgICAgIDxwYXRoCiAgICAgICAgICAgICBkPSJNIDAsMCBIIDIuNzcgTCAwLjE5NiwtMTAuNzUxIGMgLTAuMzgyLC0xLjU5NSAtMC4zMSwtMi43OTYgMC4yMTgsLTMuNTk3IDAuNTI2LC0wLjgwMiAxLjUwNSwtMS4yMDMgMi45MzYsLTEuMjAzIDEuNDIyLDAgMi41ODgsMC40MDEgMy40OTksMS4yMDMgMC45MTIsMC44MDEgMS41NTksMi4wMDIgMS45NDEsMy41OTcgTCAxMS4zNjMsMCBoIDIuODA2IGwgLTIuNjM3LC0xMS4wMTcgYyAtMC41NzMsLTIuMzk0IC0xLjU5NCwtNC4xODYgLTMuMDU2LC01LjM3NCAtMS40NjMsLTEuMTkgLTMuMzgxLC0xLjc4NCAtNS43NTQsLTEuNzg0IC0yLjM3NSwwIC00LjAwNCwwLjU5MyAtNC44OTEsMS43NzggLTAuODg4LDEuMTg0IC0xLjA0MywyLjk3OCAtMC40NjgsNS4zOCB6IgogICAgICAgICAgICAgc3R5bGU9ImZpbGw6IzY5NmE2YTtmaWxsLW9wYWNpdHk6MTtmaWxsLXJ1bGU6bm9uemVybztzdHJva2U6bm9uZSIKICAgICAgICAgICAgIGlkPSJwYXRoMzIiIC8+CiAgICAgICAgPC9nPgogICAgICAgIDxnCiAgICAgICAgICAgaWQ9ImczNCIKICAgICAgICAgICB0cmFuc2Zvcm09InRyYW5zbGF0ZSg0Ny43NzM0LDQzLjM2MzMpIj4KICAgICAgICAgIDxwYXRoCiAgICAgICAgICAgICBkPSJNIDAsMCA0LjQwNiwxOC40MDUgMTIuNzc4LDcuNTgyIEMgMTMuMDAyLDcuMjc3IDEzLjIyOCw2Ljk1IDEzLjQ1MSw2LjYwMyAxMy42NzQsNi4yNTYgMTMuOTAyLDUuODY2IDE0LjEzNiw1LjQzIGwgMi45MzksMTIuMjc0IGggMi41OTMgTCAxNS4yNjUsLTAuNjg3IDYuNzE3LDEwLjMyOSBDIDYuNDg4LDEwLjYyNiA2LjI3NSwxMC45NCA2LjA3NiwxMS4yNzEgNS44NzUsMTEuNjAyIDUuNjk0LDExLjk0OSA1LjUyOCwxMi4zMTEgTCAyLjU4MSwwIFoiCiAgICAgICAgICAgICBzdHlsZT0iZmlsbDojNjk2YTZhO2ZpbGwtb3BhY2l0eToxO2ZpbGwtcnVsZTpub256ZXJvO3N0cm9rZTpub25lIgogICAgICAgICAgICAgaWQ9InBhdGgzNiIgLz4KICAgICAgICA8L2c+CiAgICAgICAgPGcKICAgICAgICAgICBpZD0iZzM4IgogICAgICAgICAgIHRyYW5zZm9ybT0idHJhbnNsYXRlKDY3LjIxMTksNDMuMzYzMykiPgogICAgICAgICAgPHBhdGgKICAgICAgICAgICAgIGQ9Ik0gMCwwIDQuMjM4LDE3LjcwNCBIIDcuMDQyIEwgMi44MDUsMCBaIgogICAgICAgICAgICAgc3R5bGU9ImZpbGw6IzY5NmE2YTtmaWxsLW9wYWNpdHk6MTtmaWxsLXJ1bGU6bm9uemVybztzdHJva2U6bm9uZSIKICAgICAgICAgICAgIGlkPSJwYXRoNDAiIC8+CiAgICAgICAgPC9nPgogICAgICAgIDxnCiAgICAgICAgICAgaWQ9Imc0MiIKICAgICAgICAgICB0cmFuc2Zvcm09InRyYW5zbGF0ZSg3NC4wNDg4LDQzLjM2MzMpIj4KICAgICAgICAgIDxwYXRoCiAgICAgICAgICAgICBkPSJtIDAsMCA0LjIzOCwxNy43MDQgaCA5LjYzIEwgMTMuMjgzLDE1LjI2MiBIIDYuNDU4IEwgNS40MDEsMTAuODQ4IGggNi44MjUgTCAxMS42MjIsOC4zMjEgSCA0Ljc5NiBMIDIuODA1LDAgWiIKICAgICAgICAgICAgIHN0eWxlPSJmaWxsOiM2OTZhNmE7ZmlsbC1vcGFjaXR5OjE7ZmlsbC1ydWxlOm5vbnplcm87c3Ryb2tlOm5vbmUiCiAgICAgICAgICAgICBpZD0icGF0aDQ0IiAvPgogICAgICAgIDwvZz4KICAgICAgICA8ZwogICAgICAgICAgIGlkPSJnNDYiCiAgICAgICAgICAgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoODYuNzY4Niw0My4zNjMzKSI+CiAgICAgICAgICA8cGF0aAogICAgICAgICAgICAgZD0iTSAwLDAgNC4yMzgsMTcuNzA0IEggNy4wNDIgTCAyLjgwNSwwIFoiCiAgICAgICAgICAgICBzdHlsZT0iZmlsbDojNjk2YTZhO2ZpbGwtb3BhY2l0eToxO2ZpbGwtcnVsZTpub256ZXJvO3N0cm9rZTpub25lIgogICAgICAgICAgICAgaWQ9InBhdGg0OCIgLz4KICAgICAgICA8L2c+CiAgICAgICAgPGcKICAgICAgICAgICBpZD0iZzUwIgogICAgICAgICAgIHRyYW5zZm9ybT0idHJhbnNsYXRlKDkzLjYwNTUsNDMuMzYzMykiPgogICAgICAgICAgPHBhdGgKICAgICAgICAgICAgIGQ9Im0gMCwwIDQuMjM4LDE3LjcwNCBoIDkuNjMgTCAxMy4yODMsMTUuMjYyIEggNi40NTggTCA1LjM5NSwxMC44MjQgSCAxMi4yMiBMIDExLjYxNiw4LjI5NiBIIDQuNzkxIGwgLTEuMzcsLTUuNzIgaCA2LjgyNSBMIDkuNjMsMCBaIgogICAgICAgICAgICAgc3R5bGU9ImZpbGw6IzY5NmE2YTtmaWxsLW9wYWNpdHk6MTtmaWxsLXJ1bGU6bm9uemVybztzdHJva2U6bm9uZSIKICAgICAgICAgICAgIGlkPSJwYXRoNTIiIC8+CiAgICAgICAgPC9nPgogICAgICAgIDxnCiAgICAgICAgICAgaWQ9Imc1NCIKICAgICAgICAgICB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxMDkuODgxOCw0NS45NjM5KSI+CiAgICAgICAgICA8cGF0aAogICAgICAgICAgICAgZD0ibSAwLDAgaCAyLjM1OCBjIDEuMjk2LDAgMi4yOSwwLjA4OSAyLjk4MSwwLjI2NiAwLjY5MSwwLjE3NyAxLjMyNSwwLjQ3NiAxLjkwNiwwLjg5NSAwLjc4OSwwLjU3MSAxLjQ0OCwxLjI4MyAxLjk3OCwyLjEzNCAwLjUyOSwwLjg1IDAuOTMsMS44NDEgMS4yLDIuOTcgMC4yNjksMS4xMjkgMC4zNDMsMi4xMTcgMC4yMjEsMi45NjYgLTAuMTIzLDAuODUyIC0wLjQ0MSwxLjU2MyAtMC45NTYsMi4xMzYgLTAuMzg3LDAuNDE4IC0wLjg5OCwwLjcxOCAtMS41MzYsMC44OTYgLTAuNjM5LDAuMTc2IC0xLjY3OSwwLjI2NSAtMy4xMjUsMC4yNjUgSCA0LjAxMyAyLjk5OSBaIG0gLTMuNDI3LC0yLjYwMSA0LjIzOCwxNy43MDUgaCAzLjc4MyBjIDIuNDYsMCA0LjE2LC0wLjEyNiA1LjEwMiwtMC4zOCAwLjk0LC0wLjI1NSAxLjcxNywtMC42ODEgMi4zMjgsLTEuMjc3IDAuODExLC0wLjc4MiAxLjMyNywtMS43ODYgMS41NDksLTMuMDEgQyAxMy43OTQsOS4yMTEgMTMuNzE2LDcuODEyIDEzLjM0LDYuMjQgMTIuOTY0LDQuNjY4IDEyLjM3MywzLjI3NSAxMS41NjcsMi4wNjIgMTAuNzYzLDAuODQ4IDkuNzY2LC0wLjE1MyA4LjU4LC0wLjk0MyA3LjY4MywtMS41NCA2LjcyMSwtMS45NjUgNS42OTksLTIuMjIgNC42NzQsLTIuNDczIDMuMTQ2LC0yLjYwMSAxLjExLC0yLjYwMSBIIDAuMzU1IFoiCiAgICAgICAgICAgICBzdHlsZT0iZmlsbDojNjk2YTZhO2ZpbGwtb3BhY2l0eToxO2ZpbGwtcnVsZTpub256ZXJvO3N0cm9rZTpub25lIgogICAgICAgICAgICAgaWQ9InBhdGg1NiIgLz4KICAgICAgICA8L2c+CiAgICAgICAgPGcKICAgICAgICAgICBpZD0iZzU4IgogICAgICAgICAgIHRyYW5zZm9ybT0idHJhbnNsYXRlKDEzNi44Nzk5LDUzLjY2NikiPgogICAgICAgICAgPHBhdGgKICAgICAgICAgICAgIGQ9Ik0gMCwwIEggMC43MiBDIDIuMjc1LDAgMy4zNTQsMC4xNzUgMy45NTYsMC41MjEgNC41NTksMC44NjcgNC45NjQsMS40OCA1LjE3NCwyLjM1OSA1LjQsMy4zMDIgNS4yODMsMy45NjggNC44MjEsNC4zNTQgNC4zNTksNC43NDEgMy4zODcsNC45MzYgMS45MDIsNC45MzYgaCAtMC43MiB6IG0gLTAuNzQxLC0yLjM1NiAtMS45MDIsLTcuOTQ3IEggLTUuMjcxIEwgLTEuMDMyLDcuNDAxIEggMy4yMTEgQyA0LjQ2OCw3LjQwMSA1LjM3Nyw3LjMzMSA1LjkzNyw3LjE5IDYuNDk1LDcuMDUgNi45NTYsNi44MTcgNy4zMiw2LjQ5NCA3Ljc2Myw2LjA4MyA4LjA1NCw1LjUyOSA4LjE5NCw0LjgzMiA4LjMzMyw0LjEzNCA4LjMwMywzLjM2NiA4LjEwMywyLjUyOSA3LjkwMSwxLjY5IDcuNTYzLDAuOTE2IDcuMDg3LDAuMjA2IDYuNjExLC0wLjUwMyA2LjA1MywtMS4wNiA1LjQxNSwtMS40NjIgNC44OTcsLTEuNzg1IDQuMzI2LC0yLjAxNSAzLjcsLTIuMTUxIDMuMDczLC0yLjI4OSAyLjEzMiwtMi4zNTYgMC44NzUsLTIuMzU2IEggMC4zMjIgWiIKICAgICAgICAgICAgIHN0eWxlPSJmaWxsOiM2OTZhNmE7ZmlsbC1vcGFjaXR5OjE7ZmlsbC1ydWxlOm5vbnplcm87c3Ryb2tlOm5vbmUiCiAgICAgICAgICAgICBpZD0icGF0aDYwIiAvPgogICAgICAgIDwvZz4KICAgICAgICA8ZwogICAgICAgICAgIGlkPSJnNjIiCiAgICAgICAgICAgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMTQ4LjQ0NTgsNTAuMzE2NCkiPgogICAgICAgICAgPHBhdGgKICAgICAgICAgICAgIGQ9Ik0gMCwwIEggNC44MDkgTCA0LjAwNiw0LjA0IEMgMy45NjgsNC4yOTcgMy45MzIsNC41OTMgMy45MDEsNC45MjggMy44NzIsNS4yNjMgMy44NTIsNS42MzYgMy44MzksNi4wNDcgMy42NTMsNS42NiAzLjQ2Niw1LjI5OSAzLjI3OSw0Ljk2NCAzLjA5Myw0LjYzIDIuOTEyLDQuMzIyIDIuNzM0LDQuMDQgWiBNIDYuMDkyLC02Ljk1MyA1LjIyNSwtMi4zOTQgSCAtMS42MTIgTCAtNC43MDcsLTYuOTUzIEggLTcuNjUyIEwgNS4xMDksMTEuNDUyIDkuMDUsLTYuOTUzIFoiCiAgICAgICAgICAgICBzdHlsZT0iZmlsbDojNjk2YTZhO2ZpbGwtb3BhY2l0eToxO2ZpbGwtcnVsZTpub256ZXJvO3N0cm9rZTpub25lIgogICAgICAgICAgICAgaWQ9InBhdGg2NCIgLz4KICAgICAgICA8L2c+CiAgICAgICAgPGcKICAgICAgICAgICBpZD0iZzY2IgogICAgICAgICAgIHRyYW5zZm9ybT0idHJhbnNsYXRlKDE2MS41MTYxLDQzLjM2MzMpIj4KICAgICAgICAgIDxwYXRoCiAgICAgICAgICAgICBkPSJtIDAsMCAxLjkzOCw4LjEwMyAtMy41MTIsOS42MDEgaCAyLjk0NyBsIDIuMTgsLTYuMDEgYyAwLjA1LC0wLjE1NCAwLjExLC0wLjM1NSAwLjE3OSwtMC42MDUgMC4wNywtMC4yNSAwLjEzOCwtMC41MTkgMC4yMDIsLTAuODEgMC4xNzYsMC4yODIgMC4zNTcsMC41NSAwLjUzOCwwLjc5OSAwLjE4MSwwLjI1IDAuMzY0LDAuNDc5IDAuNTQ5LDAuNjg5IGwgNS4xMzMsNS45MzcgSCAxMi45NiBMIDQuNzIsOC4xMDMgMi43ODEsMCBaIgogICAgICAgICAgICAgc3R5bGU9ImZpbGw6IzY5NmE2YTtmaWxsLW9wYWNpdHk6MTtmaWxsLXJ1bGU6bm9uemVybztzdHJva2U6bm9uZSIKICAgICAgICAgICAgIGlkPSJwYXRoNjgiIC8+CiAgICAgICAgPC9nPgogICAgICAgIDxnCiAgICAgICAgICAgaWQ9Imc3MCIKICAgICAgICAgICB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxODguMjgwMyw1Mi4xMDc0KSI+CiAgICAgICAgICA8cGF0aAogICAgICAgICAgICAgZD0iTSAwLDAgQyAwLjAwMSwwLjEzNyAwLjA0MSwwLjUxNSAwLjExOSwxLjEzNiAwLjE3OSwxLjY1MiAwLjIyNiwyLjA4IDAuMjYsMi40MTkgMC4wOTMsMi4wMTUgLTAuMTA0LDEuNjExIC0wLjMzLDEuMjA5IC0wLjU1NywwLjgwNiAtMC44MTcsMC4zOTUgLTEuMTE0LC0wLjAyNSBsIC02Ljc3MywtOS40MzMgLTIuMjEsOS42MjYgYyAtMC4wOTQsMC4zOTYgLTAuMTY2LDAuNzc5IC0wLjIxNCwxLjE0OSAtMC4wNDgsMC4zNzEgLTAuMDgxLDAuNzM4IC0wLjA5NywxLjEwMiAtMC4wOTYsLTAuMzcyIC0wLjIxOCwtMC43NiAtMC4zNjcsLTEuMTY4IC0wLjE0OSwtMC40MDcgLTAuMzI3LC0wLjgzMyAtMC41MzYsLTEuMjc2IGwgLTMuOTM4LC04LjcxOSBoIC0yLjU4IGwgOC40OTUsMTguNDU1IDIuNDE4LC0xMS4xNzUgYyAwLjAzNSwtMC4xNzcgMC4wODYsLTAuNDcyIDAuMTQ4LC0wLjg4MyAwLjA2MiwtMC40MTEgMC4xMzUsLTAuOTE5IDAuMjIsLTEuNTIzIDAuMjg2LDAuNTA4IDAuNjk4LDEuMTUyIDEuMjQsMS45MzQgMC4xNDQsMC4yMSAwLjI1NCwwLjM3MSAwLjMyOCwwLjQ4NCBMIDIuNjY3LDkuNzExIDIuNDIyLC04Ljc0NCBoIC0yLjYwNiB6IgogICAgICAgICAgICAgc3R5bGU9ImZpbGw6IzY5NmE2YTtmaWxsLW9wYWNpdHk6MTtmaWxsLXJ1bGU6bm9uemVybztzdHJva2U6bm9uZSIKICAgICAgICAgICAgIGlkPSJwYXRoNzIiIC8+CiAgICAgICAgPC9nPgogICAgICAgIDxnCiAgICAgICAgICAgaWQ9Imc3NCIKICAgICAgICAgICB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxOTIuOTQxOSw0My4zNjMzKSI+CiAgICAgICAgICA8cGF0aAogICAgICAgICAgICAgZD0ibSAwLDAgNC4yMzksMTcuNzA0IGggOS42MyBMIDEzLjI4NCwxNS4yNjIgSCA2LjQ1OCBMIDUuMzk2LDEwLjgyNCBoIDYuODI1IEwgMTEuNjE3LDguMjk2IEggNC43OTEgTCAzLjQyMiwyLjU3NiBoIDYuODI1IEwgOS42MjksMCBaIgogICAgICAgICAgICAgc3R5bGU9ImZpbGw6IzY5NmE2YTtmaWxsLW9wYWNpdHk6MTtmaWxsLXJ1bGU6bm9uemVybztzdHJva2U6bm9uZSIKICAgICAgICAgICAgIGlkPSJwYXRoNzYiIC8+CiAgICAgICAgPC9nPgogICAgICAgIDxnCiAgICAgICAgICAgaWQ9Imc3OCIKICAgICAgICAgICB0cmFuc2Zvcm09InRyYW5zbGF0ZSgyMDUuNzkxLDQzLjM2MzMpIj4KICAgICAgICAgIDxwYXRoCiAgICAgICAgICAgICBkPSJNIDAsMCA0LjQwNiwxOC40MDUgMTIuNzc4LDcuNTgyIEMgMTMuMDAyLDcuMjc3IDEzLjIyOCw2Ljk1IDEzLjQ1MSw2LjYwMyAxMy42NzQsNi4yNTYgMTMuOTAyLDUuODY2IDE0LjEzNiw1LjQzIGwgMi45MzksMTIuMjc0IGggMi41OTQgTCAxNS4yNjUsLTAuNjg3IDYuNzE3LDEwLjMyOSBDIDYuNDg4LDEwLjYyNiA2LjI3NSwxMC45NCA2LjA3NiwxMS4yNzEgNS44NzUsMTEuNjAyIDUuNjk0LDExLjk0OSA1LjUyOCwxMi4zMTEgTCAyLjU4MSwwIFoiCiAgICAgICAgICAgICBzdHlsZT0iZmlsbDojNjk2YTZhO2ZpbGwtb3BhY2l0eToxO2ZpbGwtcnVsZTpub256ZXJvO3N0cm9rZTpub25lIgogICAgICAgICAgICAgaWQ9InBhdGg4MCIgLz4KICAgICAgICA8L2c+CiAgICAgICAgPGcKICAgICAgICAgICBpZD0iZzgyIgogICAgICAgICAgIHRyYW5zZm9ybT0idHJhbnNsYXRlKDIzNC40MTAyLDU4LjYyNSkiPgogICAgICAgICAgPHBhdGgKICAgICAgICAgICAgIGQ9Ik0gMCwwIC0zLjY1MywtMTUuMjYyIEggLTYuNDU4IEwgLTIuODA2LDAgaCAtNC41ODUgbCAwLjU4NSwyLjQ0MiBIIDUuMTQ2IEwgNC41NjIsMCBaIgogICAgICAgICAgICAgc3R5bGU9ImZpbGw6IzY5NmE2YTtmaWxsLW9wYWNpdHk6MTtmaWxsLXJ1bGU6bm9uemVybztzdHJva2U6bm9uZSIKICAgICAgICAgICAgIGlkPSJwYXRoODQiIC8+CiAgICAgICAgPC9nPgogICAgICAgIDxnCiAgICAgICAgICAgaWQ9Imc4NiIKICAgICAgICAgICB0cmFuc2Zvcm09InRyYW5zbGF0ZSgyMzcuMzIxMyw0Ni45MDcyKSI+CiAgICAgICAgICA8cGF0aAogICAgICAgICAgICAgZD0iTSAwLDAgMi40OTQsMS4wNjMgQyAyLjUxOSwwLjI3NCAyLjc2MywtMC4zMjkgMy4yMjksLTAuNzQ0IDMuNjk1LC0xLjE2IDQuMzY4LC0xLjM2NyA1LjI1LC0xLjM2NyBjIDAuODMyLDAgMS41NTIsMC4yMzggMi4xNTYsMC43MTQgMC42MDUsMC40NzUgMS4wMDQsMS4xMTIgMS4xOTUsMS45MSBDIDguODUsMi4yOTggOC4yMjksMy4yMjUgNi43NDQsNC4wMzggNi41MzYsNC4xNTkgNi4zNzYsNC4yNDggNi4yNjYsNC4zMDUgNC41OTEsNS4yNTYgMy41MjksNi4xMTcgMy4wODEsNi44ODcgMi42MzQsNy42NTcgMi41NDIsOC41OTggMi44MDgsOS43MSBjIDAuMzQ1LDEuNDQzIDEuMTAzLDIuNjEyIDIuMjcyLDMuNTA3IDEuMTY5LDAuODk1IDIuNTI3LDEuMzQzIDQuMDc2LDEuMzQzIDEuMjczLDAgMi4yNzgsLTAuMjUyIDMuMDEzLC0wLjc1NiAwLjczNiwtMC41MDUgMS4xNTYsLTEuMjI4IDEuMjYsLTIuMTcxIEwgMTAuOTYsMTAuNDcyIGMgLTAuMjE0LDAuNTU2IC0wLjQ5NiwwLjk2MyAtMC44NDYsMS4yMjIgLTAuMzUxLDAuMjU4IC0wLjc5NSwwLjM4NyAtMS4zMjgsMC4zODcgLTAuNzU0LDAgLTEuNDAyLC0wLjIwMyAtMS45NDMsLTAuNjA0IEMgNi4zMDUsMTEuMDczIDUuOTUyLDEwLjUzMyA1Ljc4OSw5Ljg1NSA1LjUzNSw4Ljc5MSA2LjI3Miw3LjggOC4wMDEsNi44ODEgOC4xMzQsNi44MDkgOC4yMzgsNi43NTEgOC4zMTMsNi43MTEgOS44MjYsNS45MDYgMTAuODEsNS4xMTcgMTEuMjYxLDQuMzQ3IDExLjcxMywzLjU3NiAxMS44MDIsMi42MTUgMTEuNTI1LDEuNDYzIDExLjEyNCwtMC4yMTUgMTAuMjkxLC0xLjU0NyA5LjAyNSwtMi41MzQgNy43NTksLTMuNTIxIDYuMjQ5LC00LjAxNSA0LjQ5OCwtNC4wMTUgYyAtMS40NzEsMCAtMi41OTIsMC4zNDYgLTMuMzY0LDEuMDQgQyAwLjM2LC0yLjI4MiAtMC4wMTgsLTEuMjkxIDAsMCIKICAgICAgICAgICAgIHN0eWxlPSJmaWxsOiM2OTZhNmE7ZmlsbC1vcGFjaXR5OjE7ZmlsbC1ydWxlOm5vbnplcm87c3Ryb2tlOm5vbmUiCiAgICAgICAgICAgICBpZD0icGF0aDg4IiAvPgogICAgICAgIDwvZz4KICAgICAgICA8ZwogICAgICAgICAgIGlkPSJnOTAiCiAgICAgICAgICAgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMjU4LjA0NTksNDMuMzYzMykiPgogICAgICAgICAgPHBhdGgKICAgICAgICAgICAgIGQ9Ik0gMCwwIDQuMjM4LDE3LjcwNCBIIDcuMDQzIEwgMi44MDUsMCBaIgogICAgICAgICAgICAgc3R5bGU9ImZpbGw6IzY5NmE2YTtmaWxsLW9wYWNpdHk6MTtmaWxsLXJ1bGU6bm9uemVybztzdHJva2U6bm9uZSIKICAgICAgICAgICAgIGlkPSJwYXRoOTIiIC8+CiAgICAgICAgPC9nPgogICAgICAgIDxnCiAgICAgICAgICAgaWQ9Imc5NCIKICAgICAgICAgICB0cmFuc2Zvcm09InRyYW5zbGF0ZSgyNjQuODgyOCw0My4zNjMzKSI+CiAgICAgICAgICA8cGF0aAogICAgICAgICAgICAgZD0iTSAwLDAgNC40MDYsMTguNDA1IDEyLjc3OCw3LjU4MiBDIDEzLjAwMiw3LjI3NyAxMy4yMjgsNi45NSAxMy40NTEsNi42MDMgMTMuNjc0LDYuMjU2IDEzLjkwMiw1Ljg2NiAxNC4xMzYsNS40MyBsIDIuOTM5LDEyLjI3NCBoIDIuNTkzIEwgMTUuMjY1LC0wLjY4NyA2LjcxNywxMC4zMjkgYyAtMC4yMjksMC4yOTcgLTAuNDQzLDAuNjExIC0wLjY0MiwwLjk0MiAtMC4yLDAuMzMxIC0wLjM4MiwwLjY3OCAtMC41NDgsMS4wNCBMIDIuNTgxLDAgWiIKICAgICAgICAgICAgIHN0eWxlPSJmaWxsOiM2OTZhNmE7ZmlsbC1vcGFjaXR5OjE7ZmlsbC1ydWxlOm5vbnplcm87c3Ryb2tlOm5vbmUiCiAgICAgICAgICAgICBpZD0icGF0aDk2IiAvPgogICAgICAgIDwvZz4KICAgICAgICA8ZwogICAgICAgICAgIGlkPSJnOTgiCiAgICAgICAgICAgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMjkzLjUwMiw1OC42MjUpIj4KICAgICAgICAgIDxwYXRoCiAgICAgICAgICAgICBkPSJNIDAsMCAtMy42NTQsLTE1LjI2MiBIIC02LjQ1OCBMIC0yLjgwNiwwIGggLTQuNTg1IGwgMC41ODUsMi40NDIgSCA1LjE0NiBMIDQuNTYyLDAgWiIKICAgICAgICAgICAgIHN0eWxlPSJmaWxsOiM2OTZhNmE7ZmlsbC1vcGFjaXR5OjE7ZmlsbC1ydWxlOm5vbnplcm87c3Ryb2tlOm5vbmUiCiAgICAgICAgICAgICBpZD0icGF0aDEwMCIgLz4KICAgICAgICA8L2c+CiAgICAgICAgPGcKICAgICAgICAgICBpZD0iZzEwMiIKICAgICAgICAgICB0cmFuc2Zvcm09InRyYW5zbGF0ZSgyOTYuNTU1Nyw0My4zNjMzKSI+CiAgICAgICAgICA8cGF0aAogICAgICAgICAgICAgZD0ibSAwLDAgNC4yMzgsMTcuNzA0IGggOS42MyBMIDEzLjI4NCwxNS4yNjIgSCA2LjQ1OSBMIDUuMzk2LDEwLjgyNCBoIDYuODI1IEwgMTEuNjE2LDguMjk2IEggNC43OTEgTCAzLjQyMiwyLjU3NiBoIDYuODI1IEwgOS42MywwIFoiCiAgICAgICAgICAgICBzdHlsZT0iZmlsbDojNjk2YTZhO2ZpbGwtb3BhY2l0eToxO2ZpbGwtcnVsZTpub256ZXJvO3N0cm9rZTpub25lIgogICAgICAgICAgICAgaWQ9InBhdGgxMDQiIC8+CiAgICAgICAgPC9nPgogICAgICAgIDxnCiAgICAgICAgICAgaWQ9ImcxMDYiCiAgICAgICAgICAgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMzE0LjY0MTYsNTMuNTIyNSkiPgogICAgICAgICAgPHBhdGgKICAgICAgICAgICAgIGQ9Ik0gMCwwIEggMC41MDggQyAxLjk5MiwwIDMuMDIxLDAuMTc2IDMuNTkzLDAuNTMxIDQuMTY1LDAuODg2IDQuNTYxLDEuNTE0IDQuNzc1LDIuNDE4IDUuMDA5LDMuMzkzIDQuOTEzLDQuMDgxIDQuNDg0LDQuNDc5IDQuMDU5LDQuODggMy4xMzgsNS4wNzkgMS43MjQsNS4wNzkgSCAxLjIxNiBaIG0gLTAuNzEyLC0yLjIzNyAtMS44OTcsLTcuOTIyIGggLTIuNjI4IGwgNC4yMzksMTcuNzA0IGggMy45MTMgYyAxLjE0NywwIDIuMDE5LC0wLjA3NiAyLjYxNCwtMC4yMyBDIDYuMTI1LDcuMTYyIDYuNjA1LDYuOTA5IDYuOTY4LDYuNTUzIDcuNCw2LjEyNyA3LjY4LDUuNTczIDcuODEsNC44OTYgNy45MzcsNC4yMiA3LjkwNCwzLjQ3OCA3LjcxMiwyLjY3MyA3LjM3MywxLjI1NCA2Ljc3MywwLjE0MyA1LjkxMywtMC42NiA1LjA1MywtMS40NjEgMy45NTEsLTEuOTQ0IDIuNjA4LC0yLjEwNCBsIDQuMDE0LC04LjA1NSBIIDMuNDUgbCAtMy44NDQsNy45MjIgeiIKICAgICAgICAgICAgIHN0eWxlPSJmaWxsOiM2OTZhNmE7ZmlsbC1vcGFjaXR5OjE7ZmlsbC1ydWxlOm5vbnplcm87c3Ryb2tlOm5vbmUiCiAgICAgICAgICAgICBpZD0icGF0aDEwOCIgLz4KICAgICAgICA8L2c+CiAgICAgICAgPGcKICAgICAgICAgICBpZD0iZzExMCIKICAgICAgICAgICB0cmFuc2Zvcm09InRyYW5zbGF0ZSgzMjIuOTI1OCw0My4zNjMzKSI+CiAgICAgICAgICA8cGF0aAogICAgICAgICAgICAgZD0ibSAwLDAgNC4yMzgsMTcuNzA0IGggOS42MyBMIDEzLjI4NCwxNS4yNjIgSCA2LjQ1OCBMIDUuNDAxLDEwLjg0OCBoIDYuODI2IEwgMTEuNjIyLDguMzIxIEggNC43OTcgTCAyLjgwNSwwIFoiCiAgICAgICAgICAgICBzdHlsZT0iZmlsbDojNjk2YTZhO2ZpbGwtb3BhY2l0eToxO2ZpbGwtcnVsZTpub256ZXJvO3N0cm9rZTpub25lIgogICAgICAgICAgICAgaWQ9InBhdGgxMTIiIC8+CiAgICAgICAgPC9nPgogICAgICAgIDxnCiAgICAgICAgICAgaWQ9ImcxMTQiCiAgICAgICAgICAgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMzQwLjA0NDksNTAuMzE2NCkiPgogICAgICAgICAgPHBhdGgKICAgICAgICAgICAgIGQ9Ik0gMCwwIEggNC44MSBMIDQuMDA3LDQuMDQgQyAzLjk2OCw0LjI5NyAzLjkzMyw0LjU5MyAzLjkwMiw0LjkyOCAzLjg3Myw1LjI2MyAzLjg1Myw1LjYzNiAzLjg0LDYuMDQ3IDMuNjUzLDUuNjYgMy40NjYsNS4yOTkgMy4yOCw0Ljk2NCAzLjA5NCw0LjYzIDIuOTEyLDQuMzIyIDIuNzM0LDQuMDQgWiBNIDYuMDkzLC02Ljk1MyA1LjIyNiwtMi4zOTQgSCAtMS42MTEgTCAtNC43MDYsLTYuOTUzIEggLTcuNjUyIEwgNS4xMDksMTEuNDUyIDkuMDUxLC02Ljk1MyBaIgogICAgICAgICAgICAgc3R5bGU9ImZpbGw6IzY5NmE2YTtmaWxsLW9wYWNpdHk6MTtmaWxsLXJ1bGU6bm9uemVybztzdHJva2U6bm9uZSIKICAgICAgICAgICAgIGlkPSJwYXRoMTE2IiAvPgogICAgICAgIDwvZz4KICAgICAgICA8ZwogICAgICAgICAgIGlkPSJnMTE4IgogICAgICAgICAgIHRyYW5zZm9ybT0idHJhbnNsYXRlKDM2Ny4zNTU1LDU2Ljc2MjcpIj4KICAgICAgICAgIDxwYXRoCiAgICAgICAgICAgICBkPSJtIDAsMCBjIC0wLjYyNywwLjY5MyAtMS4zNDEsMS4yMTMgLTIuMTQzLDEuNTYgLTAuOCwwLjM0NSAtMS42ODgsMC41MiAtMi42NjMsMC41MiAtMS44ODUsMCAtMy41NjksLTAuNjIxIC01LjA0OCwtMS44NjIgLTEuNDgxLC0xLjI0MiAtMi40NTcsLTIuODUgLTIuOTMsLTQuODI2IC0wLjQ1NywtMS45MTEgLTAuMjU4LC0zLjQ4NiAwLjU5NiwtNC43MjcgMC44NTQsLTEuMjQyIDIuMTU4LC0xLjg2NCAzLjkwOSwtMS44NjQgMS4wMjMsMCAyLjAzOSwwLjE4NiAzLjA1MSwwLjU1NyAxLjAxMiwwLjM3MSAyLjAzMywwLjkzMSAzLjA2LDEuNjgyIGwgLTAuNzc5LC0zLjI1NCBjIC0wLjg4NywtMC41NTYgLTEuODA4LC0wLjk3MiAtMi43NjEsLTEuMjQ1IC0wLjk1NCwtMC4yNzQgLTEuOTQ5LC0wLjQxMSAtMi45ODYsLTAuNDExIC0xLjMyLDAgLTIuNDg4LDAuMjIxIC0zLjUwMSwwLjY2NSAtMS4wMTQsMC40NDMgLTEuODQzLDEuMDk1IC0yLjQ4NCwxLjk1OSAtMC42MzgsMC44NDYgLTEuMDQ3LDEuODQzIC0xLjIyMiwyLjk5MyAtMC4xNzgsMS4xNDggLTAuMTExLDIuMzcyIDAuMTk5LDMuNjcxIDAuMzExLDEuMjk3IDAuODMsMi41MTYgMS41NTUsMy42NTcgMC43MjQsMS4xNDEgMS42MTksMi4xNDMgMi42ODEsMy4wMDUgMS4wNjYsMC44NzEgMi4yMDYsMS41MjkgMy40MiwxLjk3OCAxLjIxNSwwLjQ0NiAyLjQ2OCwwLjY3MSAzLjc1NywwLjY3MSAxLjAxNCwwIDEuOTQ0LC0wLjE1MiAyLjc5MSwtMC40NTUgQyAtMC42NTEsMy45NzMgMC4xMzEsMy41MTYgMC44NSwyLjkwMSBaIgogICAgICAgICAgICAgc3R5bGU9ImZpbGw6IzY5NmE2YTtmaWxsLW9wYWNpdHk6MTtmaWxsLXJ1bGU6bm9uemVybztzdHJva2U6bm9uZSIKICAgICAgICAgICAgIGlkPSJwYXRoMTIwIiAvPgogICAgICAgIDwvZz4KICAgICAgICA8ZwogICAgICAgICAgIGlkPSJnMTIyIgogICAgICAgICAgIHRyYW5zZm9ybT0idHJhbnNsYXRlKDM2Ny42MjcsNDMuMzYzMykiPgogICAgICAgICAgPHBhdGgKICAgICAgICAgICAgIGQ9Im0gMCwwIDQuMjM4LDE3LjcwNCBoIDkuNjMgTCAxMy4yODMsMTUuMjYyIEggNi40NTkgTCA1LjM5NiwxMC44MjQgaCA2LjgyNSBMIDExLjYxNiw4LjI5NiBIIDQuNzkxIEwgMy40MjIsMi41NzYgaCA2LjgyNSBMIDkuNjMsMCBaIgogICAgICAgICAgICAgc3R5bGU9ImZpbGw6IzY5NmE2YTtmaWxsLW9wYWNpdHk6MTtmaWxsLXJ1bGU6bm9uemVybztzdHJva2U6bm9uZSIKICAgICAgICAgICAgIGlkPSJwYXRoMTI0IiAvPgogICAgICAgIDwvZz4KICAgICAgICA8ZwogICAgICAgICAgIGlkPSJnMTI2IgogICAgICAgICAgIHRyYW5zZm9ybT0idHJhbnNsYXRlKDMxNi40NjI5LDc2LjQ5NTEpIj4KICAgICAgICAgIDxwYXRoCiAgICAgICAgICAgICBkPSJNIDAsMCBIIC0xOS4yODMgTCA3LjUzNSw5Ni44NTUgaCAxOS4yODQgeiIKICAgICAgICAgICAgIHN0eWxlPSJmaWxsOiM2NjY4NmM7ZmlsbC1vcGFjaXR5OjE7ZmlsbC1ydWxlOm5vbnplcm87c3Ryb2tlOm5vbmUiCiAgICAgICAgICAgICBpZD0icGF0aDEyOCIgLz4KICAgICAgICA8L2c+CiAgICAgICAgPGcKICAgICAgICAgICBpZD0iZzEzMCIKICAgICAgICAgICB0cmFuc2Zvcm09InRyYW5zbGF0ZSgzMDYuNDUyMSwxNzAuMjg4MSkiPgogICAgICAgICAgPHBhdGgKICAgICAgICAgICAgIGQ9Im0gMCwwIGMgLTEuMzM3LDEuODQzIC0zLjM5OSwyLjc3MyAtNi4yLDIuNzczIGggLTEwNi4wMzYgbCAtNS4yNTIsLTE4Ljk3IGggMTkuMjk0IHYgMC4wMTEgaCA3Ny4xNjkgbCAtNS42MTQsLTIwLjI3MiBoIC03Ny4xNzEgbCAwLjAwNywwLjA0MiBoIC0xOS4yODYgbCAtMTYuMDA3LC01Ny43ODcgaCAxOS4yOTYgbCAxMC43NDIsMzguNzg2IGggODYuNzQ2IGMgMi43MDksMCA1LjI1OSwwLjkyNCA3LjY1NywyLjc3MiAyLjM5MywxLjg1IDMuOTY4LDQuMTMxIDQuNzIzLDYuODU1IEwgMC44MDksLTYuOTk2IEMgMS41OTMsLTQuMTgxIDEuMzIyLC0xLjg0NSAwLDAiCiAgICAgICAgICAgICBzdHlsZT0iZmlsbDojNjY2ODZjO2ZpbGwtb3BhY2l0eToxO2ZpbGwtcnVsZTpub256ZXJvO3N0cm9rZTpub25lIgogICAgICAgICAgICAgaWQ9InBhdGgxMzIiIC8+CiAgICAgICAgPC9nPgogICAgICAgIDxnCiAgICAgICAgICAgaWQ9ImcxMzQiCiAgICAgICAgICAgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMTU2LjExOTYsODIuNTQxKSI+CiAgICAgICAgICA8cGF0aAogICAgICAgICAgICAgZD0ibSAwLDAgYyAtMS4wNjUsLTMuODM1IC00LjU1NywtNi40ODggLTguNTM4LC02LjQ4OCBoIC05OS40OTEgYyAtMi43MTEsMCAtNC43MjYsMC45MjQgLTYuMDUxLDIuNzcgLTEuMzI0LDEuODQ4IC0xLjYwOCw0LjEzNCAtMC44NTEsNi44NTcgbCAyNC4yNzYsODcuMzg3IGggMTkuMzAxIGwgLTIxLjY4MywtNzguMDUgaCA3Ny4yMDYgbCAyMS42ODMsNzguMDUgaCAxOS4yOTcgeiIKICAgICAgICAgICAgIHN0eWxlPSJmaWxsOiM2NjY4NmM7ZmlsbC1vcGFjaXR5OjE7ZmlsbC1ydWxlOm5vbnplcm87c3Ryb2tlOm5vbmUiCiAgICAgICAgICAgICBpZD0icGF0aDEzNiIgLz4KICAgICAgICA8L2c+CiAgICAgICAgPGcKICAgICAgICAgICBpZD0iZzEzOCIKICAgICAgICAgICB0cmFuc2Zvcm09InRyYW5zbGF0ZSgzNzYuNTg1OSwxNzMuMTY4OSkiPgogICAgICAgICAgPHBhdGgKICAgICAgICAgICAgIGQ9Im0gMCwwIDI0LjQxNCwtNDguNTUzIC01MS4zMjIsLTQ4LjU0IHoiCiAgICAgICAgICAgICBzdHlsZT0iZmlsbDojMjc4MDNiO2ZpbGwtb3BhY2l0eToxO2ZpbGwtcnVsZTpub256ZXJvO3N0cm9rZTpub25lIgogICAgICAgICAgICAgaWQ9InBhdGgxNDAiIC8+CiAgICAgICAgPC9nPgogICAgICAgIDxnCiAgICAgICAgICAgaWQ9ImcxNDIiCiAgICAgICAgICAgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMzU5LjQ3MTcsMTczLjE2ODkpIj4KICAgICAgICAgIDxwYXRoCiAgICAgICAgICAgICBkPSJtIDAsMCAyNC4zOTYsLTQ4LjU1MyAtNTEuMzQzLC00OC41NCB6IgogICAgICAgICAgICAgc3R5bGU9ImZpbGw6I2U5NjYxYztmaWxsLW9wYWNpdHk6MTtmaWxsLXJ1bGU6bm9uemVybztzdHJva2U6bm9uZSIKICAgICAgICAgICAgIGlkPSJwYXRoMTQ0IiAvPgogICAgICAgIDwvZz4KICAgICAgPC9nPgogICAgPC9nPgogIDwvZz4KPC9zdmc+Cg==" alt="UPI">
    <div class="donate-ask">Donate a minimum of <b>&#8377;100</b> to support our efforts</div>
    <img class="donate-qr" id="donate-qr" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAWgAAAFoCAYAAAB65WHVAAAAAklEQVR4AewaftIAAAotSURBVO3BUQ7jWJIEQY+E7n/l2PocoBd8QJPDSancLP0DSdI6gyRppUGStNIgSVppkCStNEiSVhokSSsNkqSVBknSSoMkaaVBkrTSIElaaZAkrTRIklYaJEkrDZKklQZJ0kqDJGmlQZK00iBJWmmQJK00SJJWGiRJKw2SpJUGSdJKgyRppUGStNIgSVppkCStNEiSVhokSSsNkqSVBknSSoMkaaVBkrTSIEla6cMySfjbtGWLJJy05Q1J+DVteUISrrTlCUn427Rli0GStNIgSVppkCStNEiSVhokSSsNkqSVBknSSh++TFu+SRLekgT9U1tOknClLU9IwklbTtqyRVu+SRK+xSBJWmmQJK00SJJWGiRJKw2SpJUGSdJKgyRppUGStNKHH5SEt7TlDUk4actdSXhLErZoy11J0D8l4S1t+SWDJGmlQZK00iBJWmmQJK00SJJWGiRJKw2SpJUGSdJKH/QzkvBN2vJL2vKEJLyhLdptkCStNEiSVhokSSsNkqSVBknSSoMkaaVBkrTSIEla6YP0H9pykoSTtpwk4Q1tOUnClbacJOGkLW9oi77fIElaaZAkrTRIklYaJEkrDZKklQZJ0kqDJGmlQZK00ocf1BZ9v7b8miSctOWXtEX/ziBJWmmQJK00SJJWGiRJKw2SpJUGSdJKgyRppQ9fJgn6/7XlShJ+TRJO2rJFW06ScNKWK0k4acsTkqD/jkGStNIgSVppkCStNEiSVhokSSsNkqSVBknSSoMkaaUPy7RF/04S3tCWJ7Rli7a8IQknbTlJwhvaov+dQZK00iBJWmmQJK00SJJWGiRJKw2SpJUGSdJKgyRppfQPFknClbacJOGbtOUJSfglbTlJwhPaciUJT2jLSRJO2vKGJHyTtvySQZK00iBJWmmQJK00SJJWGiRJKw2SpJUGSdJKgyRppQ9/qbY8IQlX2nKShJO2/Jq23NWWkyR8k7acJOGutjyhLW9IwhOScKUtWwySpJUGSdJKgyRppUGStNIgSVppkCStNEiSVkr/YJEkbNGWu5Jw0pYnJOGutjwhCW9oy0kSTtryhiSctOUNSThpy0kSrrTlCUl4Qlu+xSBJWmmQJK00SJJWGiRJKw2SpJUGSdJKgyRppUGStNKHv1RbTpJwV1tOkrBFEk7a8oS23JWEk7acJOFKW96ShJO2XEnCN0nCE9rySwZJ0kqDJGmlQZK00iBJWmmQJK00SJJWGiRJKw2SpJU+fJm2PCEJb0jCSVuekIQrbTlJwhPacpKEK215S1vuSsJJW06ScFdbtkjCSVv0T4MkaaVBkrTSIElaaZAkrTRIklYaJEkrDZKklQZJ0kofvkwSntCWkySctOUNSThpy5UknLTlCUk4acuVJJy05SQJJ225koSTtjyhLSdJuNKWkyS8oS1PSMIb2rLFIElaaZAkrTRIklYaJEkrDZKklQZJ0kqDJGmlQZK0UvoHiyRhi7bclYS3tOWuJJy05QlJeENbTpJwpS0nSThpy0kSTtryS5LwlrZ8i0GStNIgSVppkCStNEiSVhokSSsNkqSVBknSSh+WacuVJDyhLU9IwpW2nCThpC0nSbjSlpO2PCEJJ225koSTtnyTJLwhCU9oi/53BknSSoMkaaVBkrTSIElaaZAkrTRIklYaJEkrDZKklT58mbacJOEkCW9IwklbntCWu5LwliS8IQknbXlDW06S8EuScNKWJyThlwySpJUGSdJKgyRppUGStNIgSVppkCStNEiSVhokSSulf/BjkrBFW56QhJO2vCEJT2jLXUk4actJEn5JW06S8IS2bJGEu9qyxSBJWmmQJK00SJJWGiRJKw2SpJUGSdJKgyRppUGStNKHZZJwpS1PaMsTknAlCU9oy0kS7mrLSVvekISTtpwk4a62PCEJJ225KwknbXlDEjZpy7cYJEkrDZKklQZJ0kqDJGmlQZK00iBJWmmQJK30YZm2vCEJJ225qy0nSXhDW06S8GvacpKELZJw0pY3JOGkLXe15SQJf5tBkrTSIElaaZAkrTRIklYaJEkrDZKklQZJ0kqDJGmlD18mCSdt2SIJJ205ScJJW+5qyxOScNKWK0n4Jkk4actJErZoyxuScNKWkyT8kkGStNIgSVppkCStNEiSVhokSSsNkqSVBknSSoMkaaUPyyThSluekISTttzVlpMknLTlJAlvaMsTknBXEt6QhE2ScKUtJ0l4QluutOUkCW9JwpW2bDFIklYaJEkrDZKklQZJ0kqDJGmlQZK00iBJWmmQJK2U/sEiSbjSlpMknLTlDUk4actJEu5qy0kSntCWkyRcactbknClLSdJeEJbtkjCXW15SxJO2vItBknSSoMkaaVBkrTSIElaaZAkrTRIklYaJEkrDZKklT78oLacJOGkLXe15SQJJ205ScKVJPyaJJy05aQtV5Jw0paTJDwhCW9oy0kSriRhkyRcacsWgyRppUGStNIgSVppkCStNEiSVhokSSsNkqSV0j9YJAlX2nKShJO2PCEJd7XlJAknbbkrCSdt2SIJT2jLFknQP7XlJAknbfkWgyRppUGStNIgSVppkCStNEiSVhokSSsNkqSVBknSSukfaL0k3NWWX5OEJ7TlriQ8oS0nSbirLW9Iwklb3pKEK23ZYpAkrTRIklYaJEkrDZKklQZJ0kqDJGmlQZK00iBJWunDMkn427TlpC0nSbgrCW9py5UknLTlJAn6d5Jw0pYtknDSlm8xSJJWGiRJKw2SpJUGSdJKgyRppUGStNIgSVppkCSt9OHLtOWbJOEJSbgrCSdt2aItJ0l4QhL0T23ZIgl/m0GStNIgSVppkCStNEiSVhokSSsNkqSVBknSSh9+UBLe0pYt2vKGJJy05SQJb2jLXUk4actb2nIlCSdJ+CZtOUnCLxkkSSsNkqSVBknSSoMkaaVBkrTSIElaaZAkrTRIklb6IH2xtjwhCXcl4QltOUnClba8JQlvSMITknClLVsMkqSVBknSSoMkaaVBkrTSIElaaZAkrTRIklYaJEkrfZD+QxKekISTtlxJwkkS3tCWJyThJAlvSMIb2nKShJO2/G0GSdJKgyRppUGStNIgSVppkCStNEiSVhokSSsNkqSVPvygtvyatpwk4a62PCEJb2jLG5LwlrbclYSTtrwhCU9IwklbfskgSVppkCStNEiSVhokSSsNkqSVBknSSoMkaaVBkrTShy+ThL9RErZIwklbTpLwhiTc1Za3JOFv05YnJOGkLd9ikCStNEiSVhokSSsNkqSVBknSSoMkaaVBkrRS+geSpHUGSdJKgyRppUGStNIgSVppkCStNEiSVhokSSsNkqSVBknSSoMkaaVBkrTSIElaaZAkrTRIklYaJEkrDZKklQZJ0kqDJGmlQZK00iBJWmmQJK00SJJWGiRJKw2SpJUGSdJKgyRppUGStNIgSVppkCStNEiSVhokSSsNkqSVBknSSoMkaaX/Ax7l0AIa6govAAAAAElFTkSuQmCC" alt="UPI QR code">
    <button class="donate-upi-id" id="donate-upi-id" title="Copy UPI ID">hoxdo@ptaxis</button>
    <div class="donate-hint">Scan with any UPI app to pay &middot; click ID to copy</div>
  </div>
</div>
<div class="style-backdrop" id="stylebackdrop"></div>
<div class="style-popup" id="stylepopup">
  <div class="style-head"><span>Subtitle Style</span><button id="styleclose" title="Close">&#10005;</button></div>
  <div class="style-body">
    <div class="style-row"><label>Font family</label><select id="st-family"></select></div>
    <div class="style-row"><label>Weight</label><select id="st-weight"><option value="400">Normal</option><option value="500">Medium</option><option value="600">Semibold</option><option value="700">Bold</option></select></div>
    <div class="style-row"><label>Size</label><input type="range" id="st-size" min="10" max="48" step="1"><span id="st-size-v"></span></div>
    <div class="style-row"><label>Text color</label><input type="color" id="st-color"></div>
    <div class="style-row"><label>Background</label><input type="color" id="st-bg"></div>
    <div class="style-row"><label>Bg opacity</label><input type="range" id="st-bgop" min="0" max="100" step="1"><span id="st-bgop-v"></span></div>
    <div class="style-row"><label>Shadow</label><input type="range" id="st-shadow" min="0" max="8" step="1"><span id="st-shadow-v"></span></div>
    <div class="style-row"><label>Shadow color</label><input type="color" id="st-shcolor"></div>
    <div class="style-row"><label>Box shadow</label><input type="range" id="st-boxshadow" min="0" max="8" step="1"><span id="st-boxshadow-v"></span></div>
    <div class="style-row"><label>Box shadow color</label><input type="color" id="st-boxshcolor"></div>
    <div class="style-row"><label>Outline</label><input type="range" id="st-outline" min="0" max="3" step="1"><span id="st-outline-v"></span></div>
    <div class="style-row"><label>Outline color</label><input type="color" id="st-olcolor"></div>
  </div>
  <div class="style-foot"><button id="st-reset">Reset</button><button id="st-done">Done</button></div>
</div>
<div class="openmenu" id="openmenu" hidden>
  <div class="om-item" id="om-video"><svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="m10 11.5 5 3-5 3v-6z"/></svg><span>Add video</span></div>
  <div class="om-item" id="om-playlist"><svg viewBox="0 0 24 24"><path d="M11 12H3"/><path d="M16 6H3"/><path d="M11 18H3"/><path d="M18 9v6"/><path d="M21 12H6"/></svg><span>Add playlist</span></div>
</div>
<div class="cc-menu" id="ccmenu" hidden>
  <div class="cc-row" id="cc-local"><svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg><span>Local subtitle</span><button class="palette-btn" id="pal-sub" title="Subtitle style"><svg viewBox="0 0 24 24"><path d="M12 22a1 1 0 0 1 0-20 10 9 0 0 1 10 9 5 5 0 0 1-5 5h-2.25a1.75 1.75 0 0 0-1.4 2.8l.3.4a1.75 1.75 0 0 1-1.4 2.8z"/><circle cx="13.5" cy="6.5" r=".5"/><circle cx="17.5" cy="10.5" r=".5"/><circle cx="6.5" cy="12.5" r=".5"/><circle cx="8.5" cy="7.5" r=".5"/></svg></button></div>
  <div class="cc-sublist" id="cc-sublist" hidden>
    <div id="subtitle-menu"></div>
    <button class="external-track-btn" id="load-subtitle-btn">
      <svg class="menu-icon" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
      Add subtitle file
    </button>
  </div>
  <div class="cc-row" id="cc-live"><svg viewBox="0 0 24 24"><path d="M12 5v14"/><path d="m18.065 8.496-12.125 7"/><path d="m5.94 8.504 12.125 7"/></svg><span>Live subtitle</span><span class="cc-live-state" id="cc-live-state">OFF</span><button class="palette-btn" id="pal-cap-cc" title="Live caption style"><svg viewBox="0 0 24 24"><path d="M12 22a1 1 0 0 1 0-20 10 9 0 0 1 10 9 5 5 0 0 1-5 5h-2.25a1.75 1.75 0 0 0-1.4 2.8l.3.4a1.75 1.75 0 0 1-1.4 2.8z"/><circle cx="13.5" cy="6.5" r=".5"/><circle cx="17.5" cy="10.5" r=".5"/><circle cx="6.5" cy="12.5" r=".5"/><circle cx="8.5" cy="7.5" r=".5"/></svg></button></div>
</div>
<div class="pl-menu" id="plmenu" hidden>
  <div class="pl-head"><span>Playlist</span><div class="pl-head-btns"><span class="pl-sort-wrap"><button id="sort-btn" title="Sort playlist">Sort By</button><div class="pl-sort-menu" id="sort-menu" hidden><div class="om-item" id="sort-time"><span>By time</span></div><div class="om-item" id="sort-name"><span>By name</span></div><div class="om-item" id="sort-dur"><span>By duration</span></div><div class="pl-sort-sep"></div><div class="om-item" id="sort-asc"><span>Ascending</span></div><div class="om-item" id="sort-desc"><span>Descending</span></div></div></span><button id="autoplay-btn" title="Autoplay next"><svg viewBox="0 0 24 24"><path d="M16 12H3"/><path d="M16 6H3"/><path d="M10 18H3"/><path d="m16 12 5 3-5 3v-6Z"/></svg></button></div></div>
  <div id="pllist"></div>
</div>
<div class="upd-backdrop" id="updbackdrop"></div>
<div class="upd-popup" id="updpopup">
  <div class="upd-head"><span class="upd-ic"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 8v8"/><path d="m8 12 4 4 4-4"/></svg>Update Available</span><button id="updclose" title="Close">&#10005;</button></div>
  <div class="upd-body">
    <div class="upd-vers"><span id="upd-from">v0.4.0</span><svg viewBox="0 0 24 24"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg><span class="to" id="upd-to">v0.5.0</span></div>
    <div class="upd-notes" id="upd-notes"></div>
    <div class="upd-bar" id="updbar" hidden><div class="upd-bar-fill" id="upd-bar-fill"></div></div>
    <div class="upd-status" id="updstatus"></div>
  </div>
  <div class="upd-foot"><button id="upd-later">Later</button><button id="upd-install">Install</button></div>
</div>
<script>
let tbPlName='',tbVidName='',tbErr='';
const v=document.getElementById("v");
const play=document.getElementById("play");
const tl=document.getElementById("tl");
const fill=document.getElementById("fill");
const vol=document.getElementById("vol");
const cur=document.getElementById("cur");
const end=document.getElementById("end");
const spd=document.getElementById("spd");
const ctl=document.getElementById("ctl");
const speedmenu=document.getElementById("speedmenu");
const subtitleMenu=document.getElementById("subtitle-menu");
const subtitleMenuSet=document.getElementById("subtitle-menu-set");
const audioMenu=document.getElementById("audio-menu");
const loadSubtitleBtn=document.getElementById("load-subtitle-btn");
const loadAudioBtn=document.getElementById("load-audio-btn");
const subtitleFileInput=document.getElementById("subtitle-file");
const audioFileInput=document.getElementById("audio-file");
const dnd=document.getElementById("dnd");
const spdind=document.getElementById("spdind");
const fsbtn=document.getElementById("fsbtn");
const brandmark=document.querySelector(".brandmark");
const suboverlay=document.getElementById("suboverlay");
const stylepopup=document.getElementById("stylepopup");
const stylebackdrop=document.getElementById("stylebackdrop");
const liveCaptionsOverlay=document.getElementById("live-captions-overlay");
const openmenu=document.getElementById("openmenu");
const ccmenu=document.getElementById("ccmenu");
const plmenu=document.getElementById("plmenu");
const tbTitle=document.getElementById("tb-title");
const PLAY='<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
const PAUSE='<svg viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>';
const FOLDER='<svg viewBox="0 0 24 24"><path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>';
const VOLUME='<svg viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>';
const MUTE='<svg viewBox="0 0 24 24"><path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/></svg>';
const CC='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect class="ccb" x="2" y="5" width="20" height="14" rx="2"/><path class="ccg" d="M10 9.17a3 3 0 1 0 0 5.66"/><path class="ccg" d="M17 9.17a3 3 0 1 0 0 5.66"/></svg>';
const FS='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/></svg>';
const FS_EXIT='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3v3a2 2 0 0 1-2 2H3"/><path d="M21 8h-3a2 2 0 0 1-2-2V3"/><path d="M3 16h3a2 2 0 0 1 2 2v3"/><path d="M16 21v-3a2 2 0 0 1 2-2h3"/></svg>';
let speed=1,showRemaining=false,timer=null,volTimer=null,spdTimer=null,isMuted=false,prevVol=1,hudReady=false,lcVolWarnAt=0;
const LC_VOL_WARN="Live Captions uses the video's audio to generate subtitles — please keep the volume above 5%";
function clearVolWarn(){if(tbErr!==LC_VOL_WARN)return;const el=document.getElementById('pl-toast');if(el&&el.textContent===LC_VOL_WARN){el.classList.remove('show');clearTimeout(plToastTimer);}setTitleError('');clearTimeout(plTopErrTimer);}
let currentSubtitleTrack=null,currentAudioTrack=null,subtitleOffset=0,externalSubtitles=[],externalAudioTracks=[];
// Live Captions config
let liveCaptionsPosition='bottom';
let liveCaptionsMaxLines=3;
let liveCaptionsLanguage='en-US';
let liveCaptionsEnabled=false;
let lcAvailable=true, lcUnavailableReason='', lcState='closed', lcRestarting=false;
function fmt(s){if(!isFinite(s))return "00:00:00";s=Math.max(0,Math.floor(s));const h=Math.floor(s/3600),m=Math.floor((s%3600)/60),sec=s%60;return String(h).padStart(2,"0")+":"+String(m).padStart(2,"0")+":"+String(sec).padStart(2,"0");}
function upd(){if(v.duration){fill.style.width=(v.currentTime/v.duration*100)+"%";cur.textContent=fmt(v.currentTime);end.textContent=showRemaining?"-"+fmt(v.duration-v.currentTime):fmt(v.duration);}renderSubOverlay();}
function toggle(){v.paused?v.play():v.pause();}
function showCtl(){ctl.classList.remove("hide");clearTimeout(timer);if(!v.paused)timer=setTimeout(()=>ctl.classList.add("hide"),3000);}
function renderTitlebar(){
  const t=document.getElementById('tb-title'),d=document.getElementById('tb-divider');
  if(!t||!d)return;
  let html='';
  if(tbErr){html='<span class="tb-txt tb-err">'+escHtml(tbErr)+'</span>';}
  else{
    const segs=[];
    if(tbPlName)segs.push('<span class="tb-txt tb-pl">'+escHtml(tbPlName)+'</span><svg class="tb-playic" viewBox="0 0 24 24"><polygon points="7 4 20 12 7 20"/></svg>');
    if(tbVidName)segs.push('<span class="tb-txt">'+escHtml(tbVidName)+'</span>');
    html=segs.join('');
  }
  if(!html){t.innerHTML='';d.style.display='none';return;}
  d.style.display='';
  t.innerHTML='<span class="tb-inner">'+html+'</span>';
  const inner=t.firstChild;
  if(inner.scrollWidth>t.clientWidth+2){
    const secs=Math.max(6,Math.round(inner.scrollWidth/45));
    t.innerHTML='<span class="tb-marquee" style="animation-duration:'+secs+'s"><span class="tb-inner">'+html+'</span><span class="tb-inner" aria-hidden="true">'+html+'</span></span>';
  }
}
function setVideoName(n){if(n){const b=n.split(/[\\\\/]/).pop();document.title="PVP | "+(b||n);tbVidName=b||n;tbErr='';renderTitlebar();}}
function setPlaylistName(n){tbPlName=n||'';tbErr='';renderTitlebar();}
function setTitleError(msg){tbErr=msg;renderTitlebar();}
play.innerHTML=PLAY;document.getElementById("open").innerHTML=FOLDER;document.getElementById("volbtn").innerHTML=VOLUME;fsbtn.innerHTML=FS;ccbtn.innerHTML=CC;
play.onclick=toggle;v.onclick=toggle;v.onplay=()=>{play.innerHTML=PAUSE;ensureAudio();if(audioCtx&&audioCtx.state==="suspended")audioCtx.resume();};v.onpause=()=>play.innerHTML=PLAY;v.ontimeupdate=upd;
tl.onclick=e=>{const r=tl.getBoundingClientRect();if(v.duration)v.currentTime=(e.clientX-r.left)/r.width*v.duration;};
const tlPrev=document.getElementById('tl-preview'),tlPrevV=document.getElementById('tl-prev-v'),tlPrevT=document.getElementById('tl-prev-t');
let tlPrevLastSeek=0;
function syncTlPrevSrc(){if(v.src&&tlPrevV.getAttribute('src')!==v.src){tlPrevV.src=v.src;tlPrevV.pause();}}
v.addEventListener('loadstart',syncTlPrevSrc);
v.addEventListener('loadedmetadata',syncTlPrevSrc);
syncTlPrevSrc();
tl.addEventListener('mousemove',e=>{
  if(!v.duration||!isFinite(v.duration)){tlPrev.hidden=true;return;}
  const r=tl.getBoundingClientRect();
  const f=Math.max(0,Math.min(1,(e.clientX-r.left)/r.width));
  const t=f*v.duration;
  tlPrev.hidden=false;
  tlPrevT.textContent=fmt(t);
  let x=e.clientX-tlPrev.offsetWidth/2;
  x=Math.max(4,Math.min(window.innerWidth-tlPrev.offsetWidth-4,x));
  tlPrev.style.left=x+'px';
  tlPrev.style.bottom=(window.innerHeight-r.top+8)+'px';
  if(isFinite(t)&&Math.abs((tlPrevV.currentTime||0)-t)>0.25&&Date.now()-tlPrevLastSeek>120){
    tlPrevLastSeek=Date.now();
    try{tlPrevV.currentTime=t;}catch(err){}
  }
});
tl.addEventListener('mouseleave',()=>{tlPrev.hidden=true;});
end.onclick=()=>{showRemaining=!showRemaining;if(v.duration)upd();}
const SPEEDS=[0.5,0.7,1,1.3,1.5,1.6,1.7,1.8,1.9,2];
function applySpeed(val){let idx=SPEEDS.reduce((b,cur,i)=>Math.abs(cur-val)<Math.abs(SPEEDS[b]-val)?i:b,0);speed=SPEEDS[idx];v.playbackRate=speed;spd.textContent=speed!==1?speed.toFixed(1)+'x':'';const vi=document.getElementById("volind");if(hudReady){vi.style.opacity=0;clearTimeout(volTimer);}spdind.textContent=speed.toFixed(1)+'x';if(hudReady)spdind.classList.add("show");clearTimeout(spdTimer);spdTimer=setTimeout(()=>spdind.classList.remove("show"),900);renderSpeedMenu();}
function renderSpeedMenu(){
  speedmenu.innerHTML='';
  SPEEDS.forEach(s=>{
    const btn=document.createElement('button');
    btn.dataset.s=s;
    btn.textContent=s.toFixed(1)+'x';
    if(s===speed)btn.classList.add('active');
    btn.onclick=()=>{applySpeed(s);};
    speedmenu.appendChild(btn);
  });
}
let audioCtx=null,gainNode=null,sourceNode=null;
function ensureAudio(){if(audioCtx)return;try{audioCtx=new (window.AudioContext||window.webkitAudioContext)();sourceNode=audioCtx.createMediaElementSource(v);gainNode=audioCtx.createGain();sourceNode.connect(gainNode);gainNode.connect(audioCtx.destination);}catch(e){audioCtx=null;}}
function applyVolume(val){val=Math.max(0,Math.min(2,val));ensureAudio();if(gainNode)gainNode.gain.value=val;try{v.volume=Math.min(1,val);}catch(e){}vol.value=val;const pct=(val/2*100);vol.style.background="linear-gradient(to top, rgb(116,192,252) "+pct+"%, rgba(128,128,128,0.35) "+pct+"%)";const ind=document.getElementById("volind");ind.textContent=Math.round(val*100)+"%";spdind.classList.remove("show");clearTimeout(spdTimer);if(hudReady){ind.style.opacity=1;clearTimeout(volTimer);volTimer=setTimeout(()=>ind.style.opacity=0,900);}if(val>0){if(isMuted){isMuted=false;document.getElementById("volbtn").innerHTML=VOLUME;}prevVol=val;}else if(val===0){document.getElementById("volbtn").innerHTML=MUTE;isMuted=true;}document.getElementById("volbtn").classList.toggle("active",isMuted);if(liveCaptionsEnabled&&val<=0.05&&Date.now()-lcVolWarnAt>3000){lcVolWarnAt=Date.now();showPlToast(LC_VOL_WARN);}if(val>0.05)clearVolWarn();}
vol.oninput=()=>applyVolume(+vol.value);
function setMute(m){isMuted=m;if(m){prevVol=+vol.value||prevVol;applyVolume(0);document.getElementById("volbtn").innerHTML=MUTE;}else{applyVolume(prevVol||1);document.getElementById("volbtn").innerHTML=VOLUME;}}
document.getElementById("volbtn").onclick=e=>{e.stopPropagation();setMute(!isMuted);}

let isFs=false;
function setFs(on){isFs=on;fsbtn.innerHTML=on?FS_EXIT:FS;fsbtn.classList.toggle("active",on);document.body.classList.toggle("fs",on);}
fsbtn.onclick=e=>{e.stopPropagation();if(window.chrome&&window.chrome.webview)window.chrome.webview.postMessage("fullscreen");setFs(!isFs);};
document.addEventListener("fullscreenchange",()=>{fsbtn.innerHTML=document.fullscreenElement?FS_EXIT:FS;fsbtn.classList.toggle("active",!!document.fullscreenElement);});

// ===== Custom titlebar window controls =====
function postMsg(o){if(window.chrome&&window.chrome.webview)window.chrome.webview.postMessage(typeof o==="string"?o:JSON.stringify(o));}
try{postMsg("fsap:"+typeof window.showDirectoryPicker+":"+window.isSecureContext+":"+location.protocol+":"+location.origin+":"+JSON.stringify(document.getElementById("open").getBoundingClientRect()));}catch(err){}
document.getElementById("tb-min").onclick=e=>{e.stopPropagation();postMsg({type:"win-min"});};
document.getElementById("tb-max").onclick=e=>{e.stopPropagation();postMsg({type:"win-max"});};
document.getElementById("tb-close").onclick=e=>{e.stopPropagation();postMsg({type:"win-close"});};
tbTitle.ondblclick=e=>{e.stopPropagation();postMsg({type:"win-max"});};
// Manual window edge resize (native borders are gone)
let reEdge=null,reX=0,reY=0,reMoved=false,suppressNextClick=false;
const EDGE_CUR={"left":"ew-resize","right":"ew-resize","top":"ns-resize","bottom":"ns-resize","top-left":"nwse-resize","bottom-right":"nwse-resize","top-right":"nesw-resize","bottom-left":"nesw-resize"};
const MENU_SEL=".pl-menu,.cc-menu,.openmenu,.upd-popup,.upd-backdrop,#settingsmenu,.style-popup,.style-backdrop,#suboverlay,#titlebar";
function edgeAt(x,y){const W=innerWidth,H=innerHeight,T=6;let e=null;
 if(x<=T)e="left";else if(x>=W-T)e="right";
 if(y<=T)e=e?(e==="left"?"top-left":"top-right"):"top";
 else if(y>=H-T)e=e?(e==="left"?"bottom-left":"bottom-right"):"bottom";
 return e;}
document.addEventListener("mousedown",e=>{
 if(isFs||e.button!==0)return;
 if(e.target.closest&&e.target.closest(MENU_SEL))return;
 const edge=edgeAt(e.clientX,e.clientY);
 if(edge){reEdge=edge;reX=e.clientX;reY=e.clientY;reMoved=false;e.preventDefault();}
});
document.addEventListener("mousemove",e=>{
 if(reEdge){const dx=e.clientX-reX,dy=e.clientY-reY;reX=e.clientX;reY=e.clientY;
  if(dx||dy){reMoved=true;postMsg({type:"win-resize",edge:reEdge,dx:dx,dy:dy});}
  return;}
 if(isFs||document.fullscreenElement){document.body.style.cursor="";return;}
 if(e.target.closest&&e.target.closest(MENU_SEL)){document.body.style.cursor="";return;}
 document.body.style.cursor=EDGE_CUR[edgeAt(e.clientX,e.clientY)]||"";
});
document.addEventListener("mouseup",()=>{
 if(reEdge&&reMoved)suppressNextClick=true;
 reEdge=null;
});
document.addEventListener("click",e=>{if(suppressNextClick){suppressNextClick=false;e.stopPropagation();e.preventDefault();}},true);

// ===== Floating menus =====
function closeAllMenus(){openmenu.hidden=true;ccmenu.hidden=true;plmenu.hidden=true;const sm=document.getElementById('sort-menu');if(sm)sm.hidden=true;syncOpenBtn();}
function syncOpenBtn(){document.getElementById("open").classList.toggle("active",!openmenu.hidden);}
const donateModal=document.getElementById("donate-modal");
function closeDonateModal(){donateModal.classList.remove("show");}
document.getElementById("ver-donate").onclick=e=>{e.stopPropagation();settingsmenu.classList.remove("show");closeAllMenus();donateModal.classList.add("show");};
document.getElementById("tb-donate").onclick=e=>{e.stopPropagation();settingsmenu.classList.remove("show");closeAllMenus();donateModal.classList.add("show");};
document.getElementById("donate-close").onclick=e=>{e.stopPropagation();closeDonateModal();};
donateModal.addEventListener("click",e=>{if(e.target===donateModal)closeDonateModal();});
function fallbackCopy(text){const ta=document.createElement("textarea");ta.value=text;document.body.appendChild(ta);ta.select();try{document.execCommand("copy");}catch(err){}document.body.removeChild(ta);}
document.getElementById("donate-upi-id").onclick=e=>{e.stopPropagation();const id="hoxdo@ptaxis";showPlToast("UPI ID copied: "+id);try{if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(id).catch(()=>fallbackCopy(id));}else{fallbackCopy(id);}}catch(err){fallbackCopy(id);}};
function positionMenu(m,a){m.hidden=false;const r=a.getBoundingClientRect(),mr=m.getBoundingClientRect();
 let left=r.left+r.width/2-mr.width/2;
 left=Math.max(6,Math.min(left,innerWidth-mr.width-6));
 m.style.left=left+"px";
 m.style.top="auto";
 m.style.bottom=(innerHeight-r.top+8)+"px";}
document.getElementById("open").onclick=e=>{e.stopPropagation();const show=openmenu.hidden;closeAllMenus();
 if(show){positionMenu(openmenu,document.getElementById("open"));openmenu.hidden=false;syncOpenBtn();
  try{postMsg("orect:"+JSON.stringify([document.getElementById("om-video").getBoundingClientRect(),document.getElementById("om-playlist").getBoundingClientRect()]));}catch(err){}}};
document.getElementById("om-video").onclick=e=>{e.stopPropagation();openmenu.hidden=true;syncOpenBtn();document.getElementById("f").click();};
document.getElementById("om-playlist").onclick=e=>{e.stopPropagation();openmenu.hidden=true;syncOpenBtn();pickFolderPlaylist();};
ccbtn.onclick=e=>{e.stopPropagation();const show=ccmenu.hidden;closeAllMenus();
 if(show){renderSubtitleMenu();ccmenu.hidden=false;positionMenu(ccmenu,ccbtn);updateCcActive();}};
document.getElementById("cc-local").onclick=e=>{e.stopPropagation();
 const sl=document.getElementById("cc-sublist");
 if(sl.hidden){renderSubtitleMenu();sl.hidden=false;}else{sl.hidden=true;}};
document.getElementById("cc-live").onclick=e=>{e.stopPropagation();toggleLiveCaptions();ccmenu.hidden=true;};
function updateCcActive(){ccbtn.classList.toggle("active",!!(liveCaptionsEnabled||!!currentSubtitleTrack));}
const tbPlaylist=document.getElementById("tb-playlist");
tbPlaylist.onclick=e=>{e.stopPropagation();const show=plmenu.hidden;closeAllMenus();
 if(show){renderPlList();plmenu.hidden=false;}};

// Settings menu - click to toggle
brandmark.onclick=e=>{e.stopPropagation();closeAllMenus();settingsmenu.classList.toggle("show");};

// Close menus when clicking outside
document.addEventListener("click",e=>{
  if(!settingsmenu.contains(e.target)&&!brandmark.contains(e.target)){
    settingsmenu.classList.remove("show");
  }
  closeAllMenus();
});

// Subtitle handling
function parseSRT(content){const tracks=[];const blocks=content.trim().split(/\n\s*\n/);blocks.forEach((block,i)=>{const lines=block.trim().split('\n');if(lines.length>=3){const timeMatch=lines[1].match(/(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})/);if(timeMatch){const start=parseTime(timeMatch[1]);const end=parseTime(timeMatch[2]);const text=lines.slice(2).join('\n');tracks.push({index:i,start,end,text});}}});return tracks;}
function parseVTT(content){const tracks=[];const lines=content.split('\n');let i=0;while(i<lines.length){const line=lines[i].trim();const timeMatch=line.match(/(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})/);if(timeMatch){const start=parseTime(timeMatch[1].replace('.',','));const end=parseTime(timeMatch[2].replace('.',','));i++;let text='';while(i<lines.length&&lines[i].trim()){text+=lines[i]+'\n';i++;}tracks.push({index:tracks.length,start,end,text:text.trim()});}i++;}return tracks;}
function parseTime(t){const parts=t.split(/[:,]/);return(+parts[0])*3600+(+parts[1])*60+(+parts[2])+(+parts[3])/1000;}
function formatSRT(tracks){return tracks.map((t,i)=>`${i+1}\n${fmtTime(t.start)} --> ${fmtTime(t.end)}\n${t.text}\n`).join('\n');}
function fmtTime(s){const h=Math.floor(s/3600).toString().padStart(2,'0');const m=Math.floor((s%3600)/60).toString().padStart(2,'0');const sec=Math.floor(s%60).toString().padStart(2,'0');const ms=Math.floor((s%1)*1000).toString().padStart(3,'0');return `${h}:${m}:${sec},${ms}`;}

function renderSubtitleMenu(){
  renderSubtitleMenuInto(subtitleMenu,'cc');
  renderSubtitleMenuInto(subtitleMenuSet,'set');
  updateCcActive();
}
function renderSubtitleMenuInto(subtitleMenu,where){
  subtitleMenu.innerHTML='';
  let hasTracks=false;
  // Subtitles detected in the loaded playlist folder (associated with current video)
  playlist.forEach(it=>{
    if(it.subFile&&!externalSubtitles.some(s=>s.name===it.subFile.name)){
      hasTracks=true;
      const item=document.createElement('div');
      item.className='track-item';
      item.innerHTML=`<span class="track-lang">Sub</span><span class="track-label">${escHtml(it.subFile.name)}</span><span class="track-default">Detected</span>`;
      item.onclick=()=>{loadExternalSubtitle(it.subFile);if(where==='set')settingsmenu.classList.remove("show");else ccmenu.hidden=true;};
      subtitleMenu.appendChild(item);
    }
  });
  // Internal text tracks
  if(v.textTracks&&v.textTracks.length>0){
    hasTracks=true;
    for(let i=0;i<v.textTracks.length;i++){
      const track=v.textTracks[i];
      const item=document.createElement('div');
      item.className='track-item'+(currentSubtitleTrack===track?' active':'');
      item.innerHTML=`<span class="track-lang">${track.language||'Und'}</span><span class="track-label">${track.label||'Track '+(i+1)}</span>${track.default?'<span class="track-default">Default</span>':''}`;
      item.onclick=()=>{selectSubtitleTrack(i);if(where==='set')settingsmenu.classList.remove("show");else ccmenu.hidden=true;};
      subtitleMenu.appendChild(item);
    }
  }
  // External subtitles
  externalSubtitles.forEach((sub,idx)=>{
    hasTracks=true;
    const item=document.createElement('div');
    item.className='track-item'+(currentSubtitleTrack===sub?' active':'');
    item.innerHTML=`<span class="track-lang">${sub.lang||'Ext'}</span><span class="track-label">${escHtml(sub.name||'External '+ (idx+1))}</span><span class="track-default">External</span>`;
    item.onclick=()=>{selectExternalSubtitle(sub);if(where==='set')settingsmenu.classList.remove("show");else ccmenu.hidden=true;};
    subtitleMenu.appendChild(item);
  });
  if(!hasTracks){
    subtitleMenu.innerHTML='<div class="no-tracks">No subtitle tracks available</div>';
  }
  // Add sync controls if external subtitle selected
  if(currentSubtitleTrack&&externalSubtitles.includes(currentSubtitleTrack)){
    addSubtitleSyncControls(subtitleMenu);
  }
}

function addSubtitleSyncControls(subtitleMenu){
  const existing=subtitleMenu.querySelector('.subtitle-sync');
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
  const offsetInput=syncDiv.querySelector('#subtitle-offset');
  syncDiv.querySelector('#sync-subtitle-btn').onclick=()=>{
    subtitleOffset=parseFloat(offsetInput.value)||0;
    applySubtitleSync();
  };
  syncDiv.querySelector('#reset-subtitle-btn').onclick=()=>{
    subtitleOffset=0;
    offsetInput.value=0;
    applySubtitleSync();
  };
}

function applySubtitleSync(){
  if(currentSubtitleTrack&&externalSubtitles.includes(currentSubtitleTrack)){
    currentSubtitleTrack.offset=subtitleOffset;
    renderExternalSubtitles();
  }
}

function renderExternalSubtitles(){
  for(let i=v.textTracks.length-1;i>=0;i--){
    const track=v.textTracks[i];
    if(track.kind==='subtitles'&&track.label&&track.label.startsWith('External:')){
      v.removeTextTrack(track);
    }
  }
  if(currentSubtitleTrack&&externalSubtitles.includes(currentSubtitleTrack)){
    const track=v.addTextTrack('subtitles',currentSubtitleTrack.name,'External:'+currentSubtitleTrack.lang);
    track.mode='hidden';
    currentSubtitleTrack.cues.forEach(cue=>{
      track.addCue(new VTTCue(cue.start+subtitleOffset,cue.end+subtitleOffset,cue.text));
    });
  }
}

function selectSubtitleTrack(index){
  for(let i=0;i<v.textTracks.length;i++){
    v.textTracks[i].mode='hidden';
  }
  currentSubtitleTrack=v.textTracks[index]||null;
  subtitleOffset=0;
  renderSubtitleMenu();
  renderSubOverlay();
}

function selectExternalSubtitle(sub){
  currentSubtitleTrack=sub;
  renderExternalSubtitles();
  renderSubtitleMenu();
  renderSubOverlay();
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
document.getElementById("load-subtitle-btn-set").onclick=()=>subtitleFileInput.click();
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
      item.onclick=()=>{selectAudioTrack(i);settingsmenu.classList.remove("show");};
      audioMenu.appendChild(item);
    }
  }
  externalAudioTracks.forEach((aud,idx)=>{
    hasTracks=true;
    const item=document.createElement('div');
    item.className='track-item'+(currentAudioTrack===aud?' active':'');
    item.innerHTML=`<span class="track-lang">${aud.lang||'Ext'}</span><span class="track-label">${aud.name||'External '+ (idx+1)}</span><span class="track-default">External</span>`;
    item.onclick=()=>{selectExternalAudio(aud);settingsmenu.classList.remove("show");};
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
  renderSpeedMenu();
});

// Also update when text tracks change
v.addEventListener('loadstart',()=>{
  externalSubtitles=[];
  externalAudioTracks=[];
  currentSubtitleTrack=null;
  currentAudioTrack=null;
  subtitleOffset=0;
  renderSubOverlay();
  pvpCaptionClear();
});
v.addEventListener('seeked',()=>{renderSubOverlay();});

function pvpCaptionInit(d){
  lcAvailable=!!d.ok;
  lcUnavailableReason=d.m||'';
  if(d.lang){liveCaptionsLanguage=d.lang;}
  requestLcModels();
  const row=document.getElementById('cc-live');
  if(row){
    row.classList.toggle('disabled',!lcAvailable);
    if(!lcAvailable)row.title=lcUnavailableReason||'Live Captions is not available on this system';
  }
  const ltb=document.getElementById('live-captions-toggle');
  if(ltb){ltb.disabled=!lcAvailable;ltb.title=lcAvailable?'':(lcUnavailableReason||'Live Captions is not available on this system');}
  if(!lcAvailable&&liveCaptionsEnabled){liveCaptionsEnabled=false;lcSetUi(false);updateCcActive();}
  if(d.run&&!liveCaptionsEnabled){liveCaptionsEnabled=true;lcSetUi(true);updateCcActive();}
}
function lcSetUi(on){
  const st=document.getElementById('cc-live-state');
  if(st){st.textContent=on?'ON':'OFF';st.classList.toggle('on',on);}
  liveCaptionsOverlay.classList.toggle('hidden',!on);
  if(!on)pvpCaptionClear();
}
function pvpCaptionState(d){
  if(!d)return;
  lcState=d.s;
  const st=document.getElementById('cc-live-state');
  if(d.s==='unsupported'){
    lcAvailable=false;liveCaptionsEnabled=false;lcSetUi(false);updateCcActive();
    if(d.m)showPlToast(d.m);
    return;
  }
  if(d.s==='error'){
    if(d.m)showPlToast(d.m);
    if(st&&liveCaptionsEnabled){st.textContent='ERR';st.classList.add('on');}
    return;
  }
  if(d.s==='closed'){
    if(lcRestarting){
      lcRestarting=false;
      if(st&&liveCaptionsEnabled){st.textContent='ON';st.classList.add('on');}
      return;
    }
    liveCaptionsEnabled=false;lcSetUi(false);updateCcActive();
    return;
  }
  if(d.s==='setup'){
    if(st&&liveCaptionsEnabled){st.textContent='ON';st.classList.add('on');}
    return;
  }
  if(d.s==='ready'){
    if(st&&liveCaptionsEnabled){st.textContent='ON';st.classList.add('on');}
    return;
  }
}
function pvpCaptionUpdate(d){
  if(!liveCaptionsEnabled||!d||!d.t)return;
  if(styleOpen&&styleTarget==='cap')return; // sample line shown while editing
  let lines=d.t.split('\n');
  if(lines.length>liveCaptionsMaxLines)lines=lines.slice(-liveCaptionsMaxLines);
  const txt=lines.join('\n');
  let line=liveCaptionsOverlay.firstElementChild;
  if(!line||!line.classList.contains('live-caption-line')){
    liveCaptionsOverlay.textContent='';
    line=document.createElement('div');
    line.className='live-caption-line enter';
    liveCaptionsOverlay.appendChild(line);
  }
  let clip=line.firstElementChild;
  if(!clip||!clip.classList.contains('lc-clip')){
    line.textContent='';
    clip=document.createElement('div');
    clip.className='lc-clip';
    line.appendChild(clip);
  }
  let inner=clip.firstElementChild;
  if(!inner||!inner.classList.contains('lc-inner')){
    clip.textContent='';
    inner=document.createElement('span');
    inner.className='lc-inner';
    clip.appendChild(inner);
  }
  if(inner.textContent!==txt)inner.textContent=txt;
}
function pvpCaptionClear(){liveCaptionsOverlay.textContent='';}
function toggleLiveCaptions(){
  if(liveCaptionsEnabled){
    liveCaptionsEnabled=false;
    postMsg({type:'live-captions-disable'});
    lcSetUi(false);
  }else{
    if(!lcAvailable){showPlToast(lcUnavailableReason||'Live Captions is not available on this system');return;}
    liveCaptionsEnabled=true;
    if(+vol.value<=0.05){lcVolWarnAt=Date.now();showPlToast(LC_VOL_WARN);}
    const st=document.getElementById('cc-live-state');
    if(st){st.textContent='ON';st.classList.add('on');}
    liveCaptionsOverlay.classList.remove('top','center','bottom','mid');
    liveCaptionsOverlay.classList.add(liveCaptionsPosition);
    liveCaptionsOverlay.classList.remove('hidden');
    pvpCaptionClear();
    postMsg({type:'live-captions-enable'});
  }
  updateCcActive();
}

// Live Captions Settings Event Listeners
const LC_LANGS=[['en-US','English (US)'],['en-IN','English (India)'],['en-GB','English (UK)'],['es-ES','Spanish'],['fr-FR','French'],['de-DE','German'],['it-IT','Italian'],['ja-JP','Japanese'],['ko-KR','Korean'],['zh-CN','Chinese (Simplified)'],['hi-IN','Hindi']];
let lcModelsInstalled=[],lcModelsBusy=null,lcModelPollTimer=null;
function requestLcModels(){postMsg({type:'live-captions-models'});}
function pvpCaptionModels(d){
  lcModelsInstalled=(d&&d.installed)||[];
  if(d&&d.active)liveCaptionsLanguage=d.active;
  if(lcModelsBusy){
    const want=lcModelsBusy.op==='install';
    if(lcModelsInstalled.includes(lcModelsBusy.lang)===want){
      lcModelsBusy=null;
      if(lcModelPollTimer){clearInterval(lcModelPollTimer);lcModelPollTimer=null;}
      showPlToast(lcModelsBusyLastOp==='delete'?'Language model deleted':'Language model installed');
    }
  }
  renderLcModels();
}
let lcModelsBusyLastOp=null;
function lcModelStartPoll(){
  if(lcModelPollTimer)clearInterval(lcModelPollTimer);
  let tries=0;
  lcModelPollTimer=setInterval(()=>{
    requestLcModels();
    if(++tries>150){
      clearInterval(lcModelPollTimer);lcModelPollTimer=null;
      if(lcModelsBusy){showPlToast('Could not update the language model — check Windows Settings > Language');lcModelsBusy=null;renderLcModels();}
    }
  },2000);
}
function renderLcModels(){
  const box=document.getElementById('lc-models');
  const hint=document.getElementById('lc-models-hint');
  if(!box)return;
  if(hint)hint.textContent=lcModelsInstalled.length+' installed \u00b7 in use: '+liveCaptionsLanguage;
  const tname=document.getElementById('lc-lang-trigger-name');
  if(tname)tname.textContent=(LC_LANGS.find(p=>p[0]===liveCaptionsLanguage)||[])[1]||liveCaptionsLanguage;
  box.innerHTML='';
  LC_LANGS.forEach(pair=>{
    const tag=pair[0],name=pair[1];
    const inst=lcModelsInstalled.includes(tag);
    const active=tag===liveCaptionsLanguage;
    const row=document.createElement('div');
    row.className='lc-model'+(active?' active':'')+(inst?'':' missing');
    let meta='';
    if(lcModelsBusy&&lcModelsBusy.lang===tag){
      meta='<span class="lc-model-busy">'+(lcModelsBusy.op==='install'?'Downloading\u2026':'Deleting\u2026')+'</span>';
    }else if(active){
      meta='<span class="lc-model-badge">IN USE</span>';
    }else if(inst){
      meta='<button class="lc-model-use" data-tag="'+tag+'">Use</button><button class="lc-model-del" data-tag="'+tag+'" title="Delete language model"><svg viewBox="0 0 24 24"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v5"/><path d="M14 11v5"/></svg></button>';
    }else{
      meta='<button class="lc-model-dl" data-tag="'+tag+'">Download</button>';
    }
    row.innerHTML='<span class="lc-model-name">'+name+'</span>'+meta;
    box.appendChild(row);
  });
  box.querySelectorAll('.lc-model-use').forEach(b=>b.onclick=()=>{
    liveCaptionsLanguage=b.dataset.tag;
    if(liveCaptionsEnabled){
      lcRestarting=true;
      const st=document.getElementById('cc-live-state');
      if(st){st.textContent='ON';st.classList.add('on');}
    }
    postMsg({type:'live-captions-language',lang:b.dataset.tag});
    requestLcModels();
  });
  box.querySelectorAll('.lc-model-dl').forEach(b=>b.onclick=()=>{
    if(lcModelsBusy)return;
    lcModelsBusyLastOp='install';
    lcModelsBusy={op:'install',lang:b.dataset.tag};
    renderLcModels();
    postMsg({type:'live-captions-model-install',lang:b.dataset.tag});
    lcModelStartPoll();
  });
  box.querySelectorAll('.lc-model-del').forEach(b=>b.onclick=()=>{
    if(lcModelsBusy)return;
    lcModelsBusyLastOp='delete';
    lcModelsBusy={op:'delete',lang:b.dataset.tag};
    renderLcModels();
    postMsg({type:'live-captions-model-delete',lang:b.dataset.tag});
    lcModelStartPoll();
  });
}
requestLcModels();

function setLcLangDd(open){
  const dd=document.getElementById('lc-lang-dd');
  const trig=document.getElementById('lc-lang-trigger');
  if(!dd||!trig)return;
  dd.hidden=!open;
  trig.setAttribute('aria-expanded',open?'true':'false');
}
document.getElementById('lc-lang-trigger')?.addEventListener('click',()=>{
  const dd=document.getElementById('lc-lang-dd');
  setLcLangDd(!!dd&&dd.hidden);
});
document.addEventListener('click',e=>{
  const dd=document.getElementById('lc-lang-dd');
  const trig=document.getElementById('lc-lang-trigger');
  if(!dd||dd.hidden)return;
  if(dd.contains(e.target)||(trig&&trig.contains(e.target)))return;
  setLcLangDd(false);
});

document.getElementById('live-captions-position')?.addEventListener('change', e=>{
  liveCaptionsPosition=e.target.value;
  if(liveCaptionsEnabled){
    liveCaptionsOverlay.classList.remove('top', 'center', 'bottom', 'mid');
    liveCaptionsOverlay.classList.add(liveCaptionsPosition);
  }
});

function setMaxLines(n, from){
  n=Math.round(Number(n));
  if(!isFinite(n)||n<1)n=1;
  if(n>5)n=5;
  liveCaptionsMaxLines=n;
  const r=document.getElementById('live-captions-max-lines');
  const num=document.getElementById('live-captions-max-lines-num');
  if(from!=='range'&&r)r.value=n;
  if(from!=='num'&&num)num.value=n;
  liveCaptionsOverlay.style.setProperty('--lc-lines', n);
}
document.getElementById('live-captions-max-lines')?.addEventListener('input', e=>setMaxLines(e.target.value,'range'));
document.getElementById('live-captions-max-lines-num')?.addEventListener('input', e=>{
  if(e.target.value!=='')setMaxLines(e.target.value,'num');
});
document.getElementById('live-captions-max-lines-num')?.addEventListener('change', e=>{
  e.target.value=liveCaptionsMaxLines;
});

document.getElementById('live-captions-toggle')?.addEventListener('click',()=>toggleLiveCaptions());
(function(){
  const st=document.getElementById('cc-live-state');
  const btn=document.getElementById('live-captions-toggle');
  if(!st||!btn)return;
  function sync(){
    // The settings toggle always reads ON/OFF — transient states ("…", "ERR")
    // belong to the menu badge, not to a switch.
    const on=st.classList.contains('on');
    btn.textContent=on?'ON':'OFF';
    btn.classList.toggle('on',on);
    btn.setAttribute('aria-pressed',on?'true':'false');
  }
  new MutationObserver(sync).observe(st,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['class']});
  sync();
})();

// ===== Subtitle style editor =====
const SUBSTYLE_DEFAULT={family:'Segoe UI',weight:'600',size:18,color:'#ffffff',bg:'#000000',bgOpacity:70,shadow:2,shadowColor:'#000000',boxShadow:0,boxShadowColor:'#000000',outline:1,outlineColor:'#000000'};
let subStyle=Object.assign({},SUBSTYLE_DEFAULT);
try{const saved=JSON.parse(localStorage.getItem('pvp-substyle')||'null');if(saved)Object.assign(subStyle,saved);}catch(e){}
// Live captions have their own look (CSS vars on the overlay) so the palette
// in the Live Captions section never touches local subtitles and vice versa.
const LCSTYLE_DEFAULT={family:'system-ui',weight:'400',size:16,color:'#74c0fc',bg:'#121212',bgOpacity:85,shadow:0,shadowColor:'#000000',boxShadow:2,boxShadowColor:'#000000',outline:0,outlineColor:'#000000'};
let lcStyle=Object.assign({},LCSTYLE_DEFAULT);
try{const s=JSON.parse(localStorage.getItem('pvp-lcstyle')||'null');if(s)Object.assign(lcStyle,s);}catch(e){}
let styleTarget='sub';
function saveLcStyle(){try{localStorage.setItem('pvp-lcstyle',JSON.stringify(lcStyle));}catch(e){}}
function curStyle(){return styleTarget==='cap'?lcStyle:subStyle;}
function applyCurStyle(){if(styleTarget==='cap')applyLcStyle();else applySubStyle();}
function saveCurStyle(){if(styleTarget==='cap')saveLcStyle();else saveSubStyle();}
let styleOpen=false;
function saveSubStyle(){try{localStorage.setItem('pvp-substyle',JSON.stringify(subStyle));}catch(e){}}
function hexToRgba(hex,a){
  hex=(hex||'#000000').replace('#','');
  if(hex.length===3)hex=hex.replace(/./g,c=>c+c);
  const n=parseInt(hex,16);
  return 'rgba('+((n>>16)&255)+','+((n>>8)&255)+','+(n&255)+','+a+')';
}
function cssFamily(f){return /^[a-z-]+$/i.test(f)?f:'"'+f+'"';}
function applySubStyle(){
  const s=subStyle,st=suboverlay.style;
  st.fontFamily=cssFamily(s.family);
  st.fontWeight=s.weight;
  st.fontSize=s.size+'px';
  st.color=s.color;
  st.setProperty('--sub-bg',hexToRgba(s.bg,s.bgOpacity/100));
  const sh=[];
  if(s.shadow>0)sh.push('0 '+s.shadow+'px '+(s.shadow*2)+'px '+hexToRgba(s.shadowColor,.9));
  if(s.outline>0){const o=s.outline;
    sh.push(o+'px 0 0 '+s.outlineColor,-o+'px 0 0 '+s.outlineColor,'0 '+o+'px 0 '+s.outlineColor,'0 -'+o+'px 0 '+s.outlineColor,o+'px '+o+'px 0 '+s.outlineColor,-o+'px '+o+'px 0 '+s.outlineColor,o+'px -'+o+'px 0 '+s.outlineColor,-o+'px -'+o+'px 0 '+s.outlineColor);}
  st.textShadow=sh.length?sh.join(','):'none';
  st.setProperty('--sub-boxshadow',s.boxShadow>0?'0 '+s.boxShadow+'px '+(s.boxShadow*2)+'px '+hexToRgba(s.boxShadowColor,.85):'none');
}
function applyLcStyle(){
  const s=lcStyle,st=liveCaptionsOverlay.style;
  st.setProperty('--lc-family',cssFamily(s.family));
  st.setProperty('--lc-weight',s.weight);
  st.setProperty('--lc-size',s.size+'px');
  st.setProperty('--lc-fg',s.color);
  st.setProperty('--lc-bg',hexToRgba(s.bg,s.bgOpacity/100));
  const sh=[];
  if(s.shadow>0)sh.push('0 '+s.shadow+'px '+(s.shadow*2)+'px '+hexToRgba(s.shadowColor,.9));
  if(s.outline>0){const o=s.outline;
    sh.push(o+'px 0 0 '+s.outlineColor,-o+'px 0 0 '+s.outlineColor,'0 '+o+'px 0 '+s.outlineColor,'0 -'+o+'px 0 '+s.outlineColor,o+'px '+o+'px 0 '+s.outlineColor,-o+'px '+o+'px 0 '+s.outlineColor,o+'px -'+o+'px 0 '+s.outlineColor,-o+'px -'+o+'px 0 '+s.outlineColor);}
  st.setProperty('--lc-shadow',sh.length?sh.join(','):'none');
  st.setProperty('--lc-boxshadow',s.boxShadow>0?'0 '+s.boxShadow+'px '+(s.boxShadow*2)+'px '+hexToRgba(s.boxShadowColor,.85):'none');
}
function renderLcStyleSample(){
  if(!styleOpen||styleTarget!=='cap')return;
  let line=liveCaptionsOverlay.firstElementChild;
  if(!line||!line.classList.contains('live-caption-line')){
    liveCaptionsOverlay.textContent='';
    line=document.createElement('div');
    line.className='live-caption-line enter';
    liveCaptionsOverlay.appendChild(line);
  }
  line.innerHTML='<div class="lc-clip"><span class="lc-inner">Sample live caption \u2014 The quick brown fox jumps over the lazy dog</span></div>';
}
function escHtml(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function renderSubOverlay(){
  if(!suboverlay)return;
  if(styleOpen&&styleTarget==='sub'){
    suboverlay.innerHTML='<div class="sub-line">Sample subtitle &mdash; The quick brown fox jumps over the lazy dog</div>';
    suboverlay.classList.add('show');
    suboverlay.dataset.sh='';
    return;
  }
  if(!currentSubtitleTrack){suboverlay.innerHTML='';suboverlay.classList.remove('show');suboverlay.dataset.sh='';return;}
  const lines=[];
  if(externalSubtitles.includes(currentSubtitleTrack)){
    const sub=currentSubtitleTrack,t=v.currentTime-subtitleOffset;
    sub.cues.forEach(c=>{if(t>=c.start&&t<c.end)lines.push(c.text);});
  }else if(currentSubtitleTrack.activeCues){
    for(let i=0;i<currentSubtitleTrack.activeCues.length;i++)lines.push(currentSubtitleTrack.activeCues[i].text);
  }
  if(!lines.length){
    if(!suboverlay.childElementCount)suboverlay.classList.remove('show');
    return;
  }
  const html=lines.map(t=>'<div class="sub-line">'+escHtml(t)+'</div>').join('');
  if(suboverlay.dataset.sh!==html){suboverlay.innerHTML=html;suboverlay.dataset.sh=html;}
  suboverlay.classList.add('show');
}
const FONT_LIST=['Segoe UI','Arial','Arial Black','Calibri','Cambria','Candara','Comic Sans MS','Consolas','Constantia','Courier New','Franklin Gothic Medium','Georgia','Impact','Leelawadee UI','Malgun Gothic','Microsoft JhengHei','Microsoft YaHei','Palatino Linotype','Rockwell','Segoe Print','Segoe Script','SimSun','Tahoma','Times New Roman','Trebuchet MS','Verdana','system-ui','sans-serif','serif','monospace'];
function fillFamilySelect(){
  const sel=document.getElementById('st-family');
  sel.innerHTML='';
  FONT_LIST.forEach(f=>{const o=document.createElement('option');o.value=f;o.textContent=f;sel.appendChild(o);});
}
function mergeSystemFonts(names){
  const sel=document.getElementById('st-family');
  const have=new Set(Array.from(sel.options).map(o=>o.value));
  const frag=document.createDocumentFragment();
  names.forEach(n=>{if(!have.has(n)){const o=document.createElement('option');o.value=n;o.textContent=n;frag.appendChild(o);}});
  sel.appendChild(frag);
}
function ensureFamilyOption(){
  const sel=document.getElementById('st-family');
  if(!Array.from(sel.options).some(o=>o.value===curStyle().family)){
    const o=document.createElement('option');o.value=curStyle().family;o.textContent=curStyle().family;sel.appendChild(o);
  }
  sel.value=curStyle().family;
}
async function loadSystemFonts(){
  try{
    if(window.queryLocalFonts){
      const fonts=await window.queryLocalFonts();
      const names=[...new Set(fonts.map(f=>f.family))].sort((a,b)=>a.localeCompare(b));
      mergeSystemFonts(names);
      ensureFamilyOption();
    }
  }catch(e){/* permission denied or unsupported: keep curated list */}
}
function syncStyleControls(){
  ensureFamilyOption();
  const s=curStyle();
  document.getElementById('st-weight').value=s.weight;
  document.getElementById('st-size').value=s.size;
  document.getElementById('st-size-v').textContent=s.size+'px';
  document.getElementById('st-color').value=s.color;
  document.getElementById('st-bg').value=s.bg;
  document.getElementById('st-bgop').value=s.bgOpacity;
  document.getElementById('st-bgop-v').textContent=s.bgOpacity+'%';
  document.getElementById('st-shadow').value=s.shadow;
  document.getElementById('st-shadow-v').textContent=s.shadow;
  document.getElementById('st-shcolor').value=s.shadowColor;
  document.getElementById('st-boxshadow').value=s.boxShadow;
  document.getElementById('st-boxshadow-v').textContent=s.boxShadow;
  document.getElementById('st-boxshcolor').value=s.boxShadowColor;
  document.getElementById('st-outline').value=s.outline;
  document.getElementById('st-outline-v').textContent=s.outline;
  document.getElementById('st-olcolor').value=s.outlineColor;
}
function openStylePopup(target){
  styleTarget=(target==='cap')?'cap':'sub';
  stylepopup.querySelector('.style-head span').textContent=styleTarget==='cap'?'Live Caption Style':'Subtitle Style';
  styleOpen=true;
  settingsmenu.classList.remove('show');
  closeAllMenus();
  stylepopup.classList.add('show');
  stylebackdrop.classList.add('show');
  syncStyleControls();
  applyCurStyle();
  renderSubOverlay();
  renderLcStyleSample();
  loadSystemFonts();
}
function closeStylePopup(){
  styleOpen=false;
  stylepopup.classList.remove('show');
  stylebackdrop.classList.remove('show');
  if(styleTarget==='cap')pvpCaptionClear();
  renderSubOverlay();
}
function bindStyleCtl(id,key,parse,spanId,suffix){
  const el=document.getElementById(id);
  el.addEventListener('input',()=>{
    curStyle()[key]=parse(el.value);
    if(spanId)document.getElementById(spanId).textContent=curStyle()[key]+(suffix||'');
    applyCurStyle();saveCurStyle();renderLcStyleSample();
  });
}
fillFamilySelect();
bindStyleCtl('st-family','family',v=>v);
bindStyleCtl('st-weight','weight',v=>v);
bindStyleCtl('st-size','size',v=>parseInt(v),'st-size-v','px');
bindStyleCtl('st-color','color',v=>v);
bindStyleCtl('st-bg','bg',v=>v);
bindStyleCtl('st-bgop','bgOpacity',v=>parseInt(v),'st-bgop-v','%');
bindStyleCtl('st-shadow','shadow',v=>parseInt(v),'st-shadow-v','');
bindStyleCtl('st-shcolor','shadowColor',v=>v);
bindStyleCtl('st-boxshadow','boxShadow',v=>parseInt(v),'st-boxshadow-v','');
bindStyleCtl('st-boxshcolor','boxShadowColor',v=>v);
bindStyleCtl('st-outline','outline',v=>parseInt(v),'st-outline-v','');
bindStyleCtl('st-olcolor','outlineColor',v=>v);
document.querySelectorAll('.palette-btn').forEach(b=>b.onclick=e=>{e.stopPropagation();openStylePopup(b.id.startsWith('pal-cap')?'cap':'sub');});
stylebackdrop.onclick=closeStylePopup;
document.getElementById('styleclose').onclick=closeStylePopup;
document.getElementById('st-done').onclick=closeStylePopup;
document.getElementById('st-reset').onclick=()=>{
  if(styleTarget==='cap')lcStyle=Object.assign({},LCSTYLE_DEFAULT);
  else subStyle=Object.assign({},SUBSTYLE_DEFAULT);
  syncStyleControls();applyCurStyle();saveCurStyle();renderSubOverlay();renderLcStyleSample();
};
document.addEventListener('keydown',e=>{if(e.key==='Escape'){setLcLangDd(false);if(styleOpen){closeStylePopup();}else{closeUpdatePopup();closeAllMenus();closeDonateModal();}}});
applySubStyle();
applyLcStyle();

document.getElementById('lc-info')?.addEventListener('click',e=>{
  e.stopPropagation();
  const p=document.getElementById('lc-info-panel');
  if(p)p.hidden=!p.hidden;
});

// ===== Playlist (folder) support =====
const VIDEO_EXT=['mp4','m4v','mkv','webm','mov','qt','avi','divx','xvid','wmv','asf','wtv','flv','f4v','3gp','3g2','3gpp','ts','m2ts','mts','m2t','mpg','mpeg','mpe','m2v','m2p','vob','vro','ogv','ogg','ogx','rm','rmvb','mxf','mp4v','tod','rec','dvr-ms'];
const SUB_EXT=['srt','vtt'];
const NON_MEDIA_EXT=['srt','vtt','ass','ssa','sub','idx','txt','nfo','md','json','xml','ini','db','log','jpg','jpeg','png','gif','webp','bmp','ico','svg','pdf','zip','rar','7z','iso','exe','dll','lnk','part','tmp','crdownload','mp3','m4a','flac','wav','wma','aac','opus','ape','ac3','eac3','amr','mka','alac'];
const playlist=[];
let plIdx=-1,dragFrom=-1;
let autoplay=localStorage.getItem('pvp-autoplay')!=='0';
const autoplayBtn=document.getElementById('autoplay-btn');
function syncAutoplay(){autoplayBtn.classList.toggle('on',autoplay);}
autoplayBtn.onclick=e=>{e.stopPropagation();autoplay=!autoplay;try{localStorage.setItem('pvp-autoplay',autoplay?'1':'0');}catch(err){}syncAutoplay();};
let plSortBy=localStorage.getItem('pvp-sortby')||'name';
let plSortDir=localStorage.getItem('pvp-sortdir')||'asc';
let plOrig=[];
const sortBtn=document.getElementById('sort-btn');
const sortMenu=document.getElementById('sort-menu');
function syncSortBtn(){
  document.getElementById('sort-time').classList.toggle('active',plSortBy==='time');
  document.getElementById('sort-name').classList.toggle('active',plSortBy==='name');
  document.getElementById('sort-dur').classList.toggle('active',plSortBy==='dur');
  document.getElementById('sort-asc').classList.toggle('active',plSortDir==='asc');
  document.getElementById('sort-desc').classList.toggle('active',plSortDir==='desc');
}
let plToastTimer=null,plTopErrTimer=null;
function showPlToast(msg){const el=document.getElementById('pl-toast');el.textContent=msg;el.classList.add('show');setTitleError(msg);clearTimeout(plToastTimer);plToastTimer=setTimeout(()=>{el.classList.remove('show');},2000);clearTimeout(plTopErrTimer);plTopErrTimer=setTimeout(()=>{if(tbErr===msg)setTitleError('');},60000);}
function getPlDur(it){return new Promise(res=>{if(it.dur!=null){res(it.dur);return;}const el=document.createElement('video');el.preload='metadata';el.onloadedmetadata=()=>{it.dur=isFinite(el.duration)?el.duration:0;el.removeAttribute('src');el.load();res(it.dur);};el.onerror=()=>{it.dur=-1;res(-1);};el.src=it.url;});}
async function applyPlSort(){
  const cur=playlist[plIdx];
  const dir=plSortDir==='asc'?1:-1;
  const nameCmp=(a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true,sensitivity:'base'});
  if(plSortBy==='name')playlist.sort((a,b)=>nameCmp(a,b)*dir);
  else if(plSortBy==='time')playlist.sort((a,b)=>{const ta=(a.file&&a.file.lastModified)||0,tb=(b.file&&b.file.lastModified)||0;return (ta-tb)*dir||nameCmp(a,b);});
  else if(plSortBy==='dur'){await Promise.all(playlist.map(getPlDur));playlist.sort((a,b)=>{const d=x=>(x.dur==null||x.dur<0)?Infinity:x.dur;return (d(a)-d(b))*dir||nameCmp(a,b);});}
  plIdx=cur?playlist.indexOf(cur):-1;
  renderPlList();syncSortBtn();
}
sortBtn.onclick=e=>{e.stopPropagation();sortMenu.hidden=!sortMenu.hidden;};
function closeSortMenu(){sortMenu.hidden=true;}
document.getElementById('sort-time').onclick=e=>{e.stopPropagation();plSortBy='time';try{localStorage.setItem('pvp-sortby',plSortBy);}catch(err){}closeSortMenu();applyPlSort();};
document.getElementById('sort-name').onclick=e=>{e.stopPropagation();plSortBy='name';try{localStorage.setItem('pvp-sortby',plSortBy);}catch(err){}closeSortMenu();applyPlSort();};
document.getElementById('sort-dur').onclick=e=>{e.stopPropagation();plSortBy='dur';try{localStorage.setItem('pvp-sortby',plSortBy);}catch(err){}closeSortMenu();applyPlSort();};
document.getElementById('sort-asc').onclick=e=>{e.stopPropagation();plSortDir='asc';try{localStorage.setItem('pvp-sortdir',plSortDir);}catch(err){}closeSortMenu();applyPlSort();};
document.getElementById('sort-desc').onclick=e=>{e.stopPropagation();plSortDir='desc';try{localStorage.setItem('pvp-sortdir',plSortDir);}catch(err){}closeSortMenu();applyPlSort();};
document.addEventListener('mousedown',e=>{if(!sortMenu.hidden&&e.target.closest&&!e.target.closest('.pl-sort-wrap'))closeSortMenu();});
function isVideoFile(f){const ext=(f.name.split('.').pop()||'').toLowerCase();if(VIDEO_EXT.includes(ext))return true;if(f.type&&f.type.startsWith('video/'))return true;if(f.type&&/^(audio|image|text)\//.test(f.type))return false;if(NON_MEDIA_EXT.includes(ext))return false;return true;}
function playStandalone(file){
  playlist.length=0;plIdx=-1;
  tbPlaylist.hidden=true;plmenu.hidden=true;
  setPlaylistName('');
  v.src=URL.createObjectURL(file);
  standaloneFile=file;standaloneUrl=v.src;
  v.muted=true;v.play().then(()=>v.muted=false).catch(()=>{});
  setVideoName(file.name);
  renderSubtitleMenu();
}
function playPl(i){
  if(!playlist[i])return;
  plIdx=i;
  const it=playlist[i];
  const onMeta=()=>{
    if(it.subFile&&!externalSubtitles.some(s=>s.name===it.subFile.name)){loadExternalSubtitle(it.subFile);}
    else if(it.subFile){const s=externalSubtitles.find(s=>s.name===it.subFile.name);if(s&&currentSubtitleTrack!==s)selectExternalSubtitle(s);}
  };
  v.addEventListener('loadedmetadata',onMeta,{once:true});
  v.src=it.url;
  v.muted=true;v.play().then(()=>v.muted=false).catch(()=>{});
  setVideoName(it.name);
  renderPlList();
}
function buildPlaylist(files){
  const vids=Array.from(files).filter(isVideoFile).sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true,sensitivity:'base'}));
  if(!vids.length){showPlToast('No video found in folder — check again');return;}
  const subs=Array.from(files).filter(f=>SUB_EXT.includes((f.name.split('.').pop()||'').toLowerCase()));
  playlist.length=0;
  vids.forEach(f=>{
    const base=f.name.replace(/\.[^.]+$/,'').toLowerCase();
    const sub=subs.find(s=>s.name.replace(/\.[^.]+$/,'').toLowerCase()===base)||null;
    playlist.push({name:f.name,file:f,url:URL.createObjectURL(f),subFile:sub});
  });
  const rel=vids[0].webkitRelativePath||vids[0].name;
  const folder=rel.split('/')[0]||'Playlist';
  tbPlaylist.hidden=false;
  renderPlList();
  playPl(0);
  applyPlSort();
  setPlaylistName(folder);
  renderSubtitleMenu();
  try{postMsg("pl:"+playlist.length+":"+playlist.map(x=>x.name).join(","));}catch(e){}
}
function renderPlList(){
  const pllist=document.getElementById('pllist');
  pllist.innerHTML='';
  if(!playlist.length){pllist.innerHTML='<div class="pl-empty">No playlist loaded</div>';return;}
  playlist.forEach((it,i)=>{
    const d=document.createElement('div');
    d.className='pl-item'+(i===plIdx?' cur':'');
    d.draggable=true;
    d.innerHTML='<span class="pl-grip">&#8942;&#8942;</span><span class="pl-name">'+escHtml(it.name)+'</span><span class="pl-idx">'+(i+1)+'</span>';
    d.onclick=()=>{playPl(i);plmenu.hidden=true;};
    d.addEventListener('dragstart',e=>{dragFrom=i;e.dataTransfer.effectAllowed='move';try{e.dataTransfer.setData('text/plain',String(i));}catch(err){}});
    d.addEventListener('dragover',e=>{e.preventDefault();d.classList.add('drag-over');});
    d.addEventListener('dragleave',()=>{d.classList.remove('drag-over');});
    d.addEventListener('drop',e=>{e.preventDefault();d.classList.remove('drag-over');movePl(dragFrom,i);});
    pllist.appendChild(d);
  });
}
function movePl(from,to){
  if(from<0||from===to||from<0||from>=playlist.length||to>=playlist.length)return;
  const cur=playlist[plIdx];
  const item=playlist.splice(from,1)[0];
  playlist.splice(to,0,item);
  plIdx=playlist.indexOf(cur);
  dragFrom=-1;
  renderPlList();
}
document.getElementById('folder-input').onchange=e=>{
  if(e.target.files&&e.target.files.length)buildPlaylist(e.target.files);
  e.target.value='';
};
v.addEventListener('ended',()=>{
  if(playlist.length&&autoplay&&plIdx+1<playlist.length){playPl(plIdx+1);}
});
v.addEventListener('error',()=>{
  const E={1:'Playback aborted',2:'Network error while reading the file',3:'Decode error - unsupported codec or a broken file',4:'Format not supported by this player'};
  const msg=E[(v.error&&v.error.code)]||'Playback failed';
  onVideoError(msg);
});
// ===== Container conversion (TS/AVI/WMV need an ffmpeg remux) =====
let standaloneFile=null,standaloneUrl='',cnvBusy=false,cnvTriedFor='';
function jget(u){return fetch(u).then(r=>r.ok?r.json():null).catch(()=>null);}
async function prepPlay(file,label){
  if(cnvBusy)return;cnvBusy=true;
  try{
    showPlToast('Preparing "'+label+'" for playback…');
    if(file){
      const r=await fetch('/upload?name='+encodeURIComponent(file.name),{method:'POST',body:file});
      if(!r.ok)throw new Error('upload');
    }
    const c=await fetch('/convert',{method:'POST'});
    if(!c.ok)throw new Error('convert');
    for(let i=0;i<1200;i++){
      const s=await jget('/status');
      if(!s)throw new Error('status');
      if(s.state==='ready'){
        v.src='/video?t='+Date.now();
        v.muted=true;v.play().then(()=>v.muted=false).catch(()=>{});
        showPlToast('Converted - playing');
        return;
      }
      if(s.state==='error'){const m='Cannot convert this file: '+String(s.msg||'unknown error').slice(0,160);showPlToast(m);setTitleError(m);return;}
      if(s.state==='no-ffmpeg'){const m='This container (TS/AVI/WMV) needs ffmpeg installed: winget install ffmpeg';showPlToast(m);setTitleError(m);return;}
      if(s.state==='converting')showPlToast('Converting container… '+s.pct+'%');
      await new Promise(r=>setTimeout(r,500));
    }
    showPlToast('Conversion is taking too long - still working in the background');
  }catch(e){
    showPlToast('Could not prepare this file for playback');
    setTitleError('Playback failed');
  }finally{cnvBusy=false;}
}
async function onVideoError(defMsg){
  try{
    const code=v.error?v.error.code:0;
    if(code!==3&&code!==4){showPlToast(defMsg);setTitleError(defMsg);return;}
    if(cnvTriedFor===v.src||cnvBusy)return;
    cnvTriedFor=v.src;
    const local=String(v.src||'').indexOf('/video')>=0||/^https?:\/\/(127\.0\.0\.1|localhost)/.test(v.src||'');
    if(local){
      const info=await jget('/info');
      if(!info||!info.needConvert){showPlToast(defMsg);setTitleError(defMsg);return;}
      if(!info.ffmpeg){const m='This file uses a container WebView2 cannot play (MPEG-TS, AVI, WMV…). Install ffmpeg and PVP+ converts it automatically.';showPlToast(m);setTitleError(m);return;}
      await prepPlay(null,info.name||'video');
      return;
    }
    const it=playlist[plIdx];
    const file=(it&&it.url===v.src&&it.file)||(standaloneUrl===v.src&&standaloneFile);
    if(!file){showPlToast(defMsg);setTitleError(defMsg);return;}
    await prepPlay(file,file.name);
  }catch(e){showPlToast(defMsg);setTitleError(defMsg);}
}

document.getElementById("f").onchange=e=>{const f=e.target.files[0];if(f)playStandalone(f);e.target.value='';};
["mousemove","mousedown","wheel"].forEach(ev=>document.addEventListener(ev,showCtl));document.addEventListener("keydown",e=>{showCtl();if(e.code==="Space"){e.preventDefault();toggle();}else if(e.code==="KeyF"){e.preventDefault();if(window.chrome&&window.chrome.webview)window.chrome.webview.postMessage("fullscreen");setFs(!isFs);}else if(e.code==="ArrowUp"){e.preventDefault();applyVolume(Math.min(2,+vol.value+0.1));}else if(e.code==="ArrowDown"){e.preventDefault();applyVolume(Math.max(0,+vol.value-0.1));}else if(e.code==="ArrowLeft"){e.preventDefault();if(v.duration)v.currentTime=Math.max(0,v.currentTime-10);upd();}else if(e.code==="ArrowRight"){e.preventDefault();if(v.duration)v.currentTime=Math.min(v.duration,v.currentTime+10);upd();}else if(e.code==="KeyM"){e.preventDefault();setMute(!isMuted);}else if(e.code==="KeyC"){e.preventDefault();toggleLiveCaptions();}else if(e.code==="BracketLeft"){e.preventDefault();let i=SPEEDS.indexOf(speed);if(i>0)applySpeed(SPEEDS[i-1]);}else if(e.code==="BracketRight"){e.preventDefault();let i=SPEEDS.indexOf(speed);if(i<SPEEDS.length-1)applySpeed(SPEEDS[i+1]);}});
showCtl();
["dragenter","dragover"].forEach(ev=>document.addEventListener(ev,e=>{e.preventDefault();dnd.classList.add("show");}));
["dragleave","drop"].forEach(ev=>document.addEventListener(ev,e=>{e.preventDefault();dnd.classList.remove("show");}));
function isSubtitleFile(f){return ['srt','vtt','ass','ssa'].includes((f.name.split('.').pop()||'').toLowerCase());}
function readAllEntries(reader){return new Promise(res=>{const all=[];(function next(){reader.readEntries(es=>{if(!es.length){res(all);return;}all.push(...es);next();},()=>res(all));})();});}
function entryFile(en,path){return new Promise((res,rej)=>{en.file(f=>{if(path){try{Object.defineProperty(f,'webkitRelativePath',{value:path});}catch(err){}}res(f);},rej);});}
function walkEntry(en,path){
  if(en.isFile)return entryFile(en,path);
  if(!en.isDirectory)return Promise.resolve([]);
  return readAllEntries(en.createReader()).then(ents=>Promise.all(ents.map(c=>walkEntry(c,path?path+'/'+c.name:c.name)))).then(a=>[].concat(...a));
}
function handleDropFiles(files,fromFolder){
  const vids=files.filter(isVideoFile);
  const subs=files.filter(isSubtitleFile);
  if(!vids.length&&!subs.length)return;
  if(vids.length>1||(fromFolder&&vids.length)){buildPlaylist(files);return;}
  if(vids.length===1){
    playStandalone(vids[0]);
    const base=vids[0].name.replace(/\.[^.]+$/,'').toLowerCase();
    const m=subs.find(s=>s.name.replace(/\.[^.]+$/,'').toLowerCase()===base);
    if(m)loadExternalSubtitle(m);
    return;
  }
  if(subs.length&&v.src){subs.forEach(loadExternalSubtitle);}
}
async function walkDirHandle(h,prefix){
  const out=[];
  for await(const e of h.values()){
    const p=prefix?prefix+"/"+e.name:e.name;
    if(e.kind==="directory"){out.push(...await walkDirHandle(e,p));}
    else{const f=await e.getFile();try{Object.defineProperty(f,"webkitRelativePath",{value:p});}catch(err){}out.push(f);}
  }
  return out;
}
async function pickFolderPlaylist(){
  if(window.showDirectoryPicker){
    try{
      const h=await window.showDirectoryPicker({mode:"read"});
      const files=await walkDirHandle(h,h.name);
      if(files.length)buildPlaylist(files);
      return;
    }catch(err){
      if(err&&err.name==="AbortError")return;
    }
  }
  document.getElementById("folder-input").click();
}
document.addEventListener("drop",e=>{
  const dt=e.dataTransfer;if(!dt)return;
  const entries=[];
  if(dt.items&&dt.items.length){
    for(let i=0;i<dt.items.length;i++){
      const it=dt.items[i];
      if(it.kind==='file'&&it.webkitGetAsEntry)entries.push(it.webkitGetAsEntry());
    }
  }
  if(entries.some(en=>en&&en.isDirectory)){
    Promise.all(entries.filter(Boolean).map(en=>walkEntry(en,en.isDirectory?en.name:''))).then(arr=>handleDropFiles([].concat(...arr),true)).catch(()=>{});
    return;
  }
  handleDropFiles(Array.from(dt.files||[]),false);
});
document.addEventListener("wheel",e=>{const t=e.target;if(t&&t.closest&&(t.closest("#settingsmenu")||t.closest("#plmenu")||t.closest(".style-popup")))return;e.preventDefault();applyVolume(Math.max(0,Math.min(2,+vol.value+(e.deltaY<0?0.05:-0.05))));showCtl();});
// ===== Update system (GitHub releases) =====
const REPO='DeepanshuK2002/Personal-Video-Player---PVP';
const BAKED_VERSION='0.0.0';
function verTuple(s){return String(s).replace(/^v/i,'').split('.').map(n=>{const x=parseInt(n,10);return isNaN(x)?0:x;});}
function verGt(a,b){const x=verTuple(a),y=verTuple(b);for(let i=0;i<3;i++){const p=x[i]||0,q=y[i]||0;if(p>q)return true;if(p<q)return false;}return false;}
let installedVer=BAKED_VERSION;
try{const s=localStorage.getItem('pvp-updated-to');if(s&&verGt(s,installedVer))installedVer=s;}catch(e){}
document.getElementById('ver-text').textContent='PVP+ v'+installedVer;
document.getElementById('upd-from').textContent='v'+installedVer;
let updateInfo=null,downloading=false,installing=false;
function setUpdateUI(on){document.getElementById('tb-update').hidden=!on;document.getElementById('ver-upd').hidden=!on;}
async function checkUpdate(){
  try{
    const r=await fetch('https://api.github.com/repos/'+REPO+'/releases/latest',{headers:{'Accept':'application/vnd.github+json'}});
    if(!r.ok)return;
    const j=await r.json();
    const tag=(j.tag_name||'').trim();
    if(!tag||!verGt(tag,installedVer))return;
    const assets=j.assets||[];
    const asset=assets.find(a=>/\.exe$/i.test(a.name||''))||assets[0];
    if(!asset||!asset.browser_download_url)return;
    updateInfo={tag:tag,url:asset.browser_download_url,size:asset.size||0,notes:(j.body||'').slice(0,1500)};
    setUpdateUI(true);
  }catch(e){}
}
const updPopup=document.getElementById('updpopup'),updBackdrop=document.getElementById('updbackdrop');
function resetUpdateProgress(){
  downloading=false;installing=false;
  document.getElementById('updbar').hidden=true;
  document.getElementById('upd-bar-fill').style.width='0%';
  document.getElementById('updstatus').textContent='';
  const ib=document.getElementById('upd-install'),lb=document.getElementById('upd-later'),cb=document.getElementById('updclose');
  ib.disabled=lb.disabled=cb.disabled=false;
  ib.textContent='Install';
}
function openUpdatePopup(){
  if(!updateInfo||installing)return;
  closeAllMenus();settingsmenu.classList.remove('show');
  document.getElementById('upd-to').textContent=updateInfo.tag;
  document.getElementById('upd-notes').textContent=updateInfo.notes||'No release notes.';
  if(!downloading)resetUpdateProgress();
  updPopup.classList.add('show');updBackdrop.classList.add('show');
}
function closeUpdatePopup(){
  if(downloading||installing)return;
  updPopup.classList.remove('show');updBackdrop.classList.remove('show');
}
function updReport(total,loaded){
  const f=document.getElementById('upd-bar-fill');
  const ib=document.getElementById('upd-install');
  if(total>0){const p=Math.min(100,Math.floor(loaded/total*100));f.style.width=p+'%';ib.textContent='Downloading… '+p+'%';}
  else{f.style.width='50%';ib.textContent='Downloading…';}
}
// Rust downloads the release asset with curl (the WebView fetch is blocked by
// CORS: GitHub's download host sends no Access-Control-Allow-Origin header).
function startInstall(){
  if(!updateInfo||downloading||installing)return;
  downloading=true;
  const ib=document.getElementById('upd-install'),lb=document.getElementById('upd-later'),cb=document.getElementById('updclose'),status=document.getElementById('updstatus');
  ib.disabled=lb.disabled=cb.disabled=true;
  ib.textContent='Downloading…';
  document.getElementById('updbar').hidden=false;
  status.textContent='';
  postMsg({type:'update-begin',url:updateInfo.url,size:updateInfo.size||0,tag:updateInfo.tag});
}
function pvpDlProgress(p){
  if(!downloading)return;
  const f=document.getElementById('upd-bar-fill'),ib=document.getElementById('upd-install');
  if(p<0){f.style.width='50%';ib.textContent='Downloading…';return;}
  const pct=Math.min(100,Math.floor(p));f.style.width=pct+'%';ib.textContent='Downloading… '+pct+'%';
}
function pvpDlError(msg){
  downloading=false;
  document.getElementById('updstatus').textContent='Download failed: '+(msg||'network error');
  const ib=document.getElementById('upd-install'),lb=document.getElementById('upd-later'),cb=document.getElementById('updclose');
  ib.disabled=lb.disabled=cb.disabled=false;
  ib.textContent='Retry';
}
// Called from Rust after the downloaded file is verified
function pvpInstallReady(ok){
  const status=document.getElementById('updstatus'),ib=document.getElementById('upd-install'),lb=document.getElementById('upd-later'),cb=document.getElementById('updclose');
  if(!ok){
    downloading=false;
    status.textContent='Update package could not be verified — please retry.';
    ib.disabled=lb.disabled=cb.disabled=false;
    ib.textContent='Retry';
    postMsg({type:'update-cancel'});
    return;
  }
  try{localStorage.setItem('pvp-updated-to',updateInfo.tag);}catch(e){}
  installing=true;
  status.textContent='Installing '+updateInfo.tag+' — the app will restart…';
  ib.textContent='Installing…';
  postMsg({type:'update-run',tag:updateInfo.tag});
}
function pvpInstallLaunching(){
  document.getElementById('updstatus').textContent='Restarting…';
  setTimeout(()=>postMsg({type:'quit'}),500);
}
function pvpUpdateRejected(){
  downloading=false;installing=false;
  document.getElementById('updstatus').textContent='Update rejected (not newer than this build).';
  const ib=document.getElementById('upd-install'),lb=document.getElementById('upd-later'),cb=document.getElementById('updclose');
  ib.disabled=lb.disabled=cb.disabled=false;
}
document.getElementById('tb-update').onclick=e=>{e.stopPropagation();openUpdatePopup();};
document.getElementById('ver-upd').onclick=e=>{e.stopPropagation();openUpdatePopup();};
document.getElementById('updclose').onclick=()=>{closeUpdatePopup();};
document.getElementById('upd-later').onclick=()=>{closeUpdatePopup();};
document.getElementById('upd-install').onclick=()=>{startInstall();};
updBackdrop.onclick=()=>{closeUpdatePopup();};

showCtl();applyVolume(1);applySpeed(1);hudReady=true;renderSubtitleMenu();renderAudioMenu();syncAutoplay();syncSortBtn();renderTitlebar();updateCcActive();postMsg({type:'live-captions-init'});setTimeout(checkUpdate,1200);
let rc=0;document.addEventListener("contextmenu",e=>{e.preventDefault();const n=Date.now();if(n-rc<400){if(window.chrome&&window.chrome.webview)window.chrome.webview.postMessage("fullscreen");setFs(!isFs);rc=0;}else{rc=n;setTimeout(()=>rc=0,400);}});
const p=new URLSearchParams(location.search);if(p.get("src")){try{let s=p.get("src");if(/^[a-zA-Z]:[\\\\/]/.test(s))s="file:///"+s.replace(/\\\\/g,"/").replace(/ /g,"%20");v.src=s;v.play();setVideoName(p.get("src"));}catch(e){}}
</script></body></html>"####;

enum UserEvent {
    Js(String),
}

#[cfg(windows)]
#[link(name = "user32")]
extern "system" {
    fn GetSystemMetrics(i: i32) -> i32;
    fn GetDpiForWindow(hwnd: isize) -> u32;
    fn SystemParametersInfoW(action: u32, param: u32, pv: *mut RECT, win_ini: u32) -> i32;
}

#[cfg(windows)]
#[repr(C)]
#[derive(Default)]
struct RECT {
    left: i32,
    top: i32,
    right: i32,
    bottom: i32,
}

fn lc_dbg(msg: &str) {
    use std::io::Write as _;
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open("C:\\Users\\Public\\pvp_lc.txt")
    {
        let _ = writeln!(f, "{}", msg);
    }
}

fn parse_ver(s: &str) -> (u64, u64, u64) {
    let t = s.trim().trim_start_matches('v');
    let mut it = t.split('.');
    let mut next = || -> u64 {
        it.next()
            .and_then(|x| x.split('-').next())
            .and_then(|x| x.parse::<u64>().ok())
            .unwrap_or(0)
    };
    (next(), next(), next())
}

// Containers lie all the time (a TS stream renamed to .mp4 is common), so sniff
// the real container from the first bytes before falling back to the extension.
fn sniff_container(p: &std::path::Path) -> Option<&'static str> {
    use std::io::Read;
    let mut head = [0u8; 1024];
    let n = std::fs::File::open(p)
        .and_then(|mut f| f.read(&mut head))
        .unwrap_or(0);
    if n >= 12 && &head[4..8] == b"ftyp" {
        // isom / mp4 / m4v / 3gp / hevc-in-mp4
        return Some(if &head[8..11] == b"3gp" {
            "video/3gpp"
        } else {
            "video/mp4"
        });
    }
    if n >= 64 && head[0] == 0x47 && head[188] == 0x47 && head[376] == 0x47 {
        return Some("video/mp2t"); // MPEG-TS (.ts / .m2ts / mislabelled .mp4)
    }
    if n >= 4 && &head[0..4] == &[0x1A, 0x45, 0xDF, 0xA3] {
        // EBML — distinguish WebM from Matroska by DocType
        return Some(if head.windows(4).any(|w| w == b"webm") {
            "video/webm"
        } else {
            "video/x-matroska"
        });
    }
    if n >= 12 && &head[0..4] == b"RIFF" && &head[8..12] == b"AVI " {
        return Some("video/x-msvideo");
    }
    if n >= 4 && &head[0..4] == b"OggS" {
        return Some("video/ogg");
    }
    if n >= 4 && &head[0..3] == b"FLV" {
        return Some("video/x-flv");
    }
    if n >= 16 && &head[0..4] == b"\x00\x00\x01\xba" {
        return Some("video/mpeg"); // MPEG-PS (VCD/DVD .mpg/.vob)
    }
    None
}

fn video_mime(p: &std::path::Path) -> &'static str {
    if let Some(m) = sniff_container(p) {
        return m;
    }
    match p
        .extension()
        .and_then(|e| e.to_str())
        .map(|s| s.to_ascii_lowercase())
        .as_deref()
    {
        Some("mp4") | Some("m4v") | Some("mp4v") | Some("f4v") => "video/mp4",
        Some("webm") => "video/webm",
        Some("ogv") | Some("ogg") | Some("ogx") => "video/ogg",
        Some("mkv") | Some("mk3d") => "video/x-matroska",
        Some("avi") | Some("divx") | Some("xvid") => "video/x-msvideo",
        Some("mov") | Some("qt") => "video/quicktime",
        Some("ts") | Some("m2ts") | Some("mts") | Some("m2t") | Some("tp") => "video/mp2t",
        Some("wmv") | Some("asf") | Some("wtv") => "video/x-ms-wmv",
        Some("flv") | Some("f4p") | Some("f4c") => "video/x-flv",
        Some("3gp") | Some("3g2") | Some("3gpp") => "video/3gpp",
        Some("mpg") | Some("mpeg") | Some("mpe") | Some("mp2") | Some("vob") => "video/mpeg",
        Some("rm") | Some("rmvb") => "application/vnd.rn-realmedia",
        Some("mxf") => "application/mxf",
        _ => "application/octet-stream",
    }
}

// ===== Container conversion =====
// WebView2/Chromium only demuxes a handful of containers (MP4/WebM/MKV/Ogg).
// Anything else (MPEG-TS, AVI, WMV/ASF, FLV, MPEG-PS...) is remuxed with the
// system ffmpeg (optional; if missing we just say so) into a temp MP4 and
// played from there. Stream copy — no re-encode, no quality loss.
const CHROMIUM_OK_MIME: [&str; 6] = [
    "video/mp4",
    "video/3gpp",
    "video/webm",
    "video/x-matroska",
    "video/ogg",
    "video/quicktime",
];

fn needs_convert(p: &std::path::Path) -> bool {
    match sniff_container(p) {
        Some(m) => !CHROMIUM_OK_MIME.contains(&m),
        None => false,
    }
}

fn ffmpeg_path() -> Option<std::path::PathBuf> {
    use std::sync::OnceLock;
    static FF: OnceLock<Option<std::path::PathBuf>> = OnceLock::new();
    FF.get_or_init(|| {
        let mut cands: Vec<std::path::PathBuf> = Vec::new();
        if let Some(paths) = std::env::var_os("PATH") {
            for d in std::env::split_paths(&paths) {
                cands.push(d.join("ffmpeg.exe"));
            }
        }
        if let Some(p) = std::env::var_os("ProgramFiles") {
            cands.push(std::path::PathBuf::from(p).join("ffmpeg").join("bin").join("ffmpeg.exe"));
        }
        if let Some(p) = std::env::var_os("ProgramFiles(x86)") {
            cands.push(std::path::PathBuf::from(p).join("ffmpeg").join("bin").join("ffmpeg.exe"));
        }
        if let Some(p) = std::env::var_os("USERPROFILE") {
            cands.push(
                std::path::PathBuf::from(p).join("scoop").join("shims").join("ffmpeg.exe"),
            );
        }
        cands.push(std::path::PathBuf::from(
            r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        ));
        cands.push(std::path::PathBuf::from(r"C:\ffmpeg\bin\ffmpeg.exe"));
        cands.into_iter().find(|c| c.is_file())
    })
    .clone()
}

struct ConvState {
    state: String,
    pct: u32,
    msg: String,
}

fn remux_out_for(src: &std::path::Path) -> std::path::PathBuf {
    let dir = std::env::temp_dir().join("pvp-remux");
    let _ = std::fs::create_dir_all(&dir);
    let stem = src
        .file_stem()
        .map(|s| s.to_string_lossy().to_string())
        .unwrap_or_else(|| "video".to_string());
    let mut base = String::new();
    for ch in stem.chars() {
        if ch.is_ascii_alphanumeric() || matches!(ch, '-' | '_') {
            base.push(ch);
        } else {
            base.push('_');
        }
    }
    while base.len() > 64 {
        base.pop();
    }
    if base.trim_matches('_').is_empty() {
        base = "video".into();
    }
    let mut h: u64 = 1469598103934665603;
    for b in src.to_string_lossy().bytes() {
        h ^= b as u64;
        h = h.wrapping_mul(1099511628211);
    }
    if let Ok(md) = std::fs::metadata(src) {
        h ^= md.len();
        h = h.wrapping_mul(1099511628211);
        if let Ok(t) = md.modified() {
            if let Ok(d) = t.duration_since(std::time::UNIX_EPOCH) {
                h ^= d.as_secs();
                h = h.wrapping_mul(1099511628211);
            }
        }
    }
    dir.join(format!("{}-{:x}.mp4", base, h))
}

fn run_ffmpeg(
    ff: &std::path::Path,
    args: &[String],
    conv: &Arc<Mutex<ConvState>>,
    src_size: u64,
) -> (i32, String) {
    use std::io::{BufRead, BufReader};
    use std::process::{Command, Stdio};
    let mut cmd = Command::new(ff);
    cmd.args(args)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = match cmd.spawn() {
        Ok(c) => c,
        Err(e) => return (-1, format!("ffmpeg could not start ({e})")),
    };
    let errh = child.stderr.take().map(|e| {
        std::thread::spawn(move || {
            let mut s = String::new();
            for line in BufReader::new(e).lines().map_while(Result::ok) {
                s.push_str(&line);
                s.push('\n');
                if s.len() > 3000 {
                    let cut = s.find('\n').map(|i| i + 1).unwrap_or(0);
                    s.drain(..cut);
                }
            }
            s
        })
    });
    if let Some(out) = child.stdout.take() {
        for line in BufReader::new(out).lines().map_while(Result::ok) {
            if let Some(v) = line.strip_prefix("total_size=") {
                if let Ok(n) = v.trim().parse::<u64>() {
                    if src_size > 0 {
                        let pct = (n.saturating_mul(100) / src_size).min(99) as u32;
                        if let Ok(mut c) = conv.lock() {
                            c.pct = pct;
                        }
                    }
                }
            }
        }
    }
    let code = match child.wait() {
        Ok(s) => s.code().unwrap_or(-1),
        Err(e) => {
            let tail = errh.and_then(|h| h.join().ok()).unwrap_or_default();
            return (-1, format!("wait failed: {e}\n{tail}"));
        }
    };
    let err = errh.and_then(|h| h.join().ok()).unwrap_or_default();
    (code, err)
}

fn convert_file(
    ff: &std::path::Path,
    src: &std::path::Path,
    out: &std::path::Path,
    conv: &Arc<Mutex<ConvState>>,
) -> Result<(), String> {
    let src_size = std::fs::metadata(src).map(|m| m.len()).unwrap_or(0);
    let s = src.to_string_lossy().to_string();
    let o = out.to_string_lossy().to_string();
    let base = vec![
        "-y".to_string(),
        "-hide_banner".to_string(),
        "-loglevel".to_string(),
        "error".to_string(),
        "-nostdin".to_string(),
        "-i".to_string(),
        s.clone(),
        "-map".to_string(),
        "0:v?".to_string(),
        "-map".to_string(),
        "0:a?".to_string(),
        "-c".to_string(),
        "copy".to_string(),
    ];
    let tail = vec![
        "-progress".to_string(),
        "pipe:1".to_string(),
        "-nostats".to_string(),
        "-f".to_string(),
        "mp4".to_string(),
        o.clone(),
    ];
    let mut with_bsf = base.clone();
    with_bsf.push("-bsf:a".to_string());
    with_bsf.push("aac_adtstoasc".to_string());
    with_bsf.extend(tail.clone());
    let mut without_bsf = base.clone();
    without_bsf.extend(tail);
    let mut last = String::new();
    for args in [with_bsf, without_bsf] {
        let _ = std::fs::remove_file(out);
        let (code, err) = run_ffmpeg(ff, &args, conv, src_size);
        if code == 0 {
            if std::fs::metadata(out).map(|m| m.len() > 0).unwrap_or(false) {
                return Ok(());
            }
            last = "ffmpeg produced an empty file".into();
        } else {
            last = if err.trim().is_empty() {
                format!("ffmpeg exited with code {code}")
            } else {
                err.trim().to_string()
            };
        }
    }
    Err(last)
}

fn start_convert(cv: &Arc<Mutex<Option<std::path::PathBuf>>>, conv: &Arc<Mutex<ConvState>>) {
    let src = match cv.lock().ok().and_then(|g| g.clone()) {
        Some(p) => p,
        None => {
            if let Ok(mut c) = conv.lock() {
                c.state = "error".into();
                c.msg = "No file loaded".into();
            }
            return;
        }
    };
    if !needs_convert(&src) {
        if let Ok(mut c) = conv.lock() {
            c.state = "ready".into();
            c.pct = 100;
            c.msg.clear();
        }
        return;
    }
    let ff = match ffmpeg_path() {
        Some(f) => f,
        None => {
            if let Ok(mut c) = conv.lock() {
                c.state = "no-ffmpeg".into();
                c.pct = 0;
                c.msg = "ffmpeg not found".into();
            }
            return;
        }
    };
    {
        let Ok(mut c) = conv.lock() else { return };
        if c.state == "converting" {
            return;
        }
        c.state = "converting".into();
        c.pct = 0;
        c.msg.clear();
    }
    let out = remux_out_for(&src);
    let cv2 = cv.clone();
    let conv2 = conv.clone();
    std::thread::spawn(move || {
        // reuse a previous conversion of the same source when available
        if let Ok(md) = std::fs::metadata(&out) {
            if md.len() > 0 {
                if let Ok(mut c) = conv2.lock() {
                    c.state = "ready".into();
                    c.pct = 100;
                }
                if let Ok(mut g) = cv2.lock() {
                    *g = Some(out);
                }
                return;
            }
        }
        match convert_file(&ff, &src, &out, &conv2) {
            Ok(()) => {
                if let Ok(mut c) = conv2.lock() {
                    c.state = "ready".into();
                    c.pct = 100;
                }
                if let Ok(mut g) = cv2.lock() {
                    *g = Some(out);
                }
            }
            Err(m) => {
                if let Ok(mut c) = conv2.lock() {
                    c.state = "error".into();
                    c.msg = m;
                }
            }
        }
    });
}

fn percent_decode(s: &str) -> String {
    fn hx(c: u8) -> Option<u8> {
        match c {
            b'0'..=b'9' => Some(c - b'0'),
            b'a'..=b'f' => Some(c - b'a' + 10),
            b'A'..=b'F' => Some(c - b'A' + 10),
            _ => None,
        }
    }
    let b = s.as_bytes();
    let mut out: Vec<u8> = Vec::with_capacity(b.len());
    let mut i = 0;
    while i < b.len() {
        if b[i] == b'%' && i + 2 < b.len() {
            if let (Some(h), Some(l)) = (hx(b[i + 1]), hx(b[i + 2])) {
                out.push(h * 16 + l);
                i += 3;
                continue;
            }
        }
        out.push(b[i]);
        i += 1;
    }
    String::from_utf8_lossy(&out).to_string()
}

fn sanitize_name(n: &str) -> String {
    let mut s: String = n
        .chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || matches!(c, '.' | '-' | '_' | ' ' | '(' | ')' | '+') {
                c
            } else {
                '_'
            }
        })
        .collect();
    while s.len() > 120 {
        s.pop();
    }
    while s.starts_with('.') {
        s.remove(0);
    }
    if s.is_empty() {
        s = "upload.bin".into();
    }
    s
}

fn http_json(stream: &mut std::net::TcpStream, body: &str) {
    use std::io::Write;
    let h = format!(
        "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
        body.len()
    );
    let _ = stream.write_all(h.as_bytes());
    let _ = stream.write_all(body.as_bytes());
    let _ = stream.flush();
}

fn http_text(stream: &mut std::net::TcpStream, status: &str, ctype: &str, body: &str) {
    use std::io::Write;
    let h = format!(
        "HTTP/1.1 {}\r\nContent-Type: {}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
        status,
        ctype,
        body.len()
    );
    let _ = stream.write_all(h.as_bytes());
    let _ = stream.write_all(body.as_bytes());
    let _ = stream.flush();
}

// Serve the UI page and stream the video with HTTP Range support.
// One thread per connection, chunks straight off disk: a 20 GB file is
// never read into memory and seeking stays instant.
fn serve_conn(
    mut stream: std::net::TcpStream,
    cv: Arc<Mutex<Option<std::path::PathBuf>>>,
    hs: Arc<Mutex<Option<String>>>,
    conv: Arc<Mutex<ConvState>>,
) {
    use std::io::{Read, Seek, SeekFrom, Write};
    let _ = stream.set_read_timeout(Some(std::time::Duration::from_secs(15)));
    let mut rbuf = [0u8; 16384];
    let n = match stream.read(&mut rbuf) {
        Ok(n) => n,
        Err(_) => return,
    };
    if n == 0 {
        return;
    }
    let req = String::from_utf8_lossy(&rbuf[..n]).to_string();
    let mut tok = req.split_whitespace();
    let method = tok.next().unwrap_or("GET").to_string();
    let uri = tok.next().unwrap_or("/").to_string();
    let not_found = b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n";

    if uri == "/" || uri.starts_with("/?") {
        let page = hs.lock().ok().and_then(|g| g.clone()).unwrap_or_default();
        if page.is_empty() {
            let _ = stream.write_all(not_found);
        } else {
            let head = format!(
                "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
                page.len()
            );
            let _ = stream.write_all(head.as_bytes());
            if method != "HEAD" {
                let _ = stream.write_all(page.as_bytes());
            }
        }
        let _ = stream.flush();
        return;
    }
    let path_only = uri.split('?').next().unwrap_or("/").to_string();
    match path_only.as_str() {
        "/info" => {
            let (need, name) = match cv.lock().ok().and_then(|g| g.clone()) {
                Some(p) => (
                    needs_convert(&p),
                    p.file_name()
                        .map(|s| s.to_string_lossy().to_string())
                        .unwrap_or_default(),
                ),
                None => (false, String::new()),
            };
            let body = serde_json::json!({
                "needConvert": need,
                "name": name,
                "ffmpeg": ffmpeg_path().is_some(),
            })
            .to_string();
            http_json(&mut stream, &body);
            return;
        }
        "/status" => {
            let body = conv
                .lock()
                .map(|c| {
                    serde_json::json!({"state": c.state, "pct": c.pct, "msg": c.msg}).to_string()
                })
                .unwrap_or_else(|_| "{\"state\":\"idle\",\"pct\":0,\"msg\":\"\"}".to_string());
            http_json(&mut stream, &body);
            return;
        }
        "/convert" => {
            if method == "POST" {
                start_convert(&cv, &conv);
                http_json(&mut stream, "{\"ok\":true}");
            } else {
                http_json(&mut stream, "{\"ok\":false}");
            }
            return;
        }
        "/upload" => {
            if method != "POST" {
                http_text(&mut stream, "405 Method Not Allowed", "text/plain", "POST only");
                return;
            }
            let hdr_end = rbuf[..n]
                .windows(4)
                .position(|w| w == b"\r\n\r\n")
                .map(|i| i + 4);
            let Some(hdr_end) = hdr_end else {
                http_text(&mut stream, "400 Bad Request", "text/plain", "bad request");
                return;
            };
            let head_txt = String::from_utf8_lossy(&rbuf[..hdr_end]).to_string();
            let clen: u64 = head_txt
                .lines()
                .find(|l| l.to_ascii_lowercase().starts_with("content-length:"))
                .and_then(|l| l.splitn(2, ':').nth(1))
                .and_then(|v| v.trim().parse().ok())
                .unwrap_or(0);
            if clen == 0 {
                http_text(
                    &mut stream,
                    "411 Length Required",
                    "text/plain",
                    "Content-Length required",
                );
                return;
            }
            let mut name = "upload.bin".to_string();
            if let Some(q) = uri.split('?').nth(1) {
                for kv in q.split('&') {
                    if let Some(v) = kv.strip_prefix("name=") {
                        let d = percent_decode(v);
                        if !d.is_empty() {
                            name = sanitize_name(&d);
                        }
                    }
                }
            }
            let dir = std::env::temp_dir().join("pvp-uploads");
            let _ = std::fs::create_dir_all(&dir);
            let target = dir.join(&name);
            let mut f = match std::fs::File::create(&target) {
                Ok(f) => f,
                Err(e) => {
                    http_text(
                        &mut stream,
                        "500 Internal Server Error",
                        "text/plain",
                        &format!("cannot write temp copy: {e}"),
                    );
                    return;
                }
            };
            use std::io::Write;
            let mut written: u64 = 0;
            let mut failed = false;
            if n > hdr_end {
                if f.write_all(&rbuf[hdr_end..n]).is_err() {
                    failed = true;
                }
                written += (n - hdr_end) as u64;
            }
            let mut chunk = [0u8; 64 * 1024];
            while !failed && written < clen {
                match stream.read(&mut chunk) {
                    Ok(0) => break,
                    Ok(k) => {
                        let take = std::cmp::min(k as u64, clen - written) as usize;
                        if f.write_all(&chunk[..take]).is_err() {
                            failed = true;
                            break;
                        }
                        written += take as u64;
                    }
                    Err(_) => {
                        failed = true;
                        break;
                    }
                }
            }
            drop(f);
            if failed || written < clen {
                let _ = std::fs::remove_file(&target);
                http_text(
                    &mut stream,
                    "500 Internal Server Error",
                    "text/plain",
                    "upload interrupted",
                );
                return;
            }
            if let Ok(mut g) = cv.lock() {
                *g = Some(target);
            }
            if let Ok(mut c) = conv.lock() {
                c.state = "idle".into();
                c.pct = 0;
                c.msg.clear();
            }
            http_json(
                &mut stream,
                &serde_json::json!({"ok": true, "name": name}).to_string(),
            );
            return;
        }
        "/video" => {}
        _ => {
            let _ = stream.write_all(not_found);
            let _ = stream.flush();
            return;
        }
    }
    let path = cv.lock().ok().and_then(|g| g.clone());
    let Some(p) = path else {
        let _ = stream.write_all(not_found);
        let _ = stream.flush();
        return;
    };
    // Chromium cannot demux this container: refuse here so the page can
    // trigger the conversion flow instead of a silent media error.
    if needs_convert(&p) {
        http_text(
            &mut stream,
            "415 Unsupported Media Type",
            "text/plain",
            "container not supported by the WebView2 engine",
        );
        return;
    }
    let mut file = match std::fs::File::open(&p) {
        Ok(f) => f,
        Err(_) => {
            let _ = stream.write_all(not_found);
            let _ = stream.flush();
            return;
        }
    };
    let total = file.metadata().map(|m| m.len()).unwrap_or(0);
    let mime = video_mime(&p);

    let range = req
        .lines()
        .find(|l| l.to_ascii_lowercase().starts_with("range:"))
        .and_then(|line| {
            let spec = line.splitn(2, ':').nth(1)?.trim();
            let spec = spec.strip_prefix("bytes=")?;
            let mut seg = spec.split('-');
            let start: u64 = seg.next()?.trim().parse().ok()?;
            let end = match seg.next() {
                Some(x) if !x.trim().is_empty() => x.trim().parse::<u64>().ok()?,
                _ => total.saturating_sub(1),
            };
            let end = end.min(total.saturating_sub(1));
            if start <= end {
                Some((start, end))
            } else {
                None
            }
        });
    let (start, end, status, cr) = match range {
        Some((s, e)) => (
            s,
            e,
            "206 Partial Content",
            Some(format!("bytes {}-{}/{}", s, e, total)),
        ),
        None => (0, total.saturating_sub(1), "200 OK", None),
    };
    let len = if total == 0 { 0 } else { end - start + 1 };

    let mut head = format!(
        "HTTP/1.1 {}\r\nContent-Type: {}\r\nAccept-Ranges: bytes\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\nConnection: close\r\n",
        status, mime, len
    );
    if let Some(cr) = cr {
        head.push_str(&format!("Content-Range: {}\r\n", cr));
    }
    head.push_str("\r\n");
    if stream.write_all(head.as_bytes()).is_err() {
        return;
    }
    if method == "HEAD" || len == 0 {
        let _ = stream.flush();
        return;
    }
    if file.seek(SeekFrom::Start(start)).is_err() {
        return;
    }
    let mut remaining = len;
    let mut chunk = vec![0u8; 64 * 1024];
    while remaining > 0 {
        let want = std::cmp::min(remaining, chunk.len() as u64) as usize;
        match file.read(&mut chunk[..want]) {
            Ok(0) => break,
            Ok(n) => {
                if stream.write_all(&chunk[..n]).is_err() {
                    break;
                }
                remaining -= n as u64;
            }
            Err(_) => break,
        }
    }
    let _ = stream.flush();
}

fn main() {
    // Any panic (e.g. on the WebView IPC thread) would otherwise be silent
    // and leave the app half-dead — always leave a trace in the diag log.
    std::panic::set_hook(Box::new(|info| {
        lc_dbg(&format!("PANIC: {info}"));
    }));
    let src = env::args().nth(1);
    use std::sync::Mutex;
    
    let current_video: Arc<Mutex<Option<std::path::PathBuf>>> = Arc::new(Mutex::new(src.as_ref().map(std::path::PathBuf::from)));
    // Serve the selected file over localhost so the media pipeline can play it
    // (file:// and custom schemes are not reliably playable).
    let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    let cv = current_video.clone();
    let html_slot: Arc<Mutex<Option<String>>> = Arc::new(Mutex::new(None));
    let hs = html_slot.clone();
    let conv: Arc<Mutex<ConvState>> = Arc::new(Mutex::new(ConvState {
        state: "idle".into(),
        pct: 0,
        msg: String::new(),
    }));
    let conv_srv = conv.clone();
    std::thread::spawn(move || {
        for stream in listener.incoming().flatten() {
            let cv = cv.clone();
            let hs = hs.clone();
            let conv = conv_srv.clone();
            std::thread::spawn(move || serve_conn(stream, cv, hs, conv));
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
    let event_loop = tao::event_loop::EventLoopBuilder::<UserEvent>::with_user_event().build();
    let proxy = event_loop.create_proxy();
    let proxy_ipc = proxy.clone();
    let window = Arc::new(WindowBuilder::new()
        .with_title("PVP")
        .with_decorations(false)
        .with_inner_size(tao::dpi::LogicalSize::new(960.0, 540.0))
        .with_min_inner_size(tao::dpi::LogicalSize::new(600.0, 360.0))
        .with_window_icon(icon)
        .build(&event_loop)
        .unwrap());
    // Fit the initial window inside the screen (high-DPI / small screens).
    // NOTE: window.scale_factor() reports 1.0 before the window is first
    // shown, and GetDpiForSystem() is unreliable here, so query the real
    // per-window DPI via GetDpiForWindow and size in physical pixels.
    unsafe {
        use raw_window_handle::HasRawWindowHandle as _;
        let sw = GetSystemMetrics(0) as f64;
        let sh = GetSystemMetrics(1) as f64;
        let hwnd = match window.raw_window_handle() {
            Ok(raw_window_handle::RawWindowHandle::Win32(h)) => h.hwnd.get(),
            _ => 0,
        };
        let d = GetDpiForWindow(hwnd);
        let sc = if d > 0 { d as f64 / 96.0 } else { 1.0 };
        let w = 960f64.min(sw * 0.94 / sc).max(600f64);
        let h = 540f64.min(sh * 0.90 / sc).max(360f64);
        let pw = (w * sc) as u32;
        let ph = (h * sc) as u32;
        let _ = window.set_inner_size(tao::dpi::PhysicalSize::new(pw, ph));
        let _ = window.set_outer_position(tao::dpi::PhysicalPosition::new(
            (sw as i32 - pw as i32) / 2,
            (sh as i32 - ph as i32) / 2,
        ));
        let isz = window.inner_size();
        let _ = std::fs::write(
            "C:\\Users\\Public\\pvp_sizing_pre.txt",
            format!(
                "sw={sw} sh={sh} hwnd={hwnd} dpi={d} sc={sc} pw={pw} ph={ph} sf={} inner={}x{}",
                window.scale_factor(),
                isz.width,
                isz.height
            ),
        );
    }
    let mut html = HTML.to_string();
    html = html.replace(
        "const BAKED_VERSION='0.0.0';",
        &format!("const BAKED_VERSION='{}';", env!("CARGO_PKG_VERSION")),
    );
    let mut s = String::new();
    let stdin_piped = !io::stdin().is_terminal();
    if stdin_piped && io::stdin().lock().read_to_string(&mut s).is_ok() && !s.is_empty() {
        html = html.replace("const v=document.getElementById(\"v\");", "const v=document.getElementById(\"v\");v.src=URL.createObjectURL(new Blob([s],{type:\"video/mp4\"}));setVideoName(\"stdin\");");
    } else if let Some(path) = &src {
        let file_url = format!("http://127.0.0.1:{}/video", port);
        html = html.replace("const v=document.getElementById(\"v\");", &format!("const v=document.getElementById(\"v\");v.src=\"{}\";setVideoName(\"{}\");v.addEventListener('loadeddata',()=>{{if(window.chrome&&window.chrome.webview)window.chrome.webview.postMessage('loaded');}});v.addEventListener('error',()=>{{if(window.chrome&&window.chrome.webview)window.chrome.webview.postMessage('error:'+((v.error&&v.error.message)||'unknown'));}});v.muted=true;v.play().then(()=>{{v.muted=false;}}).catch(()=>{{}});", file_url, path.replace("\\", "\\\\")));
    }
    *html_slot.lock().unwrap() = Some(html);
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

    // Windows Live Captions provider: polls the Live Captions window via UI
    // Automation and forwards recognized text to the page as JS callbacks.
    let px_cap = proxy_ipc.clone();
    let captions: Arc<Mutex<LiveCaptionsProvider>> = Arc::new(Mutex::new(
        LiveCaptionsProvider::new(Arc::new(move |ev| {
            let code = event_to_js(&ev);
            let _ = px_cap.send_event(UserEvent::Js(code));
        })),
    ));
    let captions_ipc = captions.clone();
    let captions_loop = captions.clone();

    // Proxy used to push JS callbacks (update progress, captions, …)
    let px = proxy_ipc.clone();

    let webview = WebViewBuilder::new_with_web_context(&mut web_context)
        .with_url(format!("http://127.0.0.1:{}/", port))
        .with_devtools(true)
        .with_permission_handler(|kind| match kind {
            wry::PermissionKind::FileSystemAccess => wry::PermissionResponse::Allow,
            // The subtitle style editor enumerates installed fonts via
            // queryLocalFonts(); grant silently so the WebView2 permission
            // popup ("Use the fonts on your computer…") never appears.
            wry::PermissionKind::LocalFonts => wry::PermissionResponse::Allow,
            // navigator.clipboard (copy UPI id etc): grant silently so the
            // "See text and images copied to the clipboard" popup never appears.
            wry::PermissionKind::ClipboardRead => wry::PermissionResponse::Allow,
            _ => wry::PermissionResponse::Default,
        })
        .with_ipc_handler(move |req| {
            let body = req.body();
            if body.starts_with("fsap:") {
                let _ = std::fs::write("C:\\Users\\Public\\pvp_fsap.txt", body);
                return;
            }
            if body.starts_with("orect") {
                let _ = std::fs::write("C:\\Users\\Public\\pvp_orect.txt", body);
                return;
            }
            if body.starts_with("pl:") {
                let _ = std::fs::write("C:\\Users\\Public\\pvp_pl.txt", body);
                return;
            }
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
            
            // Handle live captions IPC messages
            if body.starts_with("{") {
                if let Ok(msg) = serde_json::from_str::<serde_json::Value>(body) {
                    if let Some(msg_type) = msg.get("type").and_then(|v| v.as_str()) {
                        match msg_type {
                            "win-min" => {
                                w2.set_minimized(true);
                            }
                            "win-max" => {
                                if w2.is_maximized() {
                                    w2.set_maximized(false);
                                } else {
                                    w2.set_maximized(true);
                                }
                            }
                            "win-close" => {
                                lc_dbg("ipc win-close");
                                captions_ipc.lock().unwrap().exit_handoff();
                                lc_dbg("win-close: handed off, exiting");
                                std::process::exit(0);
                            }
                            "win-resize" => {
                                if !w2.is_maximized() {
                                    let edge = msg.get("edge").and_then(|v| v.as_str()).unwrap_or("");
                                    let dx = msg.get("dx").and_then(|v| v.as_f64()).unwrap_or(0.0);
                                    let dy = msg.get("dy").and_then(|v| v.as_f64()).unwrap_or(0.0);
                                    let scale = w2.scale_factor();
                                    let (dxp, dyp) = (dx * scale, dy * scale);
                                    let min_w = 600.0 * scale;
                                    let min_h = 360.0 * scale;
                                    let pos_ok = w2.outer_position().is_ok();
                                    let (mut x, mut y) = match w2.outer_position() {
                                        Ok(op) => (op.x as f64, op.y as f64),
                                        Err(_) => (0.0, 0.0),
                                    };
                                    let os = w2.outer_size();
                                    let (mut w, mut h) = (os.width as f64, os.height as f64);
                                    let is_left = edge == "left" || edge.ends_with("left");
                                    let is_right = edge == "right" || edge.ends_with("right");
                                    let is_top = edge == "top" || edge.starts_with("top-");
                                    let is_bottom = edge == "bottom" || edge.starts_with("bottom-");
                                    if is_left { x += dxp; w -= dxp; }
                                    if is_right { w += dxp; }
                                    if is_top { y += dyp; h -= dyp; }
                                    if is_bottom { h += dyp; }
                                    if w < min_w {
                                        if is_left { x -= min_w - w; }
                                        w = min_w;
                                    }
                                    if h < min_h {
                                        if is_top { y -= min_h - h; }
                                        h = min_h;
                                    }
                                    if pos_ok && (is_left || is_top) {
                                        let _ = w2.set_outer_position(tao::dpi::PhysicalPosition::new(x as i32, y as i32));
                                    }
                                    let _ = w2.set_inner_size(tao::dpi::PhysicalSize::new(w as u32, h as u32));
                                }
                            }
                            // Rust downloads the release asset itself: the
                            // WebView fetch is blocked by CORS (GitHub's
                            // download host sends no Access-Control-Allow-
                            // Origin). curl.exe ships with Windows 10 1803+.
                            "update-begin" => {
                                let url = msg.get("url").and_then(|v| v.as_str()).unwrap_or("").to_string();
                                let expect = msg.get("size").and_then(|v| v.as_u64()).unwrap_or(0);
                                let tag = msg.get("tag").and_then(|v| v.as_str()).unwrap_or("").to_string();
                                let px = px.clone();
                                std::thread::spawn(move || {
                                    let out = std::env::temp_dir().join("pvp-update.exe");
                                    let _ = std::fs::remove_file(&out);
                                    let out_s = out.to_string_lossy().to_string();
                                    use std::os::windows::process::CommandExt;
                                    let spawned = std::process::Command::new("curl.exe")
                                        .args(["-L", "--fail", "-sS", "-o", &out_s, "--", &url])
                                        .creation_flags(0x0800_0000) // CREATE_NO_WINDOW
                                        .stdout(std::process::Stdio::null())
                                        .stderr(std::process::Stdio::piped())
                                        .spawn();
                                    let mut child = match spawned {
                                        Ok(c) => c,
                                        Err(e) => {
                                            let _ = px.send_event(UserEvent::Js(format!(
                                                "pvpDlError(\"curl not available ({e})\")"
                                            )));
                                            return;
                                        }
                                    };
                                    // Poll the output file for progress until curl exits.
                                    while child.try_wait().ok().flatten().is_none() {
                                        if expect > 0 {
                                            if let Ok(md) = std::fs::metadata(&out) {
                                                let pct = (md.len() as f64 / expect as f64 * 100.0).min(99.0);
                                                let _ = px.send_event(UserEvent::Js(format!(
                                                    "pvpDlProgress({pct:.0})"
                                                )));
                                            }
                                        } else {
                                            let _ = px.send_event(UserEvent::Js("pvpDlProgress(-1)".into()));
                                        }
                                        std::thread::sleep(std::time::Duration::from_millis(400));
                                    }
                                    let mut err_tail = String::new();
                                    if let Some(mut e) = child.stderr.take() {
                                        use std::io::Read as _;
                                        let _ = e.read_to_string(&mut err_tail);
                                    }
                                    let code = child.wait().map(|s| s.code().unwrap_or(-1)).unwrap_or(-1);
                                    let len = std::fs::metadata(&out).map(|m| m.len()).unwrap_or(0);
                                    let size_ok = len > 0 && (expect == 0 || len == expect);
                                    let newer = parse_ver(&tag) > parse_ver(env!("CARGO_PKG_VERSION"));
                                    let ok = code == 0 && size_ok && newer;
                                    if ok {
                                        let _ = px.send_event(UserEvent::Js("pvpInstallReady(true)".into()));
                                    } else {
                                        let _ = std::fs::remove_file(&out);
                                        let reason = if code != 0 {
                                            let t = err_tail
                                                .lines()
                                                .rev()
                                                .find(|l| !l.trim().is_empty())
                                                .unwrap_or("")
                                                .trim()
                                                .to_string();
                                            if t.is_empty() {
                                                format!("curl exit {code}")
                                            } else if t.chars().count() > 160 {
                                                t.chars().rev().take(160).collect::<String>().chars().rev().collect()
                                            } else {
                                                t
                                            }
                                        } else if !size_ok {
                                            "file size mismatch".to_string()
                                        } else {
                                            "not newer than this build".to_string()
                                        };
                                        let esc = reason.replace('\\', "\\\\").replace('"', "\\\"");
                                        let _ = px.send_event(UserEvent::Js(format!(
                                            "pvpDlError(\"{esc}\")"
                                        )));
                                    }
                                });
                            }
                            "update-cancel" => {
                                let _ = std::fs::remove_file(std::env::temp_dir().join("pvp-update.exe"));
                            }
                            "update-run" => {
                                let tag = msg.get("tag").and_then(|v| v.as_str()).unwrap_or("");
                                let mut launched = false;
                                if parse_ver(tag) > parse_ver(env!("CARGO_PKG_VERSION")) {
                                    let src = std::env::temp_dir().join("pvp-update.exe");
                                    if let Ok(dst) = std::env::current_exe() {
                                        if src.exists() {
                                            let src_s = src.to_string_lossy().replace('\'', "''");
                                            let dst_s = dst.to_string_lossy().replace('\'', "''");
                                            let ps = format!(
                                                "$src='{src}';$dst='{dst}';for($i=0;$i -lt 60;$i++){{try{{Copy-Item -LiteralPath $src -Destination $dst -Force -ErrorAction Stop;break}}catch{{Start-Sleep -Milliseconds 500}}}};Start-Process -FilePath $dst",
                                                src = src_s,
                                                dst = dst_s
                                            );
                                            use std::os::windows::process::CommandExt;
                                            let spawned = std::process::Command::new("powershell.exe")
                                                .args(["-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-Command", &ps])
                                                .creation_flags(0x08000000)
                                                .spawn();
                                            launched = spawned.is_ok();
                                        }
                                    }
                                }
                                if launched {
                                    let _ = px.send_event(UserEvent::Js("pvpInstallLaunching()".into()));
                                } else {
                                    let _ = px.send_event(UserEvent::Js("pvpUpdateRejected()".into()));
                                }
                            }
                            "quit" => {
                                lc_dbg("ipc quit");
                                captions_ipc.lock().unwrap().exit_handoff();
                                lc_dbg("quit: handed off, exiting");
                                std::process::exit(0);
                            }
                            "live-captions-init" => {
                                lc_dbg("ipc live-captions-init");
                                let cap = probe();
                                let lang = current_language();
                                let run = captions_ipc.lock().unwrap().is_running();
                                let _ = px.send_event(UserEvent::Js(format!(
                                    "pvpCaptionInit({{\"ok\":{},\"m\":{},\"lang\":{},\"run\":{}}})",
                                    if cap.supported { "true" } else { "false" },
                                    json_str(&cap.reason),
                                    json_str(&lang),
                                    if run { "true" } else { "false" }
                                )));
                            }
                            "live-captions-enable" => {
                                lc_dbg("ipc live-captions-enable");
                                captions_ipc.lock().unwrap().start();
                            }
                            "live-captions-disable" => {
                                lc_dbg("ipc live-captions-disable");
                                captions_ipc.lock().unwrap().stop();
                            }
                            "live-captions-language" => {
                                lc_dbg("ipc live-captions-language");
                                if let Some(lang) = msg.get("lang").and_then(|v| v.as_str()) {
                                    captions_ipc.lock().unwrap().set_language(lang);
                                }
                            }
                            "live-captions-models" => {
                                lc_dbg("ipc live-captions-models");
                                let px2 = px.clone();
                                std::thread::spawn(move || {
                                    let installed = speech_models_installed();
                                    let active = current_language();
                                    let arr = installed
                                        .iter()
                                        .map(|t| format!("\"{}\"", t))
                                        .collect::<Vec<_>>()
                                        .join(",");
                                    let _ = px2.send_event(UserEvent::Js(format!(
                                        "pvpCaptionModels({{\"installed\":[{}],\"active\":{}}})",
                                        arr,
                                        json_str(&active)
                                    )));
                                });
                            }
                            "live-captions-model-install" => {
                                lc_dbg("ipc live-captions-model-install");
                                if let Some(lang) = msg.get("lang").and_then(|v| v.as_str()) {
                                    if let Err(e) = start_speech_op("install", lang) {
                                        lc_dbg(&format!("speech install spawn failed: {e}"));
                                    }
                                }
                            }
                            "live-captions-model-delete" => {
                                lc_dbg("ipc live-captions-model-delete");
                                if let Some(lang) = msg.get("lang").and_then(|v| v.as_str()) {
                                    if lang != current_language() {
                                        if let Err(e) = start_speech_op("delete", lang) {
                                            lc_dbg(&format!("speech delete spawn failed: {e}"));
                                        }
                                    } else {
                                        lc_dbg("speech delete skipped: language in use");
                                    }
                                }
                            }
                            _ => {}
                        }
                    }
                }
            }
        })
        .with_document_title_changed_handler(move |title| {
            w.set_title(&title);
        })
        .build(&*window)
        .unwrap();
    
    let wfit = window.clone();
    let mut fitted = false;
    event_loop.run(move |event, _, control_flow| {
        *control_flow = ControlFlow::Wait;
        if !fitted {
            if let Event::MainEventsCleared = event {
                fitted = true;
                unsafe {
                    use raw_window_handle::HasRawWindowHandle as _;
                    let hwnd = match wfit.raw_window_handle() {
                        Ok(raw_window_handle::RawWindowHandle::Win32(h)) => h.hwnd.get(),
                        _ => 0,
                    };
                    let d = GetDpiForWindow(hwnd);
                    let sc = if d > 0 { d as f64 / 96.0 } else { wfit.scale_factor() };
                    let mut rc = RECT::default();
                    SystemParametersInfoW(0x0030, 0, &mut rc as *mut RECT, 0);
                    let sw = (rc.right - rc.left) as f64;
                    let sh = (rc.bottom - rc.top) as f64;
                    let w = 960f64.min(sw * 0.94 / sc).max(600f64);
                    let h = 540f64.min(sh * 0.90 / sc).max(360f64);
                    let pw = (w * sc) as u32;
                    let ph = (h * sc) as u32;
                    let _ = wfit.set_inner_size(tao::dpi::PhysicalSize::new(pw, ph));
                    let _ = wfit.set_outer_position(tao::dpi::PhysicalPosition::new(
                        rc.left + (sw as i32 - pw as i32) / 2,
                        rc.top + (sh as i32 - ph as i32) / 2,
                    ));
                    let os = wfit.outer_size();
                    let isz = wfit.inner_size();
                    let _ = std::fs::write(
                        "C:\\Users\\Public\\pvp_sizing.txt",
                        format!(
                            "d={d} hwnd={hwnd} sc={sc} pw={pw} ph={ph} work={}x{}+{}+{} outer={}x{} inner={}x{}",
                            sw, sh, rc.left, rc.top, os.width, os.height, isz.width, isz.height
                        ),
                    );
                }
            }
        }
        match event {
            Event::UserEvent(UserEvent::Js(code)) => {
                let _ = webview.evaluate_script(&code);
            }
            Event::WindowEvent { event: WindowEvent::CloseRequested, .. } => {
                lc_dbg("event close-requested");
                captions_loop.lock().unwrap().exit_handoff();
                lc_dbg("close-requested: handed off");
                *control_flow = ControlFlow::Exit;
            }
            _ => {}
        }
    });
}





