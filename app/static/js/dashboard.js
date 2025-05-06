
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const frequencyFilter = document.getElementById('frequencyFilter');
    const statusFilter = document.getElementById('statusFilter');
    const resetButton = document.getElementById('resetFilters');
    const tableBody = document.querySelector('table tbody');

    function filterTable() {
        const searchTerm = searchInput.value.toLowerCase();
        const frequency = frequencyFilter.value;
        const status = statusFilter.value;
        const rows = tableBody.getElementsByTagName('tr');

        Array.from(rows).forEach(row => {
            const text = row.textContent.toLowerCase();
            const rowFrequency = row.getAttribute('data-frequency');
            const rowStatus = row.getAttribute('data-status');
            
            const matchesSearch = text.includes(searchTerm);
            const matchesFrequency = !frequency || rowFrequency === frequency;
            const matchesStatus = !status || rowStatus === status;

            row.style.display = matchesSearch && matchesFrequency && matchesStatus ? '' : 'none';
        });
    }

    if (searchInput) searchInput.addEventListener('input', filterTable);
    if (frequencyFilter) frequencyFilter.addEventListener('change', filterTable);
    if (statusFilter) statusFilter.addEventListener('change', filterTable);
    if (resetButton) {
        resetButton.addEventListener('click', () => {
            searchInput.value = '';
            frequencyFilter.value = '';
            statusFilter.value = '';
            filterTable();
        });
    }
});
