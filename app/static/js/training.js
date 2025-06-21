document.addEventListener('DOMContentLoaded', function () {
    const addTrainingForm = document.getElementById('addTrainingForm');
    const editTrainingForm = document.getElementById('editTrainingForm');
    const trainingTableBody = document.querySelector('#trainingTable tbody');

    // Function to fetch and render training data
    async function fetchAndRenderTrainings() {
        try {
            const response = await fetch('/api/trainings');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const trainings = await response.json();
            renderTrainingTable(trainings);
        } catch (error) {
            console.error('Error fetching trainings:', error);
            showToast('Error fetching training data.', 'error');
        }
    }

    // Function to render the training table
    function renderTrainingTable(trainings) {
        trainingTableBody.innerHTML = ''; // Clear existing rows
        if (trainings && trainings.length > 0) {
            trainings.forEach((training, index) => {
                const row = trainingTableBody.insertRow();
                row.id = `training-row-${training.id}`;
                let assignmentsHtml = 'N/A';
                if (training.machine_trainer_assignments && training.machine_trainer_assignments.length > 0) {
                    assignmentsHtml = '<ul class="list-unstyled mb-0">';
                    training.machine_trainer_assignments.forEach(a => {
                        assignmentsHtml += `<li>${a.machine}${a.trainer ? ` (${a.trainer})` : ''}</li>`;
                    });
                    assignmentsHtml += '</ul>';
                }

                // The 'Trainer' column is removed from the table header, so we don't add a cell for it.
                row.innerHTML = `
                    <td>${index + 1}</td>
                    <td>${training.employee_id || 'N/A'}</td>
                    <td>${training.name || 'N/A'}</td>
                    <td>${training.department || 'N/A'}</td>
                    <td>${assignmentsHtml}</td>
                    <td>${training.last_trained_date || 'N/A'}</td>
                    <td>${training.next_due_date || 'N/A'}</td>
                    <td>
                        <button class="btn btn-sm btn-primary edit-training-btn"
                                data-id="${training.id}"
                                data-employee-id="${training.employee_id || ''}"
                                data-name="${training.name || ''}"
                                data-department="${training.department || ''}"
                                data-machine-assignments='${JSON.stringify(training.machine_trainer_assignments || [])}'
                                data-last-trained="${training.last_trained_date || ''}"
                                data-next-due="${training.next_due_date || ''}"
                                data-bs-toggle="modal" data-bs-target="#editTrainingModal">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                        <button class="btn btn-sm btn-danger delete-training-btn" data-id="${training.id}" data-name="${training.name || 'record'}">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </td>
                `;
            });
        } else {
            trainingTableBody.innerHTML = '<tr><td colspan="9" class="text-center">No training records found.</td></tr>';
        }
    }

    // Handle Add Training Form Submission
    if (addTrainingForm) {
        addTrainingForm.addEventListener('submit', async function (event) {
            event.preventDefault();
            const formData = new FormData(addTrainingForm);
            const data = Object.fromEntries(formData.entries());

            // Collect machine_trainer_assignments
            data.machine_trainer_assignments = [];
            const assignmentRows = document.querySelectorAll('#addMachineAssignmentsContainer .machine-assignment-entry');
            assignmentRows.forEach(row => {
                const checkbox = row.querySelector('.machine-select-checkbox');
                if (checkbox && checkbox.checked) {
                    const machineName = checkbox.value;
                    const trainerSelect = row.querySelector('.trainer-assign-select');
                    const trainer = trainerSelect ? trainerSelect.value : null;
                    if (machineName) { // Ensure machine name is valid
                        data.machine_trainer_assignments.push({ machine: machineName, trainer: trainer });
                    }
                }
            });

            // Remove individual fields that are now part of machine_trainer_assignments from top-level data
            // delete data.trained_on_machines; // This field is no longer a direct input
            // delete data.trainer; // This field is no longer a direct input

            try {
                const response = await fetch('/api/trainings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data),
                });
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                }
                // const newTraining = await response.json();
                await response.json(); // consume the response
                fetchAndRenderTrainings(); // Re-fetch and render
                bootstrap.Modal.getInstance(document.getElementById('addTrainingModal')).hide();
                addTrainingForm.reset();
                showToast('Training record added successfully!', 'success');
            } catch (error) {
                console.error('Error adding training:', error);
                showToast(`Error: ${error.message}`, 'error');
            }
        });
    }

    // Handle Edit Training Modal Population
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('edit-training-btn') || event.target.closest('.edit-training-btn')) {
            const button = event.target.closest('.edit-training-btn');
            const trainingId = button.dataset.id;
            const employeeId = button.dataset.employeeId;
            const name = button.dataset.name;
            const department = button.dataset.department;
            const machineAssignmentsStr = button.dataset.machineAssignments;
            const lastTrained = button.dataset.lastTrained;
            const nextDue = button.dataset.nextDue;

            document.getElementById('editTrainingId').value = trainingId;
            document.getElementById('editEmployeeId').value = employeeId;
            document.getElementById('editName').value = name;
            document.getElementById('editDepartment').value = department;
            document.getElementById('editLastTrainedDate').value = lastTrained;
            document.getElementById('editNextDueDate').value = nextDue;

            let machineAssignments = [];
            try {
                machineAssignments = JSON.parse(machineAssignmentsStr || '[]');
            } catch (e) {
                console.error('Error parsing machine assignments JSON:', e);
                machineAssignments = [];
            }

            // Populate machine assignments in the edit modal
            // Assumes populateMachineAssignments function is globally available or imported
            // and devicesByDepartment, trainingModules are also available in this scope.
            // This function is defined in training/list.html inline script.
            populateMachineAssignments(department, 'editMachineAssignmentsContainer', 'editMachinePlaceholder', machineAssignments);
        }
    });

    // Handle Edit Training Form Submission
    if (editTrainingForm) {
        editTrainingForm.addEventListener('submit', async function (event) {
            event.preventDefault();
            const formData = new FormData(editTrainingForm);
            const data = Object.fromEntries(formData.entries());
            const trainingId = data.id; // Keep this, as service layer might use it for matching.

            // Collect machine_trainer_assignments
            data.machine_trainer_assignments = [];
            const assignmentRows = document.querySelectorAll('#editMachineAssignmentsContainer .machine-assignment-entry');
            assignmentRows.forEach(row => {
                const checkbox = row.querySelector('.machine-select-checkbox');
                if (checkbox && checkbox.checked) {
                    const machineName = checkbox.value;
                    const trainerSelect = row.querySelector('.trainer-assign-select');
                    const trainer = trainerSelect ? trainerSelect.value : null;
                    if (machineName) {
                        data.machine_trainer_assignments.push({ machine: machineName, trainer: trainer });
                    }
                }
            });

            // Remove individual fields that are now part of machine_trainer_assignments
            // delete data.trained_on_machines;
            // delete data.trainer;

            try {
                const response = await fetch(`/api/trainings/${trainingId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data),
                });
                if (!response.ok) {
                     const errorData = await response.json();
                    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                }
                // const updatedTraining = await response.json();
                await response.json(); // consume the response
                fetchAndRenderTrainings(); // Re-fetch and render
                bootstrap.Modal.getInstance(document.getElementById('editTrainingModal')).hide();
                showToast('Training record updated successfully!', 'success');
            } catch (error) {
                console.error('Error updating training:', error);
                showToast(`Error: ${error.message}`, 'error');
            }
        });
    }

    // Handle Delete Training
    trainingTableBody.addEventListener('click', async function (event) {
        if (event.target.classList.contains('delete-training-btn') || event.target.closest('.delete-training-btn')) {
            const button = event.target.closest('.delete-training-btn');
            const trainingId = button.dataset.id;
            const trainingName = button.dataset.name || 'this record';

            if (confirm(`Are you sure you want to delete the training record for ${trainingName}?`)) {
                try {
                    const response = await fetch(`/api/trainings/${trainingId}`, {
                        method: 'DELETE',
                    });
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                    }
                    // await response.json(); // No content usually for DELETE
                    fetchAndRenderTrainings(); // Re-fetch and render
                    showToast('Training record deleted successfully!', 'success');
                } catch (error) {
                    console.error('Error deleting training:', error);
                    showToast(`Error: ${error.message}`, 'error');
                }
            }
        }
    });

    // Simple Toast Notification Function (requires Bootstrap 5 JS included in base.html)
    function showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toastPlacement');
        if (!toastContainer) {
            console.warn('Toast container #toastPlacement not found. Cannot display toast.');
            alert(message); // Fallback to alert
            return;
        }

        const toastId = `toast-${Date.now()}`;
        const toastHTML = `
            <div id="${toastId}" class="toast align-items-center text-white bg-${type === 'error' ? 'danger' : (type === 'success' ? 'success' : 'primary')}" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;

        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = toastHTML;
        const toastElement = tempDiv.firstChild;

        toastContainer.appendChild(toastElement);

        const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
        toast.show();
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }


    // Initial fetch and render of training data
    // Check if we are on the training page by looking for the table
    if (trainingTableBody) {
        fetchAndRenderTrainings();
    }
});
