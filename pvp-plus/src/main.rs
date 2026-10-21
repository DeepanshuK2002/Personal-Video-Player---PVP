#![windows_subsystem = "windows"]
use std::env;
use std::sync::{Arc, Mutex};
use tao::event::{Event, WindowEvent};
use tao::event_loop::{ControlFlow, EventLoop};
use tao::window::WindowBuilder;
use std::io::{self, Read, Write, IsTerminal};
use wry::WebViewBuilder;
#[cfg(windows)]
use wry::WebViewBuilderExtWindows;

mod captions;

use captions::{
    current_language, event_to_js, json_str, probe, CaptionProvider, LiveCaptionsProvider,
};

const HTML: &str = r####"<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
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
.pl-toast{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(0,0,0,.78);color:#fff;padding:14px 22px;border-radius:10px;font-size:15px;opacity:0;transition:opacity .3s;pointer-events:none;z-index:30;white-space:nowrap}
.pl-toast.show{opacity:1}
.volind{position:fixed;top:44px;right:12px;background:rgba(0,0,0,.6);color:#fff;padding:8px 14px;border-radius:8px;font-size:22px;font-weight:600;opacity:0;transition:opacity .4s;pointer-events:none;z-index:20}

/* CC button */
.ccbtn{background:transparent;border:none;color:#fff;cursor:pointer;display:flex;align-items:center;padding:4px;border-radius:4px;transition:background 0.15s}
.ccbtn:hover{background:rgba(255,255,255,0.1)}
.ccbtn.active{background:rgba(116,192,252,0.2)}
.ccbtn svg{width:20px;height:20px;fill:none}
.ccbtn.active .ccb{fill:rgb(116,192,252);stroke:rgb(116,192,252)}

/* Settings menu - click to toggle */
.brandmark-wrap{position:relative}
#settingsmenu{display:none;position:absolute;bottom:44px;left:0;background:#222;padding:8px;border-radius:8px;min-width:240px;max-width:300px;max-height:calc(100vh - 130px);overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:#555 transparent;z-index:20;box-shadow:0 4px 20px rgba(0,0,0,0.5)}
#settingsmenu.show{display:block}
#settingsmenu::-webkit-scrollbar{width:8px}
#settingsmenu::-webkit-scrollbar-thumb{background:#555;border-radius:4px}
#settingsmenu::-webkit-scrollbar-track{background:transparent}
.settings-section{padding:8px 0;border-bottom:1px solid #333}
.settings-section:last-child{border-bottom:none}
.settings-section h4{font-size:11px;text-transform:uppercase;color:#888;margin:0 0 8px;padding:0 4px;letter-spacing:0.5px}
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
.live-caption-line{
    background:rgba(18, 18, 18, 0.85);
    color:rgb(116, 192, 252);
    font-family:system-ui, sans-serif;
    font-size:16px;
    line-height:1.3;
    padding:6px 12px;
    border-radius:6px;
    margin:3px 0;
    max-width:85%;
    margin-left:auto;
    margin-right:auto;
    text-align:center;
    box-shadow:0 2px 6px rgba(0,0,0,0.4);
    animation:captionFadeIn 0.2s ease-out;
    word-wrap:break-word;
    border:1px solid rgba(116, 192, 252, 0.3);
}
.live-caption-line.partial{
    opacity:0.7;
}
.live-caption-line.final{
    opacity:1;
}
@keyframes captionFadeIn{
    from{opacity:0;transform:translateY(10px);}
    to{opacity:1;transform:translateY(0);}
}
.live-captions-settings{
    background:#222;
    border-radius:8px;
    padding:12px;
    margin-top:8px;
    min-width:240px;
    max-width:300px;
}
.live-captions-settings h4{
    font-size:11px;
    text-transform:uppercase;
    color:#888;
    margin:0 0 8px;
    letter-spacing:0.5px;
}
.live-captions-settings .setting-row{
    display:flex;
    align-items:center;
    gap:8px;
    margin:8px 0;
}
.live-captions-settings .setting-row label{
    min-width:100px;
    font-size:12px;
    color:#ccc;
}
.live-captions-settings .setting-row input[type="range"]{
    flex:1;
}
.live-captions-settings .setting-row select{
    flex:1;
    background:#333;
    border:none;
    color:#fff;
    padding:4px 8px;
    border-radius:4px;
}
.live-captions-settings .setting-row input[type="color"]{
    width:40px;
    height:28px;
    border:none;
    border-radius:4px;
    cursor:pointer;
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
.sub-line{background:var(--sub-bg,rgba(0,0,0,.7));color:inherit;font-weight:inherit;font-size:inherit;font-family:inherit;line-height:1.35;padding:.15em .55em;border-radius:4px;max-width:88%;text-align:center;white-space:pre-wrap;word-wrap:break-word}

/* Subtitle style popup */
.style-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:29;display:none}
.style-backdrop.show{display:block}
.style-popup{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);width:350px;max-width:92vw;max-height:86vh;overflow-y:auto;background:#222;border:1px solid #383838;border-radius:10px;z-index:30;display:none;box-shadow:0 8px 30px rgba(0,0,0,.6)}
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
.cc-live-state{font-size:10px;letter-spacing:.5px;color:#888;padding:2px 7px;border:1px solid #444;border-radius:9px;flex-shrink:0}
.cc-live-state.on{color:#000;background:rgb(116,192,252);border-color:rgb(116,192,252);font-weight:600}
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
#ver-row{display:flex;align-items:center;justify-content:space-between;padding:3px 4px 8px;gap:6px}
#ver-text{font-size:11.5px;color:#8ab4d8;letter-spacing:.4px;font-weight:600}
button.upd-icon{background:transparent;border:none;padding:3px;border-radius:4px;display:flex;cursor:pointer;color:rgb(116,192,252)}
button.upd-icon:hover{background:rgba(116,192,252,.18)}
button.upd-icon svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}

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
    <button id="tb-min" title="Minimize"><svg viewBox="0 0 24 24"><path d="M5 12h14"/></svg></button>
    <button id="tb-max" title="Maximize"><svg viewBox="0 0 24 24"><rect x="5" y="5" width="14" height="14" rx="1"/></svg></button>
    <button id="tb-close" title="Close"><svg viewBox="0 0 24 24"><path d="M6 6l12 12"/><path d="M18 6 6 18"/></svg></button>
  </div>
</div>
<video id="v"></video>
<div class="live-captions-overlay hidden" id="live-captions-overlay"></div>
<div id="suboverlay"></div>
<input type="file" id="f" accept="video/*" style="display:none">
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
        <div id="ver-row"><span id="ver-text">PVP+ v0.4.0</span><button class="upd-icon" id="ver-upd" title="Update available" hidden><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 8v8"/><path d="m8 12 4 4 4-4"/></svg></button></div>
        <div class="settings-section">
          <h4>Playback Speed</h4>
          <div class="speed-options" id="speedmenu"></div>
        </div>
        <div class="settings-section">
          <h4 class="section-head"><span>Subtitles</span><button class="palette-btn" id="pal-sub-set" title="Subtitle style"><svg viewBox="0 0 24 24"><path d="M12 22a1 1 0 0 1 0-20 10 9 0 0 1 10 9 5 5 0 0 1-5 5h-2.25a1.75 1.75 0 0 0-1.4 2.8l.3.4a1.75 1.75 0 0 1-1.4 2.8z"/><circle cx="13.5" cy="6.5" r=".5"/><circle cx="17.5" cy="10.5" r=".5"/><circle cx="6.5" cy="12.5" r=".5"/><circle cx="8.5" cy="7.5" r=".5"/></svg></button></h4>
          <div id="subtitle-menu-set"></div>
          <button class="external-track-btn" id="load-subtitle-btn-set">
            <svg class="menu-icon" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
            Load subtitle file
          </button>
        </div>
        <div class="settings-section">
          <h4>Audio Tracks</h4>
          <div id="audio-menu"></div>
          <button class="external-track-btn" id="load-audio-btn">
            <svg class="menu-icon" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
            Load audio file
          </button>
        </div>
        <div class="settings-section live-captions-settings">
          <h4 class="section-head"><span>Live Captions</span><button class="palette-btn" id="pal-cap" title="Text style"><svg viewBox="0 0 24 24"><path d="M12 22a1 1 0 0 1 0-20 10 9 0 0 1 10 9 5 5 0 0 1-5 5h-2.25a1.75 1.75 0 0 0-1.4 2.8l.3.4a1.75 1.75 0 0 1-1.4 2.8z"/><circle cx="13.5" cy="6.5" r=".5"/><circle cx="17.5" cy="10.5" r=".5"/><circle cx="6.5" cy="12.5" r=".5"/><circle cx="8.5" cy="7.5" r=".5"/></svg></button></h4>
          <div class="setting-row">
            <label>Language</label>
            <select id="live-captions-lang">
              <option value="en-US">English (US)</option>
              <option value="en-IN">English (India)</option>
              <option value="en-GB">English (UK)</option>
              <option value="es-ES">Spanish</option>
              <option value="fr-FR">French</option>
              <option value="de-DE">German</option>
              <option value="it-IT">Italian</option>
              <option value="ja-JP">Japanese</option>
              <option value="ko-KR">Korean</option>
              <option value="zh-CN">Chinese (Simplified)</option>
            </select>
          </div>
          <div class="setting-row">
            <label>Position</label>
            <select id="live-captions-position">
              <option value="bottom">Bottom</option>
              <option value="top">Top</option>
              <option value="center">Center</option>
            </select>
          </div>
          <div class="setting-row">
            <label>Max Lines</label>
            <input type="range" id="live-captions-max-lines" min="1" max="5" value="3">
            <span id="live-captions-max-lines-value">3</span>
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
  <div class="cc-row" id="cc-live"><svg viewBox="0 0 24 24"><path d="M12 6v12"/><path d="m17 8-10 8"/><path d="m7 8 10 8"/></svg><span>Live subtitle</span><span class="cc-live-state" id="cc-live-state">OFF</span></div>
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
let speed=1,showRemaining=false,timer=null,volTimer=null,spdTimer=null,isMuted=false,prevVol=1,hudReady=false;
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
function applyVolume(val){val=Math.max(0,Math.min(2,val));ensureAudio();if(gainNode)gainNode.gain.value=val;try{v.volume=Math.min(1,val);}catch(e){}vol.value=val;const pct=(val/2*100);vol.style.background="linear-gradient(to top, rgb(116,192,252) "+pct+"%, rgba(128,128,128,0.35) "+pct+"%)";const ind=document.getElementById("volind");ind.textContent=Math.round(val*100)+"%";spdind.classList.remove("show");clearTimeout(spdTimer);if(hudReady){ind.style.opacity=1;clearTimeout(volTimer);volTimer=setTimeout(()=>ind.style.opacity=0,900);}if(val>0){if(isMuted){isMuted=false;document.getElementById("volbtn").innerHTML=VOLUME;}prevVol=val;}else if(val===0){document.getElementById("volbtn").innerHTML=MUTE;isMuted=true;}}
vol.oninput=()=>applyVolume(+vol.value);
function setMute(m){isMuted=m;if(m){prevVol=+vol.value||prevVol;applyVolume(0);document.getElementById("volbtn").innerHTML=MUTE;}else{applyVolume(prevVol||1);document.getElementById("volbtn").innerHTML=VOLUME;}}
document.getElementById("volbtn").onclick=e=>{e.stopPropagation();setMute(!isMuted);}

let isFs=false;
function setFs(on){isFs=on;fsbtn.innerHTML=on?FS_EXIT:FS;document.body.classList.toggle("fs",on);}
fsbtn.onclick=e=>{e.stopPropagation();if(window.chrome&&window.chrome.webview)window.chrome.webview.postMessage("fullscreen");setFs(!isFs);};
document.addEventListener("fullscreenchange",()=>{fsbtn.innerHTML=document.fullscreenElement?FS_EXIT:FS;});

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
function closeAllMenus(){openmenu.hidden=true;ccmenu.hidden=true;plmenu.hidden=true;const sm=document.getElementById('sort-menu');if(sm)sm.hidden=true;}
function positionMenu(m,a){m.hidden=false;const r=a.getBoundingClientRect(),mr=m.getBoundingClientRect();
 let left=r.left+r.width/2-mr.width/2;
 left=Math.max(6,Math.min(left,innerWidth-mr.width-6));
 m.style.left=left+"px";
 m.style.top="auto";
 m.style.bottom=(innerHeight-r.top+8)+"px";}
document.getElementById("open").onclick=e=>{e.stopPropagation();const show=openmenu.hidden;closeAllMenus();
 if(show){positionMenu(openmenu,document.getElementById("open"));openmenu.hidden=false;
  try{postMsg("orect:"+JSON.stringify([document.getElementById("om-video").getBoundingClientRect(),document.getElementById("om-playlist").getBoundingClientRect()]));}catch(err){}}};
document.getElementById("om-video").onclick=e=>{e.stopPropagation();openmenu.hidden=true;document.getElementById("f").click();};
document.getElementById("om-playlist").onclick=e=>{e.stopPropagation();openmenu.hidden=true;pickFolderPlaylist();};
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
v.addEventListener('seeked',()=>{renderSubOverlay();pvpCaptionClear();});

function pvpCaptionInit(d){
  lcAvailable=!!d.ok;
  lcUnavailableReason=d.m||'';
  const sel=document.getElementById('live-captions-lang');
  if(sel&&d.lang){try{sel.value=d.lang;liveCaptionsLanguage=d.lang;}catch(e){}}
  const row=document.getElementById('cc-live');
  if(row){
    row.classList.toggle('disabled',!lcAvailable);
    if(!lcAvailable)row.title=lcUnavailableReason||'Live Captions is not available on this system';
  }
  if(!lcAvailable&&liveCaptionsEnabled){liveCaptionsEnabled=false;lcSetUi(false);updateCcActive();}
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
    if(st&&liveCaptionsEnabled){st.textContent='ERR';st.classList.remove('on');}
    return;
  }
  if(d.s==='closed'){
    if(lcRestarting){
      lcRestarting=false;
      if(st&&liveCaptionsEnabled){st.textContent='…';st.classList.add('on');}
      return;
    }
    liveCaptionsEnabled=false;lcSetUi(false);updateCcActive();
    return;
  }
  if(d.s==='setup'){
    if(st&&liveCaptionsEnabled){st.textContent='…';st.classList.add('on');}
    return;
  }
  if(d.s==='ready'){
    if(st&&liveCaptionsEnabled){st.textContent='ON';st.classList.add('on');}
    return;
  }
}
function pvpCaptionUpdate(d){
  if(!liveCaptionsEnabled||!d||!d.t)return;
  const line=document.createElement('div');
  line.className='live-caption-line '+(d.f?'final':'partial');
  line.textContent=d.t;
  liveCaptionsOverlay.textContent='';
  liveCaptionsOverlay.appendChild(line);
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
    const st=document.getElementById('cc-live-state');
    if(st){st.textContent='…';st.classList.add('on');}
    liveCaptionsOverlay.classList.remove('top','center','bottom');
    liveCaptionsOverlay.classList.add(liveCaptionsPosition);
    liveCaptionsOverlay.classList.remove('hidden');
    pvpCaptionClear();
    postMsg({type:'live-captions-enable'});
  }
  updateCcActive();
}

// Live Captions Settings Event Listeners
document.getElementById('live-captions-lang')?.addEventListener('change', e=>{
  liveCaptionsLanguage=e.target.value;
  if(liveCaptionsEnabled){
    lcRestarting=true;
    const st=document.getElementById('cc-live-state');
    if(st){st.textContent='…';st.classList.add('on');}
  }
  postMsg({type:'live-captions-language',lang:liveCaptionsLanguage});
});

document.getElementById('live-captions-position')?.addEventListener('change', e=>{
  liveCaptionsPosition=e.target.value;
  if(liveCaptionsEnabled){
    liveCaptionsOverlay.classList.remove('top', 'center', 'bottom');
    liveCaptionsOverlay.classList.add(liveCaptionsPosition);
  }
});

document.getElementById('live-captions-max-lines')?.addEventListener('input', e=>{
  liveCaptionsMaxLines=parseInt(e.target.value);
  document.getElementById('live-captions-max-lines-value').textContent=liveCaptionsMaxLines;
});

// ===== Subtitle style editor =====
const SUBSTYLE_DEFAULT={family:'Segoe UI',weight:'600',size:18,color:'#ffffff',bg:'#000000',bgOpacity:70,shadow:2,shadowColor:'#000000',outline:1,outlineColor:'#000000'};
let subStyle=Object.assign({},SUBSTYLE_DEFAULT);
try{const saved=JSON.parse(localStorage.getItem('pvp-substyle')||'null');if(saved)Object.assign(subStyle,saved);}catch(e){}
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
}
function escHtml(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function renderSubOverlay(){
  if(!suboverlay)return;
  if(styleOpen){
    suboverlay.innerHTML='<div class="sub-line">Sample subtitle &mdash; The quick brown fox jumps over the lazy dog</div>';
    suboverlay.classList.add('show');
    return;
  }
  if(!currentSubtitleTrack){suboverlay.innerHTML='';suboverlay.classList.remove('show');return;}
  const lines=[];
  if(externalSubtitles.includes(currentSubtitleTrack)){
    const sub=currentSubtitleTrack,t=v.currentTime-subtitleOffset;
    sub.cues.forEach(c=>{if(t>=c.start&&t<c.end)lines.push(c.text);});
  }else if(currentSubtitleTrack.activeCues){
    for(let i=0;i<currentSubtitleTrack.activeCues.length;i++)lines.push(currentSubtitleTrack.activeCues[i].text);
  }
  if(!lines.length){suboverlay.innerHTML='';suboverlay.classList.remove('show');return;}
  suboverlay.innerHTML=lines.map(t=>'<div class="sub-line">'+escHtml(t)+'</div>').join('');
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
  if(!Array.from(sel.options).some(o=>o.value===subStyle.family)){
    const o=document.createElement('option');o.value=subStyle.family;o.textContent=subStyle.family;sel.appendChild(o);
  }
  sel.value=subStyle.family;
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
  document.getElementById('st-weight').value=subStyle.weight;
  document.getElementById('st-size').value=subStyle.size;
  document.getElementById('st-size-v').textContent=subStyle.size+'px';
  document.getElementById('st-color').value=subStyle.color;
  document.getElementById('st-bg').value=subStyle.bg;
  document.getElementById('st-bgop').value=subStyle.bgOpacity;
  document.getElementById('st-bgop-v').textContent=subStyle.bgOpacity+'%';
  document.getElementById('st-shadow').value=subStyle.shadow;
  document.getElementById('st-shadow-v').textContent=subStyle.shadow;
  document.getElementById('st-shcolor').value=subStyle.shadowColor;
  document.getElementById('st-outline').value=subStyle.outline;
  document.getElementById('st-outline-v').textContent=subStyle.outline;
  document.getElementById('st-olcolor').value=subStyle.outlineColor;
}
function openStylePopup(){
  styleOpen=true;
  settingsmenu.classList.remove('show');
  closeAllMenus();
  stylepopup.classList.add('show');
  stylebackdrop.classList.add('show');
  syncStyleControls();
  renderSubOverlay();
  loadSystemFonts();
}
function closeStylePopup(){
  styleOpen=false;
  stylepopup.classList.remove('show');
  stylebackdrop.classList.remove('show');
  renderSubOverlay();
}
function bindStyleCtl(id,key,parse,spanId,suffix){
  const el=document.getElementById(id);
  el.addEventListener('input',()=>{
    subStyle[key]=parse(el.value);
    if(spanId)document.getElementById(spanId).textContent=subStyle[key]+(suffix||'');
    applySubStyle();saveSubStyle();
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
bindStyleCtl('st-outline','outline',v=>parseInt(v),'st-outline-v','');
bindStyleCtl('st-olcolor','outlineColor',v=>v);
document.querySelectorAll('.palette-btn').forEach(b=>b.onclick=e=>{e.stopPropagation();openStylePopup();});
stylebackdrop.onclick=closeStylePopup;
document.getElementById('styleclose').onclick=closeStylePopup;
document.getElementById('st-done').onclick=closeStylePopup;
document.getElementById('st-reset').onclick=()=>{
  subStyle=Object.assign({},SUBSTYLE_DEFAULT);
  syncStyleControls();applySubStyle();saveSubStyle();renderSubOverlay();
};
document.addEventListener('keydown',e=>{if(e.key==='Escape'){if(styleOpen){closeStylePopup();}else{closeUpdatePopup();closeAllMenus();}}});
applySubStyle();

// ===== Playlist (folder) support =====
const VIDEO_EXT=['mp4','mkv','webm','mov','avi','m4v','ts','flv','wmv','ogv','mpg','mpeg','3gp','m2ts'];
const SUB_EXT=['srt','vtt'];
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
let plToastTimer=null;
function showPlToast(msg){const el=document.getElementById('pl-toast');el.textContent=msg;el.classList.add('show');setTitleError(msg);clearTimeout(plToastTimer);plToastTimer=setTimeout(()=>{el.classList.remove('show');tbErr='';renderTitlebar();},2500);}
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
function isVideoFile(f){const ext=(f.name.split('.').pop()||'').toLowerCase();return (f.type&&f.type.startsWith('video/'))||VIDEO_EXT.includes(ext);}
function playStandalone(file){
  playlist.length=0;plIdx=-1;
  tbPlaylist.hidden=true;plmenu.hidden=true;
  setPlaylistName('');
  v.src=URL.createObjectURL(file);
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
document.addEventListener("wheel",e=>{const t=e.target;if(t&&t.closest&&(t.closest("#settingsmenu")||t.closest("#plmenu")))return;e.preventDefault();applyVolume(Math.max(0,Math.min(2,+vol.value+(e.deltaY<0?0.05:-0.05))));showCtl();});
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
function updB64(u8){
  let s='';const CH=0x8000;
  for(let i=0;i<u8.length;i+=CH){s+=String.fromCharCode.apply(null,u8.subarray(i,i+CH));}
  return btoa(s);
}
function updReport(total,loaded){
  const f=document.getElementById('upd-bar-fill');
  const ib=document.getElementById('upd-install');
  if(total>0){const p=Math.min(100,Math.floor(loaded/total*100));f.style.width=p+'%';ib.textContent='Downloading… '+p+'%';}
  else{f.style.width='50%';ib.textContent='Downloading…';}
}
async function startInstall(){
  if(!updateInfo||downloading||installing)return;
  downloading=true;
  const ib=document.getElementById('upd-install'),lb=document.getElementById('upd-later'),cb=document.getElementById('updclose'),status=document.getElementById('updstatus');
  ib.disabled=lb.disabled=cb.disabled=true;
  ib.textContent='Downloading…';
  document.getElementById('updbar').hidden=false;
  status.textContent='';
  try{
    const resp=await fetch(updateInfo.url,{cache:'no-store'});
    if(!resp.ok)throw new Error('HTTP '+resp.status);
    const total=parseInt(resp.headers.get('content-length')||'',10)||updateInfo.size||0;
    const reader=resp.body.getReader();
    let pending=new Uint8Array(0),loaded=0,idx=0;
    const BINSZ=256*1024;
    while(true){
      const rd=await reader.read();
      if(rd.done)break;
      const np=new Uint8Array(pending.length+rd.value.length);
      np.set(pending);np.set(rd.value,pending.length);pending=np;
      while(pending.length>=BINSZ){
        postMsg({type:'update-chunk',i:idx++,data:updB64(pending.subarray(0,BINSZ))});
        loaded+=BINSZ;pending=pending.slice(BINSZ);updReport(total,loaded);
      }
    }
    if(pending.length){postMsg({type:'update-chunk',i:idx++,data:updB64(pending)});loaded+=pending.length;}
    updReport(total,loaded);
    downloading=false;
    status.textContent='Verifying…';
    postMsg({type:'update-final',bytes:loaded,tag:updateInfo.tag});
  }catch(err){
    downloading=false;
    status.textContent='Download failed: '+((err&&err.message)||'network error');
    ib.disabled=lb.disabled=cb.disabled=false;
    ib.textContent='Retry';
  }
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

fn main() {
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
    std::thread::spawn(move || {
        use std::io::{Read, Write};
        for mut stream in listener.incoming().flatten() {
            let mut buf = [0u8; 8192];
            let n = stream.read(&mut buf).unwrap_or(0);
            let req = String::from_utf8_lossy(&buf[..n]).to_string();
            let uri = req.split_whitespace().nth(1).unwrap_or("/").to_string();
            if uri == "/" || uri.starts_with("/?") {
                let page = hs.lock().ok().and_then(|g| g.clone()).unwrap_or_default();
                if page.is_empty() {
                    let _ = stream.write_all(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n");
                } else {
                    let resp = format!(
                        "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
                        page.len()
                    );
                    let _ = stream.write_all(resp.as_bytes());
                    let _ = stream.write_all(page.as_bytes());
                }
                let _ = stream.flush();
                continue;
            }
            if !uri.starts_with("/video") {
                let _ = stream.write_all(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n");
                let _ = stream.flush();
                continue;
            }
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
Some("ts") | Some("m2ts") => "video/mp2t",
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
        "<script>",
        "<script>window.onerror=function(m,s,l,c){try{window.chrome&&window.chrome.webview.postMessage('fsap:JSERR '+m+' @'+s+' line '+l+':'+c)}catch(e){};return false;}</script><script>",
    );
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
    if env::args().any(|a| a == "--live-captions" || a == "--lc") {
        html = html.replace(
            "setTimeout(checkUpdate,1200)",
            "setTimeout(()=>{try{toggleLiveCaptions();}catch(e){}},400);setTimeout(checkUpdate,1200);var _diagN=0;var _diag=setInterval(function(){try{_diagN++;var o=document.getElementById('live-captions-overlay');var b=document.getElementById('cc-live-state');var os=o?getComputedStyle(o):null;postMsg({type:'lc-diag',m:`n=${_diagN} state=${lcState} paused=${v.paused} muted=${v.muted} t=${v.currentTime.toFixed(1)} vol=${v.volume} text=[${o?o.innerText:\"MISS\"}] disp=${os?os.display:\"?\"} badge=[${b?b.innerText:\"?\"}]`});if(_diagN>=40)clearInterval(_diag);}catch(e){postMsg({type:'lc-diag',m:'ERR '+e});clearInterval(_diag);}},1500);",
        );
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
            lc_dbg(&format!("event {}", code));
            let _ = px_cap.send_event(UserEvent::Js(code));
        })),
    ));
    let captions_ipc = captions.clone();
    let captions_loop = captions.clone();

    // State for the downloaded update file (written chunk by chunk from JS)
    let update_file: Arc<Mutex<Option<std::fs::File>>> = Arc::new(Mutex::new(None));
    let uf = update_file.clone();
    let px = proxy_ipc.clone();

    let webview = WebViewBuilder::new_with_web_context(&mut web_context)
        .with_url(format!("http://127.0.0.1:{}/", port))
        .with_devtools(true)
        .with_permission_handler(|kind| match kind {
            wry::PermissionKind::FileSystemAccess => wry::PermissionResponse::Allow,
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
                                captions_ipc.lock().unwrap().stop();
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
                            "update-chunk" => {
                                use base64::Engine as _;
                                if let Some(data) = msg.get("data").and_then(|v| v.as_str()) {
                                    if let Ok(bytes) = base64::engine::general_purpose::STANDARD.decode(data) {
                                        let mut guard = uf.lock().unwrap();
                                        if guard.is_none() {
                                            let p = std::env::temp_dir().join("pvp-update.exe");
                                            let _ = std::fs::remove_file(&p);
                                            match std::fs::File::create(&p) {
                                                Ok(f) => *guard = Some(f),
                                                Err(_) => {}
                                            }
                                        }
                                        if let Some(f) = guard.as_mut() {
                                            let _ = f.write_all(&bytes);
                                        }
                                    }
                                }
                            }
                            "update-final" => {
                                let bytes = msg.get("bytes").and_then(|v| v.as_u64()).unwrap_or(0);
                                let tag = msg.get("tag").and_then(|v| v.as_str()).unwrap_or("").to_string();
                                let mut guard = uf.lock().unwrap();
                                let mut size_ok = false;
                                if let Some(f) = guard.as_mut() {
                                    let _ = f.flush();
                                    if let Ok(md) = f.metadata() {
                                        size_ok = bytes > 0 && md.len() == bytes;
                                    }
                                }
                                *guard = None;
                                let newer = parse_ver(&tag) > parse_ver(env!("CARGO_PKG_VERSION"));
                                let ok = size_ok && newer;
                                if !ok {
                                    let _ = std::fs::remove_file(std::env::temp_dir().join("pvp-update.exe"));
                                }
                                let _ = px.send_event(UserEvent::Js(format!(
                                    "pvpInstallReady({})",
                                    if ok { "true" } else { "false" }
                                )));
                            }
                            "update-cancel" => {
                                let mut guard = uf.lock().unwrap();
                                *guard = None;
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
                                captions_ipc.lock().unwrap().stop();
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
                            "lc-diag" => {
                                let m = msg
                                    .get("m")
                                    .and_then(|v| v.as_str())
                                    .unwrap_or_default();
                                lc_dbg(&format!("js {}", m));
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
                captions_loop.lock().unwrap().stop();
                *control_flow = ControlFlow::Exit;
            }
            _ => {}
        }
    });
}





