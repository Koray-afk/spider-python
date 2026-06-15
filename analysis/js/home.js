(function() {
    /**
     * Displays a transient toast message at the bottom center of the screen.
     * @param {string} message The message to display in the toast.
     */
    function showToast(message) {
        const toast = document.createElement('div');
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: #333;
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            z-index: 10000;
            opacity: 0;
            transition: opacity 0.5s ease-in-out;
        `;
        document.body.appendChild(toast);

        // Trigger fade-in
        setTimeout(() => {
            toast.style.opacity = '1';
        }, 10);

        // Fade-out and remove after 3 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.addEventListener('transitionend', () => toast.remove());
        }, 3000);
    }

    /**
     * Displays a simple modal overlay with a message and a close button.
     * @param {string} message The message to display inside the modal.
     */
    function showSimpleModal(message) {
        const modalOverlay = document.createElement('div');
        modalOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.6);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        `;

        const modalContent = document.createElement('div');
        modalContent.textContent = message;
        modalContent.style.cssText = `
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            max-width: 80%;
            text-align: center;
        `;

        const closeButton = document.createElement('button');
        closeButton.textContent = 'Close';
        closeButton.style.cssText = `
            margin-top: 20px;
            padding: 8px 15px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        `;
        closeButton.onclick = () => modalOverlay.remove();

        modalContent.appendChild(closeButton);
        modalOverlay.appendChild(modalContent);
        document.body.appendChild(modalOverlay);

        // Allow clicking outside the content to close the modal
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                modalOverlay.remove();
            }
        });
    }

    document.addEventListener('click', function(e) {
        // Rule 3: For a[href$=".html"] links, do NOTHING — stitched href already works.
        // Rule 2: NEVER call preventDefault/stopPropagation when e.target.closest('a[href$=".html"]') is truthy.
        const htmlLink = e.target.closest('a[href$=".html"]');
        if (htmlLink) {
            return;
        }

        // Rule 4: For a[href^="#/"]: preventDefault + show a toast "not recorded yet".
        const hashLink = e.target.closest('a[href^="#/"]');
        if (hashLink) {
            e.preventDefault();
            showToast("not recorded yet");
            return;
        }

        // Rule 5: [role=tab]: switch active tab + show/hide tabpanel (aria-controls / *-panel id).
        const tab = e.target.closest('[role="tab"]');
        if (tab) {
            e.preventDefault();
            const tabContainer = tab.closest('ul') || tab.closest('div[role="tablist"]');

            if (tabContainer) {
                tabContainer.querySelectorAll('[role="tab"]').forEach(t => {
                    t.setAttribute('aria-selected', 'false');
                    const panelId = t.getAttribute('aria-controls');
                    if (panelId) {
                        const panel = document.getElementById(panelId);
                        if (panel) panel.setAttribute('aria-hidden', 'true');
                    }
                });

                tab.setAttribute('aria-selected', 'true');
                const activePanelId = tab.getAttribute('aria-controls');
                if (activePanelId) {
                    const activePanel = document.getElementById(activePanelId);
                    if (activePanel) activePanel.setAttribute('aria-hidden', 'false');
                }
            }
            return;
        }

        // Rule 6: .dropdown-toggle: toggle .show on .dropdown and .dropdown-menu.
        const dropdownToggle = e.target.closest('.dropdown-toggle');
        if (dropdownToggle) {
            const dropdown = dropdownToggle.closest('.dropdown');
            if (dropdown) {
                const isShowing = dropdown.classList.contains('show');
                
                // Close all other dropdowns
                document.querySelectorAll('.dropdown.show').forEach(openDropdown => {
                    if (openDropdown !== dropdown) {
                        openDropdown.classList.remove('show');
                        const menu = openDropdown.querySelector('.dropdown-menu');
                        if (menu) menu.classList.remove('show');
                    }
                });
                
                // Toggle the clicked dropdown
                dropdown.classList.toggle('show', !isShowing);
                const dropdownMenu = dropdown.querySelector('.dropdown-menu');
                if (dropdownMenu) {
                    dropdownMenu.classList.toggle('show', !isShowing);
                }
            }
            return;
        }

        // Rule 7: .accordion-button / [aria-expanded][aria-controls]: toggle submenu visibility.
        const accordionToggle = e.target.closest('.accordion-button') || e.target.closest('h3 > button');
        if (accordionToggle) {
            e.preventDefault();

            // Initialize aria-expanded if not present
            if (!accordionToggle.hasAttribute('aria-expanded')) {
                accordionToggle.setAttribute('aria-expanded', 'false');
            }

            const isExpanded = accordionToggle.getAttribute('aria-expanded') === 'true';
            accordionToggle.setAttribute('aria-expanded', String(!isExpanded));

            let controlledElement = null;
            const controlledElementId = accordionToggle.getAttribute('aria-controls');

            if (controlledElementId) {
                controlledElement = document.getElementById(controlledElementId);
            } else {
                // Fallback: find the sibling <ul> in the sidebar structure (e.g., li > div > div > h3 > button + ul)
                const parentH3 = accordionToggle.closest('h3');
                if (parentH3 && parentH3.nextElementSibling && parentH3.nextElementSibling.tagName === 'UL') {
                    controlledElement = parentH3.nextElementSibling;
                } else if (parentH3) { // Try finding within the same parent of h3
                    controlledElement = parentH3.parentElement.querySelector('ul');
                }
            }

            if (controlledElement) {
                controlledElement.style.display = isExpanded ? 'none' : ''; // Toggles between hidden and default display
            }
            return;
        }

        // Rule 8: .btn-primary / buttons with "New|Create|Add": show a simple modal overlay.
        const button = e.target.closest('button');
        if (button) {
            const buttonText = button.textContent.toLowerCase();
            const buttonTitle = button.title ? button.title.toLowerCase() : '';

            const isPrimary = button.classList.contains('btn-primary');
            const isNewCreateAdd = buttonText.includes('new') || buttonText.includes('create') || buttonText.includes('add') ||
                                   buttonTitle.includes('new') || buttonTitle.includes('create') || buttonTitle.includes('add');

            if (isPrimary || isNewCreateAdd) {
                e.preventDefault();
                showSimpleModal("This is a placeholder modal for New/Create/Add action.");
                return;
            }
        }
        
        // Close dropdowns if the click is outside any active dropdown or its toggle
        if (!e.target.closest('.dropdown.show') && !e.target.closest('.dropdown-toggle')) {
            document.querySelectorAll('.dropdown.show').forEach(openDropdown => {
                openDropdown.classList.remove('show');
                const menu = openDropdown.querySelector('.dropdown-menu');
                if (menu) menu.classList.remove('show');
            });
        }
    }, false); // Rule 9: Use event delegation on document (bubble phase, NOT capture).
})();