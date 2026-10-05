const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const tg = window.Telegram?.WebApp;
try { tg?.ready(); tg?.expand(); tg?.setHeaderColor?.('#050805'); tg?.setBackgroundColor?.('#050805'); } catch (_) {}

const state = { home:null, config:null, current:null, screen:'home', searchTimer:null };
const STORE_FAV='xd_kino_favorites_v1';
const STORE_HISTORY='xd_kino_history_v1';

function loadStore(key){ try{return JSON.parse(localStorage.getItem(key)||'[]')}catch{return []} }
function saveStore(key,val){ localStorage.setItem(key,JSON.stringify(val)); }
function esc(v){ return String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function num(v){ const m=String(v??'').match(/(?:10(?:\.0+)?|[0-9](?:\.\d+)?)/); return m?Number(m[0]):0; }
function formatViews(v){ v=Number(v||0); if(v>=1e6)return (v/1e6).toFixed(v>=1e7?0:1)+'M'; if(v>=1e3)return (v/1e3).toFixed(v>=1e4?0:1)+'K'; return String(v); }
async function api(url,opts){ const r=await fetch(url,opts); if(!r.ok){let d='';try{d=(await r.json()).detail||''}catch{} throw new Error(d||`HTTP ${r.status}`)} return r.json(); }
function toast(msg){ const el=$('#toast'); el.textContent=msg; el.classList.add('show'); clearTimeout(toast.t); toast.t=setTimeout(()=>el.classList.remove('show'),1700); }

function movieCard(item){
  return `<article class="movie-card" data-movie="${Number(item.code)}">
    <div class="movie-poster"><img src="${esc(item.poster_url)}" alt="${esc(item.name)}" loading="lazy"><span class="badge">${esc(item.content_type||'Kino')}</span>${item.imdb?`<span class="badge imdb-badge">★ ${esc(item.imdb)}</span>`:''}</div>
    <div class="movie-name">${esc(item.name)}</div><div class="movie-sub">${esc(item.year||'')} ${item.views!=null?'• '+formatViews(item.views)+' ko‘rish':''}</div>
  </article>`;
}
function storyCard(item){ return `<article class="story-item" data-movie="${Number(item.code)}"><div class="story-poster"><img src="${esc(item.poster_url)}" alt="${esc(item.name)}" loading="lazy"></div><div class="story-title">${esc(item.name)}</div><div class="story-imdb">★ IMDb ${esc(item.imdb||'—')}</div></article>`; }

function renderHero(item){
  const hero=$('#hero');
  if(!item){hero.classList.remove('skeleton');hero.innerHTML='<div class="hero-content"><h1>xD KINO</h1><div class="hero-meta">Katalog hozircha bo‘sh</div></div>';return}
  hero.classList.remove('skeleton'); hero.style.setProperty('--hero-img',`url("${item.poster_url}")`);
  hero.innerHTML=`<div class="hero-content"><div class="hero-kicker">xD KINO tavsiya qiladi</div><h1>${esc(item.name)}</h1><div class="hero-meta"><span>${esc(item.year||'')}</span><span>${esc(item.content_type||'Kino')}</span><span>${esc(item.genre||'')}</span>${item.imdb?`<b>★ IMDb ${esc(item.imdb)}</b>`:''}</div><div class="hero-actions"><button class="primary-btn" data-movie="${Number(item.code)}">▶ Ko‘rish</button><button class="ghost-btn" data-movie="${Number(item.code)}">Batafsil</button></div></div>`;
}
function renderHome(data){
  state.home=data; renderHero(data.featured?.[0]);
  $('#storyStrip').innerHTML=(data.stories||[]).map(storyCard).join('')||'<div class="empty">IMDb 7.5+ tavsiyalar hali yo‘q.</div>';
  $('#genreStrip').innerHTML=(data.genres||[]).map(g=>`<button class="genre-chip" data-genre="${esc(g)}">${esc(g)}</button>`).join('');
  $('#homeSections').innerHTML=(data.sections||[]).filter(s=>s.items?.length).map(s=>`<section class="content-section"><div class="section-head"><h2>${esc(s.title)}</h2></div><div class="movie-row">${s.items.map(movieCard).join('')}</div></section>`).join('');
}

function fillSelect(id,items,label){ const el=$(id); el.innerHTML=`<option value="">${label}</option>`+(items||[]).map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join(''); }
async function initFilters(){ try{const x=await api('/api/filter-options'); fillSelect('#typeFilter',x.types,'Barcha turlar');fillSelect('#genreFilter',x.genres,'Barcha janrlar');fillSelect('#yearFilter',x.years,'Barcha yillar');fillSelect('#countryFilter',x.countries,'Barcha davlatlar');}catch{} }
async function runSearch(){
  const p=new URLSearchParams(); const q=$('#searchInput').value.trim(); if(q)p.set('q',q);
  [['#typeFilter','content_type'],['#genreFilter','genre'],['#yearFilter','year'],['#countryFilter','country']].forEach(([id,k])=>{const v=$(id).value;if(v)p.set(k,v)}); p.set('sort','popular');p.set('limit','60');
  $('#searchStatus').textContent='Qidirilmoqda…';
  try{const d=await api('/api/movies?'+p); $('#searchStatus').textContent=`${d.total} ta natija`; $('#searchGrid').innerHTML=d.items.length?d.items.map(movieCard).join(''):'<div class="empty">Hech narsa topilmadi.</div>';}
  catch(e){$('#searchStatus').textContent='';$('#searchGrid').innerHTML=`<div class="error-box">${esc(e.message)}</div>`}
}

function favoriteItems(){ return loadStore(STORE_FAV); }
function historyItems(){ return loadStore(STORE_HISTORY); }
function isFavorite(code){ return favoriteItems().some(x=>Number(x.code)===Number(code)); }
function toggleFavorite(item){ let list=favoriteItems(); const exists=list.some(x=>Number(x.code)===Number(item.code)); list=exists?list.filter(x=>Number(x.code)!==Number(item.code)):[item,...list].slice(0,80);saveStore(STORE_FAV,list);updateCounts();return !exists; }
function addHistory(item){ let list=historyItems().filter(x=>Number(x.code)!==Number(item.code)); list.unshift(item); saveStore(STORE_HISTORY,list.slice(0,50)); updateCounts(); }
function renderSaved(){ const list=favoriteItems(); $('#savedGrid').innerHTML=list.length?list.map(movieCard).join(''):'<div class="empty">Hali hech narsa saqlanmagan.</div>'; }
function renderHistory(){ const list=historyItems(); $('#historyRow').innerHTML=list.length?list.map(movieCard).join(''):'<div class="empty">Tarix bo‘sh.</div>'; }
function updateCounts(){ $('#favCount').textContent=favoriteItems().length; $('#historyCount').textContent=historyItems().length; }

async function openMovie(code){
  try{
    const item=await api(`/api/movie/${code}`); state.current=item; addHistory(item); fetch(`/api/view/${code}`,{method:'POST'}).catch(()=>{});
    const fav=isFavorite(code); const qualities=(item.qualities||[]).length?item.qualities:['Mavjud'];
    $('#detailBody').innerHTML=`<div class="detail-hero" style="--detail-img:url('${esc(item.poster_url)}')"></div><div class="detail-content"><h2>${esc(item.name)}</h2><div class="detail-meta"><span>${esc(item.year||'—')}</span><span>${esc(item.country||'—')}</span><span>${esc(item.content_type||'Kino')}</span><span class="score">★ IMDb ${esc(item.imdb||'—')}</span><span>${formatViews(item.views)} ko‘rish</span></div><div class="description">${esc(item.description||'Ushbu kino uchun tavsif hali kiritilmagan.')}</div><div class="quality-row">${qualities.map(q=>`<span class="quality">${esc(q)}</span>`).join('')}</div><div class="detail-actions"><button id="watchNow" class="watch-btn">▶ Botda ko‘rish</button><button id="favNow" class="fav-btn ${fav?'on':''}" aria-label="Saqlash">${fav?'♥':'♡'}</button></div></div>`;
    $('#detailOverlay').classList.add('open'); $('#detailOverlay').setAttribute('aria-hidden','false');
    $('#favNow').onclick=()=>{const on=toggleFavorite(item);$('#favNow').classList.toggle('on',on);$('#favNow').textContent=on?'♥':'♡';toast(on?'Saqlandi':'Saqlanganlardan olib tashlandi');if(state.screen==='saved')renderSaved();};
    $('#watchNow').onclick=()=>openBot(item.code);
  }catch(e){ toast(e.message); }
}
function closeDetail(){ $('#detailOverlay').classList.remove('open');$('#detailOverlay').setAttribute('aria-hidden','true'); }
function openBot(code){ const u=state.config?.bot_username||'xDKinoCodeBot';const p=state.config?.bot_start_prefix||'movie_';const url=`https://t.me/${encodeURIComponent(u)}?start=${encodeURIComponent(p+code)}`;try{if(tg?.openTelegramLink)tg.openTelegramLink(url);else location.href=url}catch{location.href=url} }

function showScreen(name){
  state.screen=name; $$('.screen').forEach(x=>x.classList.remove('active')); $(`#${name}Screen`)?.classList.add('active'); $$('.nav-btn').forEach(b=>b.classList.toggle('active',b.dataset.screen===name));
  if(name==='search'){setTimeout(()=>$('#searchInput').focus(),80);if(!$('#searchGrid').children.length)runSearch()}
  if(name==='saved')renderSaved(); if(name==='profile'){renderHistory();updateCounts()}
  window.scrollTo({top:0,behavior:'smooth'});
}

function initProfile(){ const user=tg?.initDataUnsafe?.user; if(user){const name=[user.first_name,user.last_name].filter(Boolean).join(' ')||'Telegram foydalanuvchisi'; $('#profileName').textContent=name;$('#profileUser').textContent=user.username?'@'+user.username:'Telegram foydalanuvchisi'; const letter=(user.first_name||user.username||'D').slice(0,1).toUpperCase();$('#avatar').textContent=letter;$('#profileAvatar').textContent=letter;} }

function bind(){
  document.addEventListener('click',e=>{const m=e.target.closest('[data-movie]');if(m){openMovie(Number(m.dataset.movie));return}const g=e.target.closest('[data-genre]');if(g){showScreen('search');$('#genreFilter').value=g.dataset.genre;runSearch();return}const s=e.target.closest('[data-screen]');if(s){showScreen(s.dataset.screen);}});
  $('#searchShortcut').onclick=()=>showScreen('search');$('#detailClose').onclick=closeDetail;$('#detailOverlay').addEventListener('click',e=>{if(e.target===$('#detailOverlay'))closeDetail()});
  $('#searchInput').addEventListener('input',()=>{clearTimeout(state.searchTimer);state.searchTimer=setTimeout(runSearch,280)}); $$('.filters select').forEach(x=>x.addEventListener('change',runSearch));
  $('#clearHistory').onclick=()=>{saveStore(STORE_HISTORY,[]);renderHistory();updateCounts();toast('Tarix tozalandi')};
}

async function boot(){
  bind();initProfile();updateCounts();initFilters();
  try{const [home,config]=await Promise.all([api('/api/home'),api('/api/config')]);state.config=config;renderHome(home);}catch(e){$('#homeScreen').innerHTML=`<div class="error-box"><b>Katalog yuklanmadi.</b><br>${esc(e.message)}</div>`}
  setTimeout(()=>$('#splash').classList.add('done'),350);
}
window.addEventListener('load',boot);
setTimeout(()=>$('#splash')?.classList.add('done'),5000);
