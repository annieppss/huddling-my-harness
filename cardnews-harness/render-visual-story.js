const page=await figma.getNodeByIdAsync(DATA.target.pageId);
if(!page||page.type!=='PAGE'||!DATA.target.allowedWritePageIds.includes(page.id))throw new Error('대상 페이지 오류');
await figma.setCurrentPageAsync(page);
const name=`${DATA.run_id} · v${DATA.version} · 람이 비주얼 스토리 · 6장`;
if(page.children.some(n=>n.name===name))throw new Error('이미 존재하는 결과부터 확인하세요.');
for(const style of ['Heavy','Bold','Regular'])await figma.loadFontAsync({family:'SUIT',style});
await figma.loadFontAsync({family:'DotGothic16',style:'Regular'});
const ids=[],keep=n=>(ids.push(n.id),n),assetNodes=[];
const C={bg:'#202321',panel:'#343A35',cream:'#FFF7E8',mint:'#A6E6BD',lime:'#B8F58B',pink:'#EF65B0',white:'#FAFBF7',muted:'#B8C7BC',ink:'#202B24'};
const rgb=h=>({r:parseInt(h.slice(1,3),16)/255,g:parseInt(h.slice(3,5),16)/255,b:parseInt(h.slice(5,7),16)/255});
const fill=h=>[{type:'SOLID',color:rgb(h)}];
function rect(p,n,x,y,w,h,c,r=0){const a=keep(figma.createRectangle());p.appendChild(a);a.name=n;a.x=x;a.y=y;a.resize(w,h);a.fills=c?fill(c):[];a.cornerRadius=r;return a;}
function stack(p,n,w,gap=0,pad=0,c=null){const a=keep(figma.createAutoLayout('VERTICAL'));p.appendChild(a);a.name=n;a.resize(w,100);a.primaryAxisSizingMode='AUTO';a.counterAxisSizingMode='FIXED';a.itemSpacing=gap;a.paddingTop=a.paddingBottom=a.paddingLeft=a.paddingRight=pad;a.fills=c?fill(c):[];a.clipsContent=false;return a;}
function txt(p,n,v,w,sz=48,lh=64,c=C.white,style='Regular',family='SUIT'){const a=keep(figma.createText());p.appendChild(a);a.name=n;a.fontName={family,style};a.characters=v;a.fontSize=sz;a.lineHeight={unit:'PIXELS',value:lh};a.fills=fill(c);a.textAutoResize='HEIGHT';a.resize(w,Math.max(lh,a.height));return a;}
function at(p,n,v,x,y,w,sz,lh,c,style='Regular',center=false){const a=txt(p,n,v,w,sz,lh,c,style);a.x=x;a.y=y;if(center)a.textAlignHorizontal='CENTER';return a;}
function svg(p,n,x,y,w,h,body){const a=keep(figma.createNodeFromSvg(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${body}</svg>`));p.appendChild(a);a.name=n;a.x=x;a.y=y;for(const b of a.findAll())ids.push(b.id);return a;}
function arrow(p,x,y,w=84,h=72,color=C.mint){return svg(p,'편집 가능한 화살표',x,y,w,h,`<path d="M8 ${h/2} H${w-14} M${w-32} ${h/2-20} L${w-12} ${h/2} L${w-32} ${h/2+20}" fill="none" stroke="${color}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>`);}
function scribble(p,x,y,w,h){return svg(p,'손그림 강조',x,y,w,h,`<path d="M${w*.3} 10 C-25 0,-15 ${h-6},${w*.5} ${h-8} C${w+35} ${h+8},${w+18} -5,${w*.28} 10 M${w*.35} 5 C${w*.85} -5,${w+8} 22,${w-10} ${h*.6}" fill="none" stroke="${C.pink}" stroke-width="5" stroke-linecap="round"/>`);}
function asset(p,key,x,y,w,h){const a=rect(p,`람이 포즈 / ${key}`,x,y,w,h,null);if(DATA.asset_hashes?.[key])a.fills=[{type:'IMAGE',imageHash:DATA.asset_hashes[key],scaleMode:'FIT'}];assetNodes.push({key,node_id:a.id});return a;}
function bubble(p,v,x,y,w){const b=stack(p,'고민 말풍선',w,0,24,C.cream);b.x=x;b.y=y;b.cornerRadius=30;txt(b,'핵심',v,w-48,48,64,C.ink,'Bold');return b;}
function title(f,s){const h=stack(f,'장 제목',936,0);h.x=72;h.y=164;const t=txt(h,'제목',s.title,936,68,84,C.mint,'Heavy');t.textAlignHorizontal='CENTER';return h;}
function note(f,s,y=1100){const n=stack(f,'짧은 풀이',936,0,24,C.panel);n.x=72;n.y=y;n.cornerRadius=24;const t=txt(n,'도입',s.body_blocks.join('\n'),888,48,64,C.white);t.textAlignHorizontal='CENTER';return n;}
function twoImages(f,y,size=400,labels=true){const x1=72,x2=608;rect(f,'그림 바탕 / 시작',x1,y,size,size,C.cream,28);rect(f,'그림 바탕 / 실행',x2,y,size,size,C.cream,28);const a=asset(f,'submit',x1+8,y+8,size-16,size-16);asset(f,'notification',x2+8,y+8,size-16,size-16);arrow(f,492,y+size/2-36);if(labels){at(f,'핵심','설문이 오면',x1,y+size+24,size,48,64,C.white,'Bold',true);at(f,'핵심','알림 보내기',x2,y+size+24,size,48,64,C.white,'Bold',true);}return a;}
const right=page.children.reduce((a,n)=>Math.max(a,n.x+n.width),0);const group=stack(page,name,3560,160);group.x=right+160;group.y=160;
const frames=[];for(let r=0;r<2;r++){const row=keep(figma.createAutoLayout('HORIZONTAL'));group.appendChild(row);row.resize(3560,1350);row.itemSpacing=160;row.fills=[];row.name=`행 ${r+1}`;for(let j=0;j<3;j++){const f=keep(figma.createFrame());row.appendChild(f);f.resize(1080,1350);f.fills=fill(C.bg);f.clipsContent=true;frames.push(f);}}
const out=[];
for(let i=0;i<6;i++){
 const f=frames[i],s=DATA.slides[i];f.name=`${String(i+1).padStart(2,'0')} · ${s.role}`;f.exportSettings=[{format:'PNG',constraint:{type:'SCALE',value:1}}];
 rect(f,'브랜드 픽셀',72,79,12,12,C.mint);rect(f,'브랜드 픽셀',91,79,12,12,C.mint);
 at(f,'보조 라벨','RAMY / AUTOMATION',124,72,680,28,36,C.muted);at(f,'장식 장수',`${String(i+1).padStart(2,'0')} / 06`,896,72,112,24,32,C.muted);
 let mascot;
 if(i===0){
   at(f,'보조 라벨','한눈에 보는 자동화의 시작',72,180,936,36,48,C.mint,'Bold',true);
   mascot=twoImages(f,314,400,true);
   scribble(f,92,714,356,90);scribble(f,626,714,356,90);
   const h=stack(f,'표지 하단 제목',936,24);h.x=72;h.y=890;const t=txt(h,'제목',s.title,936,80,96,C.white,'Heavy');t.setRangeFills(s.title.indexOf('\n')+1,s.title.length,fill(C.mint));txt(h,'도입',s.body_blocks.join('\n'),936,48,64,C.muted);
 }else if(i===1){
   title(f,s);bubble(f,'트리거부터? 액션부터?',90,380,700);bubble(f,'뭘 먼저 정하지?',476,528,530);
   mascot=asset(f,'thinking',230,630,620,470);
   at(f,'보조 라벨','?',122,686,120,104,128,C.pink,'Heavy',true);at(f,'보조 라벨','?',878,812,110,90,110,C.mint,'Heavy',true);
   note(f,s,1110);
 }else if(i===2){
   title(f,s);at(f,'핵심','트리거',72,390,400,56,72,C.mint,'Heavy',true);at(f,'핵심','액션',608,390,400,56,72,C.mint,'Heavy',true);
   scribble(f,145,372,254,104);scribble(f,684,372,254,104);
   mascot=twoImages(f,520,400,true);note(f,s,1060);
 }else if(i===3){
   title(f,s);mascot=asset(f,'submit',72,406,640,610);
   const w=stack(f,'응답 도착 / 도식',354,20,24,C.cream);w.x=654;w.y=510;w.cornerRadius=20;
   txt(w,'보조 라벨','FORM / RECEIVED',306,28,36,C.ink,'Bold');txt(w,'핵심','응답 1건',306,56,72,C.ink,'Heavy');
   const check=txt(w,'핵심','✓ 도착',306,48,64,'#376B4B','Bold');
   scribble(f,744,566,224,104);arrow(f,570,852,340,72,C.pink);
   at(f,'핵심','시작 신호!',650,947,358,48,64,C.mint,'Heavy',true);note(f,s,1110);
 }else if(i===4){
   title(f,s);
   const w=stack(f,'발송할 알림 / 도식',450,22,24,C.cream);w.x=72;w.y=486;w.cornerRadius=24;
   txt(w,'보조 라벨','MESSAGE / SEND',402,28,36,C.ink,'Bold');
   const env=svg(w,'편집 가능한 봉투',0,0,150,100,`<rect x="4" y="4" width="142" height="92" rx="12" fill="${C.mint}" stroke="${C.ink}" stroke-width="6"/><path d="M8 12L75 59L142 12" fill="none" stroke="${C.ink}" stroke-width="6"/>`);
   txt(w,'핵심','새 응답 도착!',402,48,64,C.ink,'Heavy');
   mascot=asset(f,'notification',460,410,548,610);
   arrow(f,188,874,340,72,C.pink);at(f,'핵심','자동으로 전송',72,968,430,48,64,C.mint,'Heavy',true);note(f,s,1110);
 }else{
   title(f,s);
   at(f,'핵심','트리거 · 시작',72,400,400,48,68,C.mint,'Heavy',true);at(f,'핵심','액션 · 실행',608,400,400,48,68,C.mint,'Heavy',true);
   mascot=twoImages(f,500,400,true);
   const n=note(f,s,1060);
 }
 at(f,'장식 푸터',i===5?'저장해두고, 내 자동화에 써봐요.':'설명용 가상 예시 · 출처: Zapier 공식 도움말',72,1250,936,26,34,C.muted);
 out.push({order:i+1,frame_id:f.id,bounds:f.absoluteBoundingBox,mascot_id:mascot.id,role_layout:s.layout,template_reference:s.template_reference,layout_issue:false,texts:f.findAllWithCriteria({types:['TEXT']}).map(n=>({id:n.id,name:n.name,characters:n.characters,font_size:n.fontSize,bounds:n.absoluteBoundingBox}))});
}
return {run_id:DATA.run_id,version:DATA.version,page_id:page.id,container_id:group.id,createdNodeIds:ids,mutatedNodeIds:[],frames:out,asset_nodes:assetNodes};
