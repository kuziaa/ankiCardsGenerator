# Anki Cards Generator

An automated tool for creating Anki decks with flashcards for learning English vocabulary based on a CSV file.

## Features

- 📚 **5 Card Types**: Typing (EN→RU, RU→EN), Multiple Choice (EN→RU, RU→EN), Scramble (RU→EN)
- 🔊 **Automatic Audio Generation** for each word using gTTS
- 🖼️ **Image Downloads** via Google Custom Search API
- 📊 **Flexible Configuration** through properties file
- 📝 **Structured Logging** with console and file output
- ⚙️ **Modular Architecture** for easy functionality extension
- 🛡️ **Reliable Error Handling** with ability to continue on errors

## Requirements

- Python 3.7+
- Dependencies listed in `requirements.txt`

## Installation

1. **Clone the repository** or extract the archive

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure the application**:
```bash
cp config.properties.sample config.properties
```

4. **Edit `config.properties`** (optional for basic operation):
```properties
# Google Custom Search API settings (optional)
API_KEY=yourGoogleCustomSearchApiKey
CX=yourGoogleCustomSearchCx

# Anki deck settings
DECK_ID=999004
DECK_NAME=Custom EN-RU Vocabulary Deck

# Path to CSV file with cards
CSV_FILE_PATH=src/resources/cards.csv

# Path to media folder
MEDIA_DIR=media

# Path to output APKG file
OUTPUT_FILE=vocabulary.apkg
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

Example CSV file is located in `src/resources/cards.csv`.

## Usage

### Basic Execution

```bash
cd src
python anki_generator.py
```

If you have multiple CSV files in the `src/resources/` directory, the script will prompt you to select which one to use. Media files will be automatically organized into subdirectories based on the selected CSV filename.

### With Google Custom Search API (for image downloads)

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

## Multiple Deck Support

The project supports working with multiple CSV files for different vocabulary sets:

- **Add multiple CSV files** to `src/resources/` directory
- **Run the script** and select which CSV file to process
- **Media files** are automatically organized in subdirectories under `media/` based on CSV filename
- **APKG output files** are saved in `results/` directory and named after the CSV file for easy identification

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
    │   ├── *.mp3
    │   └── *.jpg
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
├── requirements.txt               # Dependencies
├── README.md                      # Documentation
├── src/
│   ├── anki_generator.py         # Main script
│   ├── models/                   # Card models
│   │   ├── en_ru_typing_model.py
│   │   ├── ru_en_typing_model.py
│   │   ├── en_ru_choice_model.py
│   │   ├── ru_en_choice_model.py
│   │   └── ru_en_scramble_model.py
│   ├── utils/                    # Utility modules
│   │   ├── logger.py             # Logging
│   │   ├── properties_util.py    # Configuration loading
│   │   ├── media_manager.py      # Media management
│   │   └── card_generator.py     # Card generation
│   ├── resources/
│   │   ├── cards.csv             # CSV with source data (deck 1)
│   │   ├── advanced_vocabulary.csv # CSV with source data (deck 2, optional)
│   │   └── ...                   # Additional CSV files (optional)
│   └── media/                    # Generated media files (not tracked)
│       ├── cards/                # Media for cards.csv
│       │   ├── *.mp3             # Audio files
│       │   └── *.jpg             # Images
│       ├── advanced_vocabulary/  # Media for advanced_vocabulary.csv
│       │   ├── *.mp3
│       │   └── *.jpg
│       └── ...
├── results/                      # Generated APKG decks (not tracked)
│   ├── cards.apkg
│   ├── advanced_vocabulary.apkg
│   └── ...
└── logs/                         # Execution logs (not tracked)
    └── anki_generator.log
```

## Output Files

After successful execution, the following will be created:

- **results/[csv_filename].apkg** - Ready Anki deck for import (saved in results directory)
- **media/[csv_filename]/** - Folder with audio files (.mp3) and images (.jpg) organized by CSV file
- **logs/anki_generator.log** - Execution log with all details

Each CSV file gets its own APKG deck in the `results/` directory and corresponding media subdirectory, allowing you to manage multiple vocabulary sets independently.

## Error Handling

The script is designed with reliability in mind:

- ❌ If an image fails to download - the process continues with the next word
- ❌ If audio generation fails - the card is created without sound
- ❌ If CSV contains incorrect rows - they are skipped with logging
- ✅ All errors are recorded in `logs/anki_generator.log`

## Card Types Created

For each word, 5 cards are created:

1. **EN→RU Typing** - Write the Russian translation of the English word
2. **RU→EN Typing** - Write the English translation of the Russian word
3. **EN→RU Choice** - Select the correct Russian translation from 4 options
4. **RU→EN Choice** - Select the correct English translation from 4 options
5. **RU→EN Scramble** - Arrange the letters of the English word in the correct order

Each card contains:
- 🔊 Audio pronunciation (if API keys are configured)
- 🖼️ Illustration (if API keys are configured)
- 📝 Usage example on the back side

## Extending Functionality

### Adding a New Card Type

1. Create a new model file in `src/models/your_model.py`
2. Define the card structure in genanki.Model
3. Add card creation to `card_generator.py`
4. Update `anki_generator.py` to use the new card

### Changing Card Design

Edit the corresponding files in `src/models/`:
- Change HTML templates in `qfmt` (front) and `afmt` (back)
- Update CSS in the `css` block
- Edit the field list in `fields`

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
**Solution**: Image downloading can be slow. This is normal.

## License

MIT

## Support

If you encounter any issues, see:
1. `logs/anki_generator.log` - detailed execution log
2. Console output (INFO, WARNING, ERROR messages)

## Changes in Version 2.0

✨ **Improvements:**
- Complete architecture refactoring into modules
- Structured logging with file output
- Reliable error handling with ability to continue on failures
- Flexible configuration through properties file
- Added CSV data validation
- Improved code readability with type hints and docstrings
- Added support for empty/missing media files

🔧 **Technical Details:**
- `MediaManager` class for media management
- `CardGenerator` class for card creation
- `CardData` class for data storage
- `logger.py` module for logging
- Complete rewrite of `anki_generator.py`