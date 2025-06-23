# app/constants.py

"""
Constants and static data for the Hospital Equipment System.
"""

import json
import os
from pathlib import Path
from typing import Dict, List

# Get the base directory (one level up from app/)
BASE_DIR = Path(__file__).resolve().parent.parent

def load_departments_and_machines() -> Dict[str, List[str]]:
    """Load departments and machines from JSON file."""
    json_file_path = os.path.join(BASE_DIR, "data", "departments_and_machines.json")
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: departments_and_machines.json not found at {json_file_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Warning: Error parsing departments_and_machines.json: {e}")
        return {}

# Load departments and machines data
DEPARTMENTS_AND_MACHINES = load_departments_and_machines()

# Create clean department names (strip trailing spaces) and mapping
DEPARTMENTS_RAW = list(DEPARTMENTS_AND_MACHINES.keys())
DEPARTMENTS = [dept.strip() for dept in DEPARTMENTS_RAW]  # Clean department names for dropdowns

# Create mapping from clean department names to original keys (with spaces)
DEPARTMENT_KEY_MAPPING = {dept.strip(): dept for dept in DEPARTMENTS_RAW}

# Training modules list
TRAINING_MODULES = [
    "Basic Equipment Operation",
    "Safety Protocols",
    "Maintenance Procedures", 
    "Emergency Response",
    "Quality Control",
    "Infection Control",
    "Equipment Calibration",
    "Documentation Standards",
    "Troubleshooting Techniques",
    "Advanced Equipment Features"
]

# Trainer names for machine assignment
TRAINERS = [
    "Marlene",
    "Aundre", 
    "Marivic",
    "Fevie",
    "Marily",
    "Ailene",
    "Mary joy",
    "Celina",
    "Jijimol",
    "Atma"
]

# Create clean devices by department mapping (using clean department names as keys)
DEVICES_BY_DEPARTMENT = {}
for clean_dept in DEPARTMENTS:
    original_key = DEPARTMENT_KEY_MAPPING[clean_dept]
    DEVICES_BY_DEPARTMENT[clean_dept] = DEPARTMENTS_AND_MACHINES[original_key]

# All devices (flattened list)
ALL_DEVICES = []
for devices in DEVICES_BY_DEPARTMENT.values():
    ALL_DEVICES.extend(devices)
ALL_DEVICES = sorted(list(set(ALL_DEVICES)))  # Remove duplicates and sort

# Status options for quarters
QUARTER_STATUS_OPTIONS = [
    "Pending",
    "In Progress", 
    "Completed",
    "Overdue",
    "Cancelled"
]

# General status options
GENERAL_STATUS_OPTIONS = [
    "Upcoming",
    "Overdue", 
    "Maintained"
]

