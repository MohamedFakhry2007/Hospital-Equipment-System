/**
 * Modern Date Picker - Global JavaScript Module
 * Automatically initializes Flatpickr date pickers with modern styling
 * Format: dd/mm/yyyy (25/12/2023)
 */

(function() {
    'use strict';

    // Configuration for Flatpickr
    const datePickerConfig = {
        dateFormat: "d/m/Y",
        allowInput: true,
        altInput: false, // Disable alt input to show actual format
        theme: "material_blue",
        locale: {
            firstDayOfWeek: 1, // Monday
            months: {
                shorthand: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                longhand: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
            },
            weekdays: {
                shorthand: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
                longhand: ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            }
        },
        animate: true,
        position: "auto center",
        allowInvalidPreload: false,
        clickOpens: true,
        time_24hr: false,
        disableMobile: false,
        monthSelectorType: "dropdown",
        showMonths: 1,
        
        // Custom parsing and formatting
        parseDate: function(datestr, format) {
            if (!datestr) return null;
            
            // Handle dd/mm/yyyy format
            const parts = datestr.split('/');
            if (parts.length === 3) {
                const day = parseInt(parts[0], 10);
                const month = parseInt(parts[1], 10) - 1; // Month is 0-indexed
                const year = parseInt(parts[2], 10);
                
                if (!isNaN(day) && !isNaN(month) && !isNaN(year)) {
                    return new Date(year, month, day);
                }
            }
            
            return null;
        },
        
        formatDate: function(date, format) {
            if (!date) return '';
            
            const day = String(date.getDate()).padStart(2, '0');
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const year = date.getFullYear();
            
            return `${day}/${month}/${year}`;
        },

        // Event handlers
        onReady: function(selectedDates, dateStr, instance) {
            console.log('Date picker ready:', instance.element.id || instance.element.name || 'unnamed');
            
            // Add visual feedback
            if (dateStr) {
                instance.element.classList.add('has-value');
            }
            
            // Add custom styling to calendar and ensure month/year visibility
            if (instance.calendarContainer) {
                instance.calendarContainer.classList.add('modern-calendar');
                
                // Force month and year display to be visible
                setTimeout(() => {
                    // Ensure month dropdown is visible
                    const monthDropdown = instance.calendarContainer.querySelector('.flatpickr-monthDropdown-months');
                    if (monthDropdown) {
                        monthDropdown.style.display = 'inline-block';
                        monthDropdown.style.visibility = 'visible';
                        monthDropdown.style.opacity = '1';
                    }
                    
                    // Ensure year input is visible
                    const yearInput = instance.calendarContainer.querySelector('.numInputWrapper');
                    if (yearInput) {
                        yearInput.style.display = 'inline-block';
                        yearInput.style.visibility = 'visible';
                        yearInput.style.opacity = '1';
                    }
                    
                    // Ensure current month container is properly displayed
                    const currentMonth = instance.calendarContainer.querySelector('.flatpickr-current-month');
                    if (currentMonth) {
                        currentMonth.style.display = 'flex';
                        currentMonth.style.alignItems = 'center';
                        currentMonth.style.justifyContent = 'center';
                        currentMonth.style.visibility = 'visible';
                        currentMonth.style.opacity = '1';
                    }
                    
                    // Force navigation arrows to be visible
                    const prevArrow = instance.calendarContainer.querySelector('.flatpickr-prev-month');
                    const nextArrow = instance.calendarContainer.querySelector('.flatpickr-next-month');
                    if (prevArrow) {
                        prevArrow.style.display = 'flex';
                        prevArrow.style.visibility = 'visible';
                        prevArrow.style.opacity = '1';
                    }
                    if (nextArrow) {
                        nextArrow.style.display = 'flex';
                        nextArrow.style.visibility = 'visible';
                        nextArrow.style.opacity = '1';
                    }
                }, 50);
            }
        },

        onChange: function(selectedDates, dateStr, instance) {
            console.log('Date changed:', dateStr, 'for element:', instance.element.id || instance.element.name);
            
            // Visual feedback
            if (dateStr && dateStr.trim()) {
                instance.element.classList.add('has-value');
                instance.element.classList.remove('is-invalid');
                
                // Validate date format
                if (isValidDateFormat(dateStr)) {
                    instance.element.classList.remove('is-invalid');
                } else {
                    instance.element.classList.add('is-invalid');
                }
            } else {
                instance.element.classList.remove('has-value');
                instance.element.classList.remove('is-invalid');
            }

            // Trigger custom event for other scripts to listen to
            const event = new CustomEvent('modernDatePickerChange', {
                detail: {
                    element: instance.element,
                    date: selectedDates[0] || null,
                    dateString: dateStr,
                    instance: instance
                }
            });
            instance.element.dispatchEvent(event);
        },

        onOpen: function(selectedDates, dateStr, instance) {
            console.log('Date picker opened');
            
            // Add animation class and ensure visibility
            if (instance.calendarContainer) {
                instance.calendarContainer.style.animation = 'fadeInScale 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
                
                // Double-check month and year visibility on open
                setTimeout(() => {
                    // Force all header elements to be visible
                    const headerElements = [
                        '.flatpickr-current-month',
                        '.flatpickr-monthDropdown-months',
                        '.numInputWrapper',
                        '.flatpickr-prev-month',
                        '.flatpickr-next-month'
                    ];
                    
                    headerElements.forEach(selector => {
                        const element = instance.calendarContainer.querySelector(selector);
                        if (element) {
                            element.style.display = selector.includes('current-month') ? 'flex' : 'inline-block';
                            element.style.visibility = 'visible';
                            element.style.opacity = '1';
                            element.style.pointerEvents = 'auto';
                        }
                    });
                    
                    // Ensure proper z-index for header
                    const monthsContainer = instance.calendarContainer.querySelector('.flatpickr-months');
                    if (monthsContainer) {
                        monthsContainer.style.position = 'relative';
                        monthsContainer.style.zIndex = '1';
                    }
                }, 100);
            }
        },

        onClose: function(selectedDates, dateStr, instance) {
            console.log('Date picker closed');
            
            // Final validation
            if (dateStr && !isValidDateFormat(dateStr)) {
                console.warn('Invalid date format detected:', dateStr);
                instance.element.classList.add('is-invalid');
            }
        }
    };

    // Validate date format (dd/mm/yyyy)
    function isValidDateFormat(dateStr) {
        if (!dateStr) return true; // Empty is valid
        
        const regex = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;
        const match = dateStr.match(regex);
        
        if (!match) return false;
        
        const day = parseInt(match[1], 10);
        const month = parseInt(match[2], 10);
        const year = parseInt(match[3], 10);
        
        // Basic validation
        if (month < 1 || month > 12) return false;
        if (day < 1 || day > 31) return false;
        if (year < 1900 || year > 2100) return false;
        
        // More specific validation
        const date = new Date(year, month - 1, day);
        return date.getFullYear() === year && 
               date.getMonth() === month - 1 && 
               date.getDate() === day;
    }

    // Initialize a single date picker
    function initializeDatePicker(element) {
        if (!element || element.dataset.flatpickrInitialized) {
            return null;
        }

        try {
            console.log('Initializing date picker for:', element.id || element.name || element.className);
            
            // Mark as initialized to prevent double initialization
            element.dataset.flatpickrInitialized = 'true';
            
            // Get existing value and clean it up
            let existingValue = element.value;
            if (existingValue) {
                // Convert various formats to dd/mm/yyyy
                existingValue = normalizeDate(existingValue);
                element.value = existingValue;
            }

            // Create flatpickr instance
            const fp = flatpickr(element, datePickerConfig);
            
            // Store reference for later use
            element._flatpickr = fp;
            
            // Set initial value if exists
            if (existingValue) {
                fp.setDate(existingValue, true);
            }

            console.log('Date picker initialized successfully for:', element.id || element.name);
            return fp;
            
        } catch (error) {
            console.error('Error initializing date picker:', error, element);
            return null;
        }
    }

    // Normalize date to dd/mm/yyyy format
    function normalizeDate(dateStr) {
        if (!dateStr) return '';
        
        // Already in correct format
        if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(dateStr)) {
            return dateStr;
        }
        
        // Try to parse various formats
        let date = null;
        
        // yyyy-mm-dd format
        if (/^\d{4}-\d{1,2}-\d{1,2}$/.test(dateStr)) {
            const parts = dateStr.split('-');
            date = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
        }
        // mm/dd/yyyy format
        else if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(dateStr)) {
            const parts = dateStr.split('/');
            // Assume first part is month if > 12, otherwise assume day
            if (parseInt(parts[0]) > 12) {
                date = new Date(parseInt(parts[2]), parseInt(parts[1]) - 1, parseInt(parts[0]));
            } else {
                date = new Date(parseInt(parts[2]), parseInt(parts[0]) - 1, parseInt(parts[1]));
            }
        }
        // Try native Date parsing as fallback
        else {
            date = new Date(dateStr);
        }
        
        if (date && !isNaN(date.getTime())) {
            const day = String(date.getDate()).padStart(2, '0');
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const year = date.getFullYear();
            return `${day}/${month}/${year}`;
        }
        
        return dateStr; // Return original if can't parse
    }

    // Initialize all date pickers on the page
    function initializeAllDatePickers() {
        console.log('Initializing all modern date pickers...');
        
        // Find all elements with the modern-date-picker class
        const dateInputs = document.querySelectorAll('.modern-date-picker');
        console.log(`Found ${dateInputs.length} date picker elements`);
        
        let initialized = 0;
        dateInputs.forEach(function(input) {
            if (initializeDatePicker(input)) {
                initialized++;
            }
        });
        
        console.log(`Successfully initialized ${initialized} date pickers`);
        return initialized;
    }

    // Destroy all date pickers (useful for cleanup)
    function destroyAllDatePickers() {
        const dateInputs = document.querySelectorAll('.modern-date-picker');
        dateInputs.forEach(function(input) {
            if (input._flatpickr) {
                input._flatpickr.destroy();
                delete input._flatpickr;
                delete input.dataset.flatpickrInitialized;
            }
        });
    }

    // Reinitialize date pickers (useful for dynamic content)
    function reinitializeDatePickers() {
        console.log('Reinitializing date pickers...');
        destroyAllDatePickers();
        return initializeAllDatePickers();
    }

    // Check if Flatpickr is available
    function checkFlatpickrAvailability() {
        if (typeof flatpickr === 'undefined') {
            console.error('Flatpickr library is not loaded! Make sure to include it before this script.');
            return false;
        }
        return true;
    }

    // Initialize when DOM is ready
    function initializeWhenReady() {
        if (!checkFlatpickrAvailability()) {
            console.error('Cannot initialize date pickers: Flatpickr not available');
            // Try again after a delay in case Flatpickr is still loading
            setTimeout(() => {
                if (checkFlatpickrAvailability()) {
                    console.log('Flatpickr now available, retrying initialization...');
                    initializeAllDatePickers();
                }
            }, 1000);
            return;
        }

        if (document.readyState === 'loading') {
            console.log('DOM still loading, waiting for DOMContentLoaded...');
            document.addEventListener('DOMContentLoaded', () => {
                console.log('DOMContentLoaded fired, initializing date pickers...');
                initializeAllDatePickers();
            });
        } else {
            console.log('DOM already ready, initializing date pickers immediately...');
            initializeAllDatePickers();
        }
    }

    // Watch for Bootstrap modal events and reinitialize
    function setupModalHandlers() {
        // Bootstrap 5 modal events
        document.addEventListener('shown.bs.modal', function(event) {
            console.log('Modal shown, reinitializing date pickers...');
            setTimeout(function() {
                const modalDatePickers = event.target.querySelectorAll('.modern-date-picker');
                modalDatePickers.forEach(initializeDatePicker);
            }, 100);
        });

        // Also handle Bootstrap 4 events for compatibility
        document.addEventListener('shown.bs.modal', function(event) {
            setTimeout(function() {
                const modalDatePickers = event.target.querySelectorAll('.modern-date-picker');
                modalDatePickers.forEach(initializeDatePicker);
            }, 100);
        });
    }

    // Observe DOM changes and initialize new date pickers
    function setupMutationObserver() {
        if (typeof MutationObserver !== 'undefined') {
            const observer = new MutationObserver(function(mutations) {
                let shouldReinitialize = false;
                
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'childList') {
                        mutation.addedNodes.forEach(function(node) {
                            if (node.nodeType === 1) { // Element node
                                if (node.classList && node.classList.contains('modern-date-picker')) {
                                    shouldReinitialize = true;
                                } else if (node.querySelectorAll) {
                                    const newDatePickers = node.querySelectorAll('.modern-date-picker');
                                    if (newDatePickers.length > 0) {
                                        shouldReinitialize = true;
                                    }
                                }
                            }
                        });
                    }
                });
                
                if (shouldReinitialize) {
                    console.log('New date picker elements detected, initializing...');
                    setTimeout(initializeAllDatePickers, 100);
                }
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
            
            console.log('Mutation observer set up for dynamic date picker initialization');
        }
    }

    // Public API
    window.ModernDatePicker = {
        initialize: initializeAllDatePickers,
        reinitialize: reinitializeDatePickers,
        destroy: destroyAllDatePickers,
        initializeElement: initializeDatePicker,
        isValidFormat: isValidDateFormat,
        normalizeDate: normalizeDate
    };

    // Auto-initialize with delay to ensure all other scripts are loaded
    console.log('Modern Date Picker module loaded');
    
    // Initialize immediately if DOM is ready
    if (document.readyState === 'complete') {
        console.log('DOM already complete, initializing immediately');
        setTimeout(() => {
            initializeWhenReady();
            setupModalHandlers();
            setupMutationObserver();
        }, 100);
    } else {
        // Wait for DOM to be ready
        initializeWhenReady();
        setupModalHandlers();
        setupMutationObserver();
    }
    
    // Also try initialization after a longer delay as fallback
    setTimeout(() => {
        console.log('Fallback initialization attempt...');
        const uninitializedInputs = document.querySelectorAll('.modern-date-picker:not([data-flatpickr-initialized])');
        if (uninitializedInputs.length > 0) {
            console.log(`Found ${uninitializedInputs.length} uninitialized date inputs, attempting initialization...`);
            uninitializedInputs.forEach(initializeDatePicker);
        }
    }, 2000);

})(); 