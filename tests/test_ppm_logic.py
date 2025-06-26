import unittest
from unittest.mock import patch, MagicMock
from flask import Flask, request
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Assuming views.py is modified to have calculate_next_quarter_date accessible
# or we test the effect via add_ppm_equipment
from app.routes.views import add_ppm_equipment
from app.services.data_service import DataService
# from app.services.data_service import DataService # To mock, but we patch its usage in views

class TestPPMDateLogic(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'super secret key'  # Needed for flash messages, though not directly tested here

        # Patch DataService.add_entry where it's used in app.routes.views
        self.data_service_patch = patch('app.routes.views.DataService.add_entry')
        self.mock_add_entry = self.data_service_patch.start()
        self.addCleanup(self.data_service_patch.stop)

        # Patch redirect and render_template where they are used in app.routes.views
        self.redirect_patch = patch('app.routes.views.redirect')
        self.mock_redirect = self.redirect_patch.start()
        self.mock_redirect.return_value = "Redirected"  # Dummy response
        self.addCleanup(self.redirect_patch.stop)

        self.render_template_patch = patch('app.routes.views.render_template')
        self.mock_render_template = self.render_template_patch.start()
        self.mock_render_template.return_value = "Rendered Template" # Dummy response
        self.addCleanup(self.render_template_patch.stop)

    def test_add_ppm_with_q1_date(self):
        form_data_with_q1 = {
            "MODEL": "TestModel",
            "Name": "TestPPM",
            "SERIAL": "TestSerial123",
            "MANUFACTURER": "TestManu",
            "Department": "TestDept",
            "LOG_Number": "TestLog",
            "Installation_Date": "01/01/2024",
            "Warranty_End": "01/01/2025",
            "PPM_Q_I_date": "15/01/2024", # Q1 Date
            "PPM_Q_I_engineer": "Engineer1",
            "PPM_Q_II_engineer": "Engineer2",
            "PPM_Q_III_engineer": "Engineer3",
            "PPM_Q_IV_engineer": "Engineer4",
            # Status is set by the route, not from form directly for new entries
        }
        with self.app.test_request_context('/equipment/ppm/add', method='POST', data=form_data_with_q1):
            # Call the route function
            add_ppm_equipment()

            self.mock_add_entry.assert_called_once()
            # The first argument to add_entry is 'ppm' (data_type), the second is ppm_data
            called_args = self.mock_add_entry.call_args[0]
            self.assertEqual(len(called_args), 2) # data_type, entry_data
            ppm_data_arg = called_args[1]

            
            self.assertEqual(ppm_data_arg['PPM_Q_I']['engineer'], "Engineer1")
            self.assertEqual(ppm_data_arg['PPM_Q_II']['engineer'], "Engineer2")
            self.assertEqual(ppm_data_arg['PPM_Q_III']['engineer'], "Engineer3")
            self.assertEqual(ppm_data_arg['PPM_Q_IV']['engineer'], "Engineer4")
            self.assertEqual(ppm_data_arg['SERIAL'], "TestSerial123")
            self.assertEqual(ppm_data_arg['Status'], "Upcoming") # Default status

    def test_add_ppm_without_q1_date(self):
        form_data_no_q1 = {
            "MODEL": "TestModelNoQ1",
            "Name": "TestPPMNoQ1",
            "SERIAL": "TestSerial456",
            "MANUFACTURER": "TestManu",
            "Department": "TestDept",
            "LOG_Number": "TestLogNoQ1",
            "Installation_Date": "01/02/2024",
            "Warranty_End": "01/02/2025",
            "PPM_Q_I_date": "", # Q1 Date is empty
            "PPM_Q_I_engineer": "EngineerA",
            "PPM_Q_II_engineer": "EngineerB",
            "PPM_Q_III_engineer": "EngineerC",
            "PPM_Q_IV_engineer": "EngineerD",
        }
        with self.app.test_request_context('/equipment/ppm/add', method='POST', data=form_data_no_q1):
            add_ppm_equipment()

            self.mock_add_entry.assert_called_once()
            called_args = self.mock_add_entry.call_args[0]
            self.assertEqual(len(called_args), 2)
            ppm_data_arg = called_args[1]

            
            self.assertEqual(ppm_data_arg['PPM_Q_I']['engineer'], "EngineerA")
            self.assertEqual(ppm_data_arg['PPM_Q_II']['engineer'], "EngineerB")
            self.assertEqual(ppm_data_arg['SERIAL'], "TestSerial456")

    

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    # Using exit=False for running in environments where sys.exit might be problematic
    # For command line execution, `unittest.main()` is fine.
