"""
Mood-Based Book Recommender
============================
A beginner-friendly command-line program that suggests books based on how you feel.

How it works:
1. Reads book data from 'emotion_book_dataset.csv' in the same folder.
2. Takes your mood from command-line arguments or prompts you interactively.
3. Recognizes 10 primary emotions and common synonyms.
4. Matches and ranks books by keyword relevance.
5. Displays top recommendations (title, author, genre, and why it fits).

Disclaimer:
This tool provides casual reading suggestions for leisure.
It is not intended to treat, diagnose, or cure any emotional or mental health condition.
"""

import argparse
import csv
import os
import re
import sys

# Ensure UTF-8 console output on Windows so special characters (like quotes/apostrophes) display nicely
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Name of the CSV file containing book recommendations
CSV_FILENAME = "emotion_book_dataset.csv"

# Columns that must exist in the CSV file
REQUIRED_COLUMNS = ["emotion", "title", "author", "genre", "why_it_may_fit", "keywords"]

# The 10 supported primary emotions and their recognized synonyms / related words
SUPPORTED_EMOTIONS = {
    "happy": [
        "happy", "joy", "joyful", "cheerful", "delighted", "glad", "great",
        "content", "happiness", "upbeat", "amused", "playful"
    ],
    "sad": [
        "sad", "down", "blue", "unhappy", "low", "sadness", "sorrow",
        "grief", "grieving", "heartbroken", "gloomy"
    ],
    "anxious": [
        "anxious", "worried", "nervous", "uneasy", "anxiety", "apprehensive",
        "jittery", "tense", "restless"
    ],
    "stressed": [
        "stressed", "overwhelmed", "busy", "pressure", "burnout", "stress",
        "exhausted", "tired", "frazzled", "overworked"
    ],
    "angry": [
        "angry", "mad", "frustrated", "irritated", "annoyed", "anger",
        "furious", "upset", "enraged", "cross"
    ],
    "lonely": [
        "lonely", "isolated", "alone", "disconnected", "loneliness",
        "solitary", "abandoned", "lonesome"
    ],
    "bored": [
        "bored", "restless", "uninterested", "boredom", "dull",
        "uninspired", "monotonous"
    ],
    "hopeful": [
        "hopeful", "optimistic", "encouraged", "inspired", "hope",
        "positive", "uplifted", "promising"
    ],
    "curious": [
        "curious", "interested", "intrigued", "curiosity", "inquisitive",
        "wonder", "inquiring", "fascinated"
    ],
    "afraid": [
        "afraid", "scared", "frightened", "fearful", "fear",
        "spooky", "terrified", "petrified", "spooked"
    ],
}

# Helpful disclaimer displayed with recommendations
DISCLAIMER = (
    "Disclaimer: This reading suggestion tool is for casual leisure reading.\n"
    "It is not intended to treat, diagnose, or cure any emotional or mental health condition."
)


def get_csv_path() -> str:
    """
    Returns the absolute path to 'emotion_book_dataset.csv' in the same folder as this script.
    """
    script_directory = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_directory, CSV_FILENAME)


def load_books(csv_path: str) -> list[dict]:
    """
    Loads books from the CSV file and validates required columns.

    Parameters:
        csv_path (str): The file path to the CSV dataset.

    Returns:
        list[dict]: A list of book dictionaries from the CSV file.
    """
    # 1. Check if the CSV file exists
    if not os.path.exists(csv_path):
        print("\n" + "!" * 70)
        print(f"Error: The dataset file '{CSV_FILENAME}' was not found.")
        print(f"Looking in: {os.path.abspath(csv_path)}")
        print("\nHow to fix:")
        print(f"  Make sure '{CSV_FILENAME}' is placed in the exact same folder")
        print("  as this Python script ('mood_book_recommender.py').")
        print("!" * 70 + "\n")
        sys.exit(1)

    # 2. Read the CSV file
    try:
        with open(csv_path, mode="r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)

            # Check that the file is not empty and has headers
            if not reader.fieldnames:
                print("\n" + "!" * 70)
                print(f"Error: The dataset file '{CSV_FILENAME}' is empty or invalid.")
                print("!" * 70 + "\n")
                sys.exit(1)

            # 3. Verify that all required columns are present in the header
            found_columns = [col.strip() for col in reader.fieldnames if col]
            missing_columns = [col for col in REQUIRED_COLUMNS if col not in found_columns]

            if missing_columns:
                print("\n" + "!" * 70)
                print(f"Error: The dataset '{CSV_FILENAME}' is missing required column(s).")
                print(f"  Required columns : {', '.join(REQUIRED_COLUMNS)}")
                print(f"  Columns in file  : {', '.join(found_columns)}")
                print(f"  Missing column(s): {', '.join(missing_columns)}")
                print("\nHow to fix:")
                print("  Please ensure the first line of the CSV includes all required column names.")
                print("!" * 70 + "\n")
                sys.exit(1)

            books = []
            for row in reader:
                # Clean up leading/trailing whitespace in values
                cleaned_row = {k.strip(): v.strip() for k, v in row.items() if k}
                # Only include rows that have at least a title and an emotion
                if cleaned_row.get("title") and cleaned_row.get("emotion"):
                    books.append(cleaned_row)

            # Check if there are any valid book rows
            if not books:
                print("\n" + "!" * 70)
                print(f"Error: No book records were found in '{CSV_FILENAME}'.")
                print("Please check that the CSV file contains data rows below the header.")
                print("!" * 70 + "\n")
                sys.exit(1)

            return books

    except UnicodeDecodeError:
        print("\n" + "!" * 70)
        print(f"Error: Could not decode '{CSV_FILENAME}'. Please ensure it is saved with UTF-8 encoding.")
        print("!" * 70 + "\n")
        sys.exit(1)
    except Exception as error:
        print("\n" + "!" * 70)
        print(f"Error reading '{CSV_FILENAME}': {error}")
        print("!" * 70 + "\n")
        sys.exit(1)


def extract_words(text: str) -> set[str]:
    """
    Converts a string of text into a set of lowercase words without punctuation.

    Parameters:
        text (str): The raw input text.

    Returns:
        set[str]: Set of lowercase words found in the text.
    """
    if not text:
        return set()
    # Find all alphabetical/numerical word tokens and convert them to lowercase
    return set(re.findall(r"\b\w+\b", text.lower()))


def detect_emotions(user_words: set[str]) -> set[str]:
    """
    Finds any supported primary emotions that match words in the user's input.

    Parameters:
        user_words (set[str]): Words typed by the user.

    Returns:
        set[str]: Primary emotion keys that were detected (e.g., {'stressed', 'anxious'}).
    """
    matched_emotions = set()

    for primary_emotion, synonyms in SUPPORTED_EMOTIONS.items():
        # If any user word is an exact match for the primary emotion or its synonyms
        if user_words.intersection(set(synonyms)):
            matched_emotions.add(primary_emotion)

    return matched_emotions


def score_and_rank_books(books: list[dict], user_words: set[str], matched_emotions: set[str]) -> list[dict]:
    """
    Filters and ranks books based on matched emotions and keyword matches.

    Ranking rules:
    - If emotions were detected, only books matching those emotions are considered.
    - If no emotion was detected, books with keywords matching the user's words are considered.
    - Books with more matching keywords are ranked higher.
    - If scores are equal, the original order in the dataset is preserved (stable sort).

    Parameters:
        books (list[dict]): All books loaded from the CSV dataset.
        user_words (set[str]): Lowercase words from the user's input.
        matched_emotions (set[str]): Primary emotions detected from user input.

    Returns:
        list[dict]: A list of book wrapper dicts, sorted by keyword match score descending.
    """
    candidate_books = []

    # 1. Determine candidate books based on detected emotions
    if matched_emotions:
        candidate_books = [
            book for book in books
            if book.get("emotion", "").lower() in matched_emotions
        ]
    else:
        # If no primary emotion was directly recognized, evaluate all books
        candidate_books = books

    # 2. Score candidate books based on matching keywords
    scored_items = []
    for book in candidate_books:
        # Extract keywords for this book
        raw_keywords = book.get("keywords", "")
        book_keywords = extract_words(raw_keywords)

        # Count how many of the user's words appear in the book's keywords
        matching_keywords = user_words.intersection(book_keywords)
        score = len(matching_keywords)

        # If emotions were matched, all candidate books are valid suggestions
        # If no emotion was matched, require at least 1 keyword match
        if matched_emotions or score > 0:
            scored_items.append({
                "book": book,
                "score": score,
                "matched_keywords": sorted(matching_keywords),
            })

    # 3. Sort books: higher keyword match score first
    # In Python, sort() is stable, so books with the same score maintain their order
    scored_items.sort(key=lambda item: item["score"], reverse=True)

    return scored_items


def display_results(user_input: str, matched_emotions: set[str], results: list[dict], limit: int) -> None:
    """
    Nicely prints the recommended books to the command line.

    Parameters:
        user_input (str): The raw text entered by the user.
        matched_emotions (set[str]): Emotions detected in the user input.
        results (list[dict]): Scored book items.
        limit (int): Maximum number of recommendations to display.
    """
    books_to_show = results[:limit]

    print("\n" + "=" * 70)
    print("                 MOOD-BASED BOOK RECOMMENDER")
    print("=" * 70)
    print(f"You entered       : \"{user_input}\"")
    if matched_emotions:
        formatted_emotions = ", ".join(sorted(matched_emotions))
        print(f"Detected emotion  : {formatted_emotions}")
    print(f"Showing           : {len(books_to_show)} recommendation(s) (requested: {limit})")
    print("-" * 70)

    for index, item in enumerate(books_to_show, start=1):
        book = item["book"]
        print(f"\n{index}. Title         : {book.get('title', 'Unknown')}")
        print(f"   Author        : {book.get('author', 'Unknown')}")
        print(f"   Genre         : {book.get('genre', 'Unknown')}")
        print(f"   Why it may fit: {book.get('why_it_may_fit', 'N/A')}")

    print("\n" + "-" * 70)
    print(DISCLAIMER)
    print("=" * 70 + "\n")


def display_no_matches(user_input: str) -> None:
    """
    Displays a friendly message when no matching books or emotions could be found,
    along with suggestions for supported emotions.

    Parameters:
        user_input (str): The input text that yielded no results.
    """
    print("\n" + "=" * 70)
    print("                 MOOD-BASED BOOK RECOMMENDER")
    print("=" * 70)
    print(f"You entered: \"{user_input}\"")
    print("\nWe could not find any book recommendations matching that feeling.")
    print("\nHere are the 10 emotions and example words we currently support:\n")

    for emotion in sorted(SUPPORTED_EMOTIONS.keys()):
        # Show top 4 synonyms for each emotion
        synonyms = [s for s in SUPPORTED_EMOTIONS[emotion] if s != emotion][:4]
        synonyms_text = ", ".join(synonyms)
        print(f"  * {emotion:<10} -> e.g. {synonyms_text}")

    print("\nHow to try again:")
    print("  python mood_book_recommender.py \"I feel stressed and overwhelmed\"")
    print("  python mood_book_recommender.py \"I feel lonely\" -n 3")
    print("  python mood_book_recommender.py \"curious\"")
    print("\n" + "-" * 70)
    print(DISCLAIMER)
    print("=" * 70 + "\n")


def parse_arguments() -> tuple[list[str], int]:
    """
    Parses command-line arguments using Python's standard 'argparse' module.

    Supports:
    - python mood_book_recommender.py "I feel stressed and overwhelmed"
    - python mood_book_recommender.py "I feel lonely" -n 3
    - python mood_book_recommender.py (interactive prompt)

    Returns:
        tuple[list[str], int]: (feeling_arg_list, number_of_recommendations)
    """
    parser = argparse.ArgumentParser(
        description="Mood-Based Book Recommender: Suggests books based on your emotional mood."
    )

    # Optional number of recommendations: -n 3 or --num 3
    parser.add_argument(
        "-n",
        "--num",
        type=int,
        default=5,
        help="Number of book recommendations to display (default: 5).",
    )

    # Positional argument for the feeling string
    # nargs="*" allows both quoted strings and multiple words without quotes
    parser.add_argument(
        "feeling",
        nargs="*",
        help="Your feeling or mood (e.g. 'I feel stressed and overwhelmed').",
    )

    args = parser.parse_args()

    # Ensure limit is a positive number
    limit = args.num
    if limit < 1:
        print("\nNotice: The number of recommendations must be at least 1. Defaulting to 5.\n")
        limit = 5

    return args.feeling, limit


def main():
    """
    Main entry point for the Mood-Based Book Recommender program.
    """
    # 1. Parse command-line arguments
    feeling_args, limit = parse_arguments()

    # 2. Determine the user's feeling input
    if feeling_args:
        # User passed feeling arguments on the command line
        feeling_text = " ".join(feeling_args).strip()
        if not feeling_text:
            print("\n" + "!" * 70)
            print("Error: Empty feeling entered.")
            print("Please enter a word or sentence describing how you feel.")
            print("Example: python mood_book_recommender.py \"I feel stressed and overwhelmed\"")
            print("!" * 70 + "\n")
            sys.exit(1)
    else:
        # No feeling argument provided: prompt the user interactively
        print("\n" + "=" * 70)
        print("          Welcome to the Mood-Based Book Recommender!")
        print("=" * 70)
        print("Tell us how you are feeling, and we will find books to suit your mood.")
        print("Example: 'I feel stressed and overwhelmed', 'happy', 'lonely', or 'bored'.\n")

        try:
            feeling_text = input("How are you feeling right now? ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nProgram closed. Have a wonderful day!")
            sys.exit(0)

        # Check for empty interactive input
        if not feeling_text:
            print("\n" + "!" * 70)
            print("Error: No feeling was entered.")
            print("Please enter a word or sentence describing how you feel.")
            print("Example: 'I feel stressed and overwhelmed' or 'happy'.")
            print("!" * 70 + "\n")
            sys.exit(1)

    # 3. Load book dataset from CSV
    csv_path = get_csv_path()
    books = load_books(csv_path)

    # 4. Extract words from user input
    user_words = extract_words(feeling_text)

    # 5. Detect matched emotions from user words
    matched_emotions = detect_emotions(user_words)

    # 6. Match and rank books
    ranked_results = score_and_rank_books(books, user_words, matched_emotions)

    # 7. Display results or friendly suggestions if nothing matched
    if not ranked_results:
        display_no_matches(feeling_text)
    else:
        display_results(feeling_text, matched_emotions, ranked_results, limit)


if __name__ == "__main__":
    main()
