(function() {
    'use strict';

    // Helper to show a simple toast message
    function showToast(message) {
        let toast = document.createElement('div');
        toast.className = 'frontend-toast';
        toast.textContent = message;
        Object.assign(toast.style, {
            position: 'fixed',
            bottom: '20px',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: '#333',
            color: '#fff',
            padding: '10px 20px',
            borderRadius: '5px',
            zIndex: '9999',
            opacity: '0',
            transition: 'opacity 0.3s ease-in-out',
            pointerEvents: 'none'
        });
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '1';
        }, 10);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.addEventListener('transitionend', () => toast.remove());
        }, 3000);
    }

    // Helper to show a simple modal overlay
    function showModal(title = 'Action', content = 'This is a modal overlay.') {
        let modalOverlay = document.createElement('div');
        modalOverlay.className = 'frontend-modal-overlay';
        Object.assign(modalOverlay.style, {
            position: 'fixed',
            top: '0',
            left: '0',
            width: '100%',
            height: '100%',
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: '10000',
            opacity: '0',
            transition: 'opacity 0.3s ease-in-out'
        });

        let modalContent = document.createElement('div');
        modalContent.className = 'frontend-modal-content';
        Object.assign(modalContent.style, {
            backgroundColor: '#fff',
            padding: '20px',
            borderRadius: '8px',
            minWidth: '300px',
            maxWidth: '500px',
            boxShadow: '0 4px 8px rgba(0, 0, 0, 0.2)',
            position: 'relative',
            transform: 'translateY(-20px)',
            transition: 'transform 0.3s ease-in-out'
        });

        modalContent.innerHTML = `
            <h4 style="margin-top: 0; margin-bottom: 15px;">${title}</h4>
            <p>${content}</p>
            <button class="frontend-modal-close-btn" style="position: absolute; top: 10px; right: 10px; background: none; border: none; font-size: 1.2em; cursor: pointer;">&times;</button>
        `;

        modalOverlay.appendChild(modalContent);
        document.body.appendChild(modalOverlay);

        setTimeout(() => {
            modalOverlay.style.opacity = '1';
            modalContent.style.transform = 'translateY(0)';
        }, 10);

        const closeModal = () => {
            modalOverlay.style.opacity = '0';
            modalContent.style.transform = 'translateY(-20px)';
            modalOverlay.addEventListener('transitionend', () => modalOverlay.remove(), { once: true });
        };

        modalOverlay.querySelector('.frontend-modal-close-btn').addEventListener('click', closeModal, false);
        modalOverlay.addEventListener('click', (event) => {
            if (event.target === modalOverlay) {
                closeModal();
            }
        }, false);
    }

    document.addEventListener('click', function(e) {
        // Rule 2 & 3: NEVER call preventDefault/stopPropagation for a[href$=".html"]
        if (e.target.closest('a[href$=".html"]')) {
            return; // Let the browser handle navigation
        }

        // Rule 4: For a[href^="#/"]: preventDefault + show a toast "not recorded yet".
        const routeLink = e.target.closest('a[href^="#/"]');
        if (routeLink) {
            e.preventDefault();
            showToast("Not recorded yet");
            return;
        }

        // Rule 5: [role=tab]: switch active tab + show/hide tabpanel (aria-controls / *-panel id).
        // Assuming a custom tab structure based on image, using data-tab-target and data-tab-panel attributes.
        const tabElement = e.target.closest('.z-tab[data-tab-target]');
        if (tabElement) {
            e.preventDefault();
            const tabContainer = tabElement.closest('.z-tabs-container');
            const tabPanelContainer = document.querySelector('.z-tab-panels-container');

            if (tabContainer && tabPanelContainer) {
                const currentActiveTab = tabContainer.querySelector('.z-tab.active');
                const currentActivePanel = tabPanelContainer.querySelector('.z-tab-panel.active');

                // Deactivate current tab and panel
                if (currentActiveTab) {
                    currentActiveTab.classList.remove('active');
                    currentActiveTab.setAttribute('aria-selected', 'false');
                    if (currentActivePanel) {
                        currentActivePanel.classList.remove('active');
                        currentActivePanel.style.display = 'none';
                    }
                }

                // Activate clicked tab and its panel
                tabElement.classList.add('active');
                tabElement.setAttribute('aria-selected', 'true');
                const targetPanelName = tabElement.dataset.tabTarget;
                const panelToShow = tabPanelContainer.querySelector(`.z-tab-panel[data-tab-panel="${targetPanelName}"]`);
                if (panelToShow) {
                    panelToShow.classList.add('active');
                    panelToShow.style.display = ''; // Show it
                }
            }
            return;
        }

        // Rule 6: .dropdown-toggle: toggle .show on .dropdown and .dropdown-menu.
        const dropdownToggle = e.target.closest('.dropdown-toggle');
        if (dropdownToggle) {
            e.preventDefault();
            const dropdown = dropdownToggle.closest('.dropdown');
            if (dropdown) {
                dropdown.classList.toggle('show');
                const dropdownMenu = dropdown.querySelector('.dropdown-menu');
                if (dropdownMenu) {
                    dropdownMenu.classList.toggle('show');
                }
            }
            return;
        }

        // Rule 7: .accordion-button / [aria-expanded][aria-controls]: toggle submenu visibility.
        // Also handling the specific sidebar menu items like "Items", "Sales" using a button within h3 pattern.
        const accordionButton = e.target.closest('.accordion-button, h3 > button[type="button"]');
        if (accordionButton) {
            e.preventDefault();

            // Standard accordion pattern with aria-expanded
            if (accordionButton.hasAttribute('aria-expanded')) {
                const isExpanded = accordionButton.getAttribute('aria-expanded') === 'true';
                accordionButton.setAttribute('aria-expanded', String(!isExpanded));
                const controlsId = accordionButton.getAttribute('aria-controls');
                const targetPanel = document.getElementById(controlsId);
                if (targetPanel) {
                    targetPanel.classList.toggle('show');
                    targetPanel.style.display = isExpanded ? 'none' : '';
                }
            } else {
                // Sidebar menu item pattern (button within h3, submenu is next sibling ul)
                const h3Parent = accordionButton.closest('h3');
                if (h3Parent) {
                    const submenu = h3Parent.nextElementSibling; // This should be the <ul>
                    const arrowIcon = accordionButton.querySelector('.right-arrow.lpanel');

                    if (submenu && submenu.tagName === 'UL') {
                        if (arrowIcon) {
                            arrowIcon.classList.toggle('rotate-90');
                        }
                        if (submenu.style.display === 'none') {
                            submenu.style.display = ''; // Show it
                        } else {
                            submenu.style.display = 'none'; // Hide it
                        }
                    }
                }
            }
            return;
        }

        // Rule 8: .btn-primary / buttons with "New|Create|Add": show a simple modal overlay.
        const button = e.target.closest('button, input[type="button"], input[type="submit"]');
        if (button) {
            const buttonText = (button.textContent || button.value || '').trim();
            const isPrimaryButton = button.classList.contains('btn-primary');
            const isNewCreateAdd = /(new|create|add)/i.test(buttonText);

            // Specific data-agent-ids that failed validation and are buttons with "toggle" purpose
            const agentId = button.dataset.agentId;
            const toggleButtons = ['el-002', 'el-003', 'el-006', 'el-008', 'el-015'];

            if (isPrimaryButton || isNewCreateAdd) {
                e.preventDefault();
                showModal('Action Required', `You clicked on "${buttonText}". This would typically open a new form or confirm an action.`);
                return;
            } else if (toggleButtons.includes(agentId)) {
                e.preventDefault();
                // For buttons with 'toggle' purpose, simulate a state change.
                // For el-002 (Verify Account), we'll toggle a 'highlight' class on its immediate parent div.
                if (agentId === 'el-002') {
                    const parentDiv = button.closest('div');
                    if (parentDiv) {
                        parentDiv.classList.toggle('highlight'); // Custom class for visual feedback
                        showToast(`"${buttonText}" toggled highlight on parent.`);
                    }
                } else {
                    showToast(`Toggle action triggered by "${buttonText || agentId}".`);
                }
                return;
            }
        }

    }, false); // Rule 1 & 9: Use event delegation on document (bubble phase, NOT capture).

    // --- Initial page setup logic ---

    // Assume custom tab structure for main content area.
    // Set up initial active tab and hide inactive panels.
    const initialActiveTab = document.querySelector('.z-tabs-container .z-tab.active');
    const allTabPanels = document.querySelectorAll('.z-tab-panels-container .z-tab-panel');

    allTabPanels.forEach(panel => {
        panel.style.display = 'none'; // Hide all panels initially
        panel.classList.remove('active');
    });

    if (initialActiveTab) {
        initialActiveTab.setAttribute('aria-selected', 'true');
        const initialPanelTarget = initialActiveTab.dataset.tabTarget;
        const initialActivePanel = document.querySelector(`.z-tab-panels-container .z-tab-panel[data-tab-panel="${initialPanelTarget}"]`);
        if (initialActivePanel) {
            initialActivePanel.classList.add('active');
            initialActivePanel.style.display = ''; // Show the active panel
        }
    } else {
        // If no active tab is explicitly set, default to the first one
        const firstTab = document.querySelector('.z-tabs-container .z-tab');
        if (firstTab) {
            firstTab.classList.add('active');
            firstTab.setAttribute('aria-selected', 'true');
            const firstPanelTarget = firstTab.dataset.tabTarget;
            const firstPanel = document.querySelector(`.z-tab-panels-container .z-tab-panel[data-tab-panel="${firstPanelTarget}"]`);
            if (firstPanel) {
                firstPanel.classList.add('active');
                firstPanel.style.display = '';
            }
        }
    }

    // Initial setup for sidebar accordion menus
    document.querySelectorAll('li > div > div > h3').forEach(h3 => {
        const button = h3.querySelector('button[type="button"]');
        const submenu = h3.nextElementSibling; // The ul element immediately after h3
        const arrowIcon = button ? button.querySelector('.right-arrow.lpanel') : null;

        if (button && submenu && submenu.tagName === 'UL') {
            const isInitiallyExpanded = arrowIcon && arrowIcon.classList.contains('rotate-90');
            if (!isInitiallyExpanded) {
                submenu.style.display = 'none'; // Hide collapsed submenus
            }
        }
    });

})();