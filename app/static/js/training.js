document.addEventListener('DOMContentLoaded', function() {
    console.log("Initializing training page script...");

    // Global state variables
    let trainingsData = [];
    let currentSort = { field: 'name', direction: 'asc' };

    // DOM element references
    const searchInput = document.getElementById('searchInput');
    const filterDepartment = document.getElementById('filterDepartment');
    const filterEmployeeId = document.getElementById('filterEmployeeId');
    const sortSelect = document.getElementById('sortSelect');
    const trainingTableBody = document.querySelector('#trainingTable tbody');
    const paginationContainer = document.querySelector('.pagination');
    const selectAllCheckbox = document.getElementById('selectAll');
    const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
    const selectedCountSpan = document.getElementById('selectedCount');

    // Debounce function for search input
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

    // Toast notification function
    function showToast(message, type = 'info') {
        const toastContainer = document.querySelector('.toast-container') || createToastContainer();
        const toastId = 'toast-' + Date.now();
        const toastHtml = `
            <div id="${toastId}" class="toast align-items-center text-bg-${type === 'error' ? 'danger' : type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: 5000 });
        toast.show();
        toastElement.addEventListener('hidden.bs.toast', () => toastElement.remove());
    }

    function createToastContainer() {
        let container = document.createElement('div');
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
        return container;
    }

    // API call to fetch training data
    async function fetchAndRenderTrainings(page = 1) {
        if (!trainingTableBody) return;
        trainingTableBody.innerHTML = '<tr><td colspan="10" class="text-center py-4"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></td></tr>';

        const searchParams = new URLSearchParams({
            page: page,
            per_page: 10, // You can make this dynamic if needed
            search: searchInput.value,
            department: filterDepartment.value,
            employee_id: filterEmployeeId.value,
            sort: currentSort.field,
            direction: currentSort.direction
        });

        try {
            const response = await fetch(`/api/trainings?${searchParams}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const result = await response.json();
            if (!result.success) throw new Error(result.error || 'Failed to fetch data');

            trainingsData = result.data || [];
            updateUrlParams(page, searchParams);
            renderTrainingTable(trainingsData);
            renderPagination(result.pagination || { page: 1, pages: 1 });
            updateEmployeeFilter(result.employee_ids || []);

        } catch (error) {
            console.error('Error fetching trainings:', error);
            showToast(error.message, 'error');
            if (trainingTableBody) trainingTableBody.innerHTML = '<tr><td colspan="10" class="text-center py-4"><div class="alert alert-danger">Failed to load data.</div></td></tr>';
        }
    }

    // Render table rows
    function renderTrainingTable(trainings) {
        trainingTableBody.innerHTML = '';
        document.getElementById('totalEmployeeCount').textContent = trainings.length;

        if (trainings.length === 0) {
            trainingTableBody.innerHTML = '<tr><td colspan="10" class="text-center">No training records found.</td></tr>';
            return;
        }

        trainings.forEach((training, index) => {
            const row = trainingTableBody.insertRow();
            row.id = `training-row-${training.id}`;
            row.dataset.trainingId = training.id;

            // ... (build row HTML as before) ...
            row.innerHTML = `
                <td><input type="checkbox" class="row-select" value="${training.id}"></td>
                <td>${index + 1}</td>
                <td>${training.employee_id || 'N/A'}</td>
                <td>${training.name || 'N/A'}</td>
                <td>${training.department || 'N/A'}</td>
                <td>${generateAssignmentsHTML(training.machine_trainer_assignments)}</td>
                <td>${generateTrainingPercentageHTML(training)}</td>
                <td>${training.last_trained_date || 'N/A'}</td>
                <td>${training.next_due_date || 'N/A'}</td>
                <td>
                    <button class="btn btn-sm btn-primary edit-training-btn" data-id="${training.id}" data-bs-toggle="modal" data-bs-target="#editTrainingModal"><i class="fas fa-edit"></i></button>
                    <button class="btn btn-sm btn-danger delete-training-btn" data-id="${training.id}" data-name="${training.name}"><i class="fas fa-trash"></i></button>
                </td>
            `;
        });
    }
    
    function generateAssignmentsHTML(assignments) {
        if (!assignments || assignments.length === 0) return '<span class="text-muted">N/A</span>';
        return `<ul class="list-unstyled mb-0">${assignments.map(a => `<li>${a.machine} <small class="text-muted">(${a.trainer || 'No trainer'})</small></li>`).join('')}</ul>`;
    }

    function generateTrainingPercentageHTML(training) {
        const trainedCount = training.machine_trainer_assignments?.length || 0;
        const totalMachines = window.devicesByDepartment[training.department]?.length || 0;
        if (totalMachines === 0) return '<span class="badge bg-secondary">N/A</span>';
        
        const percentage = Math.round((trainedCount / totalMachines) * 100);
        let badgeClass = 'bg-danger';
        if (percentage >= 80) badgeClass = 'bg-success';
        else if (percentage >= 60) badgeClass = 'bg-warning';
        else if (percentage >= 40) badgeClass = 'bg-info';
        return `<span class="badge ${badgeClass}">${percentage}%</span>`;
    }

    // Render pagination controls
    function renderPagination({ page, pages }) {
        paginationContainer.innerHTML = '';
        if (pages <= 1) return;

        const createPageItem = (p, text, active = false, disabled = false) => {
            const li = document.createElement('li');
            li.className = `page-item ${active ? 'active' : ''} ${disabled ? 'disabled' : ''}`;
            const a = document.createElement('a');
            a.className = 'page-link';
            a.href = '#';
            a.dataset.page = p;
            a.innerHTML = text;
            li.appendChild(a);
            return li;
        };

        paginationContainer.appendChild(createPageItem(page - 1, '&laquo;', false, page === 1));

        for (let i = 1; i <= pages; i++) {
            // This logic can be improved to show ellipsis for many pages
            paginationContainer.appendChild(createPageItem(i, i, i === page));
        }

        paginationContainer.appendChild(createPageItem(page + 1, '&raquo;', false, page === pages));
    }

    function updateEmployeeFilter(employeeIds) {
        const currentVal = filterEmployeeId.value;
        filterEmployeeId.innerHTML = '<option value="">All Employees</option>';
        employeeIds.forEach(id => {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = id;
            filterEmployeeId.appendChild(option);
        });
        filterEmployeeId.value = currentVal;
    }

    function updateUrlParams(page, params) {
        const url = new URL(window.location);
        url.searchParams.set('page', page);
        params.forEach((value, key) => {
            if (key !== 'page') {
                if (value) url.searchParams.set(key, value); else url.searchParams.delete(key);
            }
        });
        window.history.pushState({}, '', url);
    }

    // Event Listeners Setup
    function setupEventListeners() {
        searchInput.addEventListener('input', debounce(() => fetchAndRenderTrainings(1), 300));
        filterDepartment.addEventListener('change', () => fetchAndRenderTrainings(1));
        filterEmployeeId.addEventListener('change', () => fetchAndRenderTrainings(1));
        sortSelect.addEventListener('change', () => {
            const [field, direction] = sortSelect.value.split('_');
            currentSort = { field, direction };
            fetchAndRenderTrainings(1);
        });

        paginationContainer.addEventListener('click', e => {
            e.preventDefault();
            if (e.target.tagName === 'A' && e.target.dataset.page) {
                const page = parseInt(e.target.dataset.page, 10);
                if (!isNaN(page)) fetchAndRenderTrainings(page);
            }
        });

        // ... other listeners for modals, delete, etc. ...
    }

    // Initial Load
    setupEventListeners();
    fetchAndRenderTrainings(new URLSearchParams(window.location.search).get('page') || 1);
});