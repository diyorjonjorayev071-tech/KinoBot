'use strict';

const tg = window.Telegram?.WebApp;
const initData = tg?.initData || '';
const initUser = tg?.initDataUnsafe?.user || null;
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const state = {
  config: { bot_username: 'xDKinoCodeBot' },
  user: initUser,
  home: null,
  genres: [],
  currentView: 'home',
  heroIndex: 0,
  heroTimer: null,
  currentMovie: null,
  favorites: new Set(),
  search: { q: '', genre: '', country: '', sort: 'popular', page: 1, total: 0 },
};

if (tg) {
  tg.ready();
  tg.expand();
  tg.setHeaderColor?.('#080a13');
  tg.setBackgroundColor?.('#080a13');
  tg.setBottomBarColor?.('#080a13');
}

function authHeaders() {
  return initData ? { 'X-Telegram-Init-Data': initData } : {};
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    let message = `Xatolik: ${response.status}`;
    try { message = (await response.json()).detail || message; } catch (_) {}
    throw new Error(message);
  }
  return response.json();
}

function posterUrl(code) {
  return `/api/poster/${encodeURIComponent(code)}`;
}

function haptic(type = 'selection') {
  if (type === 'success') tg?.HapticFeedback?.notificationOccurred?.('success');
  else tg?.HapticFeedback?.selectionChanged?.();
}

function fullName(user) {
  return [user?.first_name, user?.last_name].filter(Boolean).join(' ') || 'Telegram foydalanuvchisi';
}

function firstLetter(user) {
  return (user?.first_name?.[0] || user?.username?.[0] || 'D').toUpperCase();
}

function setAvatar(element, user) {
  element.textContent = firstLetter(user);
  const url = user?.photo_url;
  if (url) {
    element.style.backgroundImage = `url("${String(url).replaceAll('"', '%22')}")`;
    element.textContent = '';
  } else {
    element.style.backgroundImage = '';
  }
}

function movieCard(movie) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'movie-card';

  const posterWrap = document.createElement('span');
  posterWrap.className = 'poster-wrap';
  const image = document.createElement('img');
  image.className = 'poster';
  image.loading = 'lazy';
  image.alt = movie.name || 'Kino posteri';
  image.src = posterUrl(movie.code);
  image.onerror = () => { image.src = '/static/placeholder.svg'; };
  const code = document.createElement('span');
  code.className = 'code-label';
  code.textContent = `#${movie.code}`;
  posterWrap.append(image, code);

  const title = document.createElement('span');
  title.className = 'card-title';
  title.textContent = movie.name || 'Nomsiz kino';
  const meta = document.createElement('span');
  meta.className = 'card-meta';
  meta.textContent = [movie.year, movie.genre].filter(Boolean).join(' • ') || 'Kino';
  button.append(posterWrap, title, meta);
  button.addEventListener('click', () => openMovie(movie.code));
  return button;
}

function renderSkeletons(container, count = 6) {
  container.replaceChildren();
  for (let i = 0; i < count; i += 1) {
    const card = document.createElement('div');
    card.className = 'movie-card';
    card.innerHTML = '<span class="poster-wrap skeleton"></span><span class="card-title skeleton">&nbsp;</span><span class="card-meta skeleton">&nbsp;</span>';
    container.append(card);
  }
}

function renderMovieList(container, items) {
  container.replaceChildren(...(items || []).map(movieCard));
}

function renderStories(items) {
  const strip = $('#storyStrip');
  strip.replaceChildren();
  (items || []).slice(0, 10).forEach((movie) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'story-item';
    const ring = document.createElement('span');
    ring.className = 'story-ring';
    const image = document.createElement('img');
    image.className = 'story-image';
    image.loading = 'lazy';
    image.alt = movie.name || 'Tavsiya';
    image.src = posterUrl(movie.code);
    image.onerror = () => { image.src = '/static/placeholder.svg'; };
    const code = document.createElement('span');
    code.className = 'story-code';
    code.textContent = `#${movie.code}`;
    ring.append(image, code);
    const label = document.createElement('small');
    label.textContent = movie.name || `#${movie.code}`;
    button.append(ring, label);
    button.addEventListener('click', () => openMovie(movie.code));
    strip.append(button);
  });
}

function setHero(index) {
  const slides = state.home?.featured || [];
  if (!slides.length) return;
  state.heroIndex = (index + slides.length) % slides.length;
  const movie = slides[state.heroIndex];
  $('#heroCarousel').classList.remove('skeleton-block');
  $('#heroBackdrop').style.backgroundImage = `url("${posterUrl(movie.code)}")`;
  $('#heroTitle').textContent = movie.name || 'xD KINO';
  $('#heroMeta').textContent = [movie.year, movie.country, movie.genre].filter(Boolean).join(' • ');
  $('#heroWatch').onclick = () => watchMovie(movie.code);
  $('#heroInfo').onclick = () => openMovie(movie.code);
  $$('.hero-dot').forEach((dot, dotIndex) => dot.classList.toggle('active', dotIndex === state.heroIndex));
}

function resetHeroTimer() {
  clearInterval(state.heroTimer);
  state.heroTimer = setInterval(() => setHero(state.heroIndex + 1), 5200);
}

function renderHero(items) {
  const dots = $('#heroDots');
  dots.replaceChildren();
  (items || []).forEach((_, index) => {
    const dot = document.createElement('span');
    dot.className = `hero-dot${index === 0 ? ' active' : ''}`;
    dots.append(dot);
  });
  setHero(0);
  resetHeroTimer();
}

function renderGenres(items) {
  state.genres = items || [];
  const strip = $('#genreStrip');
  const chips = $('#searchChips');
  strip.replaceChildren();
  chips.replaceChildren();

  const allChip = createChip('Barchasi', '');
  allChip.classList.add('active');
  chips.append(allChip);

  state.genres.slice(0, 14).forEach((item) => {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'genre-card';
    const strong = document.createElement('strong');
    strong.textContent = item.genre;
    card.append(strong);
    card.addEventListener('click', () => {
      state.search.genre = item.genre;
      openView('search');
      searchMovies(true);
    });
    strip.append(card);
    chips.append(createChip(item.genre, item.genre));
  });
}

function createChip(label, value) {
  const chip = document.createElement('button');
  chip.type = 'button';
  chip.className = 'chip';
  chip.textContent = label;
  chip.addEventListener('click', () => {
    state.search.genre = value;
    $$('#searchChips .chip').forEach((item) => item.classList.toggle('active', item === chip));
    searchMovies(true);
  });
  return chip;
}

function renderSections(sections) {
  const root = $('#homeSections');
  root.replaceChildren();
  (sections || []).forEach((section) => {
    const wrapper = document.createElement('section');
    wrapper.className = 'content-block';
    const heading = document.createElement('div');
    heading.className = 'section-heading';
    const title = document.createElement('h2');
    title.textContent = section.title;
    const all = document.createElement('button');
    all.type = 'button';
    all.textContent = 'Barchasi →';
    all.addEventListener('click', () => {
      state.search = {
        q: '',
        genre: section.filters?.genre || '',
        country: section.filters?.country || '',
        sort: section.filters?.sort || 'popular',
        page: 1,
        total: 0,
      };
      openView('search');
      searchMovies(true);
    });
    heading.append(title, all);
    const row = document.createElement('div');
    row.className = 'movie-row';
    renderMovieList(row, section.items);
    wrapper.append(heading, row);
    root.append(wrapper);
  });
}

async function loadHome() {
  try {
    const data = await api('/api/home');
    state.home = data;
    renderStories(data.stories || data.popular || []);
    renderHero(data.featured || data.popular || []);
    renderGenres(data.genres || []);
    renderSections(data.sections || [
      { title: '🔥 Ommabop', items: data.popular || [], filters: { sort: 'popular' } },
      { title: '✨ Yangi qo‘shilganlar', items: data.new || [], filters: { sort: 'new' } },
    ]);
    $('#searchTotal').textContent = `${data.sections?.find((item) => item.key === 'new')?.total || 91} ta`;
  } catch (error) {
    showToast(error.message);
  }
}

function openView(name) {
  state.currentView = name;
  ['home', 'search', 'profile'].forEach((view) => {
    $(`#${view}View`).classList.toggle('hidden', view !== name);
  });
  $$('.nav-item').forEach((item) => item.classList.toggle('active', item.dataset.nav === name));
  window.scrollTo({ top: 0, behavior: 'smooth' });
  haptic();
  if (name === 'profile') loadProfile();
  if (name === 'search' && !$('#searchGrid').children.length) searchMovies(true);
}

async function searchMovies(reset = true) {
  if (reset) state.search.page = 1;
  const params = new URLSearchParams({
    q: state.search.q,
    genre: state.search.genre,
    country: state.search.country,
    sort: state.search.sort,
    page: String(state.search.page),
    limit: '24',
  });
  const grid = $('#searchGrid');
  if (reset) renderSkeletons(grid, 9);
  $('#emptyState').classList.add('hidden');
  try {
    const data = await api(`/api/movies?${params}`);
    state.search.total = data.total;
    if (reset) grid.replaceChildren();
    data.items.forEach((movie) => grid.append(movieCard(movie)));
    $('#searchCount').textContent = `${data.total} ta`;
    $('#searchHeading').textContent = state.search.q
      ? `“${state.search.q}” natijalari`
      : (state.search.genre || state.search.country || 'Tavsiyalar');
    $('#loadMore').classList.toggle('hidden', grid.children.length >= data.total);
    $('#emptyState').classList.toggle('hidden', data.total !== 0);
    if (!data.total) grid.replaceChildren();
  } catch (error) {
    showToast(error.message);
  }
}

async function loadFavoritesCache() {
  if (!initData) return;
  try {
    const data = await api('/api/favorites');
    state.favorites = new Set(data.items.map((movie) => Number(movie.code)));
  } catch (_) {}
}

async function openMovie(code) {
  try {
    const movie = await api(`/api/movies/${code}`);
    state.currentMovie = movie;
    $('#modalCode').textContent = `#${movie.code}`;
    $('#modalTitle').textContent = movie.name || 'Kino';
    $('#modalMeta').textContent = [movie.year, movie.country, movie.language, movie.imdb ? `IMDb ${movie.imdb}` : ''].filter(Boolean).join(' • ');
    $('#modalGenre').textContent = movie.genre || 'Janr ko‘rsatilmagan';
    $('#modalPoster').style.backgroundImage = `url("${posterUrl(movie.code)}")`;
    const qualities = $('#qualityList');
    qualities.replaceChildren();
    (movie.qualities?.length ? movie.qualities : ['Original']).forEach((quality) => {
      const pill = document.createElement('span');
      pill.className = 'quality-pill';
      pill.textContent = quality;
      qualities.append(pill);
    });
    const favorite = state.favorites.has(Number(movie.code));
    $('#favoriteButton').classList.toggle('active', favorite);
    $('#favoriteButton').textContent = favorite ? '♥' : '♡';
    $('#modalWatch').onclick = () => watchMovie(movie.code);
    $('#favoriteButton').onclick = () => toggleFavorite(movie.code);
    $('#movieModal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    tg?.BackButton?.show?.();
  } catch (error) {
    showToast(error.message);
  }
}

function closeMovie() {
  $('#movieModal').classList.add('hidden');
  document.body.style.overflow = '';
  tg?.BackButton?.hide?.();
}

async function toggleFavorite(code) {
  if (!initData) {
    showToast('Sevimlilar Telegram Mini App ichida ishlaydi.');
    return;
  }
  const numericCode = Number(code);
  const enabled = !state.favorites.has(numericCode);
  try {
    await api('/api/favorites', { method: 'POST', body: JSON.stringify({ movie_code: numericCode, enabled }) });
    if (enabled) state.favorites.add(numericCode); else state.favorites.delete(numericCode);
    $('#favoriteButton').classList.toggle('active', enabled);
    $('#favoriteButton').textContent = enabled ? '♥' : '♡';
    haptic('success');
  } catch (error) {
    showToast(error.message);
  }
}

async function watchMovie(code) {
  if (initData) api('/api/history', { method: 'POST', body: JSON.stringify({ movie_code: Number(code) }) }).catch(() => {});
  const link = `https://t.me/${state.config.bot_username}?start=movie_${code}`;
  if (tg?.openTelegramLink) tg.openTelegramLink(link);
  else window.location.href = link;
}

async function loadProfile() {
  const fallback = state.user || initUser;
  setAvatar($('#profileAvatar'), fallback);
  $('#profileName').textContent = fullName(fallback);
  $('#profileUsername').textContent = fallback?.username ? `@${fallback.username}` : 'Username mavjud emas';
  $('#profileId').textContent = fallback?.id ? String(fallback.id) : '—';
  if (!initData) return;
  try {
    const data = await api('/api/profile');
    state.user = { ...fallback, ...data, id: data.user_id };
    setAvatar($('#profileAvatar'), state.user);
    setAvatar($('#topAvatar'), state.user);
    $('#profileName').textContent = fullName(state.user);
    $('#profileUsername').textContent = data.username ? `@${data.username}` : 'Username mavjud emas';
    $('#profileId').textContent = String(data.user_id || '—');
    $('#profileBalance').textContent = `${Number(data.balance || 0).toLocaleString('uz-UZ')} so‘m`;
    $('#profilePlan').textContent = data.plan || 'Bepul';
    $('#favoritesCount').textContent = `${data.favorites_count || 0} ta kino`;
    $('#historyCount').textContent = `${data.history_count || 0} ta yozuv`;
  } catch (error) {
    showToast(error.message);
  }
}

async function loadCollection(type) {
  if (!initData) {
    showToast('Bu bo‘lim Telegram Mini App ichida ishlaydi.');
    return;
  }
  const title = type === 'favorites' ? 'Sevimlilar' : 'Tomosha tarixi';
  $('#collectionTitle').textContent = title;
  $('#profileCollection').classList.remove('hidden');
  renderSkeletons($('#collectionGrid'), 6);
  $('#collectionEmpty').classList.add('hidden');
  try {
    const data = await api(type === 'favorites' ? '/api/favorites' : '/api/history');
    renderMovieList($('#collectionGrid'), data.items);
    $('#collectionEmpty').classList.toggle('hidden', data.items.length !== 0);
  } catch (error) {
    showToast(error.message);
  }
}

function openBot() {
  const link = `https://t.me/${state.config.bot_username}`;
  if (tg?.openTelegramLink) tg.openTelegramLink(link);
  else window.location.href = link;
}

let toastTimer;
function showToast(message) {
  const toast = $('#toast');
  toast.textContent = message;
  toast.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.add('hidden'), 3200);
}

let searchTimer;
$('#searchInput').addEventListener('input', (event) => {
  state.search.q = event.target.value.trim();
  state.search.country = '';
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => searchMovies(true), 320);
});
$('#clearSearch').addEventListener('click', () => {
  $('#searchInput').value = '';
  state.search.q = '';
  state.search.genre = '';
  state.search.country = '';
  state.search.sort = 'popular';
  $$('#searchChips .chip').forEach((chip, index) => chip.classList.toggle('active', index === 0));
  searchMovies(true);
});
$('#topSearch').addEventListener('click', () => { openView('search'); setTimeout(() => $('#searchInput').focus(), 100); });
$('#topAvatar').addEventListener('click', () => openView('profile'));
$('#allGenres').addEventListener('click', () => { openView('search'); $('#searchInput').focus(); });
$('#heroPrev').addEventListener('click', () => { setHero(state.heroIndex - 1); resetHeroTimer(); });
$('#heroNext').addEventListener('click', () => { setHero(state.heroIndex + 1); resetHeroTimer(); });
$('#modalClose').addEventListener('click', closeMovie);
$('#modalBackdrop').addEventListener('click', closeMovie);
$('#loadMore').addEventListener('click', () => { state.search.page += 1; searchMovies(false); });
$('#profileFavorites').addEventListener('click', () => loadCollection('favorites'));
$('#profileHistory').addEventListener('click', () => loadCollection('history'));
$('#openBot').addEventListener('click', openBot);
$('#closeCollection').addEventListener('click', () => $('#profileCollection').classList.add('hidden'));
$$('[data-nav]').forEach((button) => button.addEventListener('click', () => openView(button.dataset.nav)));

tg?.BackButton?.onClick?.(closeMovie);
document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeMovie(); });

async function boot() {
  setAvatar($('#topAvatar'), state.user);
  const minimumSplash = new Promise((resolve) => setTimeout(resolve, 650));
  try {
    const configPromise = api('/api/config').then((data) => { state.config = data; }).catch(() => {});
    await Promise.all([configPromise, loadHome(), loadFavoritesCache(), minimumSplash]);
  } finally {
    $('#splash').classList.add('done');
    setTimeout(() => $('#splash').remove(), 450);
  }
}

boot();
