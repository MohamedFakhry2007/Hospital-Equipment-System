document.addEventListener('DOMContentLoaded', function () {
    const addTrainingForm = document.getElementById('addTrainingForm');
    const editTrainingForm = document.getElementById('editTrainingForm');
    const trainingTableBody = document.querySelector('#trainingTable tbody');
    const searchInput = document.getElementById('searchInput');
    const filterEmployeeId = document.getElementById('filterEmployeeId');
    const filterDepartment = document.getElementById('filterDepartment');
    const sortSelect = document.getElementById('sortSelect');
    const selectAllCheckbox = document.getElementById('selectAll');
    const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
    const selectedCountSpan = document.getElementById('selectedCount');

    let trainingsData = [];
    let filteredData = [];
    let currentSort = { field: null, direction: 'asc' };

    // Function to fetch and render training data
    async function fetchAndRenderTrainings() {
        try {
            const response = await fetch('/api/trainings');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            trainingsData = await response.json();
            populateEmployeeFilter();
            applyFiltersAndSort();
        } catch (error) {
            console.error('Error fetching trainings:', error);
            showToast('Error fetching training data.', 'error');
        }
    }

    // Populate employee filter dropdown
    function populateEmployeeFilter() {
        const uniqueEmployeeIds = [...new Set(trainingsData.map(t => t.employee_id).filter(id => id))];
        filterEmployeeId.innerHTML = '<option value="">All Employees</option>';
        uniqueEmployeeIds.sort().forEach(id => {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = id;
            filterEmployeeId.appendChild(option);
        });
    }

    // Apply filters and sorting
    function applyFiltersAndSort() {
        let filtered = [...trainingsData];

        // Apply search filter
        const searchTerm = searchInput.value.toLowerCase();
        if (searchTerm) {
            filtered = filtered.filter(training => 
                (training.employee_id || '').toLowerCase().includes(searchTerm) ||
                (training.name || '').toLowerCase().includes(searchTerm) ||
                (training.department || '').toLowerCase().includes(searchTerm)
            );
        }

        // Apply employee ID filter
        const employeeIdFilter = filterEmployeeId.value;
        if (employeeIdFilter) {
            filtered = filtered.filter(training => training.employee_id === employeeIdFilter);
        }

        // Apply department filter
        const departmentFilter = filterDepartment.value;
        if (departmentFilter) {
            filtered = filtered.filter(training => training.department === departmentFilter);
        }

        // Apply sorting
        if (currentSort.field) {
            filtered.sort((a, b) => {
                let aVal, bVal;
                
                // Handle training percentage sorting
                if (currentSort.field === 'training_percentage') {
                    const aTrainedMachines = a.machine_trainer_assignments ? a.machine_trainer_assignments.length : 0;
                    const aTotalMachines = a.department && devicesByDepartment[a.department] ? devicesByDepartment[a.department].length : 0;
                    aVal = aTotalMachines > 0 ? (aTrainedMachines / aTotalMachines) * 100 : 0;
                    
                    const bTrainedMachines = b.machine_trainer_assignments ? b.machine_trainer_assignments.length : 0;
                    const bTotalMachines = b.department && devicesByDepartment[b.department] ? devicesByDepartment[b.department].length : 0;
                    bVal = bTotalMachines > 0 ? (bTrainedMachines / bTotalMachines) * 100 : 0;
                } else {
                    aVal = a[currentSort.field] || '';
                    bVal = b[currentSort.field] || '';
                    
                    // Handle date sorting
                    if (currentSort.field.includes('date')) {
                        aVal = new Date(aVal || '1900-01-01');
                        bVal = new Date(bVal || '1900-01-01');
                    } else {
                        aVal = aVal.toString().toLowerCase();
                        bVal = bVal.toString().toLowerCase();
                    }
                }

                if (currentSort.direction === 'asc') {
                    return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
                } else {
                    return aVal < bVal ? 1 : aVal > bVal ? -1 : 0;
                }
            });
        }

        filteredData = filtered;
        renderTrainingTable(filtered);
        updateBulkDeleteButton();
    }

    // Function to render the training table
    function renderTrainingTable(trainings) {
        trainingTableBody.innerHTML = ''; // Clear existing rows
        
        // Update employee count badge
        const totalEmployeeCount = document.getElementById('totalEmployeeCount');
        if (totalEmployeeCount) {
            totalEmployeeCount.textContent = trainings ? trainings.length : 0;
        }
        
        if (trainings && trainings.length > 0) {
            trainings.forEach((training, index) => {
                const row = trainingTableBody.insertRow();
                row.id = `training-row-${training.id}`;
                row.dataset.trainingId = training.id;
                
                let assignmentsHtml = 'N/A';
                if (training.machine_trainer_assignments && training.machine_trainer_assignments.length > 0) {
                    assignmentsHtml = '<ul class="list-unstyled mb-0">';
                    training.machine_trainer_assignments.forEach((a, idx) => {
                        assignmentsHtml += `<li>
                            <span class="machine-number" style="font-weight: 600; color: #6c757d;">${idx + 1}-</span>
                            <span class="machine-name" style="font-weight: 500; color: #212529;">${a.machine}</span>
                            ${a.trainer ? `<span class="trainer-name" style="font-weight: bold; color: #dc3545;"> (${a.trainer})</span>` : ''}
                        </li>`;
                    });
                    assignmentsHtml += '</ul>';
                }

                // Calculate training percentage
                let trainingPercentageHtml = '<span class="badge bg-secondary training-percentage">N/A</span>';
                const trainedMachines = training.machine_trainer_assignments ? training.machine_trainer_assignments.length : 0;
                const totalMachines = training.department && devicesByDepartment[training.department] ? devicesByDepartment[training.department].length : 0;
                
                if (totalMachines > 0) {
                    const percentage = Math.round((trainedMachines / totalMachines) * 100 * 10) / 10; // Round to 1 decimal
                    let badgeClass = 'bg-danger'; // < 40%
                    if (percentage >= 80) badgeClass = 'bg-success';
                    else if (percentage >= 60) badgeClass = 'bg-warning';
                    else if (percentage >= 40) badgeClass = 'bg-info';
                    
                    trainingPercentageHtml = `<span class="badge ${badgeClass} training-percentage">${percentage}%</span>`;
                }

                row.innerHTML = `
                    <td>
                        <input type="checkbox" class="row-select" value="${training.id}" title="Select this record">
                    </td>
                    <td>${index + 1}</td>
                    <td>${training.employee_id || 'N/A'}</td>
                    <td>${training.name || 'N/A'}</td>
                    <td>${training.department || 'N/A'}</td>
                    <td>${assignmentsHtml}</td>
                    <td>${trainingPercentageHtml}</td>
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
            trainingTableBody.innerHTML = '<tr><td colspan="11" class="text-center">No training records found.</td></tr>';
        }
    }

    // Handle sorting by column headers
    document.addEventListener('click', function(event) {
        if (event.target.closest('.sortable')) {
            const sortableHeader = event.target.closest('.sortable');
            const sortField = sortableHeader.dataset.sort;
            
            // Update sort direction
            if (currentSort.field === sortField) {
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.field = sortField;
                currentSort.direction = 'asc';
            }

            // Update visual indicators
            document.querySelectorAll('.sortable').forEach(header => {
                header.classList.remove('asc', 'desc');
            });
            sortableHeader.classList.add(currentSort.direction);

            // Update sort select dropdown
            sortSelect.value = sortField;

            applyFiltersAndSort();
        }
    });

    // Handle sort dropdown change
    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            if (this.value) {
                currentSort.field = this.value;
                currentSort.direction = 'asc';
                
                // Update visual indicators
                document.querySelectorAll('.sortable').forEach(header => {
                    header.classList.remove('asc', 'desc');
                });
                const sortableHeader = document.querySelector(`[data-sort="${this.value}"]`);
                if (sortableHeader) {
                    sortableHeader.classList.add('asc');
                }
            } else {
                currentSort = { field: null, direction: 'asc' };
                document.querySelectorAll('.sortable').forEach(header => {
                    header.classList.remove('asc', 'desc');
                });
            }
            applyFiltersAndSort();
        });
    }

    // Handle search input
    if (searchInput) {
        searchInput.addEventListener('input', debounce(applyFiltersAndSort, 300));
    }

    // Handle filter changes
    if (filterEmployeeId) {
        filterEmployeeId.addEventListener('change', applyFiltersAndSort);
    }

    if (filterDepartment) {
        filterDepartment.addEventListener('change', applyFiltersAndSort);
    }

    // Handle select all checkbox
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            const checkboxes = document.querySelectorAll('.row-select');
            checkboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
                const row = checkbox.closest('tr');
                if (this.checked) {
                    row.classList.add('selected');
                } else {
                    row.classList.remove('selected');
                }
            });
            updateBulkDeleteButton();
        });
    }

    // Handle individual row selection
    document.addEventListener('change', function(event) {
        if (event.target.classList.contains('row-select')) {
            const row = event.target.closest('tr');
            if (event.target.checked) {
                row.classList.add('selected');
            } else {
                row.classList.remove('selected');
                selectAllCheckbox.checked = false;
            }
            updateBulkDeleteButton();
        }
    });

    // Update bulk delete button visibility and count
    function updateBulkDeleteButton() {
        const selectedCheckboxes = document.querySelectorAll('.row-select:checked');
        const count = selectedCheckboxes.length;
        
        if (count > 0) {
            bulkDeleteBtn.style.display = 'inline-block';
            selectedCountSpan.textContent = count;
        } else {
            bulkDeleteBtn.style.display = 'none';
        }

        // Update select all checkbox state
        const allCheckboxes = document.querySelectorAll('.row-select');
        if (allCheckboxes.length > 0) {
            selectAllCheckbox.indeterminate = count > 0 && count < allCheckboxes.length;
            selectAllCheckbox.checked = count === allCheckboxes.length;
        }
    }

    // Handle bulk delete
    if (bulkDeleteBtn) {
        bulkDeleteBtn.addEventListener('click', async function() {
            const selectedCheckboxes = document.querySelectorAll('.row-select:checked');
            const selectedIds = Array.from(selectedCheckboxes).map(cb => cb.value);
            
            if (selectedIds.length === 0) return;

            const confirmMessage = `Are you sure you want to delete ${selectedIds.length} selected training record(s)? This action cannot be undone.`;
            if (!confirm(confirmMessage)) return;

            try {
                const deletePromises = selectedIds.map(id => 
                    fetch(`/api/trainings/${id}`, { method: 'DELETE' })
                );
                
                const responses = await Promise.all(deletePromises);
                const failedDeletes = responses.filter(r => !r.ok).length;
                
                if (failedDeletes > 0) {
                    showToast(`${failedDeletes} records failed to delete.`, 'warning');
                } else {
                    showToast(`Successfully deleted ${selectedIds.length} training record(s).`, 'success');
                }
                
                fetchAndRenderTrainings();
            } catch (error) {
                console.error('Error during bulk delete:', error);
                showToast('Error occurred during bulk delete operation.', 'error');
            }
        });
    }

    // Debounce function for search
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
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
                    if (machineName) {
                        data.machine_trainer_assignments.push({ machine: machineName, trainer: trainer });
                    }
                }
            });

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
                await response.json();
                fetchAndRenderTrainings();
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
            
            // Use setTimeout to ensure modal is fully rendered before populating
            setTimeout(() => {
                console.log('Populating edit modal with department:', department, 'and assignments:', machineAssignments);
                
                // Use the new generateMachineAssignments function
                if (typeof generateMachineAssignments === 'function') {
                    generateMachineAssignments(department, 'editMachineAssignmentsContainer', machineAssignments);
                } else {
                    console.error('generateMachineAssignments function not found');
                }
            }, 200);
        }
    });

    // Handle Edit Training Form Submission
    if (editTrainingForm) {
        editTrainingForm.addEventListener('submit', async function (event) {
            event.preventDefault();
            const formData = new FormData(editTrainingForm);
            const data = Object.fromEntries(formData.entries());
            const trainingId = data.id;

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
                await response.json();
                fetchAndRenderTrainings();
                bootstrap.Modal.getInstance(document.getElementById('editTrainingModal')).hide();
                showToast('Training record updated successfully!', 'success');
            } catch (error) {
                console.error('Error updating training:', error);
                showToast(`Error: ${error.message}`, 'error');
            }
        });
    }

    // Handle individual delete buttons
    document.addEventListener('click', async function(event) {
        if (event.target.classList.contains('delete-training-btn') || event.target.closest('.delete-training-btn')) {
            const button = event.target.closest('.delete-training-btn');
            const trainingId = button.dataset.id;
            const trainingName = button.dataset.name;

            if (!confirm(`Are you sure you want to delete the training record for "${trainingName}"? This action cannot be undone.`)) {
                return;
            }

            try {
                const response = await fetch(`/api/trainings/${trainingId}`, {
                    method: 'DELETE',
                });
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                }
                fetchAndRenderTrainings();
                showToast('Training record deleted successfully!', 'success');
            } catch (error) {
                console.error('Error deleting training:', error);
                showToast(`Error: ${error.message}`, 'error');
            }
        }
    });

    // Toast notification function
    function showToast(message, type = 'info') {
        // Create toast element
        const toastId = 'toast-' + Date.now();
        const toastHtml = `
            <div id="${toastId}" class="toast align-items-center text-bg-${type === 'error' ? 'danger' : type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        
        // Find or create toast container
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        // Add toast to container
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        // Show toast
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: type === 'error' ? 6000 : 4000
        });
        toast.show();
        
        // Remove toast element after it's hidden
        toastElement.addEventListener('hidden.bs.toast', function () {
            toastElement.remove();
        });
    }



    // Check for import success flash message and refresh data
    function checkForImportSuccess() {
        const flashMessages = document.querySelectorAll('.alert-success');
        flashMessages.forEach(message => {
            if (message.textContent.includes('TRAINING import successful')) {
                // Auto-refresh data after successful import
                setTimeout(() => {
                    fetchAndRenderTrainings();
                    showToast('Training data refreshed after successful import!', 'success');
                }, 500);
            }
        });
    }

    // Initial data fetch
    fetchAndRenderTrainings();
    
    // Check for import success on page load
    checkForImportSuccess();
});
