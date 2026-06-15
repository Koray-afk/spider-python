(function() {
    // Helper function to show a toast message
    function showToast(message) {
        let toast = document.createElement('div');
        toast.className = 'toast-message';
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
            zIndex: '10000',
            opacity: '0',
            transition: 'opacity 0.3s ease-in-out',
            pointerEvents: 'none',
            whiteSpace: 'nowrap'
        });
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '1';
        }, 10); // Small delay to trigger CSS transition

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.addEventListener('transitionend', () => toast.remove());
        }, 3000);
    }

    // Helper function to show a simple modal overlay
    function showModal() {
        let modalOverlay = document.createElement('div');
        modalOverlay.className = 'modal-overlay';
        Object.assign(modalOverlay.style, {
            position: 'fixed',
            top: '0',
            left: '0',
            width: '100%',
            height: '100%',
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: '9999'
        });

        let modalContent = document.createElement('div');
        modalContent.className = 'modal-content';
        Object.assign(modalContent.style, {
            background: 'white',
            padding: '20px',
            borderRadius: '8px',
            textAlign: 'center',
            minWidth: '300px'
        });
        modalContent.innerHTML = `
            <h3>Action Not Recorded</h3>
            <p>This is a simulated modal dialog for creating a new item/record.</p>
            <button class="close-modal-btn" style="padding: 8px 15px; margin-top: 15px; cursor: pointer;">Close</button>
        `;
        modalOverlay.appendChild(modalContent);
        document.body.appendChild(modalOverlay);

        modalOverlay.querySelector('.close-modal-btn').onclick = () => {
            modalOverlay.remove();
        };

        // Close modal if clicking outside the content
        modalOverlay.onclick = (e) => {
            if (e.target === modalOverlay) {
                modalOverlay.remove();
            }
        };
    }

    document.addEventListener('click', function(e) {
        let target = e.target;

        // Rule 2 & 3: For a[href$=".html"] links, do nothing (let browser navigate)
        let htmlLink = target.closest('a[href$=".html"]');
        if (htmlLink) {
            return;
        }

        // Rule 4: For a[href^="#/"] links, preventDefault and show toast
        let hashLink = target.closest('a[href^="#/"]');
        if (hashLink) {
            e.preventDefault();
            showToast('not recorded yet');
            return;
        }

        // Rule 5: For [role=tab], switch active tab and show/hide tabpanel
        let tab = target.closest('[role="tab"]');
        if (tab) {
            e.preventDefault();
            let currentActiveTab = tab.closest('.tab-list')?.querySelector('[role="tab"][aria-selected="true"]');
            if (currentActiveTab && currentActiveTab !== tab) {
                currentActiveTab.setAttribute('aria-selected', 'false');
                let currentPanelId = currentActiveTab.getAttribute('aria-controls');
                if (currentPanelId) {
                    document.getElementById(currentPanelId)?.setAttribute('hidden', 'true');
                }
            }
            tab.setAttribute('aria-selected', 'true');
            let panelId = tab.getAttribute('aria-controls');
            if (panelId) {
                document.getElementById(panelId)?.removeAttribute('hidden');
            }
            return;
        }

        // Rule 6: For .dropdown-toggle, toggle .show on .dropdown and .dropdown-menu
        let dropdownToggle = target.closest('.dropdown-toggle');
        // Also check elements identified as dropdown toggles in agent data, even if they don't have the class
        if (!dropdownToggle) {
            const agentDropdownToggles = ['el-002', 'el-003', 'el-006', 'el-008', 'el-015', 'el-216']; // el-212 already has class
            let potentialToggle = target.closest('button, a'); // Could be a button or an anchor
            if (potentialToggle && agentDropdownToggles.includes(potentialToggle.dataset.agentId)) {
                dropdownToggle = potentialToggle;
            }
        }

        if (dropdownToggle) {
            e.preventDefault();
            let parentDropdown = dropdownToggle.closest('.dropdown');
            let dropdownMenu = parentDropdown ? parentDropdown.querySelector('.dropdown-menu') : dropdownToggle.nextElementSibling; // Try sibling menu if no parent .dropdown

            // Close all currently open dropdowns first, unless it's the one being clicked to toggle itself
            document.querySelectorAll('.dropdown.show, .dropdown-menu.show, button.show').forEach(openElement => {
                // If the element is not the current dropdown being toggled (or its menu)
                if (!parentDropdown || !(openElement === parentDropdown || parentDropdown.contains(openElement))) {
                    openElement.classList.remove('show');
                }
                // Handle button toggles without parentDropdown explicitly
                if (openElement === dropdownToggle && !parentDropdown) { /* do nothing, will toggle below */ }
                else if (openElement.tagName === 'BUTTON' && openElement.classList.contains('show') && openElement !== dropdownToggle) {
                    openElement.classList.remove('show');
                }
            });


            if (parentDropdown) {
                parentDropdown.classList.toggle('show');
                if (dropdownMenu) {
                    dropdownMenu.classList.toggle('show');
                }
            } else if (dropdownMenu) { // If no parent .dropdown but a sibling .dropdown-menu was found
                dropdownMenu.classList.toggle('show');
                dropdownToggle.classList.toggle('show'); // Toggle 'show' on the button itself to indicate active state
            } else {
                dropdownToggle.classList.toggle('show'); // Fallback to just toggling 'show' on the button
            }
            return;
        }

        // Rule 7: For .accordion-button / [aria-expanded][aria-controls] OR sidebar navigation toggles
        let accordionToggle = target.closest('.accordion-button, [aria-expanded][aria-controls]');
        let sidebarNavToggle = null;

        // Check for specific sidebar navigation structure (h3 > button that toggles a sibling ul)
        if (!accordionToggle) {
            let buttonInH3 = target.closest('h3 > button');
            if (buttonInH3 && buttonInH3.querySelector('.right-arrow.lpanel')) {
                sidebarNavToggle = buttonInH3;
            }
        }

        if (accordionToggle || sidebarNavToggle) {
            e.preventDefault();
            let toggleElement = accordionToggle || sidebarNavToggle;

            // Handle standard accordion behavior if aria-expanded is present
            if (toggleElement.hasAttribute('aria-expanded')) {
                let isExpanded = toggleElement.getAttribute('aria-expanded') === 'true';
                toggleElement.setAttribute('aria-expanded', String(!isExpanded));
                let controlledElementId = toggleElement.getAttribute('aria-controls');
                if (controlledElementId) {
                    let controlledElement = document.getElementById(controlledElementId);
                    if (controlledElement) {
                        controlledElement.toggleAttribute('hidden', isExpanded);
                    }
                }
            }
            // Handle custom sidebar navigation behavior
            else if (sidebarNavToggle) {
                let arrowSvg = sidebarNavToggle.querySelector('.right-arrow.lpanel');
                // The UL to toggle is the next sibling of the H3 (parent of the button)
                let contentUl = sidebarNavToggle.closest('h3')?.nextElementSibling;

                if (arrowSvg && contentUl && contentUl.tagName === 'UL') {
                    let isExpanded = arrowSvg.classList.contains('rotate-90'); // Assume rotate-90 means expanded
                    arrowSvg.classList.toggle('rotate-90', !isExpanded);
                    contentUl.style.display = isExpanded ? 'none' : 'block';
                }
            }
            return;
        }

        // Rule 8: For .btn-primary or buttons with "New|Create|Add" (case-insensitive)
        let isModalTrigger = false;
        let buttonOrLink = target.closest('button, a');
        if (buttonOrLink) {
            const textContent = buttonOrLink.textContent.toLowerCase();
            const title = buttonOrLink.title?.toLowerCase() || '';
            const ariaLabel = buttonOrLink.ariaLabel?.toLowerCase() || '';

            const isNewCreateAddAction =
                textContent.includes('new') || textContent.includes('create') || textContent.includes('add') || textContent.includes('record') || // "Record New Payment"
                title.includes('new') || title.includes('create') || title.includes('add') || title.includes('record') || title.includes('log time') || // "Log Time (c+t)"
                ariaLabel.includes('new') || ariaLabel.includes('create') || ariaLabel.includes('add') || ariaLabel.includes('record');

            if (buttonOrLink.classList.contains('btn-primary') || isNewCreateAddAction) {
                // Exclude elements that are also known dropdown toggles (handled earlier)
                const agentDropdownToggles = ['el-002', 'el-003', 'el-006', 'el-008', 'el-015', 'el-216'];
                if (!agentDropdownToggles.includes(buttonOrLink.dataset.agentId)) {
                    isModalTrigger = true;
                }
            }
        }

        if (isModalTrigger) {
            e.preventDefault();
            showModal();
            return;
        }

        // Global close: If the click wasn't handled by any specific interactive element, close all open dropdowns.
        document.querySelectorAll('.dropdown.show, .dropdown-menu.show, button.show').forEach(openElement => {
            openElement.classList.remove('show');
        });

    }, false); // Rule 1: addEventListener with capture=false (omitted is default)

    // Close dropdowns and modals on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.querySelectorAll('.dropdown.show, .dropdown-menu.show, button.show').forEach(openElement => {
                openElement.classList.remove('show');
            });
            let modalOverlay = document.querySelector('.modal-overlay');
            if (modalOverlay) {
                modalOverlay.remove();
            }
        }
    }, false);
})();