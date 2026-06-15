(function() {
    // --- Toast Function ---
    function showToast(message) {
        const toastId = 'app-toast';
        let toast = document.getElementById(toastId);

        if (!toast) {
            toast = document.createElement('div');
            toast.id = toastId;
            toast.style.cssText = `
                position: fixed;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                background-color: #333;
                color: #fff;
                padding: 10px 20px;
                border-radius: 5px;
                z-index: 10000;
                opacity: 0;
                transition: opacity 0.3s ease-in-out;
            `;
            document.body.appendChild(toast);
        }

        toast.textContent = message;
        toast.style.opacity = '1';

        // Clear any existing timer to prevent premature fading
        if (toast.timer) {
            clearTimeout(toast.timer);
        }
        toast.timer = setTimeout(() => {
            toast.style.opacity = '0';
            toast.addEventListener('transitionend', function handler() {
                if (toast.style.opacity === '0') {
                    toast.remove();
                }
                toast.removeEventListener('transitionend', handler);
            });
        }, 3000);
    }

    // --- Modal Functionality ---
    let _currentModal = null;

    function createAndShowModal() {
        if (_currentModal) {
            _currentModal.style.display = 'flex';
            return;
        }

        const modalOverlay = document.createElement('div');
        modalOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            opacity: 0;
            transition: opacity 0.3s ease-in-out;
        `;

        const modalContent = document.createElement('div');
        modalContent.style.cssText = `
            background-color: #fff;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            max-width: 500px;
            width: 90%;
            text-align: center;
            position: relative;
            transform: translateY(-20px);
            transition: transform 0.3s ease-in-out;
        `;

        const modalTitle = document.createElement('h3');
        modalTitle.textContent = 'Simple Modal';
        modalTitle.style.marginBottom = '20px';
        modalTitle.style.color = '#333';

        const modalText = document.createElement('p');
        modalText.textContent = 'This is a simple modal overlay triggered by a button click.';
        modalText.style.marginBottom = '30px';
        modalText.style.color = '#666';

        const closeButton = document.createElement('button');
        closeButton.textContent = 'Close';
        closeButton.style.cssText = `
            padding: 10px 20px;
            background-color: #007bff;
            color: #fff;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        `;
        closeButton.onclick = () => {
            modalOverlay.style.opacity = '0';
            modalContent.style.transform = 'translateY(-20px)';
            modalOverlay.addEventListener('transitionend', function handler() {
                if (modalOverlay.style.opacity === '0') {
                    modalOverlay.style.display = 'none';
                }
                modalOverlay.removeEventListener('transitionend', handler);
            });
        };

        modalContent.appendChild(modalTitle);
        modalContent.appendChild(modalText);
        modalContent.appendChild(closeButton);
        modalOverlay.appendChild(modalContent);
        document.body.appendChild(modalOverlay);

        _currentModal = modalOverlay;

        // Animate in
        setTimeout(() => {
            modalOverlay.style.opacity = '1';
            modalContent.style.transform = 'translateY(0)';
        }, 10);
    }

    // --- Close all dropdowns ---
    function closeAllDropdowns() {
        document.querySelectorAll('.dropdown.show').forEach(dropdown => {
            dropdown.classList.remove('show');
            const menu = dropdown.querySelector('.dropdown-menu');
            if (menu) {
                menu.classList.remove('show');
            }
        });
    }

    // --- Main Event Listener ---
    document.addEventListener('click', function(e) {
        // Rule 9: Event delegation on document (bubble phase)

        // Rule 2 & 3: For a[href$=".html"] links: do NOTHING
        if (e.target.closest('a[href$=".html"]')) {
            return;
        }

        // --- Handle specific interactive elements ---

        // Rule 4: For a[href^="#/"]: preventDefault + show a toast
        const hashLink = e.target.closest('a[href^="#/"]');
        if (hashLink) {
            e.preventDefault();
            showToast("not recorded yet");
            return;
        }

        // Rule 5: [role=tab]: switch active tab + show/hide tabpanel
        const tab = e.target.closest('[role="tab"]');
        if (tab) {
            e.preventDefault();
            const tablist = tab.closest('[role="tablist"]');
            if (tablist) {
                // Deactivate current tab
                tablist.querySelectorAll('[role="tab"][aria-selected="true"]').forEach(activeTab => {
                    activeTab.setAttribute('aria-selected', 'false');
                    const activeTabPanelId = activeTab.getAttribute('aria-controls');
                    if (activeTabPanelId) {
                        const activeTabPanel = document.getElementById(activeTabPanelId);
                        if (activeTabPanel) {
                            activeTabPanel.hidden = true;
                        }
                    }
                });
            }

            // Activate clicked tab
            tab.setAttribute('aria-selected', 'true');
            const tabPanelId = tab.getAttribute('aria-controls');
            if (tabPanelId) {
                const tabPanel = document.getElementById(tabPanelId);
                if (tabPanel) {
                    tabPanel.hidden = false;
                }
            }
            return;
        }

        // Rule 6: .dropdown-toggle: toggle .show on .dropdown and .dropdown-menu
        const dropdownToggle = e.target.closest('.dropdown-toggle');
        const isClickInsideAnyDropdown = e.target.closest('.dropdown');

        if (dropdownToggle) {
            e.preventDefault();
            const dropdown = dropdownToggle.closest('.dropdown');
            if (dropdown) {
                const wasOpen = dropdown.classList.contains('show');
                closeAllDropdowns(); // Close all existing dropdowns

                if (!wasOpen) { // If the clicked dropdown was not open, open it now
                    dropdown.classList.add('show');
                    const dropdownMenu = dropdown.querySelector('.dropdown-menu');
                    if (dropdownMenu) {
                        dropdownMenu.classList.add('show');
                    }
                }
            }
            return;
        } else if (!isClickInsideAnyDropdown) {
            // Clicked outside any dropdown, close all open ones
            closeAllDropdowns();
        }


        // Rule 7: .accordion-button / [aria-expanded][aria-controls]: toggle submenu visibility.
        const accordionButton = e.target.closest('.accordion-button, [aria-expanded][aria-controls]');
        if (accordionButton && accordionButton.hasAttribute('aria-controls')) {
            e.preventDefault();
            const isExpanded = accordionButton.getAttribute('aria-expanded') === 'true';
            accordionButton.setAttribute('aria-expanded', String(!isExpanded));

            const controlsId = accordionButton.getAttribute('aria-controls');
            const controlledElement = document.getElementById(controlsId);

            if (controlledElement) {
                controlledElement.hidden = isExpanded;
            }
            return;
        }


        // Rule 8: .btn-primary / buttons with "New|Create|Add": show a simple modal overlay.
        const button = e.target.closest('button.btn-primary, button');
        if (button) {
            const text = button.textContent ? button.textContent.trim() : '';
            const title = button.title ? button.title.trim() : '';
            const isNewCreateAddKeyword = /(New|Create|Add|Record)/i.test(text) || /(New|Create|Add|Record)/i.test(title);

            // Check for buttons with the 'add-new' class or containing a plus SVG icon
            const isPlusIconButton = button.classList.contains('add-new') ||
                                     (button.querySelector('svg path[d*="H286V96c0-16.6-13.4-30-30-30s-30 13.4-30 30v130H96c-16.6 0-30 13.4-30 30s13.4 30 30 30h130v130c0 16.6 13.4 30 30 30s30-13.4 30-30V286h130c16.6 0 30-13.4 30-30s-13.4-30-30-30"]')) ||
                                     (button.querySelector('svg path[d*="h-7.06V8.47a.47.47 0 10-.94 0v7.06H8.47a.47.47 0 100 .94h7.06v7.06a.47.47 0 10.94 0v-7.06h7.06a.47.47 0 100-.94z"]'));

            if (isNewCreateAddKeyword || isPlusIconButton) {
                e.preventDefault();
                createAndShowModal();
                return;
            }
        }
    }, false); // Rule 1: capture=false
})();