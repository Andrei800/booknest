/**
 * BookNest - Главный JavaScript файл
 * Современный интерфейс с анимациями и темами
 */

console.log('📚 BookNest JS загружен!');

// === Theme Management ===
function initTheme() {
    const savedTheme = localStorage.getItem('booknest-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = savedTheme || (prefersDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('booknest-theme', next);
    
    // Анимация кнопки
    const toggle = document.getElementById('themeToggle');
    toggle.style.transform = 'scale(0.9)';
    setTimeout(() => toggle.style.transform = '', 200);
}

// Инициализация темы при загрузке
initTheme();

// === API клиент ===
const API_BASE = '/api';

async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const config = {
        headers: {
            'Content-Type': 'application/json',
        },
        ...options,
    };
    
    try {
        const response = await fetch(url, config);
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        
        if (response.status === 204) {
            return null;
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// === Состояние приложения ===
const state = {
    books: [],
    totalBooks: 0,
    currentPage: 1,
    perPage: 20,
    viewMode: localStorage.getItem('booknest-view') || 'medium',
    filters: {
        search: '',
        status: '',
        format: '',
        genre: '',
        sortBy: 'created_at',
        sortOrder: 'desc',
    },
    genres: [],
    stats: null,
};

// === Утилиты ===
const statusLabels = {
    planned: '📋 Хочу прочитать',
    reading: '📖 Читаю',
    finished: '✅ Прочитано',
    on_hold: '⏸️ Отложено',
    dropped: '❌ Брошено',
    wishlist: '🎁 Хотелки',
};

const formatLabels = {
    paper: '📕 Бумажная',
    ebook: '📱 Электронная',
    audiobook: '🎧 Аудиокнига',
};

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// === Toast уведомления ===
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    toast.innerHTML = `<span>${icons[type] || ''}</span><span>${message}</span>`;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// === Загрузка книг ===
async function loadBooks() {
    const grid = document.getElementById('booksGrid');
    grid.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    
    try {
        const params = new URLSearchParams();
        if (state.filters.search) params.set('search', state.filters.search);
        if (state.filters.status) params.set('status', state.filters.status);
        if (state.filters.format) params.set('format', state.filters.format);
        if (state.filters.genre) params.set('genre', state.filters.genre);
        params.set('sort_by', state.filters.sortBy);
        params.set('sort_order', state.filters.sortOrder);
        params.set('page', state.currentPage);
        params.set('per_page', state.perPage);
        
        const data = await apiRequest(`/books?${params}`);
        state.books = data.items;
        state.totalBooks = data.total;
        
        renderBooks();
        renderPagination();
        await loadStats(); // Обновляем счётчики
    } catch (error) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">😕</div>
                <h3>Ошибка загрузки</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

function renderBooks() {
    const grid = document.getElementById('booksGrid');
    
    if (state.books.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📚</div>
                <h3>Книг пока нет</h3>
                <p>Добавьте первую книгу, нажав кнопку "Добавить"</p>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = state.books.map(book => `
        <div class="book-card" data-id="${book.id}">
            <div class="book-cover">
                ${book.cover_url 
                    ? `<img src="${book.cover_url}" alt="${book.title}" loading="lazy">`
                    : '📖'
                }
            </div>
            <div class="book-info">
                <div class="book-title">${escapeHtml(book.title)}</div>
                <div class="book-author">${book.authors.map(a => a.name).join(', ') || 'Автор не указан'}</div>
                <div class="book-meta">
                    <span class="book-status status-${book.status}">${statusLabels[book.status] || book.status}</span>
                    ${book.rating ? `<span class="book-rating">⭐ ${book.rating}/10</span>` : ''}
                </div>
                ${book.total_pages ? `
                    <div class="book-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${book.progress}%"></div>
                        </div>
                        <div class="progress-text">${book.current_page || 0} / ${book.total_pages} стр. (${book.progress}%)</div>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
    
    // Обработчики кликов
    grid.querySelectorAll('.book-card').forEach(card => {
        card.addEventListener('click', () => openBookDetails(card.dataset.id));
    });
}

function renderPagination() {
    const pagination = document.getElementById('pagination');
    const totalPages = Math.ceil(state.totalBooks / state.perPage);
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // Кнопка "Назад"
    html += `<button ${state.currentPage === 1 ? 'disabled' : ''} data-page="${state.currentPage - 1}">←</button>`;
    
    // Номера страниц
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= state.currentPage - 2 && i <= state.currentPage + 2)) {
            html += `<button class="${i === state.currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
        } else if (i === state.currentPage - 3 || i === state.currentPage + 3) {
            html += '<button disabled>...</button>';
        }
    }
    
    // Кнопка "Вперёд"
    html += `<button ${state.currentPage === totalPages ? 'disabled' : ''} data-page="${state.currentPage + 1}">→</button>`;
    
    pagination.innerHTML = html;
    
    pagination.querySelectorAll('button[data-page]').forEach(btn => {
        btn.addEventListener('click', () => {
            state.currentPage = parseInt(btn.dataset.page);
            loadBooks();
        });
    });
}

// === Animated Counter ===
function animateCounter(element, target, duration = 1000) {
    const start = parseInt(element.textContent) || 0;
    const increment = (target - start) / (duration / 16);
    let current = start;
    
    const step = () => {
        current += increment;
        if ((increment > 0 && current >= target) || (increment < 0 && current <= target)) {
            element.textContent = target.toLocaleString();
            element.setAttribute('data-animate', 'done');
        } else {
            element.textContent = Math.round(current).toLocaleString();
            requestAnimationFrame(step);
        }
    };
    
    requestAnimationFrame(step);
}

// === Статистика ===
async function loadStats() {
    try {
        const stats = await apiRequest('/stats/full');
        state.stats = stats;
        
        // Обновляем счётчики на главной с анимацией
        animateCounter(document.getElementById('totalCount'), stats.overview.total_books);
        animateCounter(document.getElementById('readingCount'), stats.overview.books_reading);
        animateCounter(document.getElementById('finishedCount'), stats.overview.books_finished);
        animateCounter(document.getElementById('wishlistCount'), stats.overview.books_wishlist || 0);
        
        // Обновляем страницу статистики с анимацией
        animateCounter(document.getElementById('statTotalBooks'), stats.overview.total_books, 1200);
        animateCounter(document.getElementById('statFinishedBooks'), stats.overview.books_finished, 1200);
        animateCounter(document.getElementById('statPagesRead'), stats.overview.pages_read_total, 1500);
        
        const avgRatingEl = document.getElementById('statAvgRating');
        if (stats.overview.average_rating) {
            avgRatingEl.textContent = `${stats.overview.average_rating}/10`;
        } else {
            avgRatingEl.textContent = '-';
        }
        avgRatingEl.setAttribute('data-animate', 'done');
        
        // Топ авторы с анимированными рангами
        const topAuthors = document.getElementById('topAuthors');
        topAuthors.innerHTML = stats.top_authors.length 
            ? stats.top_authors.map((a, i) => `
                <div class="top-item" style="animation-delay: ${0.1 + i * 0.05}s">
                    <span class="top-item-rank">${i + 1}</span>
                    <span class="top-item-name">${escapeHtml(a.name)}</span>
                    <span class="top-item-count">${a.books_count} книг</span>
                </div>
            `).join('')
            : '<p style="color: var(--text-muted)">Пока нет данных</p>';
        
        // Топ жанры с анимированными рангами
        const topGenres = document.getElementById('topGenres');
        topGenres.innerHTML = stats.top_genres.length
            ? stats.top_genres.map((g, i) => `
                <div class="top-item" style="animation-delay: ${0.1 + i * 0.05}s">
                    <span class="top-item-rank">${i + 1}</span>
                    <span class="top-item-name">${escapeHtml(g.name)}</span>
                    <span class="top-item-count">${g.books_count} книг</span>
                </div>
            `).join('')
            : '<p style="color: var(--text-muted)">Пока нет данных</p>';
        
        // Челлендж чтения с анимированным прогрессом
        if (stats.current_year) {
            const goal = 12;
            const finished = stats.current_year.books_finished;
            const progress = Math.min((finished / goal) * 100, 100);
            
            const progressBar = document.getElementById('challengeProgress');
            progressBar.style.width = '0%';
            setTimeout(() => {
                progressBar.style.width = `${progress}%`;
            }, 300);
            
            document.getElementById('challengeText').textContent = `${finished} / ${goal} книг`;
        }
        
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// === Жанры ===
async function loadGenres() {
    try {
        const genres = await apiRequest('/genres');
        state.genres = genres;
        
        const select = document.getElementById('genreFilter');
        select.innerHTML = '<option value="">Все жанры</option>' +
            genres.map(g => `<option value="${g.name}">${g.name}</option>`).join('');
    } catch (error) {
        console.error('Error loading genres:', error);
    }
}

// === Детали книги ===
async function openBookDetails(bookId) {
    try {
        const book = await apiRequest(`/books/${bookId}`);
        
        const modal = document.getElementById('viewModal');
        const details = document.getElementById('bookDetails');
        
        details.innerHTML = `
            <div class="book-details">
                <div class="book-details-cover">
                    ${book.cover_url 
                        ? `<img src="${book.cover_url}" alt="${escapeAttr(book.title)}">`
                        : '<div class="book-details-cover-placeholder">📖</div>'
                    }
                    <div class="cover-actions">
                        <button class="btn-cover-change" data-book-id="${book.id}" data-title="${escapeAttr(book.title)}" data-author="${escapeAttr(book.authors[0]?.name || '')}">
                            🖼️ Сменить обложку
                        </button>
                    </div>
                </div>
                <div class="book-details-info">
                    <h1>${escapeHtml(book.title)}</h1>
                    ${book.subtitle ? `<p style="color: var(--text-secondary); margin-bottom: 0.5rem;">${escapeHtml(book.subtitle)}</p>` : ''}
                    <p class="book-details-author">${book.authors.map(a => a.name).join(', ') || 'Автор не указан'}</p>
                    
                    <div class="book-details-meta">
                        <span class="meta-badge status-${book.status}">${statusLabels[book.status]}</span>
                        <span class="meta-badge">${formatLabels[book.format]}</span>
                        ${book.language ? `<span class="meta-badge">🌐 ${book.language.toUpperCase()}</span>` : ''}
                        ${book.published_year ? `<span class="meta-badge">📅 ${book.published_year}</span>` : ''}
                        ${book.rating ? `<span class="meta-badge">⭐ ${book.rating}/10</span>` : ''}
                    </div>
                    
                    ${book.genres.length ? `
                        <div class="book-details-meta">
                            ${book.genres.map(g => `<span class="meta-badge">${g.name}</span>`).join('')}
                        </div>
                    ` : ''}
                    
                    ${book.total_pages ? `
                        <div class="book-details-progress">
                            <div class="progress-header">
                                <span>Прогресс чтения</span>
                                <span>${book.current_page || 0} / ${book.total_pages} стр.</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${book.progress}%"></div>
                            </div>
                        </div>
                    ` : ''}
                    
                    ${book.description ? `
                        <div class="book-details-description">
                            <strong>Описание:</strong><br>
                            ${escapeHtml(book.description)}
                        </div>
                    ` : ''}
                    
                    ${book.notes ? `
                        <div class="book-details-description">
                            <strong>Заметки:</strong><br>
                            ${escapeHtml(book.notes)}
                        </div>
                    ` : ''}
                    
                    ${book.location ? `
                        <p style="margin-bottom: 1rem;"><strong>📍 Расположение:</strong> ${escapeHtml(book.location)}</p>
                    ` : ''}
                    
                    <div class="book-details-actions" id="bookActions">
                        ${book.status === 'planned' ? `
                            <button class="btn btn-primary" id="btnStart">📖 Начать читать</button>
                        ` : ''}
                        ${book.status === 'reading' ? `
                            <button class="btn btn-primary" id="btnFinish">✅ Завершить</button>
                            <button class="btn btn-secondary" id="btnProgress">📝 Обновить прогресс</button>
                        ` : ''}
                        <button class="btn btn-ai" id="btnAI">🤖 Похожие книги</button>
                        <button class="btn btn-secondary" id="btnEdit">✏️ Редактировать</button>
                        <button class="btn btn-secondary" id="btnCover">🖼️ Обложка</button>
                        <button class="btn btn-secondary" id="btnRefresh">🔄 Обновить данные</button>
                        <button class="btn btn-danger" id="btnDelete">🗑️ Удалить</button>
                    </div>
                </div>
            </div>
        `;
        
        modal.classList.add('active');
        
        // Добавляем обработчики для кнопок напрямую
        const currentBookId = book.id;
        const currentBookTitle = book.title;
        const currentBookAuthor = book.authors[0]?.name || '';
        const currentPage = book.current_page || 0;
        
        document.getElementById('btnStart')?.addEventListener('click', () => startReading(currentBookId));
        document.getElementById('btnFinish')?.addEventListener('click', () => finishReading(currentBookId));
        document.getElementById('btnProgress')?.addEventListener('click', () => showProgressInput(currentBookId, currentPage));
        document.getElementById('btnEdit')?.addEventListener('click', () => editBook(currentBookId));
        document.getElementById('btnAI')?.addEventListener('click', () => getAIRecommendations(currentBookId));
        document.getElementById('btnCover')?.addEventListener('click', () => openCoverSelector(currentBookId, currentBookTitle, currentBookAuthor));
        document.getElementById('btnRefresh')?.addEventListener('click', () => refreshMetadata(currentBookId));
        document.getElementById('btnDelete')?.addEventListener('click', () => deleteBook(currentBookId));
        
        // Кнопка смены обложки на самой обложке
        document.querySelector('.btn-cover-change')?.addEventListener('click', () => {
            openCoverSelector(currentBookId, currentBookTitle, currentBookAuthor);
        });
    } catch (error) {
        showToast('Ошибка загрузки книги: ' + error.message, 'error');
    }
}

// === Действия с книгами ===
async function startReading(bookId) {
    try {
        await apiRequest(`/books/${bookId}/start-reading`, { method: 'POST' });
        showToast('Книга добавлена в "Читаю"', 'success');
        closeViewModal();
        loadBooks();
    } catch (error) {
        showToast('Ошибка: ' + error.message, 'error');
    }
}

async function finishReading(bookId) {
    const rating = prompt('Оценка книги (1-10):', '');
    const params = rating ? `?rating=${rating}` : '';
    
    try {
        await apiRequest(`/books/${bookId}/finish-reading${params}`, { method: 'POST' });
        showToast('Книга отмечена как прочитанная! 🎉', 'success');
        closeViewModal();
        loadBooks();
    } catch (error) {
        showToast('Ошибка: ' + error.message, 'error');
    }
}

function showProgressInput(bookId, currentPage) {
    const newPage = prompt('Текущая страница:', currentPage);
    if (newPage !== null) {
        updateProgress(bookId, parseInt(newPage));
    }
}

async function updateProgress(bookId, currentPage) {
    try {
        await apiRequest(`/books/${bookId}/update-progress?current_page=${currentPage}`, { method: 'POST' });
        showToast('Прогресс обновлён', 'success');
        openBookDetails(bookId);
        loadBooks();
    } catch (error) {
        showToast('Ошибка: ' + error.message, 'error');
    }
}

async function refreshMetadata(bookId) {
    try {
        showToast('Поиск данных...', 'info');
        await apiRequest(`/books/${bookId}/fetch-metadata`, { method: 'POST' });
        showToast('Данные обновлены', 'success');
        openBookDetails(bookId);
    } catch (error) {
        showToast('Ошибка: ' + error.message, 'error');
    }
}

async function deleteBook(bookId) {
    if (!confirm('Удалить эту книгу?')) return;
    
    try {
        await apiRequest(`/books/${bookId}`, { method: 'DELETE' });
        showToast('Книга удалена', 'success');
        closeViewModal();
        loadBooks();
    } catch (error) {
        showToast('Ошибка: ' + error.message, 'error');
    }
}

// === Модальное окно формы ===
function openBookModal(book = null) {
    const modal = document.getElementById('bookModal');
    const form = document.getElementById('bookForm');
    const title = document.getElementById('modalTitle');
    
    // Очищаем сохранённую обложку от сканера
    delete form.dataset.coverUrl;
    
    if (book) {
        title.textContent = 'Редактировать книгу';
        document.getElementById('bookId').value = book.id;
        document.getElementById('title').value = book.title || '';
        document.getElementById('authors').value = book.authors.map(a => a.name).join(', ');
        document.getElementById('genres').value = book.genres.map(g => g.name).join(', ');
        document.getElementById('isbn').value = book.isbn || '';
        document.getElementById('status').value = book.status || 'planned';
        document.getElementById('format').value = book.format || 'paper';
        document.getElementById('language').value = book.language || 'ru';
        document.getElementById('totalPages').value = book.total_pages || '';
        document.getElementById('currentPage').value = book.current_page || '';
        document.getElementById('rating').value = book.rating || '';
        document.getElementById('location').value = book.location || '';
        document.getElementById('notes').value = book.notes || '';
        document.getElementById('autoFetchCover').checked = false;
    } else {
        title.textContent = 'Добавить книгу';
        form.reset();
        document.getElementById('bookId').value = '';
        document.getElementById('autoFetchCover').checked = true;
    }
    
    modal.classList.add('active');
}

function closeBookModal() {
    document.getElementById('bookModal').classList.remove('active');
}

function closeViewModal() {
    document.getElementById('viewModal').classList.remove('active');
}

async function editBook(bookId) {
    try {
        const book = await apiRequest(`/books/${bookId}`);
        closeViewModal();
        openBookModal(book);
    } catch (error) {
        showToast('Ошибка: ' + error.message, 'error');
    }
}

async function saveBook(e) {
    e.preventDefault();
    
    const bookId = document.getElementById('bookId').value;
    const isEdit = !!bookId;
    const form = document.getElementById('bookForm');
    
    const data = {
        title: document.getElementById('title').value.trim(),
        authors: document.getElementById('authors').value.split(',').map(s => s.trim()).filter(Boolean),
        genres: document.getElementById('genres').value.split(',').map(s => s.trim()).filter(Boolean),
        isbn: document.getElementById('isbn').value.trim() || null,
        status: document.getElementById('status').value,
        format: document.getElementById('format').value,
        language: document.getElementById('language').value,
        total_pages: parseInt(document.getElementById('totalPages').value) || null,
        current_page: parseInt(document.getElementById('currentPage').value) || 0,
        rating: parseInt(document.getElementById('rating').value) || null,
        location: document.getElementById('location').value.trim() || null,
        notes: document.getElementById('notes').value.trim() || null,
    };
    
    // Если есть сохранённая обложка от ISBN сканера
    if (form.dataset.coverUrl) {
        data.cover_url = form.dataset.coverUrl;
        data.auto_fetch_cover = false;
    } else if (!isEdit) {
        data.auto_fetch_cover = document.getElementById('autoFetchCover').checked;
    }
    
    try {
        if (isEdit) {
            await apiRequest(`/books/${bookId}`, {
                method: 'PATCH',
                body: JSON.stringify(data),
            });
            showToast('Книга обновлена', 'success');
        } else {
            await apiRequest('/books', {
                method: 'POST',
                body: JSON.stringify(data),
            });
            showToast('Книга добавлена! 📚', 'success');
        }
        
        // Очищаем сохранённую обложку
        delete form.dataset.coverUrl;
        
        closeBookModal();
        loadBooks();
        loadGenres();
    } catch (error) {
        showToast('Ошибка: ' + error.message, 'error');
    }
}

// === Импорт файлов ===
async function handleFileUpload(file, isBookTracker = false) {
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    let endpoint;
    if (isBookTracker) {
        endpoint = '/import-export/import/booktracker';
    } else if (file.name.endsWith('.json')) {
        endpoint = '/import-export/import/json';
    } else {
        endpoint = '/import-export/import/csv';
    }
    
    try {
        showToast('Импорт файла...', 'info');
        
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            body: formData,
        });
        
        const result = await response.json();
        
        // Показываем результат в интерфейсе
        showImportResult(result, response.ok);
        
        if (response.ok) {
            showToast(`Импортировано: ${result.success} книг`, 'success');
            if (result.skipped > 0) {
                showToast(`Пропущено: ${result.skipped} (дубликаты)`, 'info');
            }
            if (result.failed > 0) {
                showToast(`Ошибок: ${result.failed}`, 'error');
            }
            loadBooks();
            loadGenres();
        } else {
            showToast('Ошибка импорта: ' + result.detail, 'error');
        }
    } catch (error) {
        showToast('Ошибка импорта: ' + error.message, 'error');
    }
}

function showImportResult(result, isSuccess) {
    const resultDiv = document.getElementById('importResult');
    resultDiv.style.display = 'block';
    
    document.getElementById('importSuccess').textContent = result.success || 0;
    document.getElementById('importSkipped').textContent = result.skipped || 0;
    document.getElementById('importFailed').textContent = result.failed || 0;
    
    const errorsDiv = document.getElementById('importErrors');
    if (result.errors && result.errors.length > 0) {
        errorsDiv.innerHTML = '<h4>Ошибки:</h4>' + 
            result.errors.slice(0, 10).map(e => `<p>• ${escapeHtml(e)}</p>`).join('');
        if (result.errors.length > 10) {
            errorsDiv.innerHTML += `<p>...и ещё ${result.errors.length - 10} ошибок</p>`;
        }
    } else {
        errorsDiv.innerHTML = '';
    }
}

// === Навигация ===
function switchPage(pageName) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    
    document.getElementById(`${pageName}-page`).classList.add('active');
    document.querySelector(`[data-page="${pageName}"]`).classList.add('active');
    
    if (pageName === 'stats') {
        loadStats();
    }
}

// === Вспомогательные функции ===
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function escapeAttr(text) {
    if (!text) return '';
    return text.replace(/'/g, "&#39;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// === Переключение вида ===
function initViewToggle() {
    const grid = document.getElementById('booksGrid');
    const buttons = document.querySelectorAll('.view-btn');
    
    console.log('🔧 initViewToggle:', { grid, buttonsCount: buttons.length, viewMode: state.viewMode });
    
    if (!grid || buttons.length === 0) {
        console.error('❌ Grid или кнопки не найдены!');
        return;
    }
    
    // Применить сохранённый вид
    setViewMode(state.viewMode);
    
    // Прямые обработчики на каждую кнопку (более совместимо)
    buttons.forEach(btn => {
        // Убираем старые обработчики
        btn.onclick = null;
        
        // Touch для мобильных
        btn.addEventListener('touchend', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const view = this.getAttribute('data-view');
            console.log('📱 Touch по кнопке:', view);
            setViewMode(view);
        }, { passive: false });
        
        // Click для десктопа
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const view = this.getAttribute('data-view');
            console.log('🖱️ Click по кнопке:', view);
            setViewMode(view);
        });
    });
    
    console.log('✅ View toggle инициализирован');
}

function setViewMode(mode) {
    const grid = document.getElementById('booksGrid');
    const buttons = document.querySelectorAll('.view-btn');
    
    console.log('🎨 setViewMode:', mode);
    
    if (!grid) {
        console.error('❌ booksGrid не найден!');
        return;
    }
    
    // Убираем все классы вида
    grid.classList.remove('view-small', 'view-medium', 'view-list');
    
    // Добавляем нужный (medium - дефолтный, без класса)
    if (mode === 'small') {
        grid.classList.add('view-small');
    } else if (mode === 'list') {
        grid.classList.add('view-list');
    }
    
    console.log('📝 Grid classes:', grid.className);
    
    // Обновляем активную кнопку
    buttons.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === mode);
    });
    
    // Сохраняем
    state.viewMode = mode;
    localStorage.setItem('booknest-view', mode);
}

// === Инициализация ===
document.addEventListener('DOMContentLoaded', () => {
    console.log('📚 DOMContentLoaded!');
    
    // Загрузка данных
    loadBooks();
    loadGenres();
    loadStats();
    
    // Переключатель темы
    const themeToggle = document.getElementById('themeToggle');
    console.log('themeToggle:', themeToggle);
    if (themeToggle) themeToggle.addEventListener('click', toggleTheme);
    
    // Навигация
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            switchPage(link.dataset.page);
        });
    });
    
    // Кнопка добавления
    const addBtn = document.getElementById('addBookBtn');
    console.log('addBookBtn:', addBtn);
    if (addBtn) {
        addBtn.addEventListener('click', () => {
            console.log('Кнопка Добавить нажата!');
            openBookModal();
        });
    }
    
    // Модальные окна
    const closeModal = document.getElementById('closeModal');
    const cancelBtn = document.getElementById('cancelBtn');
    const closeViewBtn = document.getElementById('closeViewModal');
    
    if (closeModal) closeModal.addEventListener('click', closeBookModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeBookModal);
    if (closeViewBtn) closeViewBtn.addEventListener('click', closeViewModal);
    
    // Закрытие по клику вне
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });
    
    // Форма
    const bookForm = document.getElementById('bookForm');
    if (bookForm) bookForm.addEventListener('submit', saveBook);
    
    // Поиск
    document.getElementById('searchInput')?.addEventListener('input', debounce((e) => {
        state.filters.search = e.target.value;
        state.currentPage = 1;
        loadBooks();
    }, 300));
    
    // Фильтры
    document.getElementById('statusFilter').addEventListener('change', (e) => {
        state.filters.status = e.target.value;
        state.currentPage = 1;
        loadBooks();
    });
    
    document.getElementById('genreFilter').addEventListener('change', (e) => {
        state.filters.genre = e.target.value;
        state.currentPage = 1;
        loadBooks();
    });
    
    document.getElementById('formatFilter').addEventListener('change', (e) => {
        state.filters.format = e.target.value;
        state.currentPage = 1;
        loadBooks();
    });
    
    document.getElementById('sortBy').addEventListener('change', (e) => {
        state.filters.sortBy = e.target.value;
        // Для названия и автора - по возрастанию (А-Я), для даты и рейтинга - по убыванию
        if (e.target.value === 'title' || e.target.value === 'author') {
            state.filters.sortOrder = 'asc';
        } else {
            state.filters.sortOrder = 'desc';
        }
        state.currentPage = 1;
        loadBooks();
    });
    
    // Переключатель вида
    initViewToggle();
    
    // Карточки статусов
    document.querySelectorAll('.status-card').forEach(card => {
        card.addEventListener('click', () => {
            const status = card.dataset.status;
            document.getElementById('statusFilter').value = status;
            state.filters.status = status;
            state.currentPage = 1;
            loadBooks();
        });
    });
    
    // Drag & Drop импорт (стандартный)
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    
    dropzone.addEventListener('click', () => fileInput.click());
    
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });
    
    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });
    
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        handleFileUpload(file, false);
    });
    
    fileInput.addEventListener('change', (e) => {
        handleFileUpload(e.target.files[0], false);
    });
    
    // Drag & Drop импорт из Book Tracker
    const dropzoneBT = document.getElementById('dropzoneBookTracker');
    const fileInputBT = document.getElementById('fileInputBookTracker');
    
    dropzoneBT.addEventListener('click', () => fileInputBT.click());
    
    dropzoneBT.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzoneBT.classList.add('dragover');
    });
    
    dropzoneBT.addEventListener('dragleave', () => {
        dropzoneBT.classList.remove('dragover');
    });
    
    dropzoneBT.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzoneBT.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        handleFileUpload(file, true);
    });
    
    fileInputBT.addEventListener('change', (e) => {
        handleFileUpload(e.target.files[0], true);
    });
    
    // Горячие клавиши
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeBookModal();
            closeViewModal();
        }
        if (e.key === 'n' && e.ctrlKey) {
            e.preventDefault();
            openBookModal();
        }
    });
});

// Регистрация Service Worker для PWA
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then(reg => console.log('SW registered'))
            .catch(err => console.log('SW registration failed:', err));
    });
}

// === Cover Selection ===
let currentCoverBookId = null;
let selectedCoverUrl = null;

function openCoverSelector(bookId, title, author) {
    currentCoverBookId = bookId;
    selectedCoverUrl = null;
    
    const modal = document.getElementById('coverModal');
    const titleInput = document.getElementById('coverSearchTitle');
    const authorInput = document.getElementById('coverSearchAuthor');
    const grid = document.getElementById('coversGrid');
    const customUrlInput = document.getElementById('customCoverUrl');
    
    // Заполняем поля поиска
    titleInput.value = title || '';
    authorInput.value = author || '';
    customUrlInput.value = '';
    grid.innerHTML = '';
    
    modal.classList.add('active');
    
    // Автоматический поиск
    if (title) {
        searchCovers();
    }
}

function closeCoverModal() {
    const modal = document.getElementById('coverModal');
    modal.classList.remove('active');
    currentCoverBookId = null;
    selectedCoverUrl = null;
}

async function searchCovers() {
    const title = document.getElementById('coverSearchTitle').value.trim();
    const author = document.getElementById('coverSearchAuthor').value.trim();
    const grid = document.getElementById('coversGrid');
    const loading = document.getElementById('coverLoading');
    
    if (!title) {
        showToast('Введите название книги', 'error');
        return;
    }
    
    grid.innerHTML = '';
    loading.style.display = 'flex';
    
    try {
        // Правильно кодируем параметры с кириллицей
        const params = new URLSearchParams();
        params.set('title', title);
        if (author) params.set('author', author);
        
        const url = `/api/books/search/covers?${params.toString()}`;
        console.log('Запрос обложек:', url);
        
        const response = await fetch(url);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        const covers = await response.json();
        
        loading.style.display = 'none';
        
        if (!covers || covers.length === 0) {
            grid.innerHTML = `
                <div class="empty-state" style="grid-column: 1/-1;">
                    <div class="empty-state-icon">🔍</div>
                    <h3>Обложки не найдены</h3>
                    <p>Попробуйте изменить запрос или вставьте URL напрямую</p>
                </div>
            `;
            return;
        }
        
        grid.innerHTML = covers.map((url, index) => `
            <div class="cover-option" data-url="${escapeAttr(url)}">
                <img src="${url}" alt="Вариант ${index + 1}" 
                     onerror="this.parentElement.style.display='none'">
                <div class="cover-option-overlay">
                    <span>✓</span>
                </div>
            </div>
        `).join('');
        
        // Добавляем обработчики клика
        grid.querySelectorAll('.cover-option').forEach(el => {
            el.addEventListener('click', () => {
                selectCover(el.dataset.url);
            });
        });
        
    } catch (error) {
        console.error('Ошибка поиска обложек:', error);
        loading.style.display = 'none';
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <div class="empty-state-icon">😕</div>
                <h3>Ошибка поиска</h3>
                <p>${escapeHtml(error.message || 'Неизвестная ошибка')}</p>
            </div>
        `;
    }
}

function selectCover(url) {
    selectedCoverUrl = url;
    
    // Обновляем визуальное выделение
    document.querySelectorAll('.cover-option').forEach(el => {
        el.classList.remove('selected');
        if (el.dataset.url === url) {
            el.classList.add('selected');
        }
    });
    
    // Заполняем поле URL
    document.getElementById('customCoverUrl').value = url;
}

async function applyCover() {
    const customUrl = document.getElementById('customCoverUrl').value.trim();
    const coverUrl = customUrl || selectedCoverUrl;
    
    if (!coverUrl) {
        showToast('Выберите обложку или введите URL', 'error');
        return;
    }
    
    if (!currentCoverBookId) {
        showToast('Ошибка: книга не выбрана', 'error');
        return;
    }
    
    try {
        await apiRequest(`/books/${currentCoverBookId}/cover`, {
            method: 'PATCH',
            body: JSON.stringify({ cover_url: coverUrl })
        });
        
        showToast('Обложка обновлена!', 'success');
        closeCoverModal();
        
        // Обновляем текущий просмотр
        if (document.getElementById('viewModal').classList.contains('active')) {
            openBookDetails(currentCoverBookId);
        }
        
        // Обновляем список
        loadBooks();
        
    } catch (error) {
        showToast('Ошибка сохранения: ' + error.message, 'error');
    }
}

// Инициализация модалки обложек
document.addEventListener('DOMContentLoaded', () => {
    const searchBtn = document.getElementById('searchCoversBtn');
    const applyBtn = document.getElementById('applyCoverBtn');
    const closeBtn = document.getElementById('closeCoverModal');
    const modal = document.getElementById('coverModal');
    
    if (searchBtn) searchBtn.addEventListener('click', searchCovers);
    if (applyBtn) applyBtn.addEventListener('click', applyCover);
    if (closeBtn) closeBtn.addEventListener('click', closeCoverModal);
    
    // Закрытие по клику на фон
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeCoverModal();
        });
    }
    
    // Поиск по Enter
    document.getElementById('coverSearchTitle')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchCovers();
    });
    document.getElementById('coverSearchAuthor')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchCovers();
    });
});

// ========================================
// ISBN Scanner
// ========================================

let isScanning = false;

function openScanModal() {
    const modal = document.getElementById('scanModal');
    modal.classList.add('active');
    document.getElementById('scanStatus').textContent = 'Наведите камеру на штрих-код книги';
    document.getElementById('scanStatus').className = 'scan-status';
    document.getElementById('manualIsbn').value = '';
    
    startScanner();
}

function closeScanModal() {
    const modal = document.getElementById('scanModal');
    modal.classList.remove('active');
    stopScanner();
}

async function startScanner() {
    const video = document.getElementById('scanVideo');
    const statusEl = document.getElementById('scanStatus');
    
    // Проверяем поддержку Quagga
    if (typeof Quagga === 'undefined') {
        statusEl.textContent = 'Библиотека сканера не загружена. Введите ISBN вручную.';
        statusEl.className = 'scan-status error';
        return;
    }
    
    try {
        // Запрашиваем доступ к камере
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment' }
        });
        
        video.srcObject = stream;
        await video.play();
        
        isScanning = true;
        
        // Инициализируем Quagga
        Quagga.init({
            inputStream: {
                name: "Live",
                type: "LiveStream",
                target: video,
                constraints: {
                    facingMode: "environment"
                }
            },
            decoder: {
                readers: ["ean_reader", "ean_8_reader", "upc_reader", "upc_e_reader"]
            },
            locate: true
        }, function(err) {
            if (err) {
                console.error('Quagga init error:', err);
                statusEl.textContent = 'Ошибка инициализации сканера. Введите ISBN вручную.';
                statusEl.className = 'scan-status error';
                return;
            }
            Quagga.start();
        });
        
        // Обработка результата
        Quagga.onDetected(async (result) => {
            if (!isScanning) return;
            
            const code = result.codeResult.code;
            console.log('📖 Обнаружен код:', code);
            
            // Проверяем что это ISBN (начинается с 978 или 979)
            if (code.startsWith('978') || code.startsWith('979') || code.length === 10) {
                isScanning = false;
                statusEl.textContent = `Найден ISBN: ${code}. Поиск книги...`;
                statusEl.className = 'scan-status success';
                
                // Вибрация для обратной связи
                if (navigator.vibrate) {
                    navigator.vibrate(200);
                }
                
                await searchBookByIsbn(code);
            }
        });
        
    } catch (err) {
        console.error('Camera error:', err);
        statusEl.textContent = 'Нет доступа к камере. Введите ISBN вручную.';
        statusEl.className = 'scan-status error';
    }
}

function stopScanner() {
    isScanning = false;
    
    const video = document.getElementById('scanVideo');
    if (video.srcObject) {
        video.srcObject.getTracks().forEach(track => track.stop());
        video.srcObject = null;
    }
    
    if (typeof Quagga !== 'undefined') {
        try {
            Quagga.stop();
        } catch (e) {}
    }
}

async function searchBookByIsbn(isbn) {
    const statusEl = document.getElementById('scanStatus');
    
    try {
        const response = await fetch(`/api/books/isbn/${isbn}`);
        
        if (!response.ok) {
            throw new Error('Книга не найдена');
        }
        
        const bookData = await response.json();
        console.log('📚 Найдена книга:', bookData);
        
        // Закрываем сканер
        closeScanModal();
        
        // Открываем форму добавления с заполненными данными
        openBookModal();
        
        // Заполняем форму
        setTimeout(() => {
            document.getElementById('title').value = bookData.title || '';
            document.getElementById('authors').value = (bookData.authors || []).join(', ');
            document.getElementById('isbn').value = bookData.isbn || isbn;
            document.getElementById('totalPages').value = bookData.total_pages || '';
            
            // Год публикации - добавляем в заметки если есть
            if (bookData.published_year) {
                const notesEl = document.getElementById('notes');
                notesEl.value = `Год издания: ${bookData.published_year}\n${bookData.description || ''}`;
            } else if (bookData.description) {
                document.getElementById('notes').value = bookData.description;
            }
            
            if (bookData.cover_url) {
                // Сохраняем URL обложки для использования при сохранении
                document.getElementById('bookForm').dataset.coverUrl = bookData.cover_url;
                // Показываем превью обложки
                const coverPreview = document.getElementById('coverPreview');
                if (coverPreview) {
                    coverPreview.src = bookData.cover_url;
                    coverPreview.style.display = 'block';
                }
            }
            
            if (bookData.genres && bookData.genres.length > 0) {
                document.getElementById('genres').value = bookData.genres.join(', ');
            }
        }, 100);
        
        showToast(`Книга "${bookData.title}" найдена!`, 'success');
        
    } catch (err) {
        console.error('ISBN search error:', err);
        statusEl.textContent = `Книга с ISBN ${isbn} не найдена. Попробуйте другой код.`;
        statusEl.className = 'scan-status error';
        isScanning = true; // Продолжаем сканирование
    }
}

// Инициализация сканера
document.addEventListener('DOMContentLoaded', () => {
    const scanBtn = document.getElementById('scanIsbnBtn');
    const closeBtn = document.getElementById('closeScanModal');
    const searchBtn = document.getElementById('searchIsbnBtn');
    const modal = document.getElementById('scanModal');
    const manualInput = document.getElementById('manualIsbn');
    
    if (scanBtn) scanBtn.addEventListener('click', openScanModal);
    if (closeBtn) closeBtn.addEventListener('click', closeScanModal);
    
    if (searchBtn) {
        searchBtn.addEventListener('click', () => {
            const isbn = manualInput.value.trim();
            if (isbn) {
                searchBookByIsbn(isbn);
            }
        });
    }
    
    if (manualInput) {
        manualInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const isbn = manualInput.value.trim();
                if (isbn) {
                    searchBookByIsbn(isbn);
                }
            }
        });
    }
    
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeScanModal();
        });
    }
});

// === AI Рекомендации ===
async function getAIRecommendations(bookId) {
    const modal = document.getElementById('aiModal');
    const loading = document.getElementById('aiLoading');
    const result = document.getElementById('aiResult');
    const error = document.getElementById('aiError');
    const summary = document.getElementById('aiSummary');
    const recommendations = document.getElementById('aiRecommendations');
    
    // Показываем модальное окно с загрузкой
    modal.classList.add('active');
    loading.style.display = 'flex';
    result.style.display = 'none';
    error.style.display = 'none';
    
    try {
        const data = await apiRequest(`/ai/recommendations/${bookId}`);
        
        loading.style.display = 'none';
        
        if (data.error) {
            error.textContent = `Ошибка: ${data.error}`;
            error.style.display = 'block';
            return;
        }
        
        // Показываем результаты
        result.style.display = 'block';
        
        // Summary
        if (data.summary) {
            summary.innerHTML = `💡 ${escapeHtml(data.summary)}`;
            summary.style.display = 'block';
        } else {
            summary.style.display = 'none';
        }
        
        // Рекомендации
        if (data.recommendations && data.recommendations.length > 0) {
            recommendations.innerHTML = data.recommendations.map(rec => `
                <div class="ai-recommendation-card">
                    <div class="ai-recommendation-title">📖 ${escapeHtml(rec.title)}</div>
                    <div class="ai-recommendation-author">✍️ ${escapeHtml(rec.author)}</div>
                    <div class="ai-recommendation-reason">${escapeHtml(rec.reason)}</div>
                    ${rec.genres && rec.genres.length > 0 ? `
                        <div class="ai-recommendation-genres">
                            ${rec.genres.map(g => `<span class="ai-recommendation-genre">${escapeHtml(g)}</span>`).join('')}
                        </div>
                    ` : ''}
                </div>
            `).join('');
        } else {
            recommendations.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">Рекомендации не найдены</p>';
        }
        
    } catch (err) {
        loading.style.display = 'none';
        error.textContent = `Ошибка: ${err.message}`;
        error.style.display = 'block';
    }
}

function closeAiModal() {
    document.getElementById('aiModal').classList.remove('active');
}

// Инициализация AI модального окна
document.addEventListener('DOMContentLoaded', () => {
    const closeBtn = document.getElementById('closeAiModal');
    const modal = document.getElementById('aiModal');
    
    if (closeBtn) closeBtn.addEventListener('click', closeAiModal);
    if (modal) modal.addEventListener('click', (e) => {
        if (e.target === modal) closeAiModal();
    });
});