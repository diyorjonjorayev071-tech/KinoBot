
const tg = window.Telegram?.WebApp || null;

// FINAL_V13_SPLASH_TIMER
const XD_SPLASH_STARTED_AT = Date.now();
const XD_SPLASH_MIN_MS = 2900;


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



// FINAL_V17_SAFE_UZBEK_TEXT

function normalizeUzbekDisplayText(value = "") {

  return String(value ?? "")

    // Curly / special apostrophes
    .replace(/[????`?]/g, "'")

    // Encoding buzilgan apostroflar:
    // ko?rish     -> ko'rish
    // O?zbek      -> O'zbek
    // qo?shilgan  -> qo'shilgan
    // to?g?ri     -> to'g'ri
    // g?alaba     -> g'alaba
    .replace(
      /([oOgG])(?:\?|\uFFFD)(?=[A-Za-z?-?])/g,
      "$1'"
    );
}


function repairUzbekVisibleText(root = document.body) {

  if (!root) return;

  // Matn tugunlari
  const walker = document.createTreeWalker(
    root,
    NodeFilter.SHOW_TEXT
  );

  const nodes = [];

  while (walker.nextNode()) {
    nodes.push(walker.currentNode);
  }

  for (const node of nodes) {

    const before = node.nodeValue || "";
    const after = normalizeUzbekDisplayText(before);

    if (before !== after) {
      node.nodeValue = after;
    }
  }


  // Input placeholder, title, aria-label
  const elements = [];

  if (
    root.nodeType === Node.ELEMENT_NODE &&
    root.matches?.(
      "[placeholder],[title],[aria-label]"
    )
  ) {
    elements.push(root);
  }

  if (root.querySelectorAll) {
    elements.push(
      ...root.querySelectorAll(
        "[placeholder],[title],[aria-label]"
      )
    );
  }

  for (const el of elements) {

    for (const attr of [
      "placeholder",
      "title",
      "aria-label"
    ]) {

      if (!el.hasAttribute(attr)) continue;

      const before =
        el.getAttribute(attr) || "";

      const after =
        normalizeUzbekDisplayText(before);

      if (before !== after) {
        el.setAttribute(attr, after);
      }
    }
  }
}


const xdUzbekTextObserver =
  new MutationObserver(records => {

    for (const record of records) {

      if (
        record.type === "characterData"
      ) {

        const node = record.target;

        const before =
          node.nodeValue || "";

        const after =
          normalizeUzbekDisplayText(before);

        if (before !== after) {
          node.nodeValue = after;
        }

        continue;
      }


      for (const added of record.addedNodes) {

        if (
          added.nodeType === Node.TEXT_NODE
        ) {

          const before =
            added.nodeValue || "";

          const after =
            normalizeUzbekDisplayText(before);

          if (before !== after) {
            added.nodeValue = after;
          }

        }

        else if (
          added.nodeType === Node.ELEMENT_NODE
        ) {

          repairUzbekVisibleText(added);
        }
      }
    }
  });


function startUzbekTextRepair() {

  if (!document.body) return;

  repairUzbekVisibleText(
    document.body
  );

  xdUzbekTextObserver.observe(
    document.body,
    {
      childList: true,
      subtree: true,
      characterData: true
    }
  );
}


if (
  document.readyState === "loading"
) {

  document.addEventListener(
    "DOMContentLoaded",
    startUzbekTextRepair,
    { once: true }
  );

} else {

  startUzbekTextRepair();
}


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
  return `/api/poster/${encodeURIComponent(code)}?v=final-v15-splash`;
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


// FINAL_V12_MOVIE_INDEX
const movieIndex = new Map();


function movieSubtitle(item) {

  const values = [
    item.year,
    item.country
  ].filter(Boolean);

  return values.join(' / ') || 'xD KINO';
}


function movieCard(item) {

  const code = Number(item.code);

  movieIndex.set(code, item);

  const type =
    escapeHtml(
      item.content_type ||
      item.type ||
      'Kino'
    );

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
        >

        <div class="movie-type">
          ${type}
        </div>

        ${
          imdb > 0
            ? `<div class="movie-imdb">IMDb ${imdb.toFixed(1)}</div>`
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

  movieIndex.set(code, item);

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
        >

        ${
          imdb > 0
            ? `<div class="story-score">IMDb ${imdb.toFixed(1)}</div>`
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
        movieIndex.get(code) ||
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



// FINAL_V16_HERO_CAROUSEL
let heroSlides = [];
let heroSlideIndex = 0;
let heroSlideTimer = null;
let heroChangeLock = false;

function showHeroSlide(index, animate = true) {

  if (!heroSlides.length || heroChangeLock) return;

  const nextIndex =
    (index + heroSlides.length) %
    heroSlides.length;

  const item =
    heroSlides[nextIndex];

  if (!item) return;

  const applySlide = () => {

    heroSlideIndex = nextIndex;

    const hero = $('#hero');

    if (!hero || !animate) {
      setHero(item);
      return;
    }

    heroChangeLock = true;
    hero.classList.add('hero-changing');

    setTimeout(() => {

      setHero(item);

      requestAnimationFrame(() => {

        hero.classList.remove('hero-changing');

        setTimeout(() => {
          heroChangeLock = false;
        }, 350);

      });

    }, 170);
  };


  // Keyingi posterni oldindan yuklaymiz:
  // almashishda qora flash bo'lmasin.
  const image = new Image();
  let finished = false;

  const finish = () => {

    if (finished) return;
    finished = true;

    applySlide();
  };

  image.onload = finish;
  image.onerror = finish;
  image.src = posterUrl(item.code);

  setTimeout(finish, 900);
}


function startHeroCarousel(items) {

  clearInterval(heroSlideTimer);

  heroSlides =
    uniqueMovies(items || [])
      .filter(
        item =>
          item &&
          item.code != null
      )
      .slice(0, 10);

  if (!heroSlides.length) return;

  heroSlideIndex = 0;

  showHeroSlide(0, false);

  if (heroSlides.length < 2) return;

  heroSlideTimer =
    setInterval(() => {

      if (document.hidden) return;

      showHeroSlide(
        heroSlideIndex + 1,
        true
      );

    }, 5200);
}


document.addEventListener(
  'visibilitychange',
  () => {

    if (document.hidden) return;

    if (heroSlides.length > 1) {

      clearInterval(heroSlideTimer);

      heroSlideTimer =
        setInterval(() => {

          if (!document.hidden) {
            showHeroSlide(
              heroSlideIndex + 1,
              true
            );
          }

        }, 5200);
    }
  }
);


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
    .join(' / ');

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
    .join(' / ');

  $('#modalDescription').textContent =
    item.description ||
    'Ushbu kontent xD KINO katalogida mavjud.';

  $('#modalWatch').onclick = () => watchMovie(item);

  $('#modalFavorite').onclick = () => toggleFavorite(item);

  $('#modalFavorite').classList.toggle(
    'active',
    state.favorites.has(code)
  );

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

    // FINAL_V13_FAVORITE_STATE
    if (
      state.selected &&
      Number(state.selected.code) === Number(item.code)
    ) {
      $('#modalFavorite').classList.toggle(
        'active',
        state.favorites.has(Number(item.code))
      );
    }

    loadProfile().catch?.(() => {});

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
  )];

  const root = $('#genreStrip');

  root.innerHTML = clean.map(genre => `
    <button
      class="genre-card"
      data-genre="${escapeHtml(genre)}"
    >
      <strong>${escapeHtml(genre)}</strong>
      <span>Ko'rish</span>
    </button>
  `).join('');

  $$('.genre-card',root).forEach(btn => {

    btn.onclick = () => {

      activeGenre = btn.dataset.genre || '';
      setView('search');

      $('#searchInput').value = '';

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

    const heroCarouselItems =
      uniqueMovies([
        hero,
        ...recommendations,
        ...(home?.featured || []),
        ...(home?.popular || []),
        ...(home?.new || [])
      ])
      .filter(Boolean);

    startHeroCarousel(heroCarouselItems);

    renderRecommendations(recommendations);

    renderGenres(home?.genres || []);

    renderSections(home || {});

  } catch (error) {

    toast(`Yuklash xatosi: ${error.message}`);

  } finally {

    setTimeout(() => {
      $('#splash').classList.add('done');
    }, Math.max(
      120,
      XD_SPLASH_MIN_MS - (Date.now() - XD_SPLASH_STARTED_AT)
    ));

  }
}


// FINAL_V13_GENRE_FILTER
let activeGenre = '';


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
      genre:activeGenre,
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
        : 'Telegram foydalanuvchisi';

    const photo =
      String(user.photo_url || '').trim();

    const topImage =
      $('#topAvatarImage');

    const topFallback =
      $('#topAvatarFallback');

    const profileImage =
      $('#profileAvatarImage');

    const profileFallback =
      $('#profileAvatarFallback');

    const useFallback = () => {

      topImage?.classList.add('hidden');
      profileImage?.classList.add('hidden');

      topFallback?.classList.remove('hidden');
      profileFallback?.classList.remove('hidden');

    };

    if (photo) {

      topImage.src = photo;
      profileImage.src = photo;

      topImage.classList.remove('hidden');
      profileImage.classList.remove('hidden');

      topFallback.classList.add('hidden');
      profileFallback.classList.add('hidden');

      topImage.onerror = useFallback;
      profileImage.onerror = useFallback;

    } else {

      useFallback();

    }
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

  activeGenre = '';

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
loadBuildInfo();


// FINAL_V12_BUILD_INFO
async function loadBuildInfo() {
  try {
    const response = await fetch(
      `/health?ui=${Date.now()}`,
      { cache: 'no-store' }
    );

    if (!response.ok) return;

    const data = await response.json();

    const version = document.getElementById('appVersionLabel');

    if (version) {
      version.textContent =
        String(data.ui_version || 'final-v12-ui')
          .toUpperCase();
    }

    const count = document.getElementById('contentCount');

    if (
      count &&
      Number.isFinite(Number(data.movies))
    ) {
      count.textContent = `${Number(data.movies)}+`;
    }

  } catch (_) {}
}


// ============================================================
// FINAL_V21_GENRE_ART
// Har bir janr: o'z poster foni + o'z cinematic style
// ============================================================

function xdNormalizeGenre(value) {

  return String(value || '')
    .toLowerCase()
    .replace(/[????`?]/g, "'")
    .replace(/\s+/g, ' ')
    .trim();
}


function xdGenreProfile(name) {

  const key =
    xdNormalizeGenre(name);


  const rules = [

    {
      words: [
        "qo'rqinchli",
        "horror",
        "dahshat"
      ],
      art: "horror",
      g1: "#7b1026",
      g2: "#160309"
    },

    {
      words: [
        "jangari",
        "action"
      ],
      art: "action",
      g1: "#ff5a19",
      g2: "#391006"
    },

    {
      words: [
        "fantastika",
        "fantasy"
      ],
      art: "fantasy",
      g1: "#6748ff",
      g2: "#101945"
    },

    {
      words: [
        "ilmiy fantastika",
        "sci-fi",
        "science fiction"
      ],
      art: "scifi",
      g1: "#18d7e8",
      g2: "#062c40"
    },

    {
      words: [
        "anime"
      ],
      art: "anime",
      g1: "#ff4f9c",
      g2: "#35165b"
    },

    {
      words: [
        "animatsion",
        "animation",
        "multfilm"
      ],
      art: "animation",
      g1: "#20d9ad",
      g2: "#124760"
    },

    {
      words: [
        "romantika",
        "romance"
      ],
      art: "romance",
      g1: "#ff557d",
      g2: "#4b102c"
    },

    {
      words: [
        "komediya",
        "comedy"
      ],
      art: "comedy",
      g1: "#f6c947",
      g2: "#725216"
    },

    {
      words: [
        "detektiv",
        "detective"
      ],
      art: "detective",
      g1: "#3a8ea7",
      g2: "#0c242e"
    },

    {
      words: [
        "kriminal",
        "crime"
      ],
      art: "crime",
      g1: "#3d6075",
      g2: "#10181e"
    },

    {
      words: [
        "triller",
        "thriller"
      ],
      art: "thriller",
      g1: "#bd2338",
      g2: "#24070c"
    },

    {
      words: [
        "drama"
      ],
      art: "drama",
      g1: "#a94449",
      g2: "#31161a"
    },

    {
      words: [
        "biografik",
        "biography"
      ],
      art: "biography",
      g1: "#b78a4b",
      g2: "#332412"
    },

    {
      words: [
        "tarixiy",
        "history",
        "historical"
      ],
      art: "history",
      g1: "#aa7135",
      g2: "#30200d"
    },

    {
      words: [
        "sarguzasht",
        "adventure"
      ],
      art: "adventure",
      g1: "#31ad76",
      g2: "#0e3b2d"
    },

    {
      words: [
        "oilaviy",
        "family"
      ],
      art: "family",
      g1: "#42c978",
      g2: "#173d35"
    },

    {
      words: [
        "musiqiy",
        "music",
        "musical"
      ],
      art: "music",
      g1: "#ab45e5",
      g2: "#291042"
    },

    {
      words: [
        "urush",
        "war"
      ],
      art: "war",
      g1: "#7b8c4a",
      g2: "#252d15"
    },

    {
      words: [
        "sport"
      ],
      art: "sport",
      g1: "#168ed7",
      g2: "#063454"
    },

    {
      words: [
        "hujjatli",
        "documentary"
      ],
      art: "documentary",
      g1: "#4b9b83",
      g2: "#142d26"
    },

    {
      words: [
        "western",
        "vestern"
      ],
      art: "western",
      g1: "#d47a2a",
      g2: "#44200a"
    },

    {
      words: [
        "sirli",
        "mystery"
      ],
      art: "mystery",
      g1: "#5656b8",
      g2: "#17172f"
    }

  ];


  for (const rule of rules) {

    if (
      rule.words.some(
        word => key.includes(word)
      )
    ) {

      return rule;
    }
  }


  // Yangi noma'lum janrlar uchun ham
  // avtomatik alohida cinematic rang.

  const fallback = [

    ["cinema-a", "#25b77f", "#0b3728"],
    ["cinema-b", "#377ed0", "#0b2848"],
    ["cinema-c", "#9d56c8", "#2b123d"],
    ["cinema-d", "#ca6c38", "#3d1b0b"],
    ["cinema-e", "#7fac45", "#253612"],
    ["cinema-f", "#b54d72", "#3d1223"]

  ];


  let hash = 0;

  for (let i = 0; i < key.length; i++) {

    hash =
      (
        (hash << 5)
        - hash
        + key.charCodeAt(i)
      ) | 0;
  }


  const pick =
    fallback[
      Math.abs(hash) %
      fallback.length
    ];


  return {
    art: pick[0],
    g1: pick[1],
    g2: pick[2]
  };
}


async function xdLoadGenrePoster(card) {

  if (
    !card ||
    card.dataset.genrePosterState
  ) {
    return;
  }


  card.dataset.genrePosterState =
    "loading";


  const genre =
    card.dataset.genre || '';


  try {

    const params =
      new URLSearchParams({
        genre,
        sort: 'popular',
        limit: '1'
      });


    const payload =
      await api(
        `/api/movies?${params.toString()}`
      );


    const movies =
      itemsFrom(payload);


    const movie =
      movies[0];


    if (
      movie &&
      movie.code != null
    ) {

      card.style.setProperty(
        '--genre-poster',
        `url("${posterUrl(movie.code)}")`
      );


      card.classList.add(
        'has-genre-poster'
      );


      card.dataset.genrePosterState =
        "loaded";

    } else {

      card.dataset.genrePosterState =
        "fallback";
    }

  }
  catch (_) {

    card.dataset.genrePosterState =
      "fallback";
  }
}


function xdDecorateGenreCards() {

  const cards =
    document.querySelectorAll(
      '.genre-card[data-genre]'
    );


  cards.forEach(card => {

    if (
      card.dataset.genreArtReady !==
      "1"
    ) {

      const profile =
        xdGenreProfile(
          card.dataset.genre || ''
        );


      card.dataset.genreArt =
        profile.art;


      card.style.setProperty(
        '--genre-g1',
        profile.g1
      );


      card.style.setProperty(
        '--genre-g2',
        profile.g2
      );


      card.dataset.genreArtReady =
        "1";
    }


    xdLoadGenrePoster(card);
  });
}


let xdGenreDecorateTimer = null;


const xdGenreObserver =
  new MutationObserver(() => {

    clearTimeout(
      xdGenreDecorateTimer
    );


    xdGenreDecorateTimer =
      setTimeout(
        xdDecorateGenreCards,
        30
      );
  });


function xdStartGenreArt() {

  xdDecorateGenreCards();


  xdGenreObserver.observe(
    document.body,
    {
      childList: true,
      subtree: true
    }
  );
}


if (
  document.readyState ===
  'loading'
) {

  document.addEventListener(
    'DOMContentLoaded',
    xdStartGenreArt,
    {
      once: true
    }
  );

}
else {

  xdStartGenreArt();
}


// ============================================================
// FINAL_V22_ORIGINAL_GENRE_POSTERS
// Har bir janr uchun ORIGINAL illustrated mini-poster
// ============================================================

function xdV22SvgUrl(svg) {

  return `url("data:image/svg+xml,${encodeURIComponent(svg)}")`;
}


function xdV22GenreArtwork(genre) {

  const profile =
    xdGenreProfile(genre);

  const art =
    profile.art || 'cinema-a';

  const c1 =
    profile.g1 || '#35df69';

  const c2 =
    profile.g2 || '#092614';


  let scene = '';


  switch (art) {


    // --------------------------------------------------------
    // ACTION
    // --------------------------------------------------------

    case 'action':

      scene = `
        <circle
          cx="252"
          cy="52"
          r="64"
          fill="${c1}"
          opacity=".36"
          filter="url(#glow)"
        />

        <path
          d="M-20 170 L150 16 L185 35 L34 190 Z"
          fill="${c1}"
          opacity=".36"
        />

        <path
          d="M120 190 L250 60 L273 82 L160 200 Z"
          fill="#ffffff"
          opacity=".13"
        />

        <g
          stroke="#ffffff"
          stroke-width="4"
          opacity=".32"
        >
          <path d="M230 22v36"/>
          <path d="M212 40h36"/>
          <circle cx="230" cy="40" r="24"/>
        </g>

        <path
          d="M0 176 L38 146 L67 161 L102 120 L136 144 L178 101 L222 136 L267 91 L320 129 L320 200 L0 200 Z"
          fill="#030604"
          opacity=".78"
        />
      `;

      break;


    // --------------------------------------------------------
    // HORROR
    // --------------------------------------------------------

    case 'horror':

      scene = `
        <circle
          cx="255"
          cy="46"
          r="54"
          fill="#d42a42"
          opacity=".27"
          filter="url(#glow)"
        />

        <rect
          x="112"
          y="35"
          width="96"
          height="150"
          rx="4"
          fill="#020302"
          stroke="${c1}"
          stroke-opacity=".32"
          stroke-width="3"
        />

        <path
          d="M137 185 L147 70 L186 70 L195 185 Z"
          fill="${c1}"
          opacity=".12"
        />

        <ellipse
          cx="167"
          cy="105"
          rx="26"
          ry="10"
          fill="#050505"
        />

        <ellipse
          cx="167"
          cy="105"
          rx="8"
          ry="8"
          fill="#e23a4c"
          opacity=".72"
          filter="url(#glow)"
        />

        <path
          d="M0 160 Q50 143 98 170 T195 167 T320 154 V200 H0Z"
          fill="#010201"
          opacity=".82"
        />
      `;

      break;


    // --------------------------------------------------------
    // FANTASY
    // --------------------------------------------------------

    case 'fantasy':

      scene = `
        <circle
          cx="248"
          cy="47"
          r="45"
          fill="#d7dcff"
          opacity=".78"
          filter="url(#glow)"
        />

        <circle cx="55" cy="40" r="2" fill="#fff"/>
        <circle cx="85" cy="72" r="1.5" fill="#fff"/>
        <circle cx="180" cy="31" r="1.7" fill="#fff"/>
        <circle cx="290" cy="98" r="1.4" fill="#fff"/>

        <path
          d="M72 175 L72 100 L101 100 L101 75 L125 75 L125 175 Z"
          fill="#050707"
        />

        <path
          d="M126 175 L126 83 L151 83 L151 51 L176 51 L176 175 Z"
          fill="#060808"
        />

        <path
          d="M178 175 L178 108 L203 108 L203 88 L228 88 L228 175 Z"
          fill="#050707"
        />

        <path
          d="M63 100 L86 68 L109 100 Z"
          fill="${c1}"
          opacity=".38"
        />

        <path
          d="M140 83 L163 40 L186 83 Z"
          fill="${c1}"
          opacity=".32"
        />

        <path
          d="M0 183 Q67 155 124 178 T245 174 T320 163 V200 H0Z"
          fill="#020403"
        />
      `;

      break;


    // --------------------------------------------------------
    // SCI-FI
    // --------------------------------------------------------

    case 'scifi':

      scene = `
        <circle
          cx="224"
          cy="70"
          r="58"
          fill="${c1}"
          opacity=".22"
          filter="url(#glow)"
        />

        <circle
          cx="224"
          cy="70"
          r="37"
          fill="#0a1425"
          stroke="#b9fbff"
          stroke-opacity=".5"
          stroke-width="2"
        />

        <ellipse
          cx="224"
          cy="70"
          rx="76"
          ry="18"
          fill="none"
          stroke="${c1}"
          stroke-width="4"
          stroke-opacity=".55"
          transform="rotate(-14 224 70)"
        />

        <path
          d="M75 150 L116 73 L132 147 L165 165 Z"
          fill="#d4fbff"
          opacity=".82"
        />

        <path
          d="M98 137 L116 101 L121 142 Z"
          fill="${c1}"
          opacity=".8"
        />

        <g fill="#fff" opacity=".65">
          <circle cx="36" cy="35" r="1.5"/>
          <circle cx="72" cy="63" r="1.2"/>
          <circle cx="142" cy="28" r="1.6"/>
          <circle cx="284" cy="33" r="1.3"/>
          <circle cx="301" cy="112" r="1.5"/>
        </g>
      `;

      break;


    // --------------------------------------------------------
    // ANIME
    // --------------------------------------------------------

    case 'anime':

      scene = `
        <circle
          cx="245"
          cy="68"
          r="52"
          fill="#ff75b6"
          opacity=".42"
          filter="url(#glow)"
        />

        <g
          stroke="#ffffff"
          stroke-opacity=".17"
          stroke-width="3"
        >
          <path d="M245 68 L320 8"/>
          <path d="M245 68 L320 46"/>
          <path d="M245 68 L320 92"/>
          <path d="M245 68 L320 145"/>
          <path d="M245 68 L267 0"/>
        </g>

        <path
          d="M94 168 Q116 112 153 91 Q179 78 198 101 Q161 108 150 135 Q134 164 94 168 Z"
          fill="#09060c"
        />

        <g fill="#ffb0d5" opacity=".58">
          <circle cx="53" cy="56" r="5"/>
          <circle cx="76" cy="78" r="3"/>
          <circle cx="42" cy="105" r="4"/>
          <circle cx="92" cy="34" r="3"/>
        </g>
      `;

      break;


    // --------------------------------------------------------
    // ANIMATION
    // --------------------------------------------------------

    case 'animation':

      scene = `
        <circle
          cx="257"
          cy="48"
          r="44"
          fill="#ffd859"
          opacity=".88"
          filter="url(#glow)"
        />

        <path
          d="M38 160 Q65 110 102 148 Q121 92 160 137 Q190 93 220 145 Q251 118 289 161 Z"
          fill="#9cf3dc"
          opacity=".38"
        />

        <path
          d="M118 174 L118 109 L141 109 L141 80 L164 80 L164 174 Z"
          fill="#f4f5ff"
          opacity=".72"
        />

        <path
          d="M166 174 L166 121 L190 121 L190 96 L214 96 L214 174 Z"
          fill="#f7d5ff"
          opacity=".72"
        />

        <circle cx="56" cy="58" r="12" fill="#ff75a7" opacity=".75"/>
        <circle cx="82" cy="41" r="8" fill="#7dc8ff" opacity=".8"/>
      `;

      break;


    // --------------------------------------------------------
    // ROMANCE
    // --------------------------------------------------------

    case 'romance':

      scene = `
        <circle
          cx="252"
          cy="48"
          r="58"
          fill="#ff7596"
          opacity=".30"
          filter="url(#glow)"
        />

        <path
          d="M160 146
             C105 107 96 76 119 59
             C140 44 158 58 160 76
             C163 58 181 44 202 59
             C225 76 216 107 160 146Z"
          fill="#ff8ca7"
          opacity=".72"
        />

        <circle cx="108" cy="133" r="23" fill="#090709"/>
        <circle cx="210" cy="133" r="23" fill="#090709"/>

        <path
          d="M82 191 Q105 147 138 151"
          stroke="#090709"
          stroke-width="25"
          fill="none"
          stroke-linecap="round"
        />

        <path
          d="M238 191 Q215 147 182 151"
          stroke="#090709"
          stroke-width="25"
          fill="none"
          stroke-linecap="round"
        />
      `;

      break;


    // --------------------------------------------------------
    // COMEDY
    // --------------------------------------------------------

    case 'comedy':

      scene = `
        <circle
          cx="247"
          cy="57"
          r="58"
          fill="#ffd95d"
          opacity=".45"
          filter="url(#glow)"
        />

        <g transform="translate(78 54)">
          <path
            d="M0 0 Q50 18 91 2 L82 73 Q44 108 10 72 Z"
            fill="#f7dc75"
            opacity=".92"
          />

          <circle cx="27" cy="39" r="6" fill="#182019"/>
          <circle cx="64" cy="39" r="6" fill="#182019"/>

          <path
            d="M27 58 Q45 77 64 58"
            stroke="#182019"
            stroke-width="5"
            fill="none"
            stroke-linecap="round"
          />
        </g>

        <g
          transform="translate(180 92) scale(.7)"
          opacity=".63"
        >
          <path
            d="M0 0 Q50 18 91 2 L82 73 Q44 108 10 72 Z"
            fill="#fff2bb"
          />

          <path
            d="M27 60 Q45 45 64 60"
            stroke="#1b201c"
            stroke-width="5"
            fill="none"
          />
        </g>
      `;

      break;


    // --------------------------------------------------------
    // DETECTIVE
    // --------------------------------------------------------

    case 'detective':

      scene = `
        <g
          stroke="#c6efff"
          stroke-opacity=".16"
          stroke-width="5"
        >
          <path d="M0 38H320"/>
          <path d="M0 66H320"/>
          <path d="M0 94H320"/>
          <path d="M0 122H320"/>
        </g>

        <circle
          cx="188"
          cy="88"
          r="43"
          fill="none"
          stroke="${c1}"
          stroke-width="10"
          stroke-opacity=".8"
          filter="url(#glow)"
        />

        <path
          d="M220 121 L270 174"
          stroke="${c1}"
          stroke-width="14"
          stroke-linecap="round"
        />

        <path
          d="M70 180 Q85 117 124 104 Q163 114 171 180Z"
          fill="#040708"
        />

        <circle
          cx="123"
          cy="87"
          r="25"
          fill="#040708"
        />

        <path
          d="M88 69 H157 L140 49 H105 Z"
          fill="#040708"
        />
      `;

      break;


    // --------------------------------------------------------
    // CRIME
    // --------------------------------------------------------

    case 'crime':

      scene = `
        <circle
          cx="265"
          cy="45"
          r="38"
          fill="#c73449"
          opacity=".35"
          filter="url(#glow)"
        />

        <path
          d="M0 177
             L0 121 L36 121 L36 93
             L71 93 L71 133
             L102 133 L102 72
             L135 72 L135 115
             L168 115 L168 88
             L205 88 L205 142
             L243 142 L243 105
             L283 105 L283 72
             L320 72 L320 200 L0 200 Z"
          fill="#020405"
        />

        <path
          d="M28 155 H292"
          stroke="${c1}"
          stroke-width="3"
          stroke-dasharray="15 10"
          opacity=".5"
        />
      `;

      break;


    // --------------------------------------------------------
    // THRILLER
    // --------------------------------------------------------

    case 'thriller':

      scene = `
        <circle
          cx="215"
          cy="89"
          r="62"
          fill="none"
          stroke="${c1}"
          stroke-width="5"
          stroke-opacity=".55"
        />

        <circle
          cx="215"
          cy="89"
          r="8"
          fill="#fff"
          opacity=".75"
        />

        <path
          d="M215 89 L215 45"
          stroke="#fff"
          stroke-width="5"
          stroke-linecap="round"
          opacity=".7"
        />

        <path
          d="M215 89 L250 111"
          stroke="${c1}"
          stroke-width="6"
          stroke-linecap="round"
        />

        <path
          d="M50 190 Q69 109 112 98 Q153 112 165 190Z"
          fill="#020303"
        />

        <circle
          cx="110"
          cy="77"
          r="25"
          fill="#020303"
        />
      `;

      break;


    // --------------------------------------------------------
    // DRAMA
    // --------------------------------------------------------

    case 'drama':

      scene = `
        <g
          stroke="#dfe7ff"
          stroke-opacity=".15"
          stroke-width="2"
        >
          <path d="M25 0 L5 200"/>
          <path d="M55 0 L35 200"/>
          <path d="M85 0 L65 200"/>
          <path d="M115 0 L95 200"/>
          <path d="M145 0 L125 200"/>
          <path d="M175 0 L155 200"/>
          <path d="M205 0 L185 200"/>
          <path d="M235 0 L215 200"/>
          <path d="M265 0 L245 200"/>
          <path d="M295 0 L275 200"/>
        </g>

        <circle
          cx="231"
          cy="55"
          r="48"
          fill="${c1}"
          opacity=".22"
          filter="url(#glow)"
        />

        <path
          d="M72 195 Q87 118 130 103 Q175 113 192 195Z"
          fill="#060606"
        />

        <circle
          cx="129"
          cy="80"
          r="29"
          fill="#060606"
        />
      `;

      break;


    // --------------------------------------------------------
    // BIOGRAPHY
    // --------------------------------------------------------

    case 'biography':

      scene = `
        <rect
          x="61"
          y="26"
          width="198"
          height="146"
          rx="4"
          fill="none"
          stroke="${c1}"
          stroke-width="3"
          stroke-opacity=".47"
        />

        <circle
          cx="160"
          cy="76"
          r="33"
          fill="#d9bd8c"
          opacity=".42"
        />

        <path
          d="M104 164 Q111 110 160 108 Q210 110 217 164Z"
          fill="#15100b"
          opacity=".9"
        />

        <path
          d="M78 185 H242"
          stroke="#f5ddad"
          stroke-opacity=".42"
          stroke-width="3"
        />

        <path
          d="M102 191 H218"
          stroke="#f5ddad"
          stroke-opacity=".25"
          stroke-width="2"
        />
      `;

      break;


    // --------------------------------------------------------
    // HISTORY
    // --------------------------------------------------------

    case 'history':

      scene = `
        <circle
          cx="261"
          cy="44"
          r="43"
          fill="#d5aa65"
          opacity=".30"
        />

        <g fill="#b68a50" opacity=".58">
          <rect x="70" y="77" width="23" height="93"/>
          <rect x="115" y="77" width="23" height="93"/>
          <rect x="160" y="77" width="23" height="93"/>
          <rect x="205" y="77" width="23" height="93"/>
        </g>

        <path
          d="M55 77 H244 L218 54 H80 Z"
          fill="#c79b5d"
          opacity=".65"
        />

        <rect
          x="50"
          y="169"
          width="203"
          height="12"
          fill="#d4ad70"
          opacity=".55"
        />
      `;

      break;


    // --------------------------------------------------------
    // ADVENTURE
    // --------------------------------------------------------

    case 'adventure':

      scene = `
        <circle
          cx="252"
          cy="49"
          r="45"
          fill="#f4cf63"
          opacity=".58"
          filter="url(#glow)"
        />

        <path
          d="M0 176 L61 104 L109 150 L158 72 L228 155 L269 111 L320 170 V200 H0Z"
          fill="#09231a"
        />

        <path
          d="M42 174 L98 120 L130 150"
          stroke="${c1}"
          stroke-width="4"
          fill="none"
          opacity=".55"
        />

        <circle
          cx="77"
          cy="61"
          r="27"
          fill="none"
          stroke="#e7fff1"
          stroke-width="3"
          stroke-opacity=".55"
        />

        <path
          d="M77 38 L87 65 L77 84 L68 60 Z"
          fill="#d8fff0"
          opacity=".65"
        />
      `;

      break;


    // --------------------------------------------------------
    // FAMILY
    // --------------------------------------------------------

    case 'family':

      scene = `
        <circle
          cx="250"
          cy="44"
          r="41"
          fill="#ffdd76"
          opacity=".72"
          filter="url(#glow)"
        />

        <path
          d="M82 112 L158 56 L236 112 V181 H82Z"
          fill="#d8ffe6"
          opacity=".52"
        />

        <rect
          x="135"
          y="126"
          width="46"
          height="55"
          rx="4"
          fill="#0e3726"
        />

        <rect
          x="102"
          y="126"
          width="25"
          height="25"
          fill="#fff7c9"
          opacity=".75"
        />

        <rect
          x="190"
          y="126"
          width="25"
          height="25"
          fill="#fff7c9"
          opacity=".75"
        />

        <g fill="#fff" opacity=".65">
          <circle cx="49" cy="47" r="3"/>
          <circle cx="78" cy="34" r="2"/>
          <circle cx="55" cy="81" r="2.5"/>
        </g>
      `;

      break;


    // --------------------------------------------------------
    // MUSIC
    // --------------------------------------------------------

    case 'music':

      scene = `
        <circle
          cx="224"
          cy="92"
          r="65"
          fill="#0d0714"
          stroke="${c1}"
          stroke-width="12"
          stroke-opacity=".58"
        />

        <circle
          cx="224"
          cy="92"
          r="22"
          fill="${c1}"
          opacity=".63"
        />

        <g fill="${c1}" opacity=".66">
          <rect x="38" y="108" width="9" height="54" rx="4"/>
          <rect x="54" y="84" width="9" height="78" rx="4"/>
          <rect x="70" y="119" width="9" height="43" rx="4"/>
          <rect x="86" y="66" width="9" height="96" rx="4"/>
          <rect x="102" y="98" width="9" height="64" rx="4"/>
          <rect x="118" y="121" width="9" height="41" rx="4"/>
        </g>
      `;

      break;


    // --------------------------------------------------------
    // WAR
    // --------------------------------------------------------

    case 'war':

      scene = `
        <circle
          cx="263"
          cy="45"
          r="42"
          fill="#cacb79"
          opacity=".27"
        />

        <path
          d="M0 162
             Q45 143 88 160
             Q121 132 157 157
             Q200 131 244 159
             Q281 138 320 155
             V200 H0Z"
          fill="#070906"
        />

        <g
          stroke="#a7b274"
          stroke-opacity=".28"
          stroke-width="2"
        >
          <path d="M30 162 L55 92"/>
          <path d="M55 92 L78 162"/>
          <path d="M217 159 L245 80"/>
          <path d="M245 80 L271 160"/>
        </g>

        <path
          d="M120 145 Q126 105 158 100 Q192 108 198 145Z"
          fill="#11150d"
        />
      `;

      break;


    // --------------------------------------------------------
    // SPORT
    // --------------------------------------------------------

    case 'sport':

      scene = `
        <ellipse
          cx="160"
          cy="149"
          rx="128"
          ry="47"
          fill="none"
          stroke="${c1}"
          stroke-width="6"
          stroke-opacity=".65"
        />

        <ellipse
          cx="160"
          cy="149"
          rx="98"
          ry="29"
          fill="#06131c"
          opacity=".75"
        />

        <circle
          cx="245"
          cy="60"
          r="34"
          fill="#d7f1ff"
          opacity=".75"
        />

        <path
          d="M225 60 L245 42 L265 60 L255 83 H235Z"
          fill="#0e4163"
          opacity=".65"
        />

        <g
          stroke="#fff"
          stroke-opacity=".22"
          stroke-width="3"
        >
          <path d="M65 144 H255"/>
          <path d="M160 121 V176"/>
        </g>
      `;

      break;


    // --------------------------------------------------------
    // DOCUMENTARY
    // --------------------------------------------------------

    case 'documentary':

      scene = `
        <rect
          x="61"
          y="43"
          width="198"
          height="122"
          rx="12"
          fill="none"
          stroke="${c1}"
          stroke-width="5"
          stroke-opacity=".62"
        />

        <circle
          cx="160"
          cy="104"
          r="42"
          fill="#071713"
          stroke="#baffdd"
          stroke-width="4"
          stroke-opacity=".43"
        />

        <circle
          cx="160"
          cy="104"
          r="19"
          fill="${c1}"
          opacity=".45"
          filter="url(#glow)"
        />

        <path
          d="M83 58 H110"
          stroke="#fff"
          stroke-width="4"
          opacity=".55"
        />

        <circle
          cx="236"
          cy="61"
          r="6"
          fill="#ff5454"
          opacity=".8"
        />
      `;

      break;


    // --------------------------------------------------------
    // WESTERN
    // --------------------------------------------------------

    case 'western':

      scene = `
        <circle
          cx="242"
          cy="68"
          r="61"
          fill="#f4a34a"
          opacity=".50"
          filter="url(#glow)"
        />

        <path
          d="M0 156 Q74 128 138 155 Q208 122 320 151 V200 H0Z"
          fill="#321609"
        />

        <path
          d="M84 151
             V92
             M84 109
             H61
             V87
             M84 120
             H104
             V99"
          stroke="#181009"
          stroke-width="13"
          stroke-linecap="round"
        />

        <path
          d="M197 150
             V103
             M197 118
             H178
             V99"
          stroke="#1d1109"
          stroke-width="10"
          stroke-linecap="round"
        />
      `;

      break;


    // --------------------------------------------------------
    // MYSTERY
    // --------------------------------------------------------

    case 'mystery':

      scene = `
        <ellipse
          cx="160"
          cy="174"
          rx="150"
          ry="40"
          fill="${c1}"
          opacity=".10"
          filter="url(#blur)"
        />

        <path
          d="M160 43
             C125 43 105 65 105 95
             C105 116 116 130 134 140
             L121 187
             H199
             L186 140
             C204 130 215 116 215 95
             C215 65 195 43 160 43Z"
          fill="#080711"
          stroke="${c1}"
          stroke-width="4"
          stroke-opacity=".52"
        />

        <circle
          cx="160"
          cy="94"
          r="14"
          fill="${c1}"
          opacity=".62"
          filter="url(#glow)"
        />

        <path
          d="M160 105 L148 156 H172Z"
          fill="${c1}"
          opacity=".55"
        />
      `;

      break;


    // --------------------------------------------------------
    // GENERIC / FUTURE GENRE
    // --------------------------------------------------------

    default:

      scene = `
        <circle
          cx="250"
          cy="47"
          r="54"
          fill="${c1}"
          opacity=".30"
          filter="url(#glow)"
        />

        <path
          d="M20 160
             L90 78
             L145 134
             L202 68
             L300 166"
          stroke="${c1}"
          stroke-width="7"
          fill="none"
          stroke-linejoin="round"
          opacity=".52"
        />

        <path
          d="M0 181 H320"
          stroke="#ffffff"
          stroke-width="2"
          stroke-opacity=".16"
        />

        <g
          fill="#fff"
          opacity=".45"
        >
          <circle cx="46" cy="46" r="2"/>
          <circle cx="91" cy="29" r="1.5"/>
          <circle cx="139" cy="56" r="2"/>
          <circle cx="191" cy="24" r="1.5"/>
        </g>
      `;

      break;
  }


  return `
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 320 200"
      preserveAspectRatio="xMidYMid slice"
    >

      <defs>

        <linearGradient
          id="bg"
          x1="0"
          y1="0"
          x2="1"
          y2="1"
        >
          <stop
            offset="0%"
            stop-color="${c2}"
          />

          <stop
            offset="54%"
            stop-color="#050806"
          />

          <stop
            offset="100%"
            stop-color="${c1}"
            stop-opacity=".35"
          />
        </linearGradient>

        <radialGradient id="halo">
          <stop
            offset="0%"
            stop-color="${c1}"
            stop-opacity=".25"
          />

          <stop
            offset="100%"
            stop-color="${c1}"
            stop-opacity="0"
          />
        </radialGradient>

        <filter id="glow">
          <feGaussianBlur
            stdDeviation="7"
          />
        </filter>

        <filter id="blur">
          <feGaussianBlur
            stdDeviation="14"
          />
        </filter>

      </defs>


      <rect
        width="320"
        height="200"
        fill="url(#bg)"
      />


      <circle
        cx="55"
        cy="40"
        r="100"
        fill="url(#halo)"
        opacity=".65"
      />


      ${scene}


      <rect
        x="0"
        y="0"
        width="320"
        height="200"
        fill="none"
        stroke="#ffffff"
        stroke-opacity=".06"
        stroke-width="2"
      />


      <rect
        y="105"
        width="320"
        height="95"
        fill="url(#shade)"
        opacity=".2"
      />

    </svg>
  `;
}


/*
  V21 dagi real movie poster loaderni
  ataylab override qilamiz.

  Endi janr kartalari kino posterini emas,
  ORIGINAL V22 artworkni oladi.
*/

function xdLoadGenrePoster(card) {

  if (!card) return;


  const genre =
    card.dataset.genre || '';


  const svg =
    xdV22GenreArtwork(
      genre
    );


  card.style.setProperty(
    '--genre-poster',
    xdV22SvgUrl(svg)
  );


  card.dataset.genrePosterState =
    'original';


  card.classList.add(
    'has-original-genre-art'
  );


  card.classList.remove(
    'has-genre-poster'
  );
}


/*
  V21 allaqachon kartalarni chizgan bo'lsa ham
  V22 ularni qayta dekoratsiya qiladi.
*/

function xdV22RefreshGenrePosters() {

  document
    .querySelectorAll(
      '.genre-card[data-genre]'
    )
    .forEach(
      card => {
        xdLoadGenrePoster(card);
      }
    );
}


setTimeout(
  xdV22RefreshGenrePosters,
  50
);


const xdV22GenreObserver =
  new MutationObserver(() => {

    clearTimeout(
      xdV22GenreObserver.timer
    );


    xdV22GenreObserver.timer =
      setTimeout(
        xdV22RefreshGenrePosters,
        40
      );
  });


if (document.body) {

  xdV22GenreObserver.observe(
    document.body,
    {
      childList: true,
      subtree: true
    }
  );
}


// ============================================================
// FINAL_V23_EDITORIAL_GENRES
// Adult / premium cinematic editorial cards
// ============================================================

function xdV23Xml(value) {

  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}


function xdV23Hash(value) {

  const text = String(value || '');

  let hash = 0;

  for (let i = 0; i < text.length; i++) {

    hash =
      (
        (hash << 5)
        - hash
        + text.charCodeAt(i)
      ) | 0;
  }

  return Math.abs(hash);
}


function xdV23Mode(art) {

  if (
    [
      'horror',
      'thriller',
      'crime',
      'detective',
      'mystery'
    ].includes(art)
  ) {
    return 'noir';
  }


  if (
    [
      'action',
      'war',
      'sport'
    ].includes(art)
  ) {
    return 'kinetic';
  }


  if (
    [
      'scifi',
      'fantasy',
      'anime'
    ].includes(art)
  ) {
    return 'cosmic';
  }


  if (
    [
      'history',
      'biography',
      'western',
      'documentary'
    ].includes(art)
  ) {
    return 'archive';
  }


  if (
    [
      'drama',
      'romance'
    ].includes(art)
  ) {
    return 'emotional';
  }


  if (
    [
      'music'
    ].includes(art)
  ) {
    return 'music';
  }


  if (
    [
      'adventure'
    ].includes(art)
  ) {
    return 'horizon';
  }


  return 'studio';
}


function xdV23GenreArtwork(genre) {

  const profile =
    xdGenreProfile(genre);

  const art =
    profile.art || 'cinema-a';

  const mode =
    xdV23Mode(art);

  const accent =
    profile.g1 || '#48e66a';

  const deep =
    profile.g2 || '#09170e';

  const title =
    xdV23Xml(
      normalizeUzbekDisplayText(
        String(genre || 'KINO')
      ).toUpperCase()
    );

  const hash =
    xdV23Hash(genre);

  const angle =
    18 + (hash % 34);

  const flareX =
    185 + (hash % 95);

  const flareY =
    30 + (hash % 55);

  let texture = '';


  // ==========================================================
  // NOIR
  // ==========================================================

  if (mode === 'noir') {

    texture = `
      <g opacity=".26">
        <path
          d="M-30 45 L350 5"
          stroke="#ffffff"
          stroke-width="2"
        />
        <path
          d="M-30 72 L350 32"
          stroke="#ffffff"
          stroke-width="1.5"
        />
        <path
          d="M-30 99 L350 59"
          stroke="#ffffff"
          stroke-width="1.2"
        />
        <path
          d="M-30 126 L350 86"
          stroke="#ffffff"
          stroke-width="1"
        />
      </g>

      <ellipse
        cx="242"
        cy="72"
        rx="88"
        ry="38"
        fill="${accent}"
        opacity=".10"
        filter="url(#blur)"
      />

      <rect
        x="226"
        y="-20"
        width="11"
        height="240"
        fill="${accent}"
        opacity=".16"
        transform="rotate(24 226 100)"
      />
    `;
  }


  // ==========================================================
  // KINETIC
  // ==========================================================

  else if (mode === 'kinetic') {

    texture = `
      <g
        transform="rotate(-${angle} 160 100)"
        opacity=".28"
      >

        <rect
          x="-80"
          y="34"
          width="480"
          height="5"
          fill="${accent}"
        />

        <rect
          x="-100"
          y="59"
          width="430"
          height="2"
          fill="#ffffff"
        />

        <rect
          x="-80"
          y="88"
          width="520"
          height="14"
          fill="${accent}"
          opacity=".30"
        />

        <rect
          x="-110"
          y="129"
          width="460"
          height="3"
          fill="#ffffff"
          opacity=".45"
        />

      </g>

      <ellipse
        cx="${flareX}"
        cy="${flareY}"
        rx="82"
        ry="30"
        fill="${accent}"
        opacity=".13"
        filter="url(#blur)"
      />
    `;
  }


  // ==========================================================
  // COSMIC
  // ==========================================================

  else if (mode === 'cosmic') {

    texture = `
      <ellipse
        cx="232"
        cy="69"
        rx="105"
        ry="46"
        fill="none"
        stroke="${accent}"
        stroke-width="2"
        stroke-opacity=".36"
        transform="rotate(-18 232 69)"
      />

      <ellipse
        cx="232"
        cy="69"
        rx="71"
        ry="28"
        fill="none"
        stroke="#ffffff"
        stroke-width="1"
        stroke-opacity=".16"
        transform="rotate(16 232 69)"
      />

      <circle
        cx="${flareX}"
        cy="${flareY}"
        r="57"
        fill="${accent}"
        opacity=".13"
        filter="url(#blur)"
      />

      <g fill="#ffffff" opacity=".38">
        <circle cx="45" cy="36" r="1"/>
        <circle cx="82" cy="67" r="1.4"/>
        <circle cx="126" cy="29" r=".8"/>
        <circle cx="176" cy="54" r="1"/>
        <circle cx="279" cy="35" r="1.2"/>
        <circle cx="298" cy="92" r=".8"/>
      </g>
    `;
  }


  // ==========================================================
  // ARCHIVE
  // ==========================================================

  else if (mode === 'archive') {

    texture = `
      <rect
        x="30"
        y="22"
        width="260"
        height="156"
        fill="none"
        stroke="${accent}"
        stroke-width="1.5"
        stroke-opacity=".20"
      />

      <rect
        x="42"
        y="34"
        width="236"
        height="132"
        fill="none"
        stroke="#ffffff"
        stroke-width="1"
        stroke-opacity=".08"
      />

      <path
        d="M65 143 H255"
        stroke="${accent}"
        stroke-width="1.5"
        stroke-opacity=".30"
      />

      <circle
        cx="252"
        cy="53"
        r="52"
        fill="${accent}"
        opacity=".11"
        filter="url(#blur)"
      />

      <g opacity=".11">
        <path d="M74 33 V165" stroke="#fff"/>
        <path d="M111 33 V165" stroke="#fff"/>
        <path d="M148 33 V165" stroke="#fff"/>
      </g>
    `;
  }


  // ==========================================================
  // EMOTIONAL
  // ==========================================================

  else if (mode === 'emotional') {

    texture = `
      <ellipse
        cx="245"
        cy="58"
        rx="91"
        ry="50"
        fill="${accent}"
        opacity=".16"
        filter="url(#blur)"
      />

      <ellipse
        cx="107"
        cy="155"
        rx="80"
        ry="48"
        fill="${accent}"
        opacity=".08"
        filter="url(#blur)"
      />

      <path
        d="M178 -20
           C142 49 215 77 175 134
           C149 170 154 191 162 220"
        fill="none"
        stroke="#ffffff"
        stroke-width="2"
        stroke-opacity=".13"
      />

      <path
        d="M193 -20
           C157 49 230 77 190 134
           C164 170 169 191 177 220"
        fill="none"
        stroke="${accent}"
        stroke-width="7"
        stroke-opacity=".13"
      />
    `;
  }


  // ==========================================================
  // MUSIC
  // ==========================================================

  else if (mode === 'music') {

    texture = `
      <g opacity=".28">

        <rect x="42"  y="105" width="4" height="56" fill="${accent}"/>
        <rect x="55"  y="78"  width="4" height="83" fill="${accent}"/>
        <rect x="68"  y="118" width="4" height="43" fill="${accent}"/>
        <rect x="81"  y="61"  width="4" height="100" fill="${accent}"/>
        <rect x="94"  y="91"  width="4" height="70" fill="${accent}"/>
        <rect x="107" y="124" width="4" height="37" fill="${accent}"/>
        <rect x="120" y="72"  width="4" height="89" fill="${accent}"/>

      </g>

      <circle
        cx="240"
        cy="67"
        r="57"
        fill="none"
        stroke="${accent}"
        stroke-width="2"
        stroke-opacity=".28"
      />

      <circle
        cx="240"
        cy="67"
        r="29"
        fill="${accent}"
        opacity=".10"
        filter="url(#blur)"
      />
    `;
  }


  // ==========================================================
  // HORIZON
  // ==========================================================

  else if (mode === 'horizon') {

    texture = `
      <circle
        cx="254"
        cy="58"
        r="58"
        fill="${accent}"
        opacity=".13"
        filter="url(#blur)"
      />

      <path
        d="M0 148
           L55 91
           L92 121
           L141 68
           L194 126
           L241 85
           L320 147"
        fill="none"
        stroke="${accent}"
        stroke-width="2"
        stroke-opacity=".29"
      />

      <path
        d="M0 158 H320"
        stroke="#ffffff"
        stroke-width="1"
        stroke-opacity=".12"
      />

      <path
        d="M0 167 H320"
        stroke="${accent}"
        stroke-width="1"
        stroke-opacity=".12"
      />
    `;
  }


  // ==========================================================
  // STUDIO
  // ==========================================================

  else {

    texture = `
      <circle
        cx="${flareX}"
        cy="${flareY}"
        r="70"
        fill="${accent}"
        opacity=".11"
        filter="url(#blur)"
      />

      <rect
        x="52"
        y="-50"
        width="2"
        height="300"
        fill="#ffffff"
        opacity=".10"
        transform="rotate(28 52 100)"
      />

      <rect
        x="87"
        y="-50"
        width="18"
        height="300"
        fill="${accent}"
        opacity=".07"
        transform="rotate(28 87 100)"
      />

      <rect
        x="128"
        y="-50"
        width="1"
        height="300"
        fill="#ffffff"
        opacity=".14"
        transform="rotate(28 128 100)"
      />
    `;
  }


  return `
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 320 200"
      preserveAspectRatio="xMidYMid slice"
    >

      <defs>

        <linearGradient
          id="base"
          x1="0"
          y1="0"
          x2="1"
          y2="1"
        >

          <stop
            offset="0%"
            stop-color="#020403"
          />

          <stop
            offset="43%"
            stop-color="${deep}"
          />

          <stop
            offset="100%"
            stop-color="#020302"
          />

        </linearGradient>


        <radialGradient id="vignette">

          <stop
            offset="0%"
            stop-color="#ffffff"
            stop-opacity="0"
          />

          <stop
            offset="70%"
            stop-color="#000000"
            stop-opacity=".15"
          />

          <stop
            offset="100%"
            stop-color="#000000"
            stop-opacity=".63"
          />

        </radialGradient>


        <filter id="blur">

          <feGaussianBlur
            stdDeviation="17"
          />

        </filter>


        <filter id="grain">

          <feTurbulence
            type="fractalNoise"
            baseFrequency=".72"
            numOctaves="2"
            seed="${(hash % 17) + 1}"
          />

          <feColorMatrix
            type="saturate"
            values="0"
          />

        </filter>

      </defs>


      <rect
        width="320"
        height="200"
        fill="url(#base)"
      />


      ${texture}


      <!-- editorial oversized type -->

      <text
        x="18"
        y="73"
        fill="#ffffff"
        fill-opacity=".055"
        font-family="Arial,Helvetica,sans-serif"
        font-size="48"
        font-weight="900"
        letter-spacing="-2"
      >
        ${title}
      </text>


      <text
        x="21"
        y="111"
        fill="${accent}"
        fill-opacity=".075"
        font-family="Arial,Helvetica,sans-serif"
        font-size="29"
        font-weight="800"
        letter-spacing="4"
      >
        XD KINO
      </text>


      <!-- fine cinematic frame -->

      <rect
        x="1"
        y="1"
        width="318"
        height="198"
        fill="none"
        stroke="#ffffff"
        stroke-opacity=".06"
        stroke-width="1"
      />


      <!-- grain -->

      <rect
        width="320"
        height="200"
        filter="url(#grain)"
        opacity=".035"
      />


      <rect
        width="320"
        height="200"
        fill="url(#vignette)"
      />


      <!-- anamorphic light -->

      <rect
        x="0"
        y="${84 + (hash % 26)}"
        width="320"
        height="1"
        fill="${accent}"
        opacity=".19"
      />

    </svg>
  `;
}


// V22 artwork engine o'rniga V23
xdV22GenreArtwork =
  xdV23GenreArtwork;


// Ekrandagi mavjud kartalarni darhol yangilash
setTimeout(
  () => {

    if (
      typeof xdV22RefreshGenrePosters ===
      'function'
    ) {

      xdV22RefreshGenrePosters();
    }

  },
  20
);


// ============================================================
// FINAL_V24_PHOTO_GENRES
// Reference-style cinematic photo genre cards
// ============================================================

let xdV24CataloguePromise = null;

const xdV24UsedMovies =
  new Set();


function xdV24Norm(value) {

  return String(value || '')
    .toLowerCase()
    .replace(/[????`?]/g, "'")
    .replace(/\s+/g, ' ')
    .trim();
}


function xdV24Score(movie) {

  const imdb =
    imdbNumber(movie?.imdb);

  const views =
    viewsNumber(movie?.views);

  return (
    imdb * 1000000 +
    Math.min(
      views,
      999999
    )
  );
}


async function xdV24Catalogue() {

  if (!xdV24CataloguePromise) {

    xdV24CataloguePromise =
      api(
        '/api/movies?sort=popular&limit=100'
      )
      .then(payload => itemsFrom(payload))
      .catch(() => []);
  }

  return xdV24CataloguePromise;
}


function xdV24MatchesGenre(
  movie,
  genre
) {

  const wanted =
    xdV24Norm(genre);

  const movieGenres =
    xdV24Norm(
      movie?.genre || ''
    );

  if (!wanted || !movieGenres) {
    return false;
  }


  // Exact / substring match
  if (
    movieGenres.includes(wanted) ||
    wanted.includes(movieGenres)
  ) {
    return true;
  }


  // Uzbek/Russian/English yaqin nomlar
  const aliases = {

    "jangari": [
      "action",
      "jangari"
    ],

    "detektiv": [
      "detective",
      "detektiv"
    ],

    "kriminal": [
      "crime",
      "kriminal"
    ],

    "qo'rqinchli": [
      "horror",
      "qo'rqinchli",
      "dahshat"
    ],

    "harbiy": [
      "war",
      "harbiy",
      "urush"
    ],

    "triller": [
      "thriller",
      "triller"
    ],

    "sarguzasht": [
      "adventure",
      "sarguzasht"
    ],

    "melodrama": [
      "melodrama",
      "romantika",
      "drama"
    ],

    "drama": [
      "drama"
    ],

    "komediya": [
      "comedy",
      "komediya"
    ],

    "sport": [
      "sport"
    ],

    "western": [
      "western",
      "vestern"
    ],

    "fantastika": [
      "fantastika",
      "fantasy"
    ],

    "fentezi": [
      "fantasy",
      "fentezi"
    ],

    "ilmiy-fantastika": [
      "science fiction",
      "sci-fi",
      "ilmiy fantastika",
      "fantastika"
    ],

    "tarixiy": [
      "history",
      "historical",
      "tarixiy"
    ],

    "biografik": [
      "biography",
      "biografik"
    ],

    "biografiya": [
      "biography",
      "biografik"
    ],

    "hujjatli": [
      "documentary",
      "hujjatli"
    ],

    "romantika": [
      "romance",
      "romantika"
    ],

    "anime": [
      "anime"
    ],

    "animatsion": [
      "animation",
      "animatsion",
      "multfilm"
    ],

    "musiqiy": [
      "music",
      "musical",
      "musiqiy"
    ],

    "oilaviy": [
      "family",
      "oilaviy"
    ]
  };


  const words =
    aliases[wanted] || [wanted];


  return words.some(
    word =>
      movieGenres.includes(
        xdV24Norm(word)
      )
  );
}


async function xdV24Candidates(
  genre
) {

  const catalogue =
    await xdV24Catalogue();


  let candidates =
    catalogue
      .filter(
        movie =>
          xdV24MatchesGenre(
            movie,
            genre
          )
      );


  // 100 ta mashhur kino ichida topilmasa
  // aynan shu janrni serverdan qidiramiz.

  if (!candidates.length) {

    try {

      const params =
        new URLSearchParams({
          genre,
          sort: 'popular',
          limit: '20'
        });


      const payload =
        await api(
          `/api/movies?${params.toString()}`
        );


      candidates =
        itemsFrom(payload);

    }
    catch (_) {

      candidates = [];
    }
  }


  return candidates
    .filter(
      movie =>
        movie &&
        movie.code != null
    )
    .sort(
      (a,b) =>
        xdV24Score(b) -
        xdV24Score(a)
    );
}


async function xdLoadGenrePoster(
  card
) {

  if (!card) return;


  if (
    card.dataset.v24Photo ===
    'ready'
  ) {
    return;
  }


  if (
    card.dataset.v24Photo ===
    'loading'
  ) {
    return;
  }


  card.dataset.v24Photo =
    'loading';


  const genre =
    card.dataset.genre || '';


  const candidates =
    await xdV24Candidates(
      genre
    );


  if (!candidates.length) {

    card.dataset.v24Photo =
      'fallback';

    card.classList.add(
      'v24-photo-genre'
    );

    return;
  }


  // Bir xil kino iloji boricha
  // bir nechta janrda takrorlanmasin.

  const movie =
    candidates.find(
      item =>
        !xdV24UsedMovies.has(
          Number(item.code)
        )
    )
    ||
    candidates[0];


  const code =
    Number(movie.code);


  xdV24UsedMovies.add(code);


  const imageUrl =
    posterUrl(code);


  // Avval rasmni tekshiramiz.
  // Faqat yuklangandan keyin kartaga qo'yiladi.

  const preload =
    new Image();


  preload.onload = () => {

    card.style.setProperty(
      '--genre-photo',
      `url("${imageUrl}")`
    );


    card.dataset.v24Photo =
      'ready';


    card.classList.add(
      'v24-photo-genre'
    );
  };


  preload.onerror = () => {

    card.dataset.v24Photo =
      'fallback';


    card.classList.add(
      'v24-photo-genre'
    );
  };


  preload.src =
    imageUrl;
}


function xdV24ApplyGenres() {

  const cards =
    document.querySelectorAll(
      '.genre-card[data-genre]'
    );


  cards.forEach(
    card => {

      card.classList.add(
        'v24-photo-genre'
      );

      xdLoadGenrePoster(
        card
      );
    }
  );
}


setTimeout(
  xdV24ApplyGenres,
  40
);


const xdV24Observer =
  new MutationObserver(() => {

    clearTimeout(
      xdV24Observer.timer
    );


    xdV24Observer.timer =
      setTimeout(
        xdV24ApplyGenres,
        40
      );
  });


if (document.body) {

  xdV24Observer.observe(
    document.body,
    {
      childList: true,
      subtree: true
    }
  );
}


// ============================================================
// FINAL_V27_CINEMA_FILTERS
// Native select -> xD KINO cinematic filter sheet
// ============================================================

const XD_V27_FILTERS = {

  typeSelect: {
    kicker: "KONTENT",
    title: "Nimani ko'ramiz?",
    options: {
      "": {
        label: "Barchasi",
        hint: "Barcha kontent"
      },
      "Kino": {
        label: "Kino",
        hint: "To'liq metrajli filmlar"
      },
      "Serial": {
        label: "Serial",
        hint: "Serial va qismlar"
      },
      "Multfilm": {
        label: "Multfilm",
        hint: "Animatsion kontent"
      }
    }
  },

  sortSelect: {
    kicker: "SARALASH",
    title: "Qanday tartibda?",
    options: {
      "popular": {
        label: "Mashhur",
        hint: "Ko'p ko'rilganlar"
      },
      "new": {
        label: "Yangi",
        hint: "Eng so'nggi qo'shilganlar"
      },
      "year": {
        label: "Yil",
        hint: "Chiqqan yili bo'yicha"
      },
      "name": {
        label: "Nomi",
        hint: "A dan Z gacha"
      }
    }
  }

};


function xdV27ChevronSvg() {

  return `
    <svg viewBox="0 0 24 24"
         aria-hidden="true">
      <path d="M7 9.5 12 14.5 17 9.5"></path>
    </svg>
  `;
}


function xdV27FilterIcon(type) {

  if (type === "sortSelect") {

    return `
      <svg viewBox="0 0 24 24"
           aria-hidden="true">
        <path d="M4 7h11"></path>
        <path d="M4 12h8"></path>
        <path d="M4 17h5"></path>
        <path d="m16 14 3 3 3-3"></path>
        <path d="M19 5v12"></path>
      </svg>
    `;
  }

  return `
    <svg viewBox="0 0 24 24"
         aria-hidden="true">
      <rect x="3.5"
            y="5"
            width="17"
            height="14"
            rx="3"></rect>

      <path d="M8 5v14"></path>
      <path d="M16 5v14"></path>
      <path d="M3.5 9h4.5"></path>
      <path d="M16 9h4.5"></path>
      <path d="M3.5 15h4.5"></path>
      <path d="M16 15h4.5"></path>
    </svg>
  `;
}


function xdV27CurrentLabel(
  select,
  config
) {

  return (
    config.options[
      select.value
    ]?.label
    ||
    select.options[
      select.selectedIndex
    ]?.textContent
    ||
    ""
  );
}


let xdV27Sheet = null;


function xdV27CloseSheet() {

  if (!xdV27Sheet) return;

  xdV27Sheet.classList.remove(
    "show"
  );

  document.body.classList.remove(
    "xd-filter-open"
  );

  setTimeout(() => {

    xdV27Sheet?.remove();
    xdV27Sheet = null;

  }, 240);
}


function xdV27OpenSheet(
  select,
  config,
  trigger
) {

  xdV27CloseSheet();


  const overlay =
    document.createElement(
      "div"
    );

  overlay.className =
    "xd-filter-overlay";


  const sheet =
    document.createElement(
      "div"
    );

  sheet.className =
    "xd-filter-sheet";


  const handle =
    document.createElement(
      "div"
    );

  handle.className =
    "xd-filter-handle";


  const head =
    document.createElement(
      "div"
    );

  head.className =
    "xd-filter-sheet-head";


  const copy =
    document.createElement(
      "div"
    );


  const kicker =
    document.createElement(
      "span"
    );

  kicker.className =
    "xd-filter-kicker";

  kicker.textContent =
    config.kicker;


  const title =
    document.createElement(
      "strong"
    );

  title.textContent =
    config.title;


  copy.append(
    kicker,
    title
  );


  const close =
    document.createElement(
      "button"
    );

  close.type =
    "button";

  close.className =
    "xd-filter-close";

  close.setAttribute(
    "aria-label",
    "Yopish"
  );

  close.innerHTML = `
    <svg viewBox="0 0 24 24"
         aria-hidden="true">
      <path d="M6 6 18 18"></path>
      <path d="M18 6 6 18"></path>
    </svg>
  `;


  head.append(
    copy,
    close
  );


  const grid =
    document.createElement(
      "div"
    );

  grid.className =
    "xd-filter-grid";


  Object.entries(
    config.options
  ).forEach(
    ([value, option], index) => {

      const button =
        document.createElement(
          "button"
        );

      button.type =
        "button";

      button.className =
        "xd-filter-option";

      if (
        String(select.value) ===
        String(value)
      ) {

        button.classList.add(
          "active"
        );
      }


      const number =
        document.createElement(
          "span"
        );

      number.className =
        "xd-filter-number";

      number.textContent =
        String(index + 1)
          .padStart(2, "0");


      const optionTitle =
        document.createElement(
          "strong"
        );

      optionTitle.textContent =
        option.label;


      const hint =
        document.createElement(
          "small"
        );

      hint.textContent =
        option.hint;


      const check =
        document.createElement(
          "span"
        );

      check.className =
        "xd-filter-check";

      check.innerHTML = `
        <svg viewBox="0 0 24 24"
             aria-hidden="true">
          <path d="m6 12 4 4 8-9"></path>
        </svg>
      `;


      button.append(
        number,
        optionTitle,
        hint,
        check
      );


      button.addEventListener(
        "click",
        () => {

          select.value =
            value;

          select.dispatchEvent(
            new Event(
              "change",
              {
                bubbles: true
              }
            )
          );


          const label =
            trigger.querySelector(
              ".xd-filter-trigger-label"
            );

          if (label) {
            label.textContent =
              option.label;
          }


          try {

            tg?.HapticFeedback
              ?.selectionChanged?.();

          } catch (_) {}


          xdV27CloseSheet();
        }
      );


      grid.appendChild(
        button
      );
    }
  );


  sheet.append(
    handle,
    head,
    grid
  );


  overlay.appendChild(
    sheet
  );


  document.body.appendChild(
    overlay
  );


  xdV27Sheet =
    overlay;


  requestAnimationFrame(
    () => {

      overlay.classList.add(
        "show"
      );

      document.body.classList.add(
        "xd-filter-open"
      );
    }
  );


  overlay.addEventListener(
    "click",
    event => {

      if (
        event.target === overlay
      ) {

        xdV27CloseSheet();
      }
    }
  );


  close.addEventListener(
    "click",
    xdV27CloseSheet
  );
}


function xdV27EnhanceSelect(
  selectId
) {

  const select =
    document.getElementById(
      selectId
    );

  const config =
    XD_V27_FILTERS[
      selectId
    ];

  if (
    !select ||
    !config ||
    select.dataset.xdEnhanced === "1"
  ) {
    return;
  }


  const trigger =
    document.createElement(
      "button"
    );

  trigger.type =
    "button";

  trigger.className =
    "xd-filter-trigger";


  const icon =
    document.createElement(
      "span"
    );

  icon.className =
    "xd-filter-trigger-icon";

  icon.innerHTML =
    xdV27FilterIcon(
      selectId
    );


  const content =
    document.createElement(
      "span"
    );

  content.className =
    "xd-filter-trigger-content";


  const eyebrow =
    document.createElement(
      "small"
    );

  eyebrow.textContent =
    config.kicker;


  const label =
    document.createElement(
      "strong"
    );

  label.className =
    "xd-filter-trigger-label";

  label.textContent =
    xdV27CurrentLabel(
      select,
      config
    );


  content.append(
    eyebrow,
    label
  );


  const chevron =
    document.createElement(
      "span"
    );

  chevron.className =
    "xd-filter-chevron";

  chevron.innerHTML =
    xdV27ChevronSvg();


  trigger.append(
    icon,
    content,
    chevron
  );


  select.insertAdjacentElement(
    "afterend",
    trigger
  );


  select.classList.add(
    "xd-native-select"
  );

  select.dataset.xdEnhanced =
    "1";


  trigger.addEventListener(
    "click",
    () => {

      xdV27OpenSheet(
        select,
        config,
        trigger
      );
    }
  );


  select.addEventListener(
    "change",
    () => {

      label.textContent =
        xdV27CurrentLabel(
          select,
          config
        );
    }
  );
}


function xdV27StartFilters() {

  xdV27EnhanceSelect(
    "typeSelect"
  );

  xdV27EnhanceSelect(
    "sortSelect"
  );
}


if (
  document.readyState ===
  "loading"
) {

  document.addEventListener(
    "DOMContentLoaded",
    xdV27StartFilters,
    {
      once: true
    }
  );

} else {

  xdV27StartFilters();
}


document.addEventListener(
  "keydown",
  event => {

    if (
      event.key === "Escape" &&
      xdV27Sheet
    ) {

      xdV27CloseSheet();
    }
  }
);
