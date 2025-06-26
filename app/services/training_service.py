import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.models.training import Training
from app.config import Config

logger = logging.getLogger(__name__)

DATA_FILE = Path(Config.DATA_DIR) / 'training.json'

def load_trainings() -> List[Training]:
    """
    Load training data from the JSON file.
    
    Returns:
        List[Training]: List of Training objects
    """
    if not DATA_FILE.exists():
        logger.info(f"Training data file not found: {DATA_FILE}")
        return []
        
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                logger.info("Training data file is empty")
                return []
                
            data = json.loads(content)
            if not isinstance(data, list):
                logger.error(f"Invalid training data format in {DATA_FILE}")
                return []
                
            logger.info(f"Successfully loaded {len(data)} training records from {DATA_FILE}")
            return [Training.from_dict(item) for item in data]
            
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {DATA_FILE}: {e}")
    except Exception as e:
        logger.error(f"Error loading training data from {DATA_FILE}: {e}")
        
    return []

def save_trainings(trainings: List[Training]) -> bool:
    """
    Save training data to the JSON file.
    
    Args:
        trainings: List of Training objects to save
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert Training objects to dicts
        data = [training.to_dict() for training in trainings]
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Successfully saved {len(trainings)} training records to {DATA_FILE}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving training data to {DATA_FILE}: {e}")
        return False

def get_all_trainings() -> List[Training]:
    """
    Get all training records.
    
    Returns:
        List[Training]: List of all training records
    """
    return load_trainings()

def add_training(training_data: Dict[str, Any]) -> Optional[Training]:
    """
    Add a new training record.
    
    Args:
        training_data: Dictionary containing training data
        
    Returns:
        Training: The created training record, or None if failed
    """
    try:
        trainings = load_trainings()
        
        # Generate new ID if not provided
        if 'id' not in training_data or not training_data['id']:
            # Find the highest existing ID and increment by 1
            existing_ids = [t.id for t in trainings if t.id is not None]
            new_id = max(existing_ids, default=0) + 1
            training_data['id'] = new_id
            
        # Ensure machine_trainer_assignments is a list
        if 'machine_trainer_assignments' not in training_data:
            training_data['machine_trainer_assignments'] = []
            
        # Create the training record
        training = Training.from_dict(training_data)
        trainings.append(training)
        
        if save_trainings(trainings):
            return training
            
    except Exception as e:
        logger.error(f"Error adding training record: {e}")
        
    return None

def get_training_by_id(training_id: int) -> Optional[Training]:
    """
    Get a training record by ID.
    
    Args:
        training_id: ID of the training record to retrieve
        
    Returns:
        Training: The requested training record, or None if not found
    """
    try:
        trainings = load_trainings()
        return next((t for t in trainings if t.id == training_id), None)
    except Exception as e:
        logger.error(f"Error getting training record {training_id}: {e}")
        return None

def update_training(training_id: int, training_data: Dict[str, Any]) -> Optional[Training]:
    """
    Update an existing training record.
    
    Args:
        training_id: ID of the training record to update
        training_data: Dictionary containing updated training data
        
    Returns:
        Training: The updated training record, or None if update failed
    """
    try:
        trainings = load_trainings()
        
        # Find the training record to update
        for i, training in enumerate(trainings):
            if training.id == training_id:
                # Update the training record with new data
                updated_data = training.to_dict()
                updated_data.update(training_data)
                updated_data['id'] = training_id  # Ensure ID doesn't change
                
                # Ensure machine_trainer_assignments is a list
                if 'machine_trainer_assignments' not in updated_data:
                    updated_data['machine_trainer_assignments'] = []
                
                # Update the training record
                trainings[i] = Training.from_dict(updated_data)
                
                if save_trainings(trainings):
                    return trainings[i]
                return None
                
        logger.warning(f"Training record with ID {training_id} not found")
        return None
        
    except Exception as e:
        logger.error(f"Error updating training record {training_id}: {e}")
        return None

def delete_training(training_id: int) -> bool:
    """
    Delete a training record by ID.
    
    Args:
        training_id: ID of the training record to delete
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        trainings = load_trainings()
        initial_count = len(trainings)
        
        # Filter out the training record with the given ID
        updated_trainings = [t for t in trainings if t.id != training_id]
        
        if len(updated_trainings) < initial_count:
            # Only save if a record was actually removed
            if save_trainings(updated_trainings):
                logger.info(f"Deleted training record with ID {training_id}")
                return True
            return False
            
        logger.warning(f"Training record with ID {training_id} not found for deletion")
        return False
        
    except Exception as e:
        logger.error(f"Error deleting training record {training_id}: {e}")
        return False
