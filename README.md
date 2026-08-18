# Anki Cards Generator

An automated tool for creating Anki decks with flashcards for learning English vocabulary based on CSV files.

## Features

- 📚 **Flexible Card Types**: Choose from 5 types - Typing (EN→RU, RU→EN), Multiple Choice (EN→RU, RU→EN), Scramble with error counter (RU→EN)
- 🔊 **Automatic Audio Generation** for each word using gTTS
- 🖼️ **Image Downloads** via Google Custom Search API
- 📊 **Multiple Deck Support** - Create multiple vocabulary decks from different CSV files
- 🎯 **Selective Model Generation** - Choose which card types to generate
- 📝 **Structured Logging** with console and file output
- ⚙️ **Modular Architecture** for easy functionality extension
- 🛡️ **Reliable Error Handling** with ability to continue on errors

## Quick Start

```bash
# 1. Clone the repository
git clone <repository-url>
cd ankiCardsGenerator

# 2. Install the package
pip install -e .

# 3. Configure (optional, for image downloads)
cp config.properties.sample config.properties
# Edit config.properties and add your Google API keys

# 4. Run the generator
anki-cards-generator

# 5. Follow the prompts:
#    - Select a CSV file from src/resources/
#    - Select which card models to generate (1-6)
#    - Wait for deck generation to complete

# 6. Import the APKG file
# Your deck will be created in the results/ directory
```

- Python 3.9+
- Dependencies listed in `pyproject.toml` and `requirements.txt`

## Installation

1. **Clone the repository** or extract the archive

2. **Install dependencies**:
```bash
pip install -e .
```

3. **Configure the application** (optional, for image downloads):
```bash
cp config.properties.sample config.properties
```

4. **Edit `config.properties`** to add Google Custom Search API keys (optional):
```properties
# Google Custom Search API settings (optional for image downloads)
API_KEY=yourGoogleCustomSearchApiKey
CX=yourGoogleCustomSearchCx

# Anki deck settings
# DECK_ID is optional: when omitted, a stable ID is derived from the CSV file name
#DECK_ID=999004
# The final deck is named DECK_NAME::<csv name> (a subdeck per CSV in Anki)
DECK_NAME=Custom EN-RU Vocabulary Deck
```

## Data Preparation

### CSV File Format

Create a CSV file with the following required columns:

| Column | Description | Example |
|--------|-------------|---------|
| `english` | English word/phrase | "express my deep gratitude" |
| `russian` | Russian translation | "выразить глубокую благодарность" |
| `example` | Usage example | "I would like to express my deep gratitude…" |
| `incorrectEnVariant1` | Wrong variant (EN) 1 | "impress my dog gratitude" |
| `incorrectEnVariant2` | Wrong variant (EN) 2 | "depress my seed gratitude" |
| `incorrectEnVariant3` | Wrong variant (EN) 3 | "compress my deep attitude" |
| `incorrectEnVariant4` | Wrong variant (EN) 4 | "oppress my cheap gratitude" |
| `incorrectRuVariant1` | Wrong variant (RU) 1 | "выразить легкую благодарность" |
| `incorrectRuVariant2` | Wrong variant (RU) 2 | "выразить поверхностную признательность" |
| `incorrectRuVariant3` | Wrong variant (RU) 3 | "выразить формальную благодарность" |
| `incorrectRuVariant4` | Wrong variant (RU) 4 | "выразить обычную признательность" |

Example CSV file is located in `src/resources/cards.example.csv`. 

**Note**: CSV files in `src/resources/` (except `cards.example.csv`) are not tracked by Git. Copy and rename `cards.example.csv` to create your own vocabulary files.

### Creating CSV Files

#### Option 1: Convert Dictionary/Table to CSV

Use [ChatGPT Prompt for CSV Creation](docs/prompt_csv_creation.txt) to convert any dictionary or table into a compatible CSV file.

**Quick guide:**
1. Open the prompt file and copy it
2. Paste into ChatGPT
3. Replace `(Insert the table here)` with your dictionary data
4. Copy the generated CSV output
5. Save as `.csv` file in `src/resources/` directory

#### Option 2: Extract Vocabulary from Text by CEFR Level

Use [ChatGPT Prompt for Vocabulary Extraction](docs/prompt_vocabulary_extraction.txt) to extract vocabulary from any English text (books, articles, etc.) based on CEFR proficiency level.

**Workflow:**
1. Open the prompt file and copy it
2. Paste into ChatGPT
3. Send your chapter/text to extract vocabulary
4. Convert the resulting table to CSV using Option 1 prompt
5. Save in `src/resources/` directory

## Usage

### Basic Execution

```bash
anki-cards-generator
```

Running without arguments starts the interactive flow: CSV selection first,
then card model selection.

### Non-Interactive CLI

Use `--csv` and `--models` to generate a deck without prompts:

```bash
anki-cards-generator --csv cards.example.csv --models 1,2,5
```

CSV paths are resolved in this order:

1. The path exactly as provided, absolute or relative to the current directory
2. If only a file name was provided, `src/resources/<file name>`

You can also generate directly from an Obsidian markdown table:

```bash
anki-cards-generator --from-md note.md --models all
```

Markdown input expects a table with `word`/`english`,
`translation`/`russian`, and `example` columns. Markdown tables do not include
multiple-choice distractors, so markdown mode supports only models `1`, `2`,
and `5`; `--models all` maps to those safe models.

Model selection accepts `all` or comma-separated model numbers:

- `1` = EN→RU Typing
- `2` = RU→EN Typing
- `3` = EN→RU Choice
- `4` = RU→EN Choice
- `5` = RU→EN Scramble

For a no-network run, use cached local media only:

```bash
anki-cards-generator --csv cards.example.csv --models all --offline
```

Exit codes are stable for scripted usage: `0` means success, `1` means a
runtime failure such as CSV validation errors or a missing CSV file, and `2`
means invalid CLI usage.

### CSV Validation

Check an input file without generating a deck:

```bash
anki-cards-generator --validate --csv my_words.csv
anki-cards-generator --validate --from-md note.md
```

CSV validation checks structural problems (wrong field count, distractors equal
to the answer, duplicates, hostile characters). Markdown validation checks that
a supported vocabulary table is present and has required columns.

### Interactive Prompts

The script will guide you through two selections:

#### 1. Select CSV File

If you have multiple CSV files in `src/resources/`:
```
============================================================
Multiple CSV files found. Please select one:
============================================================
1. cards.csv
2. advanced_vocabulary.csv
3. technical_terms.csv

Enter the number of your choice (1-3): 1
✓ Selected: cards.csv
```

#### 2. Select Card Models

Choose which types of flashcards to generate:
```
============================================================
Available card models:
============================================================
1. EN→RU Typing
2. RU→EN Typing
3. EN→RU Choice
4. RU→EN Choice
5. RU→EN Scramble
6. All models

Enter model numbers separated by space (e.g., '1 3 5') or '6' for all: 1 2 3
✓ Selected models: [1, 2, 3]
```

You can:
- Select specific models: `1 3 5`
- Select all models: `6`
- Select individual model: `1`

### With Google Custom Search API (for Image Downloads)

1. **Create Google Custom Search API key**:
   - Go to https://programmablesearchengine.google.com/
   - Create a new search engine
   - Obtain API KEY and CX

2. **Update `config.properties`**:
```properties
API_KEY=your_actual_api_key
CX=your_actual_cx
```

3. **Run the script**:
```bash
cd src
python anki_generator.py
```

## Card Types Explained

The project supports creating up to 5 different types of flashcards per word:

### 1. EN→RU Typing
- **What**: Translate English word/phrase to Russian by typing
- **Use case**: Active production of Russian translation
- **Format**: Shows English word, you type Russian translation

### 2. RU→EN Typing
- **What**: Translate Russian to English by typing
- **Use case**: Active production of English translation
- **Format**: Shows Russian word, you type English translation

### 3. EN→RU Choice
- **What**: Select correct Russian translation from 4 options
- **Use case**: Passive recognition, multiple choice practice
- **Format**: Shows English word with 4 Russian options

### 4. RU→EN Choice
- **What**: Select correct English translation from 4 options
- **Use case**: Passive recognition, multiple choice practice
- **Format**: Shows Russian word with 4 English options

### 5. RU→EN Scramble ⭐ Special Feature
- **What**: Arrange shuffled letters to spell the English word
- **Use case**: Active spelling and word formation practice
- **Special Features**:
  - Buttons with shuffled letters
  - Click letters to spell the word (in correct order)
  - Type the word with keyboard validation
  - **Error Counter** - tracks mistakes (red counter)
  - Errors increment when:
    - Clicking wrong letter button
    - Typing incorrect character on keyboard
- **Format**: Shows Russian word, shuffle letter buttons below

## Multiple Deck Support

The project supports working with multiple CSV files for different vocabulary sets:

- **Add multiple CSV files** to `src/resources/` directory
- **Run the script** and select which CSV file to process
- **Media files** are automatically organized in subdirectories under `media/` based on CSV filename
- **APKG output files** are saved in `results/` directory and named after the CSV file

Example structure:
```
ankiCardsGenerator/
├── src/
│   ├── resources/
│   │   ├── cards.csv              # Deck 1
│   │   ├── advanced_vocabulary.csv # Deck 2
│   │   └── technical_terms.csv     # Deck 3
│
├── results/                        # Output APKG files
│   ├── cards.apkg                  # Generated from cards.csv
│   ├── advanced_vocabulary.apkg     # Generated from advanced_vocabulary.csv
│   └── technical_terms.apkg         # Generated from technical_terms.csv
│
└── media/
    ├── cards/                      # Media for cards.csv
    │   ├── *.mp3                   # Audio files
    │   └── *.jpg                   # Images
    ├── advanced_vocabulary/        # Media for advanced_vocabulary.csv
    │   ├── *.mp3
    │   └── *.jpg
    └── technical_terms/            # Media for technical_terms.csv
        ├── *.mp3
        └── *.jpg
```

## Project Structure

```
ankiCardsGenerator/
├── config.properties              # Configuration (not tracked by Git)
├── config.properties.sample       # Configuration example
├── pyproject.toml                 # Package metadata, entry point, pytest config
├── requirements.txt               # Dependencies
├── README.md                      # Documentation
├── .github/workflows/tests.yml    # CI test workflow
├── docs/                          # Documentation and prompts
│   ├── prompt_csv_creation.txt
│   └── prompt_vocabulary_extraction.txt
├── src/
│   ├── anki_generator.py         # Main script with CSV and model selection
│   ├── models/                   # Card models (Anki templates)
│   │   ├── en_ru_typing_model.py
│   │   ├── ru_en_typing_model.py
│   │   ├── en_ru_choice_model.py
│   │   ├── ru_en_choice_model.py
│   │   └── ru_en_scramble_model.py (includes error counter)
│   ├── utils/                    # Utility modules
│   │   ├── logger.py             # Logging
│   │   ├── properties_util.py    # Configuration loading
│   │   ├── csv_validator.py      # Pre-flight CSV validation
│   │   ├── media_manager.py      # Media management
│   │   └── card_generator.py     # Card generation with model selection
│   └── resources/
│       ├── cards.example.csv     # Example CSV file (template for your data)
│       └── ...                   # Your CSV files (not tracked by Git)
├── media/                        # Generated media files (not tracked)
│   ├── cards/                    # Media for cards.csv
│   │   ├── *.mp3
│   │   └── *.jpg
│   └── ...
├── results/                      # Generated APKG decks (not tracked)
│   └── *.apkg
├── tests/                        # Pytest test suite
│   ├── test_card_generator.py
│   ├── test_cli.py
│   ├── test_csv_validator.py
│   └── test_media_manager.py
└── logs/                         # Execution logs (not tracked)
    └── anki_generator.log
```

## Output Files

After successful execution, the following will be created:

- **results/[csv_filename].apkg** - Ready Anki deck for import (saved in results directory)
- **media/[csv_filename]/** - Folder with audio files (.mp3) and images (.jpg) organized by CSV file
- **logs/anki_generator.log** - Execution log with all details

Example:
```
results/
├── cards.apkg
├── advanced_vocabulary.apkg
└── technical_terms.apkg

media/
├── cards/
│   ├── express_my_deep_gratitude.mp3
│   ├── express_my_deep_gratitude.jpg
│   └── ...
├── advanced_vocabulary/
│   └── ...
└── technical_terms/
    └── ...
```

## Error Handling

The script is designed with reliability in mind:

- ❌ If an image fails to download - the process continues with the next word
- ❌ If audio generation fails - the card is created without sound
- ✅ CSV is validated before generation - broken rows are reported with physical line numbers and the run stops
- ✅ All errors are recorded in `logs/anki_generator.log`

## Card Types Created

The project supports creating up to 5 different types of flashcards per word. You can choose which types to generate:

1. **EN→RU Typing** - Write the Russian translation of the English word
2. **RU→EN Typing** - Write the English translation of the Russian word
3. **EN→RU Choice** - Select the correct Russian translation from 4 options
4. **RU→EN Choice** - Select the correct English translation from 4 options
5. **RU→EN Scramble** - Arrange the letters of the English word in the correct order (includes error counter)

Each card contains:
- 🔊 Audio pronunciation (generated with gTTS, no API keys required)
- 🖼️ Illustration (if API keys are configured)
- 📝 Usage example on the back side

## Extending Functionality

### Adding a New Card Type

1. Create a new model file in `src/models/your_model.py`
2. Define the structure in genanki.Model
3. Add import and instantiation in `card_generator.py`
4. Add creation logic in `CardGenerator.create_cards()` method
5. Update `anki_generator.py` to include new model number in `select_card_models()`

### Changing Card Design

Edit the corresponding files in `src/models/`:
- Modify HTML templates in `qfmt` (front side) and `afmt` (back side)
- Update CSS in the `css` block
- Edit the field list in `fields`

Example: To add a new visual element to the Scramble card, edit `ru_en_scramble_model.py`

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'genanki'"
**Solution**: Install dependencies: `pip install -r requirements.txt`

### Issue: "FileNotFoundError: config.properties file not found"
**Solution**: Create the file: `cp config.properties.sample config.properties`

### Issue: Images are not downloading
**Solution**:
- Check for API_KEY and CX in config.properties
- Ensure API quota is not exhausted
- Check internet connection
- See logs in `logs/anki_generator.log`

### Issue: Slow execution
**Solution**: Image downloading can be slow. This is normal. One image usually takes 1-3 seconds.

### Issue: CSV file not found
**Solution**: Make sure your CSV file is placed in `src/resources/` directory with `.csv` extension

## License

MIT

## Support

If you encounter any issues:

1. Check `logs/anki_generator.log` for detailed error messages
2. Review console output (INFO, WARNING, ERROR messages)
3. Check the Troubleshooting section above
4. Ensure all dependencies are installed: `pip install -r requirements.txt`

## Contributing

Feel free to extend functionality by:
- Adding new card models
- Improving existing templates
- Creating new ChatGPT prompts for data extraction
- Optimizing media processing

---

**Happy learning! 🎓**

## Recent Changes

### Version 2.1
✨ **New Features:**
- Selective card model generation - choose which types to create
- Multiple CSV file selection on startup
- Media and APKG organization by CSV filename
- Results directory for organized output
- Error counter for Scramble cards
- Complete README restructuring with separate prompt files

🔧 **Technical Details:**
- `CardGenerator` now accepts `selected_models` parameter
- `select_card_models()` function for interactive model selection
- Media files organized in subdirectories
- APKG files saved to `results/` directory

### Version 2.0
✨ **Improvements:**
- Complete architecture refactoring into modules
- Structured logging with file output
- Reliable error handling with continue-on-error
- Flexible configuration through properties file
- CSV data validation
- Improved code readability with type hints and docstrings

🔧 **Technical Details:**
- `MediaManager` class for media management
- `CardGenerator` class for card creation
- `CardData` class for data storage
- `logger.py` module for logging
- Complete rewrite of `anki_generator.py`