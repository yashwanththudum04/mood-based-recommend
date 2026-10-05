"""
Mood-Based Book Recommender - Web Application
=============================================
A visual, beginner-friendly Streamlit web app that recommends books
tailored to how you feel, complete with cover images and book details.

Features:
- Natural text input for describing your current mood or feelings.
- Recognizes 10 primary emotions and their synonyms.
- Ranks matching books by keyword relevance (up to 5 books).
- Looks up book covers using the public Google Books API.
- Generates neat placeholders if a cover is unavailable or network is down.
- Privacy-focused: No feelings or CSV data are uploaded anywhere.
- Casual leisure reading focus with an appropriate disclaimer.
"""

import concurrent.futures
from io import BytesIO
import os
from pathlib import Path
import re
import textwrap
from PIL import Image, ImageDraw, ImageFont
import requests
import streamlit as st

# -----------------------------------------------------------------------------
# Reusing CLI recommender logic if available, with robust standalone fallbacks
# -----------------------------------------------------------------------------
try:
    import mood_book_recommender as mbr
    SUPPORTED_EMOTIONS = mbr.SUPPORTED_EMOTIONS
    REQUIRED_COLUMNS = mbr.REQUIRED_COLUMNS
    DISCLAIMER = mbr.DISCLAIMER
    extract_words = mbr.extract_words
    detect_emotions = mbr.detect_emotions
    score_and_rank_books = mbr.score_and_rank_books
except Exception:
    REQUIRED_COLUMNS = ["emotion", "title", "author", "genre", "why_it_may_fit", "keywords"]
    SUPPORTED_EMOTIONS = {
        "happy": ["happy", "joy", "joyful", "cheerful", "delighted", "glad", "great", "content", "happiness", "upbeat", "amused", "playful"],
        "sad": ["sad", "down", "blue", "unhappy", "low", "sadness", "sorrow", "grief", "grieving", "heartbroken", "gloomy"],
        "anxious": ["anxious", "worried", "nervous", "uneasy", "anxiety", "apprehensive", "jittery", "tense", "restless"],
        "stressed": ["stressed", "overwhelmed", "busy", "pressure", "burnout", "stress", "exhausted", "tired", "frazzled", "overworked"],
        "angry": ["angry", "mad", "frustrated", "irritated", "annoyed", "anger", "furious", "upset", "enraged", "cross"],
        "lonely": ["lonely", "isolated", "alone", "disconnected", "loneliness", "solitary", "abandoned", "lonesome"],
        "bored": ["bored", "restless", "uninterested", "boredom", "dull", "uninspired", "monotonous"],
        "hopeful": ["hopeful", "optimistic", "encouraged", "inspired", "hope", "positive", "uplifted", "promising"],
        "curious": ["curious", "interested", "intrigued", "curiosity", "inquisitive", "wonder", "inquiring", "fascinated"],
        "afraid": ["afraid", "scared", "frightened", "fearful", "fear", "spooky", "terrified", "petrified", "spooked"],
    }
    DISCLAIMER = (
        "Disclaimer: This reading suggestion tool is for casual leisure reading.\n"
        "It is not intended to treat, diagnose, or cure any emotional or mental health condition."
    )

    def extract_words(text: str) -> set[str]:
        if not text:
            return set()
        return set(re.findall(r"\b\w+\b", text.lower()))

    def detect_emotions(user_words: set[str]) -> set[str]:
        matched = set()
        for emotion, synonyms in SUPPORTED_EMOTIONS.items():
            if user_words.intersection(set(synonyms)):
                matched.add(emotion)
        return matched

    def score_and_rank_books(books: list[dict], user_words: set[str], matched_emotions: set[str]) -> list[dict]:
        if matched_emotions:
            candidate_books = [b for b in books if b.get("emotion", "").lower() in matched_emotions]
        else:
            candidate_books = books

        scored_items = []
        for book in candidate_books:
            raw_keywords = book.get("keywords", "")
            book_keywords = extract_words(raw_keywords)
            matching_keywords = user_words.intersection(book_keywords)
            score = len(matching_keywords)
            if matched_emotions or score > 0:
                scored_items.append({
                    "book": book,
                    "score": score,
                    "matched_keywords": sorted(matching_keywords),
                })
        scored_items.sort(key=lambda item: item["score"], reverse=True)
        return scored_items

# Base folder relative to this app.py file
BASE_DIR = Path(__file__).resolve().parent
CSV_FILENAME = "emotion_book_dataset.csv"
CSV_PATH = BASE_DIR / CSV_FILENAME

# Color mapping and icons for emotion badges
EMOTION_COLORS = {
    "happy": "#F59E0B",
    "sad": "#3B82F6",
    "anxious": "#8B5CF6",
    "stressed": "#EC4899",
    "angry": "#EF4444",
    "lonely": "#6366F1",
    "bored": "#14B8A6",
    "hopeful": "#10B981",
    "curious": "#F97316",
    "afraid": "#64748B",
}

EMOTION_EMOJIS = {
    "happy": "😊",
    "sad": "🌧️",
    "anxious": "💭",
    "stressed": "🧘",
    "angry": "🔥",
    "lonely": "🌙",
    "bored": "⚡",
    "hopeful": "🌱",
    "curious": "🔍",
    "afraid": "🛡️",
}


# -----------------------------------------------------------------------------
# Dataset Loading & Validation
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_and_validate_dataset(filepath: str) -> tuple[list[dict] | None, str | None]:
    """
    Loads and validates the book recommendations CSV file.
    Returns (books_list, error_message).
    """
    path = Path(filepath)
    if not path.is_file():
        return None, (
            f"Dataset file '{path.name}' was not found in the project folder.\n\n"
            f"Expected location: `{path.resolve()}`\n\n"
            f"Please ensure `{CSV_FILENAME}` is placed in the same folder as `app.py`."
        )

    try:
        import csv
        with open(path, mode="r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames:
                return None, f"Dataset file '{path.name}' is empty or does not contain column headers."

            found_columns = [col.strip() for col in reader.fieldnames if col]
            missing = [col for col in REQUIRED_COLUMNS if col not in found_columns]
            if missing:
                return None, (
                    f"Dataset file is missing required column(s):\n\n"
                    f"- **Missing columns:** `{', '.join(missing)}`\n"
                    f"- **Required columns:** `{', '.join(REQUIRED_COLUMNS)}`\n"
                    f"- **Found columns:** `{', '.join(found_columns)}`"
                )

            books = []
            for row in reader:
                cleaned = {k.strip(): v.strip() for k, v in row.items() if k}
                if cleaned.get("title") and cleaned.get("emotion"):
                    books.append(cleaned)

            if not books:
                return None, f"No valid book rows found in '{path.name}'. Please check the file contents."

            return books, None

    except UnicodeDecodeError:
        return None, f"Could not decode '{path.name}'. Please make sure the CSV is saved using standard UTF-8 encoding."
    except Exception as exc:
        return None, f"An unexpected error occurred while reading '{path.name}': {exc}"


# -----------------------------------------------------------------------------
# Google Books Cover Image Lookup & Caching
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=86400)
def fetch_book_cover_url(title: str, author: str) -> str | None:
    """
    Queries the public Google Books API by book title and author to find a cover thumbnail URL.
    Returns the HTTPS URL if found, or None on failure/missing image.
    Only sends book title and author to Google Books.
    """
    try:
        query_parts = [f"intitle:{title.strip()}"]
        if author and author.strip().lower() != "unknown":
            clean_author = author.split(" and ")[0].split(",")[0].strip()
            query_parts.append(f"inauthor:{clean_author}")

        query_str = " ".join(query_parts)
        api_url = "https://www.googleapis.com/books/v1/volumes"
        params = {
            "q": query_str,
            "maxResults": 1,
            "printType": "books",
        }
        headers = {
            "User-Agent": "MoodBookRecommender/1.0 (Public Educational App)"
        }

        response = requests.get(api_url, params=params, headers=headers, timeout=2.0)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            if items:
                volume_info = items[0].get("volumeInfo", {})
                image_links = volume_info.get("imageLinks", {})
                img_url = (
                    image_links.get("thumbnail")
                    or image_links.get("smallThumbnail")
                    or image_links.get("medium")
                )
                if img_url and isinstance(img_url, str):
                    if img_url.startswith("http://"):
                        img_url = "https://" + img_url[7:]
                    return img_url
    except Exception:
        # Gracefully handle network timeouts, rate limits (429), or network dropouts
        pass

    return None


def fetch_covers_in_parallel(books: list[dict]) -> dict[str, str | None]:
    """
    Fetches cover URLs for multiple books concurrently to keep the UI snappy.
    """
    def _fetch_single(book_dict):
        t = book_dict.get("title", "")
        a = book_dict.get("author", "")
        return t, fetch_book_cover_url(t, a)

    if not books:
        return {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(books))) as executor:
        results = dict(executor.map(_fetch_single, books))
    return results


# -----------------------------------------------------------------------------
# Placeholder Cover Image Generator (Pillow)
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def generate_placeholder_cover(title: str, author: str = "") -> bytes:
    """
    Generates a clean, neat placeholder image when the cover cannot be found
    or loaded from Google Books API.
    Contains the book title, author, and the exact text 'Cover unavailable'.
    Returns PNG image bytes.
    """
    width, height = 320, 480
    image = Image.new("RGB", (width, height), color="#1E293B")
    draw = ImageDraw.Draw(image)

    # Smooth subtle vertical gradient from dark slate to deep navy
    for y_idx in range(height):
        factor = y_idx / height
        r = int(30 * (1 - factor) + 15 * factor)
        g = int(41 * (1 - factor) + 23 * factor)
        b = int(59 * (1 - factor) + 42 * factor)
        draw.line([(0, y_idx), (width, y_idx)], fill=(r, g, b))

    # Outer elegant borders
    draw.rectangle([10, 10, width - 11, height - 11], outline="#334155", width=2)
    draw.rectangle([14, 14, width - 15, height - 15], outline="#475569", width=1)

    # Simulated book spine on left edge
    draw.rectangle([10, 10, 26, height - 11], fill="#0F172A", outline="#334155", width=1)
    draw.line([(28, 14), (28, height - 15)], fill="#64748B", width=1)

    # Helper to resolve TTF fonts if present on system
    def get_system_font(size: int, bold: bool = False):
        font_candidates = [
            "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for candidate in font_candidates:
            if os.path.exists(candidate):
                try:
                    return ImageFont.truetype(candidate, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    title_font = get_system_font(20, bold=True)
    author_font = get_system_font(14, bold=False)
    badge_font = get_system_font(13, bold=True)

    # Decorative header emblem
    icon_y = 65
    draw.polygon([(165, icon_y - 16), (180, icon_y), (165, icon_y + 16), (150, icon_y)], outline="#60A5FA", fill="#1E3A8A", width=2)
    draw.line([(155, icon_y), (175, icon_y)], fill="#93C5FD", width=2)

    # Wrap and draw title
    wrapped_title = textwrap.wrap(title, width=19)[:5]
    start_y = 120
    for line in wrapped_title:
        draw.text((170, start_y), line, fill="#F8FAFC", font=title_font, anchor="mm")
        start_y += 26

    # Draw author
    if author:
        author_y = start_y + 14
        auth_text = f"by {author}" if not author.lower().startswith("by") else author
        wrapped_author = textwrap.wrap(auth_text, width=24)[:2]
        for a_line in wrapped_author:
            draw.text((170, author_y), a_line, fill="#94A3B8", font=author_font, anchor="mm")
            author_y += 20

    # Decorative divider
    draw.line([(60, 365), (280, 365)], fill="#334155", width=1)

    # "Cover unavailable" badge
    badge_box = [55, 390, 285, 425]
    draw.rounded_rectangle(badge_box, radius=6, fill="#0F172A", outline="#64748B", width=1)
    draw.text((170, 407), "Cover unavailable", fill="#CBD5E1", font=badge_font, anchor="mm")

    buffer = BytesIO()
    image.save(buffer, format="PNG", quality=95)
    return buffer.getvalue()


# -----------------------------------------------------------------------------
# Streamlit Application Page Configuration & CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Mood-Based Book Recommender",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom styles for polished responsive cards and typography
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    .genre-badge {
        display: inline-block;
        padding: 0.2rem 0.65rem;
        font-size: 0.8rem;
        font-weight: 600;
        border-radius: 9999px;
        background-color: rgba(59, 130, 246, 0.15);
        color: #60a5fa;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
        border: 1px solid rgba(59, 130, 246, 0.25);
    }
    .emotion-badge {
        display: inline-block;
        padding: 0.2rem 0.65rem;
        font-size: 0.8rem;
        font-weight: 600;
        border-radius: 9999px;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .why-box {
        background-color: rgba(255, 255, 255, 0.03);
        border-left: 3px solid #60a5fa;
        padding: 0.75rem 1rem;
        border-radius: 0 8px 8px 0;
        font-style: italic;
        margin: 0.85rem 0;
        line-height: 1.5;
    }
    .disclaimer-text {
        font-size: 0.82rem;
        color: #94a3b8;
        padding: 1rem;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        margin-top: 2rem;
        text-align: center;
        line-height: 1.4;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Main Application Logic
# -----------------------------------------------------------------------------
def main():
    # Load dataset
    books, error_message = load_and_validate_dataset(str(CSV_PATH))

    # Sidebar: Project Info & Supported Emotions
    with st.sidebar:
        st.markdown("### 📚 About the Project")
        st.markdown(
            "This app recommends books tailored to your emotional state "
            "by matching your feelings to themes and keyword patterns in our curated dataset."
        )
        st.markdown("---")

        st.markdown("### 🎭 Supported Emotions")
        st.caption("The recommender recognizes 10 primary emotions and their common synonyms:")
        for emotion, emoji in EMOTION_EMOJIS.items():
            syns = [s for s in SUPPORTED_EMOTIONS.get(emotion, []) if s != emotion][:3]
            syn_str = ", ".join(syns)
            st.markdown(f"**{emoji} {emotion.capitalize()}**  \n<small style='color:#94a3b8'>e.g., {syn_str}</small>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🔒 Privacy & Safety")
        st.caption(
            "Your inputs stay in your session. Book titles and authors are only sent to "
            "the public Google Books API to look up book covers."
        )
        if books:
            st.success(f"✓ Loaded {len(books)} books from dataset")

    # App Header
    st.markdown('<div class="main-title">📖 Mood-Based Book Recommender</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Find comforting, inspiring, or exciting books that match how you are feeling right now.</div>',
        unsafe_allow_html=True,
    )

    # Stop and display error if dataset is missing or corrupt
    if error_message or not books:
        st.error("⚠️ Dataset Error")
        st.markdown(error_message)
        st.info("Please verify that `emotion_book_dataset.csv` exists and is formatted properly.")
        return

    # Quick suggestion chips to inspire user input
    st.markdown("**Quick inspiration:** click a mood below to test, or type your own feeling in the box:")
    chip_cols = st.columns(5)
    sample_queries = [
        ("🧘 Stressed & Overwhelmed", "I feel stressed and overwhelmed"),
        ("😊 Joyful & Cheerful", "I feel joyful and happy"),
        ("🌧️ Down & Blue", "I am feeling sad and low"),
        ("🔍 Curious & Inquisitive", "I am curious and want to learn something new"),
        ("🌙 Lonely & Isolated", "I feel lonely and isolated"),
    ]

    # Initialize session state for the feeling input
    if "user_feeling" not in st.session_state:
        st.session_state.user_feeling = ""
    if "has_searched" not in st.session_state:
        st.session_state.has_searched = False

    for idx, (label, query_text) in enumerate(sample_queries):
        col = chip_cols[idx % 5]
        if col.button(label, key=f"chip_{idx}", width="stretch"):
            st.session_state.user_feeling = query_text
            st.session_state.has_searched = True

    # User Input Form
    with st.form("recommendation_form"):
        user_input = st.text_input(
            label="How are you feeling right now?",
            value=st.session_state.user_feeling,
            placeholder="e.g., I feel stressed and overwhelmed, anxious, or curious...",
            help="Type a few words or a complete sentence describing your emotional state.",
        )

        col_btn, col_count, _ = st.columns([1.5, 1.2, 3])
        with col_count:
            recommendation_limit = st.selectbox(
                "Max recommendations:",
                options=[1, 2, 3, 4, 5],
                index=4,  # default 5
                help="Choose up to 5 book recommendations.",
            )
        with col_btn:
            submit_button = st.form_submit_button("🔍 Get Recommendations", type="primary", width="stretch")

    # Handle form submission
    if submit_button:
        st.session_state.user_feeling = user_input.strip()
        st.session_state.has_searched = True

    # Main content display
    if not st.session_state.has_searched or not st.session_state.user_feeling:
        if st.session_state.has_searched and not st.session_state.user_feeling:
            st.warning("💡 **Please tell us how you are feeling!** Type your mood in the box above or choose one of the quick inspiration buttons.")
        else:
            # Welcoming initial guidance
            st.info("👋 **Welcome!** Enter how you are feeling in the search box above to receive tailored book recommendations.")
            
            # Showcase supported moods overview
            st.markdown("#### Explore books by how you feel:")
            mood_grid = st.columns(5)
            all_emotions = list(SUPPORTED_EMOTIONS.keys())
            for i, emo in enumerate(all_emotions):
                with mood_grid[i % 5]:
                    color = EMOTION_COLORS.get(emo, "#3B82F6")
                    emoji = EMOTION_EMOJIS.get(emo, "📖")
                    st.markdown(
                        f"""
                        <div style="border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 0.75rem; text-align: center; margin-bottom: 0.5rem; background: rgba(255,255,255,0.02);">
                            <span style="font-size: 1.5rem;">{emoji}</span><br/>
                            <strong style="color: {color};">{emo.capitalize()}</strong>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        
        # Render disclaimer at bottom
        st.markdown(f'<div class="disclaimer-text">{DISCLAIMER}</div>', unsafe_allow_html=True)
        return

    # Process feeling text
    feeling_text = st.session_state.user_feeling
    user_words = extract_words(feeling_text)
    matched_emotions = detect_emotions(user_words)
    ranked_results = score_and_rank_books(books, user_words, matched_emotions)
    books_to_show = ranked_results[:recommendation_limit]

    # No matches found: display friendly helpful guide
    if not books_to_show:
        st.warning(f"🔍 We could not find any book recommendations matching **\"{feeling_text}\"**.")
        st.markdown(
            """
            ### Supported Emotions & Example Words
            Our recommender understands the following 10 emotions and many related words.
            Try describing your feeling with one of these or similar words:
            """
        )

        col_a, col_b = st.columns(2)
        halfway = len(SUPPORTED_EMOTIONS) // 2
        items = list(SUPPORTED_EMOTIONS.items())

        with col_a:
            for emo, syns in items[:halfway]:
                emoji = EMOTION_EMOJIS.get(emo, "•")
                sample_syns = ", ".join([s for s in syns if s != emo][:4])
                st.markdown(f"**{emoji} {emo.capitalize()}** — *{sample_syns}*")

        with col_b:
            for emo, syns in items[halfway:]:
                emoji = EMOTION_EMOJIS.get(emo, "•")
                sample_syns = ", ".join([s for s in syns if s != emo][:4])
                st.markdown(f"**{emoji} {emo.capitalize()}** — *{sample_syns}*")

        st.info("💡 **Tip:** Try typing phrases like *'I feel stressed and overwhelmed'* or *'Looking for something curious and inspiring'*.")
        st.markdown(f'<div class="disclaimer-text">{DISCLAIMER}</div>', unsafe_allow_html=True)
        return

    # Matches found: Display detected emotion badges & summary
    st.markdown("---")
    badge_html = ""
    if matched_emotions:
        for emo in sorted(matched_emotions):
            color = EMOTION_COLORS.get(emo, "#3B82F6")
            emoji = EMOTION_EMOJIS.get(emo, "")
            badge_html += f'<span class="emotion-badge" style="background-color: {color}22; color: {color}; border: 1px solid {color}55;">{emoji} {emo.capitalize()}</span> '
    else:
        badge_html = '<span class="emotion-badge" style="background-color: #64748B22; color: #94A3B8; border: 1px solid #64748B55;">Keywords match</span>'

    st.markdown(
        f"**Showing {len(books_to_show)} book recommendation(s)** for: *\"{feeling_text}\"*  &nbsp;&nbsp; {badge_html}",
        unsafe_allow_html=True,
    )

    # Pre-fetch covers concurrently in parallel
    raw_books = [item["book"] for item in books_to_show]
    cover_urls = fetch_covers_in_parallel(raw_books)

    # Render each book recommendation
    for rank, item in enumerate(books_to_show, start=1):
        book = item["book"]
        title = book.get("title", "Unknown Title")
        author = book.get("author", "Unknown Author")
        genre = book.get("genre", "General")
        why = book.get("why_it_may_fit", "A suitable match for your mood.")
        matched_kws = item.get("matched_keywords", [])

        # Fetch cover from pre-fetched map or fallback to placeholder
        cover_url = cover_urls.get(title)

        with st.container():
            col_cover, col_details = st.columns([1, 2.8], gap="medium")

            # Cover column
            with col_cover:
                if cover_url:
                    st.image(
                        cover_url,
                        caption=f"{title}",
                        width="stretch",
                    )
                else:
                    placeholder_png = generate_placeholder_cover(title, author)
                    st.image(
                        placeholder_png,
                        caption=f"{title} (Cover unavailable)",
                        width="stretch",
                    )

            # Details column
            with col_details:
                st.markdown(f"### {rank}. {title}")
                st.markdown(f"**✍️ Author:** {author}")
                st.markdown(
                    f'<span class="genre-badge">🏷️ {genre}</span>',
                    unsafe_allow_html=True,
                )

                # "Why it may fit" block
                st.markdown(
                    f"""
                    <div class="why-box">
                        <strong>Why it may fit:</strong><br/>
                        {why}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Matched keywords if available
                if matched_kws:
                    kw_badges = " ".join([f"`{kw}`" for kw in matched_kws])
                    st.caption(f"🎯 Matched keyword(s): {kw_badges}")

            st.markdown("<hr style='border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 1.5rem 0;' />", unsafe_allow_html=True)

    # Disclaimer at the bottom of the page
    st.markdown(f'<div class="disclaimer-text">{DISCLAIMER}</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
