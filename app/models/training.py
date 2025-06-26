class Training:
    def __init__(self, id, employee_id, name, department, machine_trainer_assignments, last_trained_date=None, next_due_date=None):
        self.id = id
        self.employee_id = employee_id
        self.name = name
        self.department = department
        # self.trainer = trainer # This field is removed.
        self.machine_trainer_assignments = machine_trainer_assignments # New structure: list of dicts
        self.last_trained_date = last_trained_date
        self.next_due_date = next_due_date

    def to_dict(self):
        # Ensure all fields are JSON serializable
        result = {
            "id": str(self.id) if self.id is not None else None,
            "employee_id": str(self.employee_id) if self.employee_id is not None else None,
            "name": str(self.name) if self.name is not None else None,
            "department": str(self.department) if self.department is not None else None,
            "machine_trainer_assignments": self.machine_trainer_assignments or [],
        }
        
        # Handle date fields
        if isinstance(self.last_trained_date, str):
            result["last_trained_date"] = self.last_trained_date
        elif self.last_trained_date is not None:
            result["last_trained_date"] = self.last_trained_date.isoformat() if hasattr(self.last_trained_date, 'isoformat') else str(self.last_trained_date)
            
        if isinstance(self.next_due_date, str):
            result["next_due_date"] = self.next_due_date
        elif self.next_due_date is not None:
            result["next_due_date"] = self.next_due_date.isoformat() if hasattr(self.next_due_date, 'isoformat') else str(self.next_due_date)
            
        return result

    @staticmethod
    def from_dict(data):
        training_id = data.get("id")

        machine_trainer_assignments = data.get("machine_trainer_assignments")

        # Backward compatibility: If new field is missing, try to convert from old fields
        if machine_trainer_assignments is None:
            machine_trainer_assignments = []
            old_trained_on_machines = data.get("trained_on_machines", [])
            # The old 'trainer' field was a single string, intended as a general trainer for all machines listed.
            # If new form sends individual trainers, this old field might not be present or relevant.
            # However, for purely old data, it might exist.
            old_general_trainer = data.get("trainer")

            if isinstance(old_trained_on_machines, str):
                old_trained_on_machines = [m.strip() for m in old_trained_on_machines.split(',') if m.strip()]

            if old_trained_on_machines:
                for machine_name in old_trained_on_machines:
                    # If an old_general_trainer was specified, use it. Otherwise, trainer for this machine is None.
                    machine_trainer_assignments.append({
                        "machine": machine_name,
                        "trainer": old_general_trainer if old_general_trainer else None
                    })

        # Ensure machine_trainer_assignments is a list, even if it came as null from JSON
        if machine_trainer_assignments is None:
            machine_trainer_assignments = []


        return Training(
            id=training_id,
            employee_id=data.get("employee_id"),
            name=data.get("name"),
            department=data.get("department"),
            machine_trainer_assignments=machine_trainer_assignments,
            last_trained_date=data.get("last_trained_date"),
            next_due_date=data.get("next_due_date")
        )