(function() {
    // Helper function to show a toast message
    function showToast(message) {
        const toast = document.createElement('div');
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: rgba(0, 0, 0, 0.8);
            color: #fff;
            padding: 10px 20px;
            border-radius: 5px;
            z-index: 9999;
            font-family: sans-serif;
            font-size: 14px;
            opacity: 0;
            transition: opacity 0.3s ease-in-out;
            pointer-events: none;
        `;
        document.body.appendChild(toast);

        requestAnimationFrame(() => {
            toast.style.opacity = '1';
        });

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.addEventListener('transitionend', () => toast.remove(), { once: true });
        }, 3000);
    }

    // Helper function to show a simple modal overlay
    function showSimpleModal(message = "This is a generic modal action.") {
        let modal = document.getElementById('simple-modal-overlay');
        if (modal) {
            modal.remove(); // Remove existing modal if any
        }

        modal = document.createElement('div');
        modal.id = 'simple-modal-overlay';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10000;
        `;

        const modalContent = document.createElement('div');
        modalContent.style.cssText = `
            background-color: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
            max-width: 400px;
            width: 90%;
            text-align: center;
            position: relative;
            font-family: sans-serif;
        `;
        modalContent.innerHTML = `<p>${message}</p>`;

        const closeButton = document.createElement('button');
        closeButton.textContent = 'X';
        closeButton.style.cssText = `
            position: absolute;
            top: 10px;
            right: 10px;
            background: none;
            border: none;
            font-size: 1.2em;
            cursor: pointer;
        `;
        closeButton.onclick = () => modal.remove();

        modalContent.appendChild(closeButton);
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
    }

    // Map for sidebar accordion-like toggles (specific to the provided HTML structure)
    const sidebarToggleTargets = {
        'el-031': 'ul[data-agent-id="el-036"]', // Items button -> Items ul
        'el-044': 'ul[data-agent-id="el-049"]', // Sales button -> Sales ul
        'el-090': 'ul[data-agent-id="el-095"]', // Purchases button -> Purchases ul
        'el-137': 'ul[data-agent-id="el-142"]', // Time Tracking button -> Time Tracking ul
        'el-157': 'ul[data-agent-id="el-162"]'  // Accountant button -> Accountant ul
    };

    // Data for interactive elements with "toggle" action not covered by explicit rules
    const genericToggleElementsData = [
      {"id": "el-002", "text": "Verify Account", "purpose": "Open dropdown menu", "expected_action": "toggle"},
      {"id": "el-003", "text": "Navigate To (Opt+0)", "purpose": "Open dropdown menu", "expected_action": "toggle"},
      {"id": "el-008", "text": "Search", "purpose": "Open dropdown menu", "expected_action": "toggle"},
      {"id": "el-015", "text": "Quick Add", "purpose": "Open dropdown menu", "expected_action": "toggle"}
    ];

    document.addEventListener('click', function(e) {
        // Rule 2 & 3: NEVER call preventDefault/stopPropagation for a[href$=".html"]
        const htmlLink = e.target.closest('a[href$=".html"]');
        if (htmlLink) {
            return; // Let browser navigate
        }

        // Rule 4: For a[href^="#/"]: preventDefault + show a toast
        const hashLink = e.target.closest('a[href^="#/"]');
        if (hashLink) {
            e.preventDefault();
            showToast("Not recorded yet");
            return;
        }

        // Rule 6: .dropdown-toggle: toggle .show on .dropdown and .dropdown-menu
        const dropdownToggle = e.target.closest('.dropdown-toggle');
        if (dropdownToggle) {
            e.preventDefault();
            const dropdown = dropdownToggle.closest('.dropdown');
            const dropdownMenu = dropdown ? dropdown.querySelector('.dropdown-menu') : null;

            // Close other open dropdowns first
            document.querySelectorAll('.dropdown.show, .dropdown-menu.show').forEach(el => {
                if (el !== dropdown && el !== dropdownMenu) {
                    el.classList.remove('show');
                }
            });

            if (dropdown) {
                dropdown.classList.toggle('show');
            }
            if (dropdownMenu) {
                dropdownMenu.classList.toggle('show');
            }
            return;
        }

        // Close dropdowns if click is outside any dropdown (must be after dropdownToggle check)
        if (!e.target.closest('.dropdown') && !e.target.closest('.dropdown-menu')) {
            document.querySelectorAll('.dropdown.show, .dropdown-menu.show').forEach(el => {
                el.classList.remove('show');
            });
        }

        // Rule 5: [role=tab]: switch active tab + show/hide tabpanel
        const tab = e.target.closest('[role="tab"]');
        if (tab) {
            e.preventDefault();
            const tabList = tab.closest('[role="tablist"]');
            if (tabList) {
                tabList.querySelectorAll('[role="tab"]').forEach(t => {
                    t.setAttribute('aria-selected', 'false');
                    t.classList.remove('active');
                    const panelId = t.getAttribute('aria-controls');
                    if (panelId) {
                        const panel = document.getElementById(panelId);
                        if (panel) {
                            panel.style.display = 'none';
                            panel.setAttribute('hidden', 'true');
                        }
                    }
                });
            }
            tab.setAttribute('aria-selected', 'true');
            tab.classList.add('active');
            const activePanelId = tab.getAttribute('aria-controls');
            if (activePanelId) {
                const activePanel = document.getElementById(activePanelId);
                if (activePanel) {
                    activePanel.style.display = 'block';
                    activePanel.removeAttribute('hidden');
                }
            }
            return;
        }

        // Rule 7: .accordion-button / [aria-expanded][aria-controls]: toggle submenu visibility
        const accordionToggle = e.target.closest('.accordion-button, [aria-expanded][aria-controls]');
        if (accordionToggle) {
            e.preventDefault();
            const isExpanded = accordionToggle.getAttribute('aria-expanded') === 'true';
            accordionToggle.setAttribute('aria-expanded', String(!isExpanded));
            const controlsId = accordionToggle.getAttribute('aria-controls');
            const controlledElement = document.getElementById(controlsId);
            if (controlledElement) {
                controlledElement.style.display = isExpanded ? 'none' : 'block';
                controlledElement.setAttribute('hidden', isExpanded ? 'true' : 'false');
            }
            return;
        }

        // Handle specific sidebar accordions (e.g., "Items", "Sales") as implied by JSON 'toggle' action
        const sidebarAccordionToggle = e.target.closest('li > div > div > h3 > button');
        const sidebarTogglerId = sidebarAccordionToggle ? sidebarAccordionToggle.getAttribute('data-agent-id') : null;
        if (sidebarTogglerId && sidebarToggleTargets[sidebarTogglerId]) {
            e.preventDefault();
            const targetUlSelector = sidebarToggleTargets[sidebarTogglerId];
            const parentLi = sidebarAccordionToggle.closest('li');
            const targetUl = parentLi ? parentLi.querySelector(targetUlSelector) : null;
            if (targetUl) {
                const isHidden = targetUl.style.display === 'none' || targetUl.style.display === '';
                targetUl.style.display = isHidden ? 'block' : 'none';

                const arrow = sidebarAccordionToggle.querySelector('.right-arrow');
                if (arrow) {
                    arrow.style.transform = isHidden ? 'rotate(90deg)' : 'rotate(0deg)';
                    arrow.style.transition = 'transform 0.2s ease-in-out';
                }
            }
            return;
        }

        // Handle the "Dashboard | Getting Started | Recent Updates" as visual tabs
        const visualTab = e.target.closest('[data-agent-id="el-216"], [data-agent-id="el-218"], [data-agent-id="el-220"]');
        if (visualTab) {
            e.preventDefault();
            const parentUl = visualTab.closest('ul[data-agent-id="el-214"]');
            if (parentUl) {
                parentUl.querySelectorAll('li').forEach(li => {
                    li.classList.remove('active');
                });
            }
            visualTab.closest('li').classList.add('active');
            showToast(`Switched to ${visualTab.textContent.trim()} tab.`);
            return;
        }

        // Rule 8: .btn-primary / buttons with "New|Create|Add": show a simple modal overlay
        const button = e.target.closest('button, a[role="button"]');
        if (button) {
            const text = (button.textContent || '').trim();
            const title = (button.title || '').trim();
            const isNewCreateAdd = /^(New|Create|Add)/i.test(text) || /^(New|Create|Add)/i.test(title);

            if (button.classList.contains('btn-primary') || isNewCreateAdd) {
                e.preventDefault();
                showSimpleModal(`Action: '${text || title || 'New/Create/Add'}' clicked.`);
                return;
            }
        }

        // Fallback generic toggle for other buttons with expected_action: "toggle" from JSON,
        // if not covered by more specific dropdown or accordion rules or modal rule.
        const genericToggleCandidate = e.target.closest('button');
        if (genericToggleCandidate) {
            const dataAgentId = genericToggleCandidate.getAttribute('data-agent-id');
            const matchingElement = genericToggleElementsData.find(item => item.id === dataAgentId);

            if (matchingElement && matchingElement.expected_action === 'toggle' && !genericToggleCandidate.classList.contains('dropdown-toggle')) {
                e.preventDefault();
                showToast(`Generic toggle action for '${matchingElement.text || matchingElement.purpose}' (not fully implemented yet).`);
                return;
            }
        }

    }, false); // Rule 9: Use event delegation on document (bubble phase, NOT capture)
})();