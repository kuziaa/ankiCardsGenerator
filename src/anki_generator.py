#!/usr/bin/env python3
"""
Anki Cards Generator - Generate flashcards for learning English vocabulary

This script creates an Anki deck with flashcards from a CSV file, including:
- Audio generation for each word
- Image downloading via Google Custom Search
- Creation of 5 types of flashcards (typing, choice, scramble)
"""

import argparse
import csv
import random
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path

import genanki

from utils.logger import setup_logger
from utils.properties_util import load_properties
from utils.media_manager import MediaManager
from utils.card_generator import CardGenerator, CardData, create_deck_from_cards
from utils.csv_validator import validate_csv, validate_word_entries
from utils.known_words import (filter_known_words, load_known_words,
                               record_known_words, record_word_list)
from utils.anki_connect import (AnkiConnectClient, AnkiConnectError,
                                AnkiNotAvailableError, ensure_deck, ensure_models,
                                fetch_mature_words, push_notes, store_media,
                                trigger_sync)
from utils.md_loader import MarkdownTableError, load_rows_from_markdown

# Initialize logger
logger = setup_logger(__name__)

MARKDOWN_SAFE_MODELS = [
    CardGenerator.EN_RU_TYPING,
    CardGenerator.RU_EN_TYPING,
    CardGenerator.RU_EN_SCRAMBLE,
    CardGenerator.EN_CLOZE,
]


@dataclass
class CliOptions:
    """Resolved command-line options for one run."""

    csv_path: Path = None
    markdown_path: Path = None
    selected_models: list = None
    validate_only: bool = False
    offline: bool = False
    include_known: bool = False
    push: bool = False
    overwrite_media: bool = False


def project_root() -> Path:
    return Path(__file__).parent.parent


def resources_dir() -> Path:
    return project_root() / 'src' / 'resources'


def _model_help() -> str:
    models = ', '.join(f"{number}={name}" for number, name in CardGenerator.MODEL_NAMES.items())
    return f"Card models to generate: all or comma-separated numbers ({models})"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Anki decks from vocabulary CSV files."
    )
    parser.add_argument(
        '--csv',
        dest='csv_file',
        metavar='PATH',
        help="CSV path. Bare file names are also searched in src/resources/.",
    )
    parser.add_argument(
        '--models',
        metavar='LIST',
        help=_model_help(),
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help="Validate input and exit without generating a deck.",
    )
    parser.add_argument(
        '--offline',
        action='store_true',
        help="Use only cached local media; do not call TTS or image search services.",
    )
    parser.add_argument(
        '--include-known',
        action='store_true',
        help="Do not skip words already present in the known-words ledger.",
    )
    parser.add_argument(
        '--from-md',
        metavar='PATH',
        help="Create cards from an Obsidian markdown table.",
    )
    parser.add_argument(
        '--push',
        action='store_true',
        help="Push cards into a running Anki via AnkiConnect instead of writing an .apkg file.",
    )
    parser.add_argument(
        '--overwrite-media',
        action='store_true',
        help="With --push: overwrite media files that already exist in the Anki collection.",
    )
    return parser


def resolve_csv_path(csv_arg: str, default_resources_dir: Path) -> Path:
    csv_path = Path(csv_arg).expanduser()
    if csv_path.exists():
        return csv_path

    if csv_path.parent == Path('.'):
        resource_csv = default_resources_dir / csv_path.name
        if resource_csv.exists():
            return resource_csv

    raise FileNotFoundError(csv_arg)


def resolve_existing_path(path_arg: str) -> Path:
    path = Path(path_arg).expanduser()
    if path.exists():
        return path
    raise FileNotFoundError(path_arg)


def parse_model_selection(models_arg: str) -> list:
    if models_arg.lower() == 'all':
        return sorted(CardGenerator.MODEL_NAMES.keys())

    try:
        selected_models = sorted({int(part.strip()) for part in models_arg.split(',') if part.strip()})
    except ValueError as e:
        raise ValueError("models must be 'all' or comma-separated numbers") from e

    if not selected_models:
        raise ValueError("models list cannot be empty")

    valid_models = set(CardGenerator.MODEL_NAMES.keys())
    invalid_models = [model for model in selected_models if model not in valid_models]
    if invalid_models:
        raise ValueError(f"unknown model number(s): {', '.join(map(str, invalid_models))}")

    return selected_models


def parse_args(argv: list = None) -> CliOptions:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.overwrite_media and not args.push:
        parser.error("--overwrite-media requires --push")

    if args.from_md and args.csv_file:
        parser.error("--from-md and --csv are mutually exclusive")

    options = CliOptions(validate_only=args.validate, offline=args.offline,
                         include_known=args.include_known, push=args.push,
                         overwrite_media=args.overwrite_media)
    if args.from_md:
        try:
            options.markdown_path = resolve_existing_path(args.from_md)
        except FileNotFoundError:
            logger.error(f"✗ File {args.from_md} not found!")
            raise
    elif args.csv_file:
        try:
            options.csv_path = resolve_csv_path(args.csv_file, resources_dir())
        except FileNotFoundError:
            logger.error(f"✗ File {args.csv_file} not found!")
            raise

    if args.from_md:
        if args.models and args.models.lower() == 'all':
            options.selected_models = MARKDOWN_SAFE_MODELS.copy()
        elif args.models:
            try:
                selected_models = parse_model_selection(args.models)
            except ValueError as e:
                parser.error(str(e))
            invalid_models = [model for model in selected_models if model not in MARKDOWN_SAFE_MODELS]
            if invalid_models:
                parser.error("--from-md supports only models 1, 2, 5, and 6")
            options.selected_models = selected_models
        else:
            options.selected_models = MARKDOWN_SAFE_MODELS.copy()
    elif args.models and not args.validate:
        try:
            options.selected_models = parse_model_selection(args.models)
        except ValueError as e:
            parser.error(str(e))

    return options


def find_csv_files(resources_dir: Path) -> list:
    """
    Find all CSV files in the resources directory.
    
    Args:
        resources_dir: Path to resources directory
        
    Returns:
        List of CSV file paths sorted alphabetically
    """
    if not resources_dir.exists():
        return []
    
    csv_files = sorted(resources_dir.glob('*.csv'))
    return csv_files


def select_csv_file(resources_dir: Path) -> Path:
    """
    Let user select a CSV file if multiple files exist.
    
    Args:
        resources_dir: Path to resources directory
        
    Returns:
        Selected CSV file path
    """
    csv_files = find_csv_files(resources_dir)
    
    if not csv_files:
        logger.error("✗ No CSV files found in resources directory!")
        return None
    
    if len(csv_files) == 1:
        logger.info(f"✓ Using CSV file: {csv_files[0].name}")
        return csv_files[0]
    
    # Multiple CSV files - ask user to choose
    logger.info("\n" + "=" * 60)
    logger.info("Multiple CSV files found. Please select one:")
    logger.info("=" * 60)
    
    for idx, csv_file in enumerate(csv_files, 1):
        logger.info(f"{idx}. {csv_file.name}")
    
    while True:
        try:
            choice = input("\nEnter the number of your choice (1-{}): ".format(len(csv_files)))
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(csv_files):
                selected_file = csv_files[choice_num - 1]
                logger.info(f"✓ Selected: {selected_file.name}")
                return selected_file
            else:
                logger.warning(f"✗ Invalid choice. Please enter a number between 1 and {len(csv_files)}")
        except ValueError:
            logger.warning("✗ Invalid input. Please enter a number.")


def select_card_models() -> list:
    """
    Let user select which card models to use for generation.
    
    Returns:
        List of selected model numbers (1-5)
    """
    logger.info("\n" + "=" * 60)
    logger.info("Available card models:")
    logger.info("=" * 60)
    logger.info("1. EN→RU Typing")
    logger.info("2. RU→EN Typing")
    logger.info("3. EN→RU Choice")
    logger.info("4. RU→EN Choice")
    logger.info("5. RU→EN Scramble")
    logger.info("6. EN-RU Cloze")
    logger.info("7. All models")
    
    while True:
        try:
            choice = input("\nEnter model numbers separated by space (e.g., '1 3 5') or '7' for all: ").strip()
            
            if choice == "7":
                selected_models = [1, 2, 3, 4, 5, 6]
                logger.info(f"✓ Selected: All models (1, 2, 3, 4, 5, 6)")
                return selected_models
            
            # Parse individual numbers
            choices = [int(x) for x in choice.split()]
            
            # Validate choices
            if not choices:
                logger.warning("✗ No models selected. Please enter at least one number.")
                continue
            
            if not all(1 <= c <= 6 for c in choices):
                logger.warning("✗ Invalid choice. Please enter numbers between 1 and 6.")
                continue
            
            # Remove duplicates and sort
            selected_models = sorted(list(set(choices)))
            logger.info(f"✓ Selected models: {selected_models}")
            return selected_models
            
        except ValueError:
            logger.warning("✗ Invalid input. Please enter numbers separated by space.")


def load_cards_from_csv(csv_file_path: str) -> list:
    """
    Load flashcards from a CSV file.
    
    Args:
        csv_file_path: Path to the CSV file
        
    Returns:
        List of CardData objects
    """
    cards = []
    
    if not Path(csv_file_path).exists():
        logger.error(f"✗ File {csv_file_path} not found!")
        return cards
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Check for required columns
            required_columns = {
                'english', 'russian', 'example',
                'incorrectEnVariant1', 'incorrectEnVariant2', 
                'incorrectEnVariant3', 'incorrectEnVariant4',
                'incorrectRuVariant1', 'incorrectRuVariant2',
                'incorrectRuVariant3', 'incorrectRuVariant4'
            }
            
            if reader.fieldnames is None:
                logger.error("CSV file is empty or corrupted!")
                return cards
            
            # Tolerate stray spaces in header names
            reader.fieldnames = [name.strip() for name in reader.fieldnames]
            
            if not required_columns.issubset(set(reader.fieldnames)):
                missing = required_columns - set(reader.fieldnames)
                logger.error(f"Missing columns in CSV file: {missing}")
                return cards
            
            for idx, row in enumerate(reader, 1):
                try:
                    card = CardData(
                        english=row['english'].strip(),
                        russian=row['russian'].strip(),
                        example=row['example'].strip(),
                        incorrect_en=[
                            row['incorrectEnVariant1'].strip(),
                            row['incorrectEnVariant2'].strip(),
                            row['incorrectEnVariant3'].strip(),
                            row['incorrectEnVariant4'].strip(),
                        ],
                        incorrect_ru=[
                            row['incorrectRuVariant1'].strip(),
                            row['incorrectRuVariant2'].strip(),
                            row['incorrectRuVariant3'].strip(),
                            row['incorrectRuVariant4'].strip(),
                        ]
                    )
                    
                    # Data validation
                    if not card.english or not card.russian:
                        logger.warning(f"Row {idx}: skipped (missing english or russian word)")
                        continue
                    
                    cards.append(card)
                    
                except KeyError as e:
                    logger.warning(f"Row {idx}: error reading column {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Row {idx}: unexpected error {e}")
                    continue
        
        logger.info(f"✓ Successfully loaded {len(cards)} flashcards from {csv_file_path}")
        return cards
        
    except Exception as e:
        logger.error(f"✗ Error reading CSV file: {e}")
        return []


def example_audio_enabled(properties: dict) -> bool:
    """EXAMPLE_AUDIO=FALSE in config.properties disables example-sentence audio."""
    return properties.get('EXAMPLE_AUDIO', 'true').strip().lower() != 'false'


def derive_deck_id(source_stem: str) -> int:
    """Stable per-source deck ID so different inputs never merge on import."""
    return (zlib.crc32(source_stem.encode('utf-8')) % (1 << 30)) + (1 << 30)


def _report_csv_validation(csv_path: str) -> bool:
    """Run the validator and log its findings. Returns True when no errors."""
    report = validate_csv(csv_path)
    for warning in report.warnings:
        logger.warning(f"CSV: {warning}")
    for error in report.errors:
        logger.error(f"CSV: {error}")
    logger.info(f"CSV validation: {report.row_count} rows, "
                f"{len(report.errors)} errors, {len(report.warnings)} warnings")
    return report.ok


def _load_and_validate_markdown(markdown_path: Path):
    """Parse and validate a markdown note. Returns a CardData list or None on errors."""
    try:
        rows, structural_errors = load_rows_from_markdown(markdown_path)
    except MarkdownTableError as e:
        logger.error(f"Markdown: {e}")
        return None

    report = validate_word_entries(rows)
    for warning in report.warnings:
        logger.warning(f"Markdown: {warning}")
    for error in structural_errors + report.errors:
        logger.error(f"Markdown: {error}")
    total_errors = len(structural_errors) + len(report.errors)
    logger.info(f"Markdown validation: {report.row_count} rows, "
                f"{total_errors} errors, {len(report.warnings)} warnings")
    if total_errors:
        return None
    return [CardData(english, russian, example, [], [])
            for _line_num, english, russian, example in rows]


def _sync_learned_words_from_anki(ledger_path: Path, anki_url: str) -> None:
    """Best-effort: record words already mature in Anki as known."""
    from utils.card_generator import model_names_for_sync
    client = AnkiConnectClient(url=anki_url)
    try:
        words = fetch_mature_words(client, model_names_for_sync())
    except AnkiNotAvailableError:
        logger.info("Anki is not running - skipping learned-words sync")
        return
    except AnkiConnectError as e:
        logger.warning(f"AnkiConnect error during learned-words sync: {e}")
        return
    if words:
        added = record_word_list(ledger_path, sorted(words), 'anki')
        if added:
            logger.info(f"Known-words ledger: {added} mature word(s) pulled from Anki")


def validate_command(csv_path: Path = None, markdown_path: Path = None) -> bool:
    """--validate mode: check an input file and exit without generating a deck."""
    if markdown_path is not None:
        return _load_and_validate_markdown(markdown_path) is not None

    if csv_path is None:
        csv_path = select_csv_file(resources_dir())
        if not csv_path:
            return False
    return _report_csv_validation(str(csv_path))


def main(options: CliOptions = None):
    """Main function to generate Anki deck."""
    if options is None:
        options = CliOptions()
    
    logger.info("=" * 60)
    logger.info("Starting Anki Cards Generator")
    logger.info("=" * 60)
    
    # Load configuration
    try:
        # Find config in project root directory
        config_path = Path(__file__).parent.parent / 'config.properties'
        properties = load_properties(str(config_path))
    except Exception as e:
        logger.error(f"✗ Failed to load configuration: {e}")
        return False
    
    # Get parameters from config
    api_key = properties.get('API_KEY', '')
    cx = properties.get('CX', '')
    deck_id_override = properties.get('DECK_ID', '')
    deck_name = properties.get('DECK_NAME', 'Custom EN-RU Vocabulary Deck')
    anki_url = properties.get('ANKICONNECT_URL', 'http://127.0.0.1:8765')
    generate_example_audio = example_audio_enabled(properties)
    
    # Transform paths relative to project root directory
    root_path = project_root()
    csv_resources_dir = resources_dir()
    media_root_dir = root_path / 'media'
    
    selected_csv = None
    cards_data = None
    if options.markdown_path:
        source_name_no_ext = options.markdown_path.stem
        cards_data = _load_and_validate_markdown(options.markdown_path)
        if cards_data is None:
            logger.error("✗ Markdown validation failed. Fix the errors above and rerun.")
            return False
    else:
        # Select CSV file (let user choose if multiple exist)
        selected_csv = options.csv_path or select_csv_file(csv_resources_dir)
        if not selected_csv:
            logger.error("✗ No CSV file selected. Exiting.")
            return False

        # Validate CSV before the expensive media phase
        if not _report_csv_validation(str(selected_csv)):
            logger.error("✗ CSV validation failed. Fix the errors above and rerun.")
            return False

        source_name_no_ext = selected_csv.stem

    # Select card models to use
    selected_models = options.selected_models or select_card_models()
    if not selected_models:
        logger.error("✗ No models selected. Exiting.")
        return False
    
    # Deck ID: explicit config override wins, otherwise stable per-CSV ID
    deck_id = int(deck_id_override) if deck_id_override else derive_deck_id(source_name_no_ext)
    
    # Create media subdirectory for this input file
    media_dir = media_root_dir / source_name_no_ext
    media_dir.mkdir(parents=True, exist_ok=True)
    
    # Create results directory for output APKG files
    results_dir = root_path / 'results'
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Set output file name based on input file name
    output_file = results_dir / f"{source_name_no_ext}.apkg"
    
    # Hierarchical deck name: Anki builds a subdeck per CSV under the base name
    deck_name = f"{deck_name}::{source_name_no_ext}"
    
    logger.info(f"Media files will be saved to: {media_dir}")
    logger.info(f"Output file: {output_file}")
    logger.info(f"Card models to use: {len(selected_models)} model(s)")
    
    # Load flashcards from CSV
    if cards_data is None:
        cards_data = load_cards_from_csv(str(selected_csv))
    
    if not cards_data:
        logger.error("✗ No flashcards to process. Exiting.")
        return False
    
    # Known-words ledger: skip vocabulary already generated from other sources
    ledger_path = root_path / 'known_words.json'
    if not options.include_known:
        _sync_learned_words_from_anki(ledger_path, anki_url)
        ledger = load_known_words(ledger_path)
        cards_data, skipped_words = filter_known_words(cards_data, ledger, source_name_no_ext)
        if skipped_words:
            preview = ', '.join(skipped_words[:20])
            if len(skipped_words) > 20:
                preview += f" and {len(skipped_words) - 20} more"
            logger.info(f"Skipped {len(skipped_words)} known word(s): {preview}")
        if not cards_data:
            logger.error("✗ All words are already in the known-words ledger. "
                         "Use --include-known to regenerate them.")
            return False
    
    # Initialize media manager and card generator with selected models
    media_manager = MediaManager(
        media_dir=str(media_dir),
        api_key=api_key,
        cx=cx,
        offline=options.offline,
    )
    card_generator = CardGenerator(selected_models=selected_models)
    
    all_notes = []
    media_files = []
    
    logger.info(f"Processing {len(cards_data)} words...")
    
    # Process each word
    for idx, card_data in enumerate(cards_data, 1):
        try:
            logger.info(f"[{idx}/{len(cards_data)}] Processing: {card_data.english}")
            
            # Generate audio
            audio_path = media_manager.generate_audio(
                text=card_data.english,
                safe_filename=card_data.safe_filename
            )
            if audio_path:
                media_files.append(audio_path)
            
            # Example-sentence audio (second mp3, played on the back)
            example_audio_path = None
            if generate_example_audio and card_data.example:
                example_audio_path = media_manager.generate_audio(
                    text=card_data.example,
                    safe_filename=f"{card_data.safe_filename}_example",
                )
                if example_audio_path:
                    media_files.append(example_audio_path)
            
            # Download image
            image_path = media_manager.download_image(
                search_term=card_data.english,
                safe_filename=card_data.safe_filename
            )
            if image_path:
                media_files.append(image_path)
            
            # Create flashcards
            notes = card_generator.create_cards(
                card_data=card_data,
                audio_path=audio_path,
                image_path=image_path,
                example_audio_path=example_audio_path
            )
            
            if notes:
                all_notes.extend(notes)
            else:
                logger.warning(f"Failed to create flashcards for {card_data.english}")
                
        except Exception as e:
            logger.error(f"✗ Error processing word '{card_data.english}': {e}")
            continue
    
    if not all_notes:
        logger.error("✗ Failed to create any flashcards. Exiting.")
        return False
    
    # Shuffle flashcards
    logger.info(f"Shuffling {len(all_notes)} flashcards...")
    random.shuffle(all_notes)
    
    # Create deck
    try:
        deck = create_deck_from_cards(all_notes, deck_id, deck_name)
    except Exception as e:
        logger.error(f"✗ Failed to create deck: {e}")
        return False
    
    if options.push:
        # Push straight into the running Anki instead of writing a file
        try:
            client = AnkiConnectClient(url=anki_url)
            unique_models = {note.model.name: note.model for note in all_notes}
            created_models = ensure_models(client, unique_models.values())
            if created_models:
                logger.info(f"Created note types in Anki: {', '.join(created_models)}")
            ensure_deck(client, deck_name)
            stored, skipped = store_media(client, media_files,
                                          overwrite=options.overwrite_media)
            logger.info(f"Media pushed to Anki: {stored} stored, {skipped} already present")
            added, updated = push_notes(client, all_notes, deck_name)
            logger.info(f"✓ Pushed to Anki deck '{deck_name}': "
                        f"{added} added, {updated} updated")
            if trigger_sync(client):
                logger.info("AnkiWeb sync triggered")
            else:
                logger.warning("AnkiWeb sync failed - sync manually in Anki")
        except AnkiNotAvailableError as e:
            logger.error(f"✗ {e}")
            logger.error("Start Anki with the AnkiConnect add-on installed, "
                         "or rerun without --push to write an .apkg file.")
            return False
        except AnkiConnectError as e:
            logger.error(f"✗ AnkiConnect error: {e}")
            return False
    else:
        # Package into APKG file
        try:
            logger.info(f"Saving deck to {output_file}...")
            genanki.Package(deck, media_files).write_to_file(str(output_file))
            logger.info(f"✓ APKG file successfully created: {output_file}")
        except Exception as e:
            logger.error(f"✗ Error saving APKG file: {e}")
            return False
    
    # Record generated words into the ledger
    added_words = record_known_words(ledger_path, cards_data, source_name_no_ext)
    if added_words:
        logger.info(f"Known-words ledger: {added_words} new word(s) recorded")
    
    logger.info("=" * 60)
    logger.info("✓ Process completed successfully!")
    logger.info(f"  Total flashcards created: {len(all_notes)}")
    if options.push:
        logger.info(f"  Pushed to Anki deck: {deck_name}")
    else:
        logger.info(f"  File saved: {output_file}")
    logger.info(f"  Media directory: {media_dir}")
    logger.info("=" * 60)
    
    return True


def cli(argv: list = None) -> int:
    """Console-script entry point."""
    try:
        options = parse_args(argv)
        if options.validate_only:
            success = validate_command(options.csv_path, options.markdown_path)
        else:
            success = main(options)
        return 0 if success else 1
    except FileNotFoundError:
        return 1
    except KeyboardInterrupt:
        logger.info("\n⚠ Process interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
