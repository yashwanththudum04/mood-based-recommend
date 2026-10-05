# 📚 Mood-Based Book Recommender

A beginner-friendly Python project that recommends books tailored to your emotional state. It matches your feelings to book themes and keywords, and now offers both a **visual Streamlit web application** and the original **command-line interface**.

---

## 🌟 Features

- **Visual Web Application (`app.py`)**:
  - Interactive web interface with a clean, responsive layout for desktop and mobile.
  - Natural text box where you can type how you feel (e.g., *"I feel stressed and overwhelmed"*).
  - Quick-inspiration buttons for one-click mood selection.
  - Book cover images fetched dynamically via the public Google Books API.
  - Elegant fallback placeholders with *"Cover unavailable"* and the book title if offline or if no cover is found.
  - Displays book title, author, genre, and a thoughtful *"Why it may fit"* explanation.
  - Emotion badges and matched keyword indicators.
  - In-memory caching for speedy searches without repeated API requests.
- **Command-Line Recommender (`mood_book_recommender.py`)**:
  - The original CLI tool remains fully functional and intact.
  - Run with arguments or via an interactive prompt.
- **10 Recognized Emotions & Synonyms**:
  - Happy, Sad, Anxious, Stressed, Angry, Lonely, Bored, Hopeful, Curious, Afraid.
- **Privacy & Safety**:
  - No API key required.
  - Zero personal data or feelings uploaded anywhere; only book titles and authors are sent to Google Books to find covers.

---

## 📁 Project Structure

```text
MOODBASED/
├── app.py                     # Streamlit visual web application
├── mood_book_recommender.py   # Original command-line recommender
├── emotion_book_dataset.csv   # Dataset of books, moods, genres, and keywords
├── requirements.txt           # Python dependencies
└── README.md                  # Project documentation and setup guide
```

### Dataset Columns
`emotion_book_dataset.csv` contains the following required columns:
- `emotion`: The target mood (e.g., `happy`, `stressed`, `curious`).
- `title`: Title of the book.
- `author`: Author of the book.
- `genre`: Literary genre.
- `why_it_may_fit`: Contextual explanation of why this book matches the mood.
- `keywords`: Space-separated keywords used for relevance scoring.

---

## 🚀 Getting Started

### 1. Prerequisites
Make sure you have **Python 3.10+** installed on your system. You can verify your Python installation by running:

```bash
python --version
```

### 2. Install Dependencies
Open your terminal or PowerShell in the project directory (`d:\MOODBASED`) and install the required packages:

```bash
python -m pip install -r requirements.txt
```

*The dependencies installed are:*
- `streamlit` (interactive web app framework)
- `requests` (for fetching book covers from Google Books API)
- `pillow` (for generating elegant cover placeholders)

---

## 🖥️ Running the Applications

### Option A: Launch the Visual Web App (Recommended)

Run the following command in your terminal:

```bash
python -m streamlit run app.py
```

Streamlit will automatically open the app in your default web browser (typically at `http://localhost:8501`).

#### In the Web App:
1. Type how you are feeling in the text box (e.g., `"I feel stressed and overwhelmed"`, `"curious"`, or `"lonely"`).
2. Or click one of the **Quick inspiration** buttons.
3. Select how many recommendations you'd like (1 to 5).
4. Click **🔍 Get Recommendations**.
5. Browse the recommended books with their covers, author, genre, and reasoning!

---

### Option B: Run the Command-Line Tool

The original command-line recommender is preserved and can be run in two ways:

#### 1. Pass your mood directly:
```bash
python mood_book_recommender.py "I feel stressed and overwhelmed"
```

#### 2. Request a specific number of books (e.g., 3 books):
```bash
python mood_book_recommender.py "I feel lonely" -n 3
```

#### 3. Interactive prompt mode:
```bash
python mood_book_recommender.py
```

---

## 📖 Book Cover Lookup Details

- **Public Google Books API**: The app queries `https://www.googleapis.com/books/v1/volumes` with `intitle` and `inauthor`.
- **No API Key Required**: Works out of the box with public access.
- **Graceful Fallbacks**: If the API is rate-limited, unreachable, times out, or the book doesn't have an available thumbnail, the app automatically displays a neat generated placeholder with the book's title and the text **"Cover unavailable"**. The recommender continues working seamlessly without interruptions.
- **Caching**: Lookups are cached locally in memory for 24 hours to prevent redundant network calls.

---

## ⚠️ Disclaimer

This reading suggestion tool is designed for casual leisure reading. It is not intended to treat, diagnose, or cure any emotional or mental health condition.
