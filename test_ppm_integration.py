"""
Test script to verify PPM service integration with the database.
"""
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.resolve())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_ppm_integration.log')
    ]
)
logger = logging.getLogger(__name__)

def test_ppm_integration():
    """Test PPM service integration with the database."""
    from app import create_app
    from app.services.data_service import DataService
    from app.services.ppm_service import PPMService
    
    logger.info("Starting PPM integration test...")
    
    # Create app and push context
    app = create_app()
    
    with app.app_context():
        try:
            # Test 1: Get all equipment
            logger.info("Test 1: Getting all PPM equipment...")
            all_equipment = PPMService.get_all_equipment()
            logger.info(f"Found {len(all_equipment)} PPM equipment records")
            
            if not all_equipment:
                logger.warning("No PPM equipment found in the database")
                return False
            
            # Test 2: Get a single equipment by serial
            test_serial = all_equipment[0].get('SERIAL')
            if test_serial:
                logger.info(f"Test 2: Getting equipment with SERIAL={test_serial}")
                equipment = PPMService.get_equipment_by_serial(test_serial)
                if equipment:
                    logger.info(f"Found equipment: {equipment.get('Name')} (SERIAL: {equipment.get('SERIAL')})")
                else:
                    logger.error(f"Failed to find equipment with SERIAL={test_serial}")
                    return False
            
            # Test 3: Add new equipment
            logger.info("Test 3: Adding new test equipment...")
            test_equipment = {
                'Department': 'TEST',
                'Name': 'Test Equipment',
                'MODEL': 'TEST-001',
                'SERIAL': 'TEST-12345',
                'MANUFACTURER': 'Test Manufacturer',
                'LOG_Number': 'TEST-001',
                'Status': 'Upcoming',
                'PPM_Q_I': {'status': 'Pending'},
                'PPM_Q_II': {'status': 'Pending'},
                'PPM_Q_III': {'status': 'Pending'},
                'PPM_Q_IV': {'status': 'Pending'}
            }
            
            # First, delete if it exists
            PPMService.delete_equipment('TEST-12345')
            
            # Add new
            new_equipment = PPMService.add_equipment(test_equipment)
            if new_equipment:
                logger.info(f"Successfully added test equipment: {new_equipment.get('SERIAL')}")
            else:
                logger.error("Failed to add test equipment")
                return False
            
            # Test 4: Update equipment
            logger.info("Test 4: Updating test equipment...")
            test_equipment['Name'] = 'Updated Test Equipment'
            updated = PPMService.update_equipment(test_equipment)
            if updated:
                logger.info("Successfully updated test equipment")
            else:
                logger.error("Failed to update test equipment")
                return False
            
            # Test 5: Delete test equipment
            logger.info("Test 5: Deleting test equipment...")
            deleted = PPMService.delete_equipment('TEST-12345')
            if deleted:
                logger.info("Successfully deleted test equipment")
            else:
                logger.error("Failed to delete test equipment")
                return False
            
            # Test 6: Test DataService integration
            logger.info("Test 6: Testing DataService integration...")
            ppm_data = DataService.load_data('ppm')
            logger.info(f"DataService returned {len(ppm_data)} PPM records")
            
            if len(ppm_data) != len(all_equipment):
                logger.warning(f"DataService returned {len(ppm_data)} records, expected {len(all_equipment)}")
            
            logger.info("All tests completed successfully!")
            return True
            
        except Exception as e:
            logger.exception("Error during PPM integration test")
            return False

if __name__ == "__main__":
    if test_ppm_integration():
        print("✅ PPM integration test PASSED")
        sys.exit(0)
    else:
        print("❌ PPM integration test FAILED - check logs for details")
        sys.exit(1)
