import json
import os
from app.models.training import Training

DATA_FILE = os.path.join('data', 'training.json')

def load_trainings():
    """Loads training data from the JSON file."""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, 'r') as f:
            # Handle empty file case
            content = f.read()
            if not content:
                return []
            data = json.loads(content)
        return [Training.from_dict(item) for item in data]
    except (IOError, json.JSONDecodeError):
        # Handle file not found, not readable, or invalid JSON
        return []

def save_trainings(trainings):
    """Saves training data to the JSON file."""
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True) # Ensure directory exists
        with open(DATA_FILE, 'w') as f:
            json.dump([training.to_dict() for training in trainings], f, indent=4)
    except IOError:
        # Handle file not writable
        print(f"Error: Could not write to {DATA_FILE}") # Or raise an exception

def get_all_trainings():
    """Returns all training records."""
    return load_trainings()

def add_training(training_data):
    """Adds a new training record."""
    trainings = load_trainings()

    new_id = max([t.id for t in trainings if t.id is not None], default=0) + 1 if trainings else 1
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
        if training.id == training_id:
            return training
    return None

def update_training(training_id, training_data):
    """Updates an existing training record."""
    trainings = load_trainings()
    training_to_update_idx = -1

    for i, training in enumerate(trainings):
        if training.id == training_id:
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
        if getattr(current_training, 'id', None) != training_id :
             setattr(current_training, 'id', training_id) # Enforce consistency
        elif 'id' not in training_data or training_data['id'] is None:
            setattr(current_training, 'id', training_id)

        trainings[training_to_update_idx] = current_training
        save_trainings(trainings)
        return current_training
    return None

def delete_training(training_id):
    """Deletes a training record by its ID."""
    trainings = load_trainings()
    original_length = len(trainings)
    trainings = [training for training in trainings if training.id != training_id]

    if len(trainings) < original_length:
        save_trainings(trainings)
        return True
    return False
