/* Company AI — Layan Realtime v12 — window-level voice interception */
(function(){
'use strict';
var active=false,wrapped=false,observer=null;
function root(){return document.getElementById('layanRealtimeHotfix');}
function keepAlive(){var r=root();if(!active||!r)return;if(!r.isConnected)document.body.appendChild(r);r.classList.add('open');r.style.display='block';}
function isVoiceTarget(el){if(!el)return false;var x=el.closest&&el.closest('button,[role="button"],a,[onclick],.voiceChoice,.layanChoice.voiceChoice,.layanQuickVoice');if(!x)return false;var t=((x.innerText||x.textContent||'')+' '+(x.getAttribute('aria-label')||'')+' '+(x.getAttribute('title')||'')+' '+(x.className||'')).toLowerCase();return /voice|audio|speak|talk|live|صوت|صوتي|صوتية|محادثة صوت|دردشة صوت|تكلم|تحدث/.test(t)}
function installObserver(){if(observer)return;observer=new MutationObserver(function(){if(active)keepAlive()});observer.observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['class','style']});}
function wrap(){if(wrapped||typeof window.startLayanVoice!=='function')return;wrapped=true;var start=window.startLayanVoice,stop=window.stopLayanVoice;window.startLayanVoice=function(){active=true;installObserver();keepAlive();return start.apply(this,arguments)};window.openLayanVoice=window.startLayanVoice;window.stopLayanVoice=function(){active=false;return stop.apply(this,arguments)};window.closeLayanVoice=window.stopLayanVoice;window.toggleLayanVoice=function(){if(active){active=false;return stop.apply(this,arguments)}active=true;installObserver();return start.apply(this,arguments)};keepAlive()}
function intercept(){['pointerdown','mousedown','touchstart','click'].forEach(function(type){window.addEventListener(type,function(e){var r=root();if(r&&r.contains(e.target))return;if(isVoiceTarget(e.target)){e.preventDefault();e.stopPropagation();if(e.stopImmediatePropagation)e.stopImmediatePropagation();if(type==='pointerdown'||type==='mousedown'||type==='touchstart'){try{window.startLayanVoice()}catch(err){console.error('Layan v12 start failed',err)}}}},true)})}
function wait(){wrap();if(!wrapped)setTimeout(wait,20)}
intercept();wait();
})();
