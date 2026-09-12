/* Company AI — Layan Realtime v11 stability guard */
(function(){
'use strict';
var active=false,userStop=false,wrapped=false,observer=null;
function root(){return document.getElementById('layanRealtimeHotfix');}
function keepAlive(){
 var r=root();
 if(!active||!r)return;
 if(!r.isConnected){document.body.appendChild(r);}
 r.classList.add('open');
 r.style.display='block';
}
function installObserver(){
 if(observer)return;
 observer=new MutationObserver(function(){ if(active) keepAlive(); });
 observer.observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['class','style']});
}
function wrap(){
 if(wrapped||typeof window.startLayanVoice!=='function')return;
 wrapped=true;
 var start=window.startLayanVoice;
 var stop=window.stopLayanVoice;
 window.startLayanVoice=function(){
   userStop=false; active=true; installObserver();
   var r=keepAlive();
   try{return start.apply(this,arguments);}catch(e){active=false;throw e;}
 };
 window.openLayanVoice=window.startLayanVoice;
 window.stopLayanVoice=function(){
   if(!userStop && active){ console.warn('Layan v11 ignored external stop while live'); return; }
   active=false;
   return stop.apply(this,arguments);
 };
 window.closeLayanVoice=function(){userStop=true;active=false;return stop.apply(this,arguments);};
 window.toggleLayanVoice=function(){ if(active){userStop=true;active=false;return stop.apply(this,arguments);} userStop=false;active=true;installObserver();return start.apply(this,arguments); };
 var events=['pointerdown','pointerup','mousedown','mouseup','touchstart','touchend','click'];
 events.forEach(function(type){
   window.addEventListener(type,function(e){
     var r=root();
     if(r&&r.contains(e.target)){
       if(e.target.closest&&e.target.closest('#lhClose,#lhEnd')){userStop=true;active=false;return;}
       e.stopPropagation();
       if(e.stopImmediatePropagation)e.stopImmediatePropagation();
     }
   },true);
 });
 keepAlive();
}
function wait(){wrap();if(!wrapped)setTimeout(wait,25);}
wait();
})();
