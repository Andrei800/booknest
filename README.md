# 📚 BookNest — Personal Book Diary with AI

A personal book tracking application with automatic cover search, metadata fetching, and AI-powered recommendations.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

### 📖 Book Catalog
- Title, authors, genres, language
- Format: paperback / ebook / audiobook
- Status: want to read / reading / finished / on hold / dropped
- Reading progress (pages and percentage)
- Rating (1-10), notes, quotes
- Physical location tracking

### 🔍 Search & Filters
- Search by title and author
- Filters: status, genre, format, language, rating
- Sorting: by date, title, rating

### 📊 Statistics
- Books per year/month
- Top authors and genres
- Average rating
- Reading challenge tracker

### 🤖 AI / Automation
- Automatic cover search (Google Books, Open Library)
- Auto-fill description and publication year
- **AI book recommendations** (powered by Google Gemini)
- ISBN barcode scanning

### 📥 Import / Export
- Import from CSV and JSON
- Import from Book Tracker app
- Export to CSV and JSON
- CSV template download

## 🚀 Quick Start

### Requirements
- Python 3.11+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/booknest.git
cd booknest

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration (optional)

Create a `.env` file in the root directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### Run

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Open in browser: **http://localhost:8000**

## 📱 PWA Support

BookNest works as a Progressive Web App:
1. Open http://localhost:8000 on your phone
2. Tap "Add to Home Screen"
3. Done! Use it like a native app

## 🌐 Deploy to Render (Free)

1. Fork this repository
2. Go to [render.com](https://render.com)
3. Create new **Web Service**
4. Connect your GitHub repo
5. Settings will auto-fill from `render.yaml`
6. Choose **Free** plan
7. Click **Create Web Service**

Your app will be live at `https://your-app.onrender.com`

## 📁 Project Structure

```
booknest/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entry point
│   │   ├── config.py        # Configuration
│   │   ├── db.py            # Database setup
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── schemas.py       # Pydantic schemas
│   │   ├── routers/         # API endpoints
│   │   │   ├── books.py
│   │   │   ├── authors.py
│   │   │   ├── genres.py
│   │   │   ├── stats.py
│   │   │   ├── ai.py
│   │   │   └── import_export.py
│   │   └── services/        # Business logic
│   │       ├── covers.py    # Cover search
│   │       └── ai_recommendations.py
│   └── requirements.txt
├── frontend/
│   ├── index.html           # Main page
│   ├── styles.css           # Styles
│   ├── app.js               # JavaScript
│   ├── manifest.json        # PWA manifest
│   └── sw.js                # Service Worker
├── requirements.txt
├── render.yaml              # Render deploy config
└── Dockerfile
```

## 🔧 API

API documentation available at: **http://localhost:8000/docs**

### Main Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/books | List books with filters |
| POST | /api/books | Create book |
| GET | /api/books/{id} | Get book |
| PATCH | /api/books/{id} | Update book |
| DELETE | /api/books/{id} | Delete book |
| POST | /api/books/{id}/start-reading | Start reading |
| POST | /api/books/{id}/finish-reading | Finish reading |
| POST | /api/books/{id}/update-progress | Update progress |
| GET | /api/books/isbn/{isbn} | Search book by ISBN |
| GET | /api/ai/recommendations/{id} | Get AI recommendations |
| GET | /api/stats/full | Full statistics |
| POST | /api/import-export/import/csv | Import from CSV |
| GET | /api/import-export/export/json | Export to JSON |

## 🧪 Tests

```bash
pytest backend/tests/ -v
```

## 📝 CSV Import Format

Prepare a CSV file with columns:
- `title` — book title (required)
- `authors` — comma-separated authors
- `genres` — comma-separated genres
- `status` — planned/reading/finished/on_hold/dropped
- `format` — paper/ebook/audiobook
- `language` — ru/en/uk/...
- `total_pages` — total pages
- `current_page` — current page
- `rating` — rating 1-10
- `notes` — notes
- `location` — physical location

Download template in app: Import → "Download CSV Template"

## 🖼️ Screenshots

![BookNest Screenshot](https://via.placeholder.com/800x400?text=BookNest+Screenshot)

## 🔮 Roadmap

- [x] Book catalog with filters
- [x] Automatic cover search
- [x] AI recommendations (Gemini)
- [x] ISBN scanning
- [x] PWA support
- [ ] Cloud sync between devices
- [ ] Social features (share lists)
- [ ] Goodreads integration
- [ ] Mobile app (React Native)

## 📄 License

MIT License — free to use!

---

Made with ❤️ for book lovers
