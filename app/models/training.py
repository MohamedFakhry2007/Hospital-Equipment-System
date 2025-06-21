class Training:
    def __init__(self, id, employee_id, name, department, trainer, trained_on_machines, last_trained_date=None, next_due_date=None):
        self.id = id
        self.employee_id = employee_id
        self.name = name
        self.department = department
        self.trainer = trainer
        self.trained_on_machines = trained_on_machines # Expected to be a list of strings
        self.last_trained_date = last_trained_date
        self.next_due_date = next_due_date

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "name": self.name,
            "department": self.department,
            "trainer": self.trainer,
            "trained_on_machines": self.trained_on_machines,
            "last_trained_date": self.last_trained_date,
            "next_due_date": self.next_due_date
        }

    @staticmethod
    def from_dict(data):
        # Ensure 'id' is handled correctly, especially if it might be missing for new entries before saving
        training_id = data.get("id")
        # If 'trained_on_machines' is a string, convert it to a list
        trained_on_machines = data.get("trained_on_machines", [])
        if isinstance(trained_on_machines, str):
            trained_on_machines = [m.strip() for m in trained_on_machines.split(',') if m.strip()]

        return Training(
            id=training_id,
            employee_id=data.get("employee_id"),
            name=data.get("name"),
            department=data.get("department"),
            trainer=data.get("trainer"),
            trained_on_machines=trained_on_machines,
            last_trained_date=data.get("last_trained_date"),
            next_due_date=data.get("next_due_date")
        )
