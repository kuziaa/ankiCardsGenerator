#!/usr/bin/env python3
"""
Anki Cards Generator - Generate flashcards for learning English vocabulary

This script creates an Anki deck with flashcards from a CSV file, including:
- Audio generation for each word
- Image downloading via Google Custom Search
- Creation of 5 types of flashcards (typing, choice, scramble)
"""

import csv
import random
import sys
from pathlib import Path

import genanki

from utils.logger import setup_logger
from utils.properties_util import load_properties
from utils.media_manager import MediaManager
from utils.card_generator import CardGenerator, CardData, create_deck_from_cards

# Initialize logger
logger = setup_logger(__name__)


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
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
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


def main():
    """Main function to generate Anki deck."""
    
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
    deck_id = int(properties.get('DECK_ID', '999004'))
    deck_name = properties.get('DECK_NAME', 'Custom EN-RU Vocabulary Deck')
    
    # Transform paths relative to project root directory
    root_path = Path(__file__).parent.parent
    csv_file_path = root_path / properties.get('CSV_FILE_PATH', 'src/resources/cards.csv')
    media_dir = root_path / properties.get('MEDIA_DIR', 'media')
    output_file = root_path / properties.get('OUTPUT_FILE', 'vocabulary.apkg')
    
    # Load flashcards from CSV
    cards_data = load_cards_from_csv(str(csv_file_path))
    
    if not cards_data:
        logger.error("✗ No flashcards to process. Exiting.")
        return False
    
    # Initialize media manager and card generator
    media_manager = MediaManager(media_dir=str(media_dir), api_key=api_key, cx=cx)
    card_generator = CardGenerator()
    
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
                image_path=image_path
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
    
    # Package into APKG file
    try:
        logger.info(f"Saving deck to {output_file}...")
        genanki.Package(deck, media_files).write_to_file(str(output_file))
        logger.info(f"✓ APKG file successfully created: {output_file}")
    except Exception as e:
        logger.error(f"✗ Error saving APKG file: {e}")
        return False
    
    logger.info("=" * 60)
    logger.info("✓ Process completed successfully!")
    logger.info(f"  Total flashcards created: {len(all_notes)}")
    logger.info(f"  File saved: {output_file}")
    logger.info("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
