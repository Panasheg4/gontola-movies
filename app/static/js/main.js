// ── LIVE SEARCH ───────────────────────────────────────────
const searchInput = document.getElementById('search-input');
const searchDropdown = document.getElementById('search-dropdown');

if (searchInput) {
    searchInput.addEventListener('input', async function() {
        const query = this.value.trim();

        if (query.length < 2) {
            searchDropdown.classList.remove('active');
            searchDropdown.innerHTML = '';
            return;
        }

        try {
            const res = await fetch(
                `/search/suggestions?q=${encodeURIComponent(query)}`
            );
            const movies = await res.json();

            if (movies.length === 0) {
                searchDropdown.classList.remove('active');
                return;
            }

            searchDropdown.innerHTML = movies.map(m => `
                <a href="/movie/${m.id}" class="search-item">
                    <img src="https://image.tmdb.org/t/p/w92${m.poster_path}"
                         class="search-item-poster"
                         onerror="this.style.display='none'"
                         alt="${m.title}">
                    <div class="search-item-info">
                        <div class="search-item-title">
                            ${m.title}
                        </div>
                        <div class="search-item-genre">
                            ${m.genre_names || ''}
                        </div>
                    </div>
                    <div class="search-item-rating">
                        ${m.vote_average
                            ? m.vote_average.toFixed(1)
                            : 'N/A'}
                    </div>
                </a>
            `).join('');

            searchDropdown.classList.add('active');

        } catch(err) {
            console.error('Search error:', err);
        }
    });

    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) &&
            !searchDropdown.contains(e.target)) {
            searchDropdown.classList.remove('active');
        }
    });
}

// ── ADMIN SEARCH ──────────────────────────────────────────
const adminSearchInput = document.getElementById(
    'admin-search-input'
);
const adminDropdown = document.getElementById(
    'admin-search-dropdown'
);

if (adminSearchInput && adminDropdown) {
    adminSearchInput.addEventListener(
        'input',
        async function() {
            const query = this.value.trim();

            if (query.length < 2) {
                adminDropdown.classList.remove('active');
                adminDropdown.innerHTML = '';
                return;
            }

            try {
                const res = await fetch(
                    `/admin/movie-suggestions?q=${encodeURIComponent(query)}`
                );
                const movies = await res.json();

                if (movies.length === 0) {
                    adminDropdown.innerHTML = `
                        <div class="admin-search-empty">
                            No results for "${query}"
                        </div>`;
                    adminDropdown.classList.add('active');
                    return;
                }

                adminDropdown.innerHTML = movies.map(m => `
                    <a href="/movie/${m.id}"
                       target="_blank"
                       class="admin-search-item">
                        <img src="https://image.tmdb.org/t/p/w92${m.poster_path}"
                             class="admin-search-thumb"
                             alt="${m.title}">
                        <div class="admin-search-item-info">
                            <div class="admin-search-item-title">
                                ${m.title}
                            </div>
                            <div class="admin-search-item-meta">
                                ${m.genre_names} · ${m.release_date}
                            </div>
                        </div>
                        <div class="admin-search-item-rating">
                            ⭐ ${m.vote_average
                                ? m.vote_average.toFixed(1)
                                : 'N/A'}
                        </div>
                    </a>
                `).join('');

                adminDropdown.classList.add('active');

            } catch(err) {
                console.error('Admin search error:', err);
            }
        }
    );

    document.addEventListener('click', function(e) {
        if (!adminSearchInput.contains(e.target) &&
            !adminDropdown.contains(e.target)) {
            adminDropdown.classList.remove('active');
        }
    });
}

// ── DROPDOWN MENU ─────────────────────────────────────────
const dropdownBtn = document.querySelector('.dropdown-btn');
const dropdownMenu = document.querySelector('.dropdown-menu');

if (dropdownBtn && dropdownMenu) {
    dropdownBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        dropdownMenu.classList.toggle('open');
    });

    document.addEventListener('click', function(e) {
        if (!dropdownBtn.contains(e.target)) {
            dropdownMenu.classList.remove('open');
        }
    });
}

// ── HAMBURGER MENU ────────────────────────────────────────
const hamburger = document.getElementById('hamburger');
const navLinks = document.getElementById('nav-links');

if (hamburger && navLinks) {
    hamburger.addEventListener('click', function(e) {
        e.stopPropagation();
        const isOpen = navLinks.classList.contains('open');
        navLinks.classList.toggle('open');
        const icon = hamburger.querySelector('i');
        icon.className = isOpen
            ? 'fa-solid fa-bars'
            : 'fa-solid fa-xmark';
    });

    document.addEventListener('click', function(e) {
        if (!navLinks.contains(e.target) &&
            !hamburger.contains(e.target)) {
            navLinks.classList.remove('open');
            const icon = hamburger.querySelector('i');
            if (icon) icon.className = 'fa-solid fa-bars';
        }
    });
}

// ── BROWSE CONTINUE ───────────────────────────────────────
const browseBtn = document.getElementById('browse-btn');
const browseFade = document.getElementById('browse-fade');
const browseGrid = document.getElementById('browse-grid');

if (browseBtn && browseFade && browseGrid) {
    browseGrid.style.maxHeight = '600px';
    browseGrid.style.overflow = 'hidden';

    browseBtn.addEventListener('click', function() {
        browseFade.style.display = 'none';
        browseGrid.style.maxHeight = 'none';
        browseGrid.style.overflow = 'visible';
    });
}

// ── SMOOTH PAGE TRANSITIONS ───────────────────────────────
window.addEventListener('pageshow', function() {
    const main = document.querySelector('.main-content');
    if (main) main.style.opacity = '1';
});

// ── SYSTEM STATUS CHECK ───────────────────────────────────
async function checkStatus() {
    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');
    if (!dot || !text) return;

    try {
        const res = await fetch(
            '/search/suggestions?q=test'
        );
        if (res.ok) {
            dot.style.background = '#4caf50';
            text.textContent = 'All systems operational';
        } else {
            dot.style.background = '#ff9800';
            text.textContent = 'Some issues detected';
        }
    } catch {
        dot.style.background = '#f44336';
        text.textContent = 'System offline';
    }
}

checkStatus();
setInterval(checkStatus, 30000);

// ── UPCOMING MOVIE LABEL ─────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
    const countdownInline = document.getElementById('countdown-inline');
    if (countdownInline) {
        countdownInline.textContent = 'Coming Soon';
    }

    const heroBanner = document.getElementById('hero-banner');
    const heroSlides = document.querySelectorAll('.hero-slide');
    const heroDots = document.querySelectorAll('.hero-dot');
    const heroArrows = document.querySelectorAll('.hero-arrow');

    if (heroBanner && heroSlides.length > 0) {
        let activeIndex = 0;
        const intervalMs = parseInt(heroBanner.dataset.rotationInterval, 10) || 7000;
        let heroTimer = null;
        let arrowHideTimer = null;

        const setActiveSlide = (index) => {
            heroSlides.forEach((slide, idx) => {
                slide.classList.toggle('active', idx === index);
            });
            heroDots.forEach((dot, idx) => {
                dot.classList.toggle('active', idx === index);
            });
            activeIndex = index;
        };

        const startHeroRotation = () => {
            heroTimer = setInterval(() => {
                const nextIndex = (activeIndex + 1) % heroSlides.length;
                setActiveSlide(nextIndex);
            }, intervalMs);
        };

        const showHeroArrows = () => {
            heroBanner.classList.add('hero-arrows-visible');
            if (arrowHideTimer) {
                clearTimeout(arrowHideTimer);
            }
            arrowHideTimer = setTimeout(() => {
                heroBanner.classList.remove('hero-arrows-visible');
            }, 2000);
        };

        const moveSlide = (direction) => {
            const nextIndex = (activeIndex + direction + heroSlides.length) % heroSlides.length;
            setActiveSlide(nextIndex);
            clearInterval(heroTimer);
            startHeroRotation();
            showHeroArrows();
        };

        heroDots.forEach((dot) => {
            dot.addEventListener('click', function() {
                const index = parseInt(this.dataset.index, 10);
                if (Number.isInteger(index)) {
                    setActiveSlide(index);
                    clearInterval(heroTimer);
                    startHeroRotation();
                    showHeroArrows();
                }
            });
        });

        heroArrows.forEach((button) => {
            button.addEventListener('click', function() {
                if (button.classList.contains('hero-arrow-left')) {
                    moveSlide(-1);
                } else {
                    moveSlide(1);
                }
            });
        });

        heroBanner.addEventListener('mousemove', showHeroArrows);
        heroBanner.addEventListener('mouseenter', showHeroArrows);
        heroBanner.addEventListener('mouseleave', () => {
            heroBanner.classList.remove('hero-arrows-visible');
            if (arrowHideTimer) {
                clearTimeout(arrowHideTimer);
            }
        });

        // Touch swipe support
        let touchStartX = 0;
        heroBanner.addEventListener('touchstart', function(e) {
            touchStartX = e.touches[0].clientX;
        }, { passive: true });
        
        heroBanner.addEventListener('touchend', function(e) {
            const diff = touchStartX - e.changedTouches[0].clientX;
            if (Math.abs(diff) > 50) {
                moveSlide(diff > 0 ? 1 : -1);
            }
        }, { passive: true });
        
        showHeroArrows();
        startHeroRotation();
    }
});

// ── TRAILER MODAL ─────────────────────────────────────────
function openTrailer(videoId, title) {
    const modal = document.getElementById('trailer-modal');
    const iframe = document.getElementById('trailer-iframe');
    const titleEl = document.getElementById('trailer-modal-title');

    if (!modal || !iframe) return;

    iframe.src = `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0`;
    if (titleEl) titleEl.textContent = title || '';
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
}

function closeTrailer() {
    const modal = document.getElementById('trailer-modal');
    const iframe = document.getElementById('trailer-iframe');

    if (!modal) return;

    iframe.src = '';
    modal.classList.remove('open');
    document.body.style.overflow = '';
}

// Close on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeTrailer();
});

document.addEventListener("DOMContentLoaded", function () {
    const modal = document.querySelector('.trailer-modal');
    if (modal) {
        // Moves the modal to the absolute root of the body element
        document.body.appendChild(modal);
    }
});

