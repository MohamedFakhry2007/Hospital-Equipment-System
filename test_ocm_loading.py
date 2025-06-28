"""
Test script to verify OCM data loading functionality.
"""
import sys
import os
import json
import logging
import traceback
from pathlib import Path
from typing import List, Dict, Any

# Set up logging
log_file = Path('test_ocm_loading.log')
if log_file.exists():
    log_file.unlink()  # Remove existing log file

logging.basicConfig(
    level=logging.DEBUG,  # More verbose logging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_ocm_loading.log')
    ]
)
logger = logging.getLogger(__name__)

def print_section(title: str, char: str = '='):
    """Print a section header for better log readability."""
    logger.info(f"\n{char * 10} {title} {char * 10}")

def test_ocm_loading() -> bool:
    """Test OCM data loading functionality."""
    try:
        # Add the project root to the Python path
        project_root = str(Path(__file__).parent.resolve())
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        print_section("Starting OCM Loading Test")
        logger.info(f"Python path: {sys.path}")
        
        # Import required modules
        from app import create_app
        from app.services.data_service import DataService
        from app.config import Config
        
        logger.info(f"OCM JSON path: {Config.OCM_JSON_PATH}")
        logger.info(f"File exists: {os.path.exists(Config.OCM_JSON_PATH)}")
        
        # Create app and push context
        app = create_app()
        
        with app.app_context():
            # Test 1: Load OCM data directly from file
            print_section("Test 1: Direct File Load")
            try:
                with open(Config.OCM_JSON_PATH, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                    logger.info(f"Directly loaded {len(file_data)} records from {Config.OCM_JSON_PATH}")
                    if file_data:
                        logger.info("Sample record from direct file load:")
                        logger.info(json.dumps(file_data[0], indent=2))
            except Exception as e:
                logger.error(f"Failed to load OCM file directly: {str(e)}")
                logger.error(traceback.format_exc())
            
            # Test 2: Load OCM data through DataService
            print_section("Test 2: DataService.load_data('ocm')")
            try:
                ocm_data = DataService.load_data('ocm')
                logger.info(f"Loaded {len(ocm_data)} OCM records")
                
                if not ocm_data:
                    logger.warning("No OCM data found. This might be expected if the database is empty.")
                else:
                    # Print first few records
                    logger.info("Sample OCM records (first 3):")
                    for i, record in enumerate(ocm_data[:3], 1):
                        logger.info(f"  {i}. SERIAL: {record.get('SERIAL', 'N/A')}")
                        logger.info(f"     Model: {record.get('MODEL', 'N/A')}")
                        logger.info(f"     Status: {record.get('STATUS', 'N/A')}")
            except Exception as e:
                logger.error(f"Error in DataService.load_data('ocm'): {str(e)}")
                logger.error(traceback.format_exc())
                return False
            
            # Test 3: Get all OCM entries
            print_section("Test 3: DataService.get_all_entries('ocm')")
            try:
                all_entries = DataService.get_all_entries('ocm')
                logger.info(f"Got {len(all_entries)} OCM entries via get_all_entries")
                
                if all_entries:
                    logger.info("Sample entry from get_all_entries:")
                    sample = all_entries[0]
                    for key, value in list(sample.items())[:5]:  # Show first 5 fields
                        logger.info(f"  {key}: {value}")
            except Exception as e:
                logger.error(f"Error in DataService.get_all_entries('ocm'): {str(e)}")
                logger.error(traceback.format_exc())
                return False
            
            logger.info("\n✅ OCM loading test completed successfully!")
            return True
            
    except Exception as e:
        logger.error(f"Unexpected error during OCM loading test: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function to run the test."""
    print("Starting OCM loading test...")
    print(f"Log file: {os.path.abspath('test_ocm_loading.log')}")
    
    if test_ocm_loading():
        print("✅ OCM loading test completed successfully!")
        sys.exit(0)
    else:
        print("❌ OCM loading test FAILED - check test_ocm_loading.log for details")
        sys.exit(1)

if __name__ == "__main__":
    main()
