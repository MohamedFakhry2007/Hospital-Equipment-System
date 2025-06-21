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
                row.innerHTML = `
                    <td>${index + 1}</td>
                    <td>${training.employee_id || 'N/A'}</td>
                    <td>${training.name || 'N/A'}</td>
                    <td>${training.department || 'N/A'}</td>
                    <td>${training.trainer || 'N/A'}</td>
                    <td>${(Array.isArray(training.trained_on_machines) ? training.trained_on_machines.join(', ') : (training.trained_on_machines || 'N/A'))}</td>
                    <td>${training.last_trained_date || 'N/A'}</td>
                    <td>${training.next_due_date || 'N/A'}</td>
                    <td>
                        <button class="btn btn-sm btn-primary edit-training-btn"
                                data-id="${training.id}"
                                data-employee-id="${training.employee_id || ''}"
                                data-name="${training.name || ''}"
                                data-department="${training.department || ''}"
                                data-trainer="${training.trainer || ''}"
                                data-machines="${Array.isArray(training.trained_on_machines) ? training.trained_on_machines.join(',') : (training.trained_on_machines || '')}"
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
            // Convert comma-separated string for machines to array if needed by backend,
            // or ensure backend handles string. Service expects string and converts.
            // data.trained_on_machines = data.trained_on_machines.split(',').map(s => s.trim()).filter(s => s);

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
            document.getElementById('editTrainingId').value = button.dataset.id;
            document.getElementById('editEmployeeId').value = button.dataset.employeeId;
            document.getElementById('editName').value = button.dataset.name;
            document.getElementById('editDepartment').value = button.dataset.department;
            document.getElementById('editTrainer').value = button.dataset.trainer;
            document.getElementById('editTrainedOnMachines').value = button.dataset.machines;
            document.getElementById('editLastTrainedDate').value = button.dataset.lastTrained;
            document.getElementById('editNextDueDate').value = button.dataset.nextDue;
        }
    });

    // Handle Edit Training Form Submission
    if (editTrainingForm) {
        editTrainingForm.addEventListener('submit', async function (event) {
            event.preventDefault();
            const formData = new FormData(editTrainingForm);
            const data = Object.fromEntries(formData.entries());
            const trainingId = data.id;
            // delete data.id; // ID is in URL, not body for typical REST APIs, but our backend expects it in body too.

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
