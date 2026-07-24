'use strict';

const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  tg.setHeaderColor?.('#08090d');
  tg.setBackgroundColor?.('#08090d');
  tg.disableVerticalSwipes?.();
}

const state = {
  config: { bot_username: 'xDKinoCodeBot' },
  home: null,
  currentMovie: null,
  currentView: 'home',
  selectedGenre: '',
  query: '',
  page: 1,
  total: 0,
  user: tg?.initDataUnsafe?.user || null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const initData = tg?.initData || '';

function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (initData) headers.set('X-Telegram-Init-Data', initData);
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  return fetch(path, { ...options, headers }).then(async (response) => {
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `HTTP ${response.status}`);
    }
    return response.json();
  });
}

function escapeText(value) {
  return String(value ?? '');
}

function posterUrl(code) {
  return `/api/poster/${encodeURIComponent(code)}`;
}

function movieCard(movie) {
  const button = document.createElement('button');
  button.className = 'movie-card';
  button.type = 'button';
  button.dataset.code = movie.code;

  const poster = document.createElement('div');
  poster.className = 'poster';
  const image = document.createElement('img');
  image.src = posterUrl(movie.code);
  image.alt = escapeText(movie.name);
  image.loading = 'lazy';
  image.decoding = 'async';
  image.onerror = () => { image.src = '/static/placeholder.svg'; };
  const badge = document.createElement('span');
  badge.className = 'code-badge';
  badge.textContent = `#${movie.code}`;
  poster.append(image, badge);

  const title = document.createElement('span');
  title.className = 'card-title';
  title.textContent = movie.name || 'Nomsiz kino';
  const meta = document.createElement('span');
  meta.className = 'card-meta';
  meta.textContent = [movie.year, movie.genre].filter(Boolean).join(' • ') || 'Kino';
  button.append(poster, title, meta);
  button.addEventListener('click', () => openMovie(movie.code));
  return button;
}

function renderMovies(container, movies, grid = false) {
  container.replaceChildren();
  movies.forEach((movie) => container.append(movieCard(movie)));
  if (grid && !movies.length) $('#emptyState').classList.remove('hidden');
}

function renderSkeletons(container, count = 6) {
  container.replaceChildren();
  for (let i = 0; i < count; i += 1) {
    const card = document.createElement('div');
    card.className = 'movie-card';
    card.innerHTML = '<div class="poster skeleton"></div><span class="card-title skeleton">&nbsp;</span><span class="card-meta skeleton">&nbsp;</span>';
    container.append(card);
  }
}

function setHero(movie) {
  if (!movie) return;
  const hero = $('#hero');
  hero.classList.remove('skeleton-block');
  hero.style.backgroundImage = `url("${posterUrl(movie.code)}")`;
  $('#heroTitle').textContent = movie.name;
  $('#heroMeta').textContent = [movie.year, movie.country, movie.genre].filter(Boolean).join(' • ');
  $('#heroWatch').onclick = () => watchMovie(movie.code);
  $('#heroInfo').onclick = () => openMovie(movie.code);
}

async function loadHome() {
  state.currentView = 'home';
  updateNav('home');
  $('#resultsSection').classList.add('hidden');
  $('#emptyState').classList.add('hidden');
  $$('.content-section').forEach((section) => {
    if (section.id !== 'resultsSection') section.classList.remove('hidden');
  });
  $('#hero').classList.remove('hidden');
  renderSkeletons($('#popularRow'));
  renderSkeletons($('#newRow'));
  try {
    const data = await api('/api/home');
    state.home = data;
    setHero(data.featured?.[0] || data.popular?.[0]);
    renderMovies($('#popularRow'), data.popular || []);
    renderMovies($('#newRow'), data.new || []);
  } catch (error) {
    showToast(error.message);
  }
}

async function loadGenres() {
  try {
    const data = await api('/api/genres');
    const chips = $('#genreChips');
    chips.replaceChildren();
    const all = createChip('Barchasi', '');
    all.classList.add('active');
    chips.append(all);
    data.items.slice(0, 18).forEach((item) => chips.append(createChip(item.genre, item.genre)));
  } catch (_) {
    // Katalog ishlashda davom etadi.
  }
}

function createChip(label, value) {
  const button = document.createElement('button');
  button.className = 'chip';
  button.type = 'button';
  button.textContent = label;
  button.dataset.genre = value;
  button.addEventListener('click', () => {
    state.selectedGenre = value;
    $$('.chip').forEach((chip) => chip.classList.toggle('active', chip === button));
    searchMovies(true);
  });
  return button;
}

async function searchMovies(reset = true, sort = 'popular') {
  if (reset) state.page = 1;
  const params = new URLSearchParams({
    q: state.query,
    genre: state.selectedGenre,
    sort,
    page: String(state.page),
    limit: '24',
  });
  const grid = $('#resultsGrid');
  if (reset) renderSkeletons(grid, 8);
  $('#resultsSection').classList.remove('hidden');
  $('#emptyState').classList.add('hidden');
  $('#hero').classList.add('hidden');
  $$('.content-section').forEach((section) => {
    if (section.id !== 'resultsSection') section.classList.add('hidden');
  });
  try {
    const data = await api(`/api/movies?${params}`);
    state.total = data.total;
    const existing = reset ? [] : [...grid.querySelectorAll('.movie-card')].map(() => null);
    if (reset) grid.replaceChildren();
    data.items.forEach((movie) => grid.append(movieCard(movie)));
    $('#resultsCount').textContent = `${data.total} ta`;
    $('#resultsTitle').textContent = state.query ? `“${state.query}” natijalari` : (state.selectedGenre || 'Barcha kinolar');
    $('#loadMore').classList.toggle('hidden', grid.children.length >= data.total);
    $('#emptyState').classList.toggle('hidden', data.total !== 0);
    if (!existing.length && !data.items.length) grid.replaceChildren();
  } catch (error) {
    showToast(error.message);
  }
}

async function openMovie(code) {
  try {
    const movie = await api(`/api/movies/${code}`);
    state.currentMovie = movie;
    $('#modalTitle').textContent = movie.name;
    $('#modalMeta').textContent = [movie.year, movie.country, movie.language, movie.imdb ? `IMDb ${movie.imdb}` : ''].filter(Boolean).join(' • ');
    $('#modalGenres').textContent = movie.genre || 'Janr ko‘rsatilmagan';
    $('#modalPoster').style.backgroundImage = `url("${posterUrl(movie.code)}")`;
    const qualities = $('#qualityList');
    qualities.replaceChildren();
    (movie.qualities?.length ? movie.qualities : ['Original']).forEach((quality) => {
      const pill = document.createElement('span');
      pill.className = 'quality-pill';
      pill.textContent = quality;
      qualities.append(pill);
    });
    $('#modalWatch').onclick = () => watchMovie(movie.code);
    $('#favoriteButton').onclick = () => toggleFavorite(movie.code);
    $('#favoriteButton').classList.remove('active');
    $('#favoriteButton').textContent = '♡';
    $('#movieModal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  } catch (error) {
    showToast(error.message);
  }
}

function closeMovie() {
  $('#movieModal').classList.add('hidden');
  document.body.style.overflow = '';
}

async function toggleFavorite(code) {
  if (!initData) {
    showToast('Sevimlilar uchun Mini Appni Telegram ichida oching.');
    return;
  }
  const button = $('#favoriteButton');
  const enabled = !button.classList.contains('active');
  try {
    await api('/api/favorites', {
      method: 'POST',
      body: JSON.stringify({ movie_code: code, enabled }),
    });
    button.classList.toggle('active', enabled);
    button.textContent = enabled ? '♥' : '♡';
    tg?.HapticFeedback?.notificationOccurred?.('success');
  } catch (error) {
    showToast(error.message);
  }
}

async function loadFavorites() {
  state.currentView = 'favorites';
  updateNav('favorites');
  if (!initData) {
    showToast('Sevimlilar Telegram ichida ishlaydi.');
    openProfile();
    return;
  }
  $('#hero').classList.add('hidden');
  $$('.content-section').forEach((section) => section.classList.add('hidden'));
  $('#resultsSection').classList.remove('hidden');
  $('#resultsTitle').textContent = 'Sevimlilar';
  $('#resultsCount').textContent = '';
  renderSkeletons($('#resultsGrid'), 8);
  try {
    const data = await api('/api/favorites');
    renderMovies($('#resultsGrid'), data.items, true);
    $('#resultsCount').textContent = `${data.items.length} ta`;
    $('#loadMore').classList.add('hidden');
    $('#emptyState').classList.toggle('hidden', data.items.length !== 0);
  } catch (error) {
    showToast(error.message);
  }
}

async function watchMovie(code) {
  if (initData) {
    api('/api/history', { method: 'POST', body: JSON.stringify({ movie_code: code }) }).catch(() => {});
  }
  const link = `https://t.me/${state.config.bot_username}?start=movie_${code}`;
  if (tg?.openTelegramLink) tg.openTelegramLink(link);
  else window.location.href = link;
}

function openSearch() {
  $('#searchPanel').classList.remove('hidden');
  $('#searchInput').focus();
  updateNav('search');
}

function closeSearch() {
  $('#searchPanel').classList.add('hidden');
  if (!state.query && !state.selectedGenre) loadHome();
}

function openProfile() {
  const user = state.user;
  $('#profileAvatar').textContent = (user?.first_name?.[0] || 'D').toUpperCase();
  $('#profileName').textContent = user ? [user.first_name, user.last_name].filter(Boolean).join(' ') : 'Mehmon';
  $('#profileUsername').textContent = user?.username ? `@${user.username}` : 'Telegram ichida oching';
  $('#profileSheet').classList.remove('hidden');
  updateNav('profile');
}

function closeProfile() {
  $('#profileSheet').classList.add('hidden');
  updateNav(state.currentView === 'favorites' ? 'favorites' : 'home');
}

function updateNav(action) {
  $$('.nav-item').forEach((item) => item.classList.toggle('active', item.dataset.action === action));
}

let toastTimer;
function showToast(message) {
  const toast = $('#toast');
  toast.textContent = message;
  toast.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.add('hidden'), 3000);
}

let searchTimer;
$('#searchInput').addEventListener('input', (event) => {
  state.query = event.target.value.trim();
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => searchMovies(true), 350);
});
$('#searchOpen').addEventListener('click', openSearch);
$('#searchClose').addEventListener('click', closeSearch);
$('#modalClose').addEventListener('click', closeMovie);
$('#modalBackdrop').addEventListener('click', closeMovie);
$('#profileButton').addEventListener('click', openProfile);
$$('[data-close-profile]').forEach((button) => button.addEventListener('click', closeProfile));
$('#loadMore').addEventListener('click', () => { state.page += 1; searchMovies(false); });
$$('[data-view]').forEach((button) => button.addEventListener('click', () => {
  state.query = '';
  state.selectedGenre = '';
  searchMovies(true, button.dataset.view);
}));
$$('[data-action]').forEach((button) => button.addEventListener('click', () => {
  const action = button.dataset.action;
  if (action === 'home') loadHome();
  if (action === 'search') openSearch();
  if (action === 'favorites') loadFavorites();
  if (action === 'profile') openProfile();
}));

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    closeMovie();
    closeProfile();
  }
});

async function boot() {
  try {
    state.config = await api('/api/config');
  } catch (_) {}
  await Promise.all([loadHome(), loadGenres()]);
}

boot();
