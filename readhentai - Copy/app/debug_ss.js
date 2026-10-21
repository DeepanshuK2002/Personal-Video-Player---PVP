const m = require('./.test-build/lib/providers/source-selection.js');
function ver(p){return Object.assign({providerId:'prov-a',providerSeriesId:'series-1',providerChapterId:'ch-1',chapterNumber:'1',volumeNumber:null,title:null,language:'en',releaseGroup:null,sourceUrl:null,pageAccessCapability:'available',pageCount:20,publishedAt:new Date().toISOString()},p);}
function chapter(versions){return {id:'series-1:ch:en::num::1',seriesId:'series-1',chapterNumber:1,label:'Chapter 1',volumeNumber:null,title:null,language:'en',chapterType:'main',sourceVersions:versions,sortKey:1};}
m.resetObservations();
const chap = chapter([ver({providerId:'primary',providerChapterId:'p-1'}), ver({providerId:'secondary',providerChapterId:'s-1'})]);
console.log('ranked', m.rankVersions(chap,{}).map(r=>r.version.providerId+' eligible='+r.eligible+' score='+r.score));
m.resolveWithFallback(chap, async (v)=>{ if(v.providerId==='primary') throw new Error('primary down'); return 'pages-from-'+v.providerId;}).then(r=>console.log(JSON.stringify(r)));
