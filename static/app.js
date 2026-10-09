
const tg = window.Telegram?.WebApp || null;

// FINAL_V13_SPLASH_TIMER
const XD_SPLASH_STARTED_AT = Date.now();
const XD_SPLASH_MIN_MS = 1850;


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
