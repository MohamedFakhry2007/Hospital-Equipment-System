"""
Service for managing OCM (Other Corrective Maintenance) equipment data using SQLAlchemy.
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app import db
from app.models.ocm_equipment import OCMEquipment
from app.models.ocm import OCMEntry, OCMEntryCreate

logger = logging.getLogger(__name__)

class OCMService:
    """Service for managing OCM equipment data."""
    
    @staticmethod
    def get_all_equipment(
        page: int = 1,
        per_page: int = 20,
        search: str = '',
        status_filter: str = '',
        sort_by: str = '',
        sort_dir: str = 'asc'
    ) -> Dict[str, Any]:
        """
        Get paginated OCM equipment entries with filtering and sorting.
        
        Args:
            page: Page number (1-based)
            per_page: Number of items per page
            search: Search term to filter equipment by equipment name, model, or serial
            status_filter: Status to filter by (e.g., 'completed', 'pending', 'overdue')
            sort_by: Field to sort by
            sort_dir: Sort direction ('asc' or 'desc')
            
        Returns:
            Dict containing items, total count, and pagination info
        """
        try:
            from sqlalchemy import or_, and_, func, extract
            from datetime import datetime, date, timedelta
            
            logger.info(f"Fetching OCM equipment - page: {page}, per_page: {per_page}, search: '{search}', status_filter: '{status_filter}', sort_by: '{sort_by}', sort_dir: '{sort_dir}'")
            
            # Log the total count of records in the table
            total_count = OCMEquipment.query.count()
            logger.info(f"Total OCM equipment records in database: {total_count}")
            
            query = OCMEquipment.query
            
            # Apply search filter
            if search:
                search_filter = or_(
                    OCMEquipment.name.ilike(f'%{search}%'),
                    OCMEquipment.model.ilike(f'%{search}%'),
                    OCMEquipment.serial.ilike(f'%{search}%'),
                    OCMEquipment.department.ilike(f'%{search}%'),
                    OCMEquipment.manufacturer.ilike(f'%{search}%')
                )
                query = query.filter(search_filter)
            
            # Apply status filter
            if status_filter:
                today = date.today()
                
                if status_filter.lower() == 'completed':
                    # Equipment with maintenance completed
                    query = query.filter(
                        OCMEquipment.status.ilike('%completed%') | 
                        OCMEquipment.status.ilike('%done%') |
                        OCMEquipment.status.ilike('%maintained%')
                    )
                elif status_filter.lower() == 'pending':
                    # Equipment with pending maintenance
                    query = query.filter(
                        OCMEquipment.status.ilike('%pending%') |
                        OCMEquipment.status.ilike('%in progress%') |
                        OCMEquipment.status.ilike('%upcoming%')
                    )
                elif status_filter.lower() == 'overdue':
                    # Equipment with overdue maintenance
                    query = query.filter(
                        OCMEquipment.next_maintenance.isnot(None),
                        OCMEquipment.next_maintenance < today,
                        ~OCMEquipment.status.ilike('%completed%'),
                        ~OCMEquipment.status.ilike('%done%'),
                        ~OCMEquipment.status.ilike('%maintained%')
                    )
            
            # Apply sorting
            if sort_by:
                sort_column = None
                
                # Map sort_by to actual model columns
                sort_mapping = {
                    'name': OCMEquipment.name,
                    'model': OCMEquipment.model,
                    'serial': OCMEquipment.serial,
                    'department': OCMEquipment.department,
                    'manufacturer': OCMEquipment.manufacturer,
                    'service_date': OCMEquipment.service_date,
                    'next_maintenance': OCMEquipment.next_maintenance,
                    'status': OCMEquipment.status,
                    'no': OCMEquipment.no
                }
                
                sort_column = sort_mapping.get(sort_by.lower())
                
                if sort_column is not None:
                    if sort_dir.lower() == 'desc':
                        sort_column = sort_column.desc()
                    query = query.order_by(sort_column)
            else:
                # Default sorting by no (original order)
                query = query.order_by(OCMEquipment.no.asc())
            
            # Get pagination object
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            
            # Log pagination info
            logger.info(f"Pagination info - page: {page}, items: {len(pagination.items)}, total: {pagination.total}, pages: {pagination.pages}")
            
            # Log the first item (if any) to verify data structure
            if pagination.items:
                first_item = pagination.items[0]
                logger.info(f"First item data: {first_item.to_dict()}")
            
            result = {
                'items': [eq.to_dict() for eq in pagination.items],
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page,
                'per_page': per_page,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
                'next_page': page + 1 if pagination.has_next else None,
                'prev_page': page - 1 if pagination.has_prev else None
            }
            
            logger.info(f"Returning {len(result['items'])} items")
            return result
            
        except SQLAlchemyError as e:
            error_msg = f"Error fetching paginated OCM equipment: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result = {
                'items': [],
                'total': 0,
                'pages': 0,
                'current_page': page,
                'per_page': per_page,
                'has_next': False,
                'has_prev': False,
                'next_page': None,
                'prev_page': None,
                'error': error_msg
            }
            logger.error(f"Returning error result: {result}")
            return result
    
    @staticmethod
    def get_equipment_by_serial(serial: str) -> Optional[Dict[str, Any]]:
        """Get a single OCM equipment entry by serial number."""
        try:
            equipment = OCMEquipment.query.filter_by(serial=serial).first()
            return equipment.to_dict() if equipment else None
        except SQLAlchemyError as e:
            logger.error(f"Error fetching OCM equipment {serial}: {str(e)}")
            return None
    
    @staticmethod
    def parse_date(date_str):
        """
        Parse a date string into a date object.
        
        Args:
            date_str: Date string in DD/MM/YYYY or YYYY-MM-DD format
            
        Returns:
            date object or None if parsing fails
        """
        if not date_str or date_str == 'N/A':
            return None
        try:
            # Try DD/MM/YYYY format first
            return datetime.strptime(date_str, '%d/%m/%Y').date()
        except (ValueError, TypeError):
            try:
                # Fallback to YYYY-MM-DD format
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return None
                
    @staticmethod
    def add_equipment(equipment_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Add a new OCM equipment entry.
        
        Args:
            equipment_data: Dictionary containing equipment data
            
        Returns:
            Tuple of (equipment_dict, error_message)
        """
        try:
            # Generate a default serial if not provided
            if not equipment_data.get('SERIAL') or not str(equipment_data['SERIAL']).strip():
                # Create a unique identifier based on other fields
                import hashlib
                from datetime import datetime
                unique_str = f"{equipment_data.get('EQUIPMENT', '')}-{equipment_data.get('MODEL', '')}-{datetime.utcnow().timestamp()}"
                equipment_data['SERIAL'] = f"OCM-{hashlib.md5(unique_str.encode()).hexdigest()[:8].upper()}"
                logger.warning(f"Generated default serial number: {equipment_data['SERIAL']}")
                
            # Check if equipment with this serial already exists
            if OCMEquipment.query.filter_by(serial=equipment_data.get('SERIAL', '')).first():
                error_msg = f"Equipment with serial {equipment_data.get('SERIAL')} already exists"
                logger.warning(error_msg)
                return None, error_msg
                
            # Create a new OCM entry using the Pydantic model for validation
            try:
                # Ensure we have a valid name with fallback strategy
                name = equipment_data.get('Name', '')
                if not name or name.upper() == 'N/A':
                    name = equipment_data.get('EQUIPMENT', '')
                if not name or name.upper() == 'N/A':
                    model = equipment_data.get('Model', 'Equipment')
                    serial = equipment_data.get('SERIAL', 'No Serial')
                    name = f"{model} - {serial}"
                    
                # Map the incoming data to match OCMEntryCreate model
                entry_data = {
                    'EQUIPMENT': name,  # Use the derived name
                    'Name': name,  # Also set Name for the Pydantic model
                    'MODEL': equipment_data.get('Model', ''),
                    'SERIAL': equipment_data.get('SERIAL', ''),
                    'MANUFACTURER': equipment_data.get('Manufacturer', 'Unknown Manufacturer'),
                    'Department': equipment_data.get('Department', 'UNKNOWN'),
                    'LOG_NO': equipment_data.get('Log_Number', ''),
                    'Installation_Date': equipment_data.get('Installation_Date', ''),
                    'Warranty_End': equipment_data.get('Warranty_End', ''),
                    'Service_Date': equipment_data.get('Service_Date', ''),
                    'ENGINEER': equipment_data.get('Engineer', 'Technician'),
                    'Next_Maintenance': equipment_data.get('Next_Maintenance', ''),
                    'Status': equipment_data.get('Status', 'Upcoming'),
                    'PPM': equipment_data.get('PPM', '')
                }
                
                # Validate the data using Pydantic model
                validated_data = OCMEntryCreate(**entry_data).model_dump()
                
                # Create equipment from validated data
                equipment = OCMEquipment()
                equipment.no = equipment_data.get('NO', 0) or 0
                equipment.department = validated_data.get('Department', '')
                equipment.name = validated_data.get('Name', '')
                equipment.model = validated_data.get('MODEL', '')
                equipment.serial = validated_data.get('SERIAL', '')
                equipment.manufacturer = validated_data.get('MANUFACTURER', '')
                equipment.log_number = validated_data.get('LOG_NO', '')
                
                # Convert date strings to date objects for SQLAlchemy
                equipment.installation_date = OCMService.parse_date(validated_data.get('Installation_Date'))
                equipment.warranty_end = OCMService.parse_date(validated_data.get('Warranty_End'))
                equipment.service_date = OCMService.parse_date(validated_data.get('Service_Date'))
                equipment.next_maintenance = OCMService.parse_date(validated_data.get('Next_Maintenance'))
                
                equipment.engineer = validated_data.get('ENGINEER', '')
                equipment.status = validated_data.get('Status', 'Upcoming')
                
                db.session.add(equipment)
                db.session.commit()
                
                return equipment.to_dict(), None
                
            except Exception as e:
                db.session.rollback()
                error_msg = f"Validation error: {str(e)}"
                logger.error(error_msg)
                return None, error_msg
                
        except IntegrityError as e:
            db.session.rollback()
            error_msg = f"Database integrity error: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
            
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return None, error_msg
    
    @staticmethod
    def update_equipment(serial: str, update_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Update an existing OCM equipment entry.
        
        Args:
            serial: Current serial number of the equipment
            update_data: Dictionary containing updated data
            
        Returns:
            Tuple of (updated_equipment_dict, error_message)
        """
        try:
            equipment = OCMEquipment.query.filter_by(serial=serial).first()
            if not equipment:
                error_msg = f"OCM equipment with serial {serial} not found"
                logger.warning(error_msg)
                return None, error_msg
                
            # If serial is being updated, check if new serial already exists
            new_serial = update_data.get('SERIAL')
            if new_serial and new_serial != serial:
                if OCMEquipment.query.filter_by(serial=new_serial).first():
                    error_msg = f"Equipment with serial {new_serial} already exists"
                    logger.warning(error_msg)
                    return None, error_msg
            
            # Map the update data to match the expected format
            mapped_data = {}
            field_mapping = {
                'Name': 'name',
                'MODEL': 'model',
                'SERIAL': 'serial',
                'MANUFACTURER': 'manufacturer',
                'Department': 'department',
                'LOG_NO': 'log_number',
                'Installation_Date': 'installation_date',
                'Warranty_End': 'warranty_end',
                'Service_Date': 'service_date',
                'ENGINEER': 'engineer',
                'Next_Maintenance': 'next_maintenance',
                'Status': 'status',
                'PPM': 'ppm'
            }
            
            # Map the update data to the correct field names
            for key, value in update_data.items():
                if key in field_mapping and hasattr(equipment, field_mapping[key]):
                    mapped_data[field_mapping[key]] = value
            
            # Update non-date fields
            for key, value in mapped_data.items():
                if key not in ['installation_date', 'warranty_end', 'service_date', 'next_maintenance']:
                    setattr(equipment, key, value)
            
            # Update date fields with proper conversion
            if 'installation_date' in mapped_data:
                equipment.installation_date = OCMService.parse_date(mapped_data['installation_date'])
            if 'warranty_end' in mapped_data:
                equipment.warranty_end = OCMService.parse_date(mapped_data['warranty_end'])
            if 'service_date' in mapped_data:
                equipment.service_date = OCMService.parse_date(mapped_data['service_date'])
            if 'next_maintenance' in mapped_data:
                equipment.next_maintenance = OCMService.parse_date(mapped_data['next_maintenance'])
            
            equipment.updated_at = datetime.utcnow()
            db.session.commit()
            
            return equipment.to_dict(), None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error updating equipment {serial}: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Unexpected error updating equipment {serial}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return None, error_msg
    
    @staticmethod
    def delete_equipment(serial: str) -> Tuple[bool, Optional[str]]:
        """
        Delete an OCM equipment entry.
        
        Args:
            serial: Serial number of the equipment to delete
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            equipment = OCMEquipment.query.filter_by(serial=serial).first()
            if not equipment:
                error_msg = f"OCM equipment with serial {serial} not found"
                logger.warning(error_msg)
                return False, error_msg
                
            db.session.delete(equipment)
            db.session.commit()
            return True, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error deleting equipment {serial}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Unexpected error deleting equipment {serial}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    @staticmethod
    def bulk_import_equipment(equipment_list: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Bulk import OCM equipment entries.
        
        Args:
            equipment_list: List of equipment dictionaries to import
            
        Returns:
            Dictionary with import statistics
        """
        stats = {
            'total': len(equipment_list),
            'imported': 0,
            'updated': 0,
            'errors': 0,
            'error_messages': []
        }
        
        for idx, item in enumerate(equipment_list, 1):
            try:
                # Skip if no serial number
                if not item.get('SERIAL'):
                    error_msg = f"Row {idx}: Missing SERIAL"
                    stats['error_messages'].append(error_msg)
                    stats['errors'] += 1
                    continue
                
                # Check if equipment with this serial already exists
                existing = OCMEquipment.query.filter_by(serial=item['SERIAL']).first()
                
                if existing:
                    # Update existing
                    _, error = OCMService.update_equipment(item['SERIAL'], item)
                    if error:
                        stats['error_messages'].append(f"Row {idx} (SERIAL: {item['SERIAL']}): {error}")
                        stats['errors'] += 1
                    else:
                        stats['updated'] += 1
                else:
                    # Add new
                    _, error = OCMService.add_equipment(item)
                    if error:
                        stats['error_messages'].append(f"Row {idx} (SERIAL: {item['SERIAL']}): {error}")
                        stats['errors'] += 1
                    else:
                        stats['imported'] += 1
                        
            except Exception as e:
                error_msg = f"Row {idx} (SERIAL: {item.get('SERIAL', 'N/A')}): {str(e)}"
                stats['error_messages'].append(error_msg)
                stats['errors'] += 1
                logger.error(f"Error in bulk import: {error_msg}", exc_info=True)
        
        return stats
