# app/constants.py

"""
Constants and static data for the Hospital Equipment System.
"""

# Department list for dropdowns
DEPARTMENTS = [
    "Cardiology",
    "Radiology", 
    "Emergency Department",
    "Intensive Care Unit (ICU)",
    "Operating Theater",
    "Laboratory",
    "Pharmacy",
    "Physiotherapy",
    "Dialysis Unit",
    "Oncology",
    "Pediatrics",
    "Maternity Ward",
    "Orthopedics",
    "Neurology",
    "General Surgery"
]

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

# Devices/Equipment list by department
DEVICES_BY_DEPARTMENT = {
    "Cardiology": [
        "ECG Machine",
        "Echocardiogram",
        "Cardiac Monitor",
        "Defibrillator",
        "Holter Monitor",
        "Stress Test Machine"
    ],
    "Radiology": [
        "X-Ray Machine",
        "CT Scanner",
        "MRI Scanner",
        "Ultrasound Machine",
        "Mammography Unit",
        "Fluoroscopy Machine"
    ],
    "Emergency Department": [
        "Defibrillator",
        "Ventilator",
        "Patient Monitor",
        "Crash Cart",
        "Suction Unit",
        "Infusion Pump"
    ],
    "Intensive Care Unit (ICU)": [
        "Ventilator",
        "Patient Monitor",
        "Infusion Pump",
        "Dialysis Machine",
        "ECMO Machine",
        "Defibrillator"
    ],
    "Operating Theater": [
        "Anesthesia Machine",
        "Surgical Monitor",
        "Electrosurgical Unit",
        "Operating Table",
        "Surgical Lights",
        "Suction Unit"
    ],
    "Laboratory": [
        "Centrifuge",
        "Microscope",
        "Analyzer",
        "Incubator",
        "Autoclave",
        "Spectrophotometer"
    ],
    "Pharmacy": [
        "Medication Dispenser",
        "Compounding Equipment",
        "Refrigeration Unit",
        "Scale",
        "Pill Counter",
        "Laminar Flow Hood"
    ],
    "Physiotherapy": [
        "Ultrasound Therapy Unit",
        "TENS Unit",
        "Exercise Equipment",
        "Heat Therapy Unit",
        "Electrical Stimulator",
        "Traction Unit"
    ],
    "Dialysis Unit": [
        "Dialysis Machine",
        "Water Treatment System",
        "Patient Monitor",
        "Blood Pressure Monitor",
        "Scale",
        "Infusion Pump"
    ],
    "Oncology": [
        "Linear Accelerator",
        "Chemotherapy Pump",
        "Patient Monitor",
        "Infusion Pump",
        "Radiation Monitor",
        "Treatment Planning System"
    ],
    "Pediatrics": [
        "Pediatric Monitor",
        "Infant Incubator",
        "Pediatric Ventilator",
        "Warming Unit",
        "Phototherapy Unit",
        "Pediatric Scale"
    ],
    "Maternity Ward": [
        "Fetal Monitor",
        "Delivery Bed",
        "Infant Warmer",
        "Ultrasound Machine",
        "Infusion Pump",
        "Patient Monitor"
    ],
    "Orthopedics": [
        "X-Ray Machine",
        "Bone Drill",
        "Surgical Table",
        "Traction Unit",
        "Bone Saw",
        "Arthroscopy Equipment"
    ],
    "Neurology": [
        "EEG Machine",
        "EMG Machine",
        "Nerve Conduction Unit",
        "Brain Monitor",
        "Neurostimulator",
        "Cranial Doppler"
    ],
    "General Surgery": [
        "Surgical Monitor",
        "Electrosurgical Unit",
        "Laparoscopy Equipment",
        "Surgical Table",
        "Anesthesia Machine",
        "Suction Unit"
    ]
}

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

