const artistList = document.getElementById('artist-grid');
const searchInput = document.getElementById('artist-search');
const filters = document.getElementById('genre-filters');
const artistCount = document.getElementById('artist-count');

const state = {
  artists: [],
  query: '',
  genre: 'all',
};

function normalizeText(value) {
  return String(value || '').trim().toLowerCase();
}

function getGenres(artist) {
  if (!artist) return ['uncategorized'];
  if (Array.isArray(artist.tags) && artist.tags.length) return artist.tags;
  if (artist.genre) return [artist.genre];
  return ['uncategorized'];
}

function renderFilters() {
  const uniqueGenres = [...new Set(state.artists.flatMap((artist) => getGenres(artist)))].sort();
  const items = ['all', ...uniqueGenres];

  filters.innerHTML = items
    .map((genre) => {
      const activeClass = state.genre === genre ? 'is-active' : '';
      const label = genre === 'all' ? 'All' : genre;
      return `<button class="filter-pill ${activeClass}" data-genre="${genre}">${label}</button>`;
    })
    .join('');

  filters.querySelectorAll('.filter-pill').forEach((button) => {
    button.addEventListener('click', () => {
      state.genre = button.dataset.genre;
      renderFilters();
      renderList();
    });
  });
}

function renderList() {
  const filtered = state.artists.filter((artist) => {
    const matchesQuery = !state.query || normalizeText(artist.name).includes(normalizeText(state.query));
    const matchesGenre = state.genre === 'all' || getGenres(artist).includes(state.genre);
    return matchesQuery && matchesGenre;
  });

  artistList.innerHTML = filtered.length
    ? filtered
        .map(
          (artist) => `
            <article class="artist-card">
              <h4>${artist.name}</h4>
              <span class="artist-meta">${getGenres(artist)[0]}</span>
            </article>
          `
        )
        .join('')
    : '<p class="empty-state">No artists match that search yet.</p>';

  artistCount.textContent = String(filtered.length);
}

async function loadArtists() {
  try {
    const response = await fetch('artists.json');
    if (!response.ok) throw new Error('Failed to load artist list');
    const data = await response.json();
    const rawArtists = Array.isArray(data) ? data : data.artists || [];
    state.artists = rawArtists.filter((artist, index, list) => {
      const name = String(artist?.name || '').trim();
      return name && list.findIndex((item) => String(item?.name || '').trim().toLowerCase() === name.toLowerCase()) === index;
    });
    renderFilters();
    renderList();
  } catch (error) {
    artistList.innerHTML = '<p class="empty-state">Unable to load the artist list right now.</p>';
    console.error(error);
  }
}

searchInput.addEventListener('input', (event) => {
  state.query = event.target.value;
  renderList();
});

loadArtists();
