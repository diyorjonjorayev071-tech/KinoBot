
const tg = window.Telegram?.WebApp || null;

try {
  tg?.ready();
  tg?.expand();
  tg?.setHeaderColor?.('#050705');
  tg?.setBackgroundColor?.('#050705');
  tg?.setBottomBarColor?.('#050705');
} catch (_) {}


const state = {
  home: null,
  hero: null,
  selected: null,
  favorites: new Set(),
  searchTimer: null
};


const $ = (selector, root=document) => root.querySelector(selector);
const $$ = (selector, root=document) => [...root.querySelectorAll(selector)];


function escapeHtml(value='') {
  return String(value)
    .replaceAll('&','&amp;')
    .replaceAll('<','&lt;')
    .replaceAll('>','&gt;')
    .replaceAll('"','&quot;')
    .replaceAll("'","&#039;");
}


function posterUrl(code) {
  return `/api/poster/${encodeURIComponent(code)}?v=final-v8`;
}


function imdbNumber(value) {
  const match = String(value ?? '').replace(',', '.').match(/\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : 0;
}


function viewsNumber(value) {
  const n = Number(value || 0);
  return Number.isFinite(n) ? n : 0;
}


function itemsFrom(payload) {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload.items)) return payload.items;
  return [];
}


function uniqueMovies(items) {
  const map = new Map();

  for (const item of items || []) {
    if (!item || item.code == null) continue;
    if (!map.has(String(item.code))) {
      map.set(String(item.code), item);
    }
  }

  return [...map.values()];
}


async function api(path, options={}) {

  const headers = {
    ...(options.headers || {})
  };

  if (tg?.initData) {
    headers['X-Telegram-Init-Data'] = tg.initData;
  }

  if (
    options.body &&
    typeof options.body === 'string' &&
    !headers['Content-Type']
  ) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(path, {
    ...options,
    headers
  });

  let data = null;

  try {
    data = await response.json();
  } catch (_) {}

  if (!response.ok) {
    const message =
      data?.detail ||
      data?.message ||
      `HTTP ${response.status}`;

    throw new Error(message);
  }

  return data;
}


function toast(message) {
  const el = $('#toast');

  el.textContent = String(message || '');

  el.classList.add('show');

  clearTimeout(el._timer);

  el._timer = setTimeout(() => {
    el.classList.remove('show');
  }, 2200);
}


function movieSubtitle(item) {

  const values = [
    item.year,
    item.country
  ].filter(Boolean);

  return values.join(' ? ') || 'xD KINO';
}


function movieCard(item) {

  const code = Number(item.code);

  const type =
    escapeHtml(item.content_type || item.type || 'Kino');

  const imdb = imdbNumber(item.imdb);

  return `
    <article
      class="movie-card"
      data-code="${code}"
    >
      <div class="movie-poster">

        <img
          src="${posterUrl(code)}"
          alt="${escapeHtml(item.name || 'Kino')}"
          loading="lazy"
          onerror="this.style.display='none'"
        >

        <div class="movie-type">${type}</div>

        ${
          imdb > 0
            ? `<div class="movie-imdb">? ${imdb.toFixed(1)}</div>`
            : ''
        }

      </div>

      <div class="movie-name">
        ${escapeHtml(item.name || `Kino ${code}`)}
      </div>

      <div class="movie-sub">
        ${escapeHtml(movieSubtitle(item))}
      </div>
    </article>
  `;
}


function storyCard(item) {

  const code = Number(item.code);
  const imdb = imdbNumber(item.imdb);

  return `
    <article
      class="story-card"
      data-code="${code}"
    >

      <div class="story-poster">

        <img
          src="${posterUrl(code)}"
          alt="${escapeHtml(item.name || '')}"
          loading="lazy"
          onerror="this.style.display='none'"
        >

        ${
          imdb
            ? `<div class="story-score">? ${imdb.toFixed(1)}</div>`
            : ''
        }

      </div>

      <div class="story-title">
        ${escapeHtml(item.name || `Kino ${code}`)}
      </div>

    </article>
  `;
}


function bindMovieClicks(root=document) {

  $$('[data-code]', root).forEach(card => {

    card.onclick = () => {

      const code = Number(card.dataset.code);

      const all = collectHomeMovies();

      const item =
        all.find(x => Number(x.code) === code) ||
        state.selected;

      if (item) {
        openMovie(item);
      }

    };

  });
}


function collectHomeMovies() {

  const home = state.home || {};

  const items = [
    ...(home.featured || []),
    ...(home.stories || []),
    ...(home.popular || []),
    ...(home.new || [])
  ];

  for (const section of home.sections || []) {
    items.push(...(section.items || []));
  }

  return uniqueMovies(items);
}


function setHero(item) {

  if (!item) return;

  state.hero = item;

  const code = Number(item.code);

  $('#heroBackdrop').style.backgroundImage =
    `linear-gradient(to bottom,rgba(0,0,0,.03),rgba(0,0,0,.10)),url("${posterUrl(code)}")`;

  $('#heroTitle').textContent =
    item.name || 'xD KINO';

  $('#heroMeta').textContent =
    [
      item.year,
      item.country,
      item.genre,
      imdbNumber(item.imdb)
        ? `IMDb ${imdbNumber(item.imdb).toFixed(1)}`
        : ''
    ]
    .filter(Boolean)
    .join(' ? ');

  $('#heroDescription').textContent =
    item.description ||
    `${item.name || 'Ushbu kontent'}ni xD KINO orqali tomosha qiling.`;

  $('#heroWatch').onclick = () => watchMovie(item);
  $('#heroDetails').onclick = () => openMovie(item);
}


function watchMovie(item) {

  if (!item?.code) return;

  const link =
    `https://t.me/xDKinoCodeBot?start=movie_${encodeURIComponent(item.code)}`;

  try {
    if (tg?.openTelegramLink) {
      tg.openTelegramLink(link);
      return;
    }
  } catch (_) {}

  window.location.href = link;
}


function openMovie(item) {

  state.selected = item;

  const code = Number(item.code);

  $('#modalPoster').style.backgroundImage =
    `url("${posterUrl(code)}")`;

  $('#modalType').textContent =
    item.content_type || item.type || 'KINO';

  $('#modalTitle').textContent =
    item.name || `Kino ${code}`;

  $('#modalMeta').textContent =
    [
      item.year,
      item.country,
      item.genre,
      item.language,
      imdbNumber(item.imdb)
        ? `IMDb ${imdbNumber(item.imdb).toFixed(1)}`
        : '',
      viewsNumber(item.views)
        ? `${viewsNumber(item.views)} ko?rish`
        : ''
    ]
    .filter(Boolean)
    .join(' ? ');

  $('#modalDescription').textContent =
    item.description ||
    'Ushbu kontent xD KINO katalogida mavjud.';

  $('#modalWatch').onclick = () => watchMovie(item);

  $('#modalFavorite').onclick = () => toggleFavorite(item);

  $('#movieModal').classList.remove('hidden');

  document.body.style.overflow = 'hidden';
}


function closeMovie() {
  $('#movieModal').classList.add('hidden');
  document.body.style.overflow = '';
}


async function toggleFavorite(item) {

  try {

    const enabled = !state.favorites.has(Number(item.code));

    const data = await api('/api/favorites', {
      method:'POST',
      body:JSON.stringify({
        movie_code:Number(item.code),
        enabled
      })
    });

    if (data.enabled ?? enabled) {
      state.favorites.add(Number(item.code));
      toast('Sevimlilarga qo?shildi');
    } else {
      state.favorites.delete(Number(item.code));
      toast('Sevimlilardan olib tashlandi');
    }

  } catch (error) {
    toast(
      tg?.initData
        ? error.message
        : 'Sevimlilar Telegram ichida ishlaydi'
    );
  }
}


function renderRecommendations(items) {

  const root = $('#recommendations');

  root.innerHTML =
    items.slice(0,12).map(storyCard).join('');

  bindMovieClicks(root);
}


function renderGenres(genres) {

  const clean = [...new Set(
    (genres || [])
      .flatMap(value =>
        String(
          typeof value === 'object'
            ? value.name || value.genre || ''
            : value
        ).split(/[,;]+/)
      )
      .map(x => x.trim())
      .filter(Boolean)
  )].slice(0,16);

  const root = $('#genreStrip');

  root.innerHTML = clean.map(genre => `
    <button
      class="genre-card"
      data-genre="${escapeHtml(genre)}"
    >
      <strong>${escapeHtml(genre)}</strong>
      <span>Ko?rish ?</span>
    </button>
  `).join('');

  $$('.genre-card',root).forEach(btn => {

    btn.onclick = () => {

      setView('search');

      $('#searchInput').value = btn.dataset.genre;

      searchMovies();

    };

  });
}


function renderSections(home) {

  const root = $('#homeSections');

  let sections = Array.isArray(home.sections)
    ? home.sections
    : [];

  if (!sections.length) {

    sections = [
      {
        title:'Mashhur',
        items:home.popular || []
      },
      {
        title:'Yangi qo?shilganlar',
        items:home.new || []
      }
    ];

  }

  root.innerHTML = sections
    .filter(section => section?.items?.length)
    .map((section,index) => `

      <section class="content-section">

        <div class="section-head">

          <div>
            <div class="section-kicker">
              ${index === 0 ? 'XUSUSIY TANLOV' : 'xD KINO'}
            </div>

            <h2>${escapeHtml(section.title || 'Kinolar')}</h2>
          </div>

        </div>

        <div
          class="movie-row"
          data-section-index="${index}"
        >
          ${(section.items || [])
            .slice(0,18)
            .map(movieCard)
            .join('')}
        </div>

      </section>
    `)
    .join('');

  bindMovieClicks(root);
}


async function loadHome() {

  try {

    const [home, popularPayload] =
      await Promise.all([
        api('/api/home'),
        api('/api/movies?sort=popular&limit=60')
          .catch(() => ({items:[]}))
      ]);

    state.home = home || {};

    const popular =
      itemsFrom(popularPayload);

    let recommendations =
      popular
        .filter(item => imdbNumber(item.imdb) >= 7.5)
        .sort((a,b) =>
          viewsNumber(b.views) - viewsNumber(a.views) ||
          imdbNumber(b.imdb) - imdbNumber(a.imdb)
        );

    if (!recommendations.length) {
      recommendations =
        uniqueMovies([
          ...(home?.stories || []),
          ...(home?.popular || [])
        ]);
    }

    const hero =
      home?.featured?.[0] ||
      recommendations[0] ||
      home?.popular?.[0] ||
      home?.new?.[0];

    if (hero) {
      setHero(hero);
    }

    renderRecommendations(recommendations);

    renderGenres(home?.genres || []);

    renderSections(home || {});

  } catch (error) {

    toast(`Yuklash xatosi: ${error.message}`);

  } finally {

    setTimeout(() => {
      $('#splash').classList.add('done');
    }, 650);

  }
}


async function searchMovies() {

  const q =
    $('#searchInput').value.trim();

  const type =
    $('#typeSelect').value;

  const sort =
    $('#sortSelect').value;

  const params =
    new URLSearchParams({
      q,
      content_type:type,
      sort,
      limit:'60'
    });

  try {

    const payload =
      await api(`/api/movies?${params.toString()}`);

    const items =
      itemsFrom(payload);

    $('#searchCount').textContent =
      `${payload?.total ?? items.length} ta`;

    $('#searchGrid').innerHTML =
      items.map(movieCard).join('');

    bindMovieClicks($('#searchGrid'));

  } catch (error) {

    $('#searchCount').textContent = '0 ta';

    $('#searchGrid').innerHTML = '';

    toast(error.message);

  }
}


async function loadFavorites() {

  try {

    const payload =
      await api('/api/favorites');

    const items =
      itemsFrom(payload);

    state.favorites =
      new Set(items.map(x => Number(x.code)));

    $('#favoritesGrid').innerHTML =
      items.map(movieCard).join('');

    $('#favoritesEmpty')
      .classList.toggle('hidden',items.length > 0);

    bindMovieClicks($('#favoritesGrid'));

  } catch (error) {

    $('#favoritesGrid').innerHTML = '';

    $('#favoritesEmpty')
      .classList.remove('hidden');

  }
}


async function loadProfile() {

  const user =
    tg?.initDataUnsafe?.user;

  if (user) {

    const name =
      [user.first_name,user.last_name]
        .filter(Boolean)
        .join(' ') || 'xD KINO';

    $('#profileName').textContent =
      name;

    $('#profileUsername').textContent =
      user.username
        ? `@${user.username}`
        : 'Telegram foydalanuvchi';

    const letter =
      (user.first_name || 'D')
        .trim()
        .charAt(0)
        .toUpperCase();

    $('#avatarLetter').textContent = letter;
    $('#profileAvatarLetter').textContent = letter;
  }

  try {

    const profile =
      await api('/api/profile');

    $('#favoriteCount').textContent =
      profile.favorites_count ?? 0;

    $('#historyCount').textContent =
      profile.history_count ?? 0;

  } catch (_) {}

}


function setView(name) {

  $$('.view').forEach(view => {
    view.classList.remove('active');
  });

  $(`#view-${name}`)?.classList.add('active');

  $$('.nav-item').forEach(btn => {
    btn.classList.toggle(
      'active',
      btn.dataset.nav === name
    );
  });

  window.scrollTo({
    top:0,
    behavior:'instant'
  });

  if (name === 'search') {
    searchMovies();
  }

  if (name === 'favorites') {
    loadFavorites();
  }

  if (name === 'profile') {
    loadProfile();
  }
}


$$('[data-nav]').forEach(btn => {
  btn.addEventListener('click',() => {
    setView(btn.dataset.nav);
  });
});


$$('[data-close-modal]').forEach(el => {
  el.addEventListener('click',closeMovie);
});


$('#searchInput').addEventListener('input',() => {

  clearTimeout(state.searchTimer);

  state.searchTimer =
    setTimeout(searchMovies,320);

});


$('#typeSelect').addEventListener(
  'change',
  searchMovies
);

$('#sortSelect').addEventListener(
  'change',
  searchMovies
);


document.addEventListener('keydown',event => {
  if (event.key === 'Escape') {
    closeMovie();
  }
});


loadProfile();
loadHome();
