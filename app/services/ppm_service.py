"""
Service for managing PPM (Planned Preventive Maintenance) equipment data using SQLAlchemy.
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional

from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.models.ppm_equipment import PPMEquipment

logger = logging.getLogger(__name__)

class PPMService:
    """Service for managing PPM equipment data."""
    
    @staticmethod
    def get_all_equipment(
        page: int = 1,
        per_page: int = 20,
        search: str = '',
        status_filter: str = '',
        sort_by: str = '',
        sort_dir: str = 'asc'
    ) -> Dict:
        """
        Get paginated PPM equipment entries with filtering and sorting.
        
        Args:
            page: Page number (1-based)
            per_page: Number of items per page
            search: Search term to filter equipment by name, model, or serial
            status_filter: Status to filter by (e.g., 'completed', 'pending', 'overdue')
            sort_by: Field to sort by
            sort_dir: Sort direction ('asc' or 'desc')
            
        Returns:
            Dict containing items, total count, and pagination info
        """
        try:
            from sqlalchemy import or_, and_, func, extract
            from datetime import datetime, date, timedelta
            
            query = PPMEquipment.query
            
            # Apply search filter
            if search:
                search_filter = or_(
                    PPMEquipment.name.ilike(f'%{search}%'),
                    PPMEquipment.model.ilike(f'%{search}%'),
                    PPMEquipment.serial.ilike(f'%{search}%'),
                    PPMEquipment.location.ilike(f'%{search}%')
                )
                query = query.filter(search_filter)
            
            # Apply status filter
            if status_filter:
                today = date.today()
                
                if status_filter.lower() == 'completed':
                    # Equipment with maintenance completed in the current quarter
                    query = query.filter(
                        PPMEquipment.last_maintenance_date.isnot(None),
                        extract('quarter', PPMEquipment.last_maintenance_date) == (today.month - 1) // 3 + 1,
                        extract('year', PPMEquipment.last_maintenance_date) == today.year
                    )
                elif status_filter.lower() == 'pending':
                    # Equipment with upcoming maintenance in the current quarter
                    query = query.filter(
                        PPMEquipment.next_maintenance_date.isnot(None),
                        PPMEquipment.next_maintenance_date >= today,
                        PPMEquipment.next_maintenance_date <= today + timedelta(days=30)  # Next 30 days
                    )
                elif status_filter.lower() == 'overdue':
                    # Equipment with overdue maintenance
                    query = query.filter(
                        PPMEquipment.next_maintenance_date.isnot(None),
                        PPMEquipment.next_maintenance_date < today
                    )
            
            # Apply sorting
            if sort_by:
                sort_column = None
                
                # Map sort_by to actual model columns
                sort_mapping = {
                    'name': PPMEquipment.name,
                    'model': PPMEquipment.model,
                    'serial': PPMEquipment.serial,
                    'location': PPMEquipment.location,
                    'last_maintenance_date': PPMEquipment.last_maintenance_date,
                    'next_maintenance_date': PPMEquipment.next_maintenance_date,
                    'status': PPMEquipment.status
                }
                
                sort_column = sort_mapping.get(sort_by.lower())
                
                if sort_column is not None:
                    if sort_dir.lower() == 'desc':
                        sort_column = sort_column.desc()
                    query = query.order_by(sort_column)
            else:
                # Default sorting by name
                query = query.order_by(PPMEquipment.name.asc())
            
            # Get pagination object
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            
            return {
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
            
        except SQLAlchemyError as e:
            logger.error(f"Error fetching paginated equipment: {str(e)}", exc_info=True)
            return {
                'items': [],
                'total': 0,
                'pages': 0,
                'current_page': page,
                'per_page': per_page,
                'has_next': False,
                'has_prev': False,
                'next_page': None,
                'prev_page': None
            }
    
    @staticmethod
    def get_equipment_by_serial(serial: str) -> Optional[Dict]:
        """Get a single PPM equipment entry by serial number."""
        try:
            equipment = PPMEquipment.query.filter_by(serial=serial).first()
            return equipment.to_dict() if equipment else None
        except SQLAlchemyError as e:
            logger.error(f"Error fetching equipment {serial}: {str(e)}")
            return None
    
    @staticmethod
    def add_equipment(equipment_data: Dict) -> Optional[Dict]:
        """Add a new PPM equipment entry."""
        try:
            # Check if equipment with this serial already exists
            if PPMEquipment.query.filter_by(serial=equipment_data.get('SERIAL')).first():
                logger.warning(f"Equipment with serial {equipment_data.get('SERIAL')} already exists")
                return None
                
            equipment = PPMEquipment.from_dict(equipment_data)
            db.session.add(equipment)
            db.session.commit()
            return equipment.to_dict()
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error adding equipment: {str(e)}")
            return None
    
    @staticmethod
    def update_equipment(serial: str, update_data: Dict) -> Optional[Dict]:
        """Update an existing PPM equipment entry."""
        try:
            equipment = PPMEquipment.query.filter_by(serial=serial).first()
            if not equipment:
                logger.warning(f"Equipment with serial {serial} not found")
                return None
                
            # Update fields from update_data
            for key, value in update_data.items():
                if key == 'SERIAL' and value != serial:
                    # Check if new serial already exists
                    if PPMEquipment.query.filter_by(serial=value).first():
                        logger.warning(f"Equipment with serial {value} already exists")
                        return None
                setattr(equipment, key.lower(), value)
                
            equipment.updated_at = datetime.utcnow()
            db.session.commit()
            return equipment.to_dict()
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error updating equipment {serial}: {str(e)}")
            return None
    
    @staticmethod
    def delete_equipment(serial: str) -> bool:
        """Delete a PPM equipment entry."""
        try:
            equipment = PPMEquipment.query.filter_by(serial=serial).first()
            if not equipment:
                logger.warning(f"Equipment with serial {serial} not found")
                return False
                
            db.session.delete(equipment)
            db.session.commit()
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error deleting equipment {serial}: {str(e)}")
            return False
    
    @staticmethod
    def bulk_import_equipment(equipment_list: List[Dict]) -> Dict[str, int]:
        """Bulk import PPM equipment entries."""
        success_count = 0
        error_count = 0
        
        for equipment_data in equipment_list:
            try:
                # Check if equipment with this serial already exists
                if PPMEquipment.query.filter_by(serial=equipment_data.get('SERIAL')).first():
                    logger.warning(f"Equipment with serial {equipment_data.get('SERIAL')} already exists, skipping")
                    error_count += 1
                    continue
                    
                equipment = PPMEquipment.from_dict(equipment_data)
                db.session.add(equipment)
                success_count += 1
            except Exception as e:
                logger.error(f"Error importing equipment {equipment_data.get('SERIAL')}: {str(e)}")
                error_count += 1
        
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error committing bulk import: {str(e)}")
            return {"success": 0, "errors": len(equipment_list), "message": str(e)}
        
        return {
            "success": success_count,
            "errors": error_count,
            "message": f"Successfully imported {success_count} entries, {error_count} errors"
        }
    
    @staticmethod
    def update_ppm_statuses() -> Dict[str, int]:
        """Update status for all PPM equipment based on maintenance dates."""
        try:
            from datetime import date
            
            today = date.today()
            updated_count = 0
            
            # Get all equipment
            all_equipment = PPMEquipment.query.all()
            
            for equipment in all_equipment:
                status_changed = False
                
                # Check each quarter
                for q in ['q1', 'q2', 'q3', 'q4']:
                    date_attr = f'ppm_{q}_date'
                    status_attr = f'ppm_{q}_status'
                    
                    due_date = getattr(equipment, date_attr, None)
                    if not due_date:
                        continue
                    
                    # Calculate days until due
                    days_until_due = (due_date - today).days
                    
                    # Determine status
                    new_status = None
                    if days_until_due > 30:
                        new_status = "Upcoming"
                    elif days_until_due > 0:
                        new_status = "Due Soon"
                    else:
                        new_status = "Overdue"
                    
                    # Update if status changed
                    current_status = getattr(equipment, status_attr)
                    if current_status != new_status:
                        setattr(equipment, status_attr, new_status)
                        status_changed = True
                
                # Update overall status if any quarter status changed
                if status_changed:
                    # Determine overall status (most critical status)
                    statuses = [
                        getattr(equipment, f'ppm_q{i}_status') 
                        for i in range(1, 5) 
                        if getattr(equipment, f'ppm_q{i}_status')
                    ]
                    
                    if statuses:
                        if "Overdue" in statuses:
                            equipment.status = "Overdue"
                        elif "Due Soon" in statuses:
                            equipment.status = "Due Soon"
                        else:
                            equipment.status = "Upcoming"
                    
                    updated_count += 1
            
            if updated_count > 0:
                db.session.commit()
            
            return {"status": "success", "updated_count": updated_count}
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating PPM statuses: {str(e)}")
            return {"status": "error", "message": str(e)}
