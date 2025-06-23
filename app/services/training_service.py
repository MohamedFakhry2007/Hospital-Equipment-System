import json
import os
from app.models.training import Training
from flask import current_app

def get_data_file_path():
    """Get the correct path to the training data file using Flask's root path."""
    try:
        # Use Flask's application root path
        return os.path.join(current_app.root_path, '..', 'data', 'training.json')
    except RuntimeError:
        # Fallback for when not in Flask context (e.g., during testing)
        return os.path.join('data', 'training.json')

def load_trainings():
    """Loads training data from the JSON file."""
    data_file = get_data_file_path()
    if not os.path.exists(data_file):
        print(f"Training data file not found: {data_file}")
        return []
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            # Handle empty file case
            content = f.read()
            if not content:
                return []
            data = json.loads(content)
        print(f"Successfully loaded {len(data)} training records from {data_file}")
        return [Training.from_dict(item) for item in data]
    except (IOError, json.JSONDecodeError) as e:
        # Handle file not found, not readable, or invalid JSON
        print(f"Error loading training data from {data_file}: {e}")
        return []

def save_trainings(trainings):
    """Saves training data to the JSON file."""
    data_file = get_data_file_path()
    try:
        os.makedirs(os.path.dirname(data_file), exist_ok=True) # Ensure directory exists
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump([training.to_dict() for training in trainings], f, indent=4, ensure_ascii=False)
        print(f"Successfully saved {len(trainings)} training records to {data_file}")
    except IOError as e:
        # Handle file not writable
        print(f"Error: Could not write to {data_file}: {e}") # Or raise an exception

def get_all_trainings():
    """Returns all training records."""
    return load_trainings()

def add_training(training_data):
    """Adds a new training record."""
    trainings = load_trainings()

    # Ensure we get integer IDs for proper comparison
    existing_ids = []
    for t in trainings:
        if t.id is not None:
            try:
                existing_ids.append(int(t.id))
            except (ValueError, TypeError):
                pass
    
    new_id = max(existing_ids, default=0) + 1 if existing_ids else 1
    training_data['id'] = new_id

    # The Training.from_dict method now handles the structure of 'machine_trainer_assignments'
    # and backward compatibility from 'trained_on_machines' and 'trainer'.
    # So, direct manipulation of 'trained_on_machines' or 'machine_trainer_assignments'
    # in training_data before calling from_dict is less critical here, assuming client sends correct new format.
    # If client sends 'machine_trainer_assignments', it should be a list of dicts.
    # If client sends old format, from_dict will handle it.

    new_training = Training.from_dict(training_data)
    trainings.append(new_training)
    save_trainings(trainings)
    return new_training

def get_training_by_id(training_id):
    """Retrieves a specific training record by its ID."""
    trainings = load_trainings()
    for training in trainings:
        # Handle both string and integer IDs for comparison
        try:
            if int(training.id) == int(training_id):
                return training
        except (ValueError, TypeError):
            # Fallback to string comparison if conversion fails
            if str(training.id) == str(training_id):
                return training
    return None

def update_training(training_id, training_data):
    """Updates an existing training record."""
    trainings = load_trainings()
    training_to_update_idx = -1

    for i, training in enumerate(trainings):
        # Handle both string and integer IDs for comparison
        try:
            if int(training.id) == int(training_id):
                training_to_update_idx = i
                break
        except (ValueError, TypeError):
            # Fallback to string comparison if conversion fails
            if str(training.id) == str(training_id):
                training_to_update_idx = i
                break

    if training_to_update_idx != -1:
        current_training = trainings[training_to_update_idx]
        # Update attributes from training_data
        for key, value in training_data.items():
            # The key 'trained_on_machines' is deprecated in favor of 'machine_trainer_assignments'.
            # The client should send 'machine_trainer_assignments' as a list of dicts.
            # No special conversion is needed here for 'machine_trainer_assignments' if client sends correct format.
            setattr(current_training, key, value)

        # Ensure 'id' is not accidentally overwritten by None from form if not present
        # Also, ensure the 'id' on the object matches the training_id from the URL parameter.
        try:
            current_id = int(getattr(current_training, 'id', None))
            expected_id = int(training_id)
            if current_id != expected_id:
                setattr(current_training, 'id', expected_id)
        except (ValueError, TypeError):
            # Fallback for non-numeric IDs
            if getattr(current_training, 'id', None) != training_id:
                setattr(current_training, 'id', training_id)
        
        if 'id' not in training_data or training_data['id'] is None:
            try:
                setattr(current_training, 'id', int(training_id))
            except (ValueError, TypeError):
                setattr(current_training, 'id', training_id)

        trainings[training_to_update_idx] = current_training
        save_trainings(trainings)
        return current_training
    return None

def delete_training(training_id):
    """Deletes a training record by its ID."""
    trainings = load_trainings()
    original_length = len(trainings)
    
    # Handle both string and integer IDs for comparison
    filtered_trainings = []
    for training in trainings:
        should_keep = True
        try:
            if int(training.id) == int(training_id):
                should_keep = False
        except (ValueError, TypeError):
            # Fallback to string comparison if conversion fails
            if str(training.id) == str(training_id):
                should_keep = False
        
        if should_keep:
            filtered_trainings.append(training)
    
    trainings = filtered_trainings

    if len(trainings) < original_length:
        save_trainings(trainings)
        return True
    return False
