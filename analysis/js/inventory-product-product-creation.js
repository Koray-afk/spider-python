(function() {
    function showToast(message) {
        console.log("Toast: " + message);
        // alert("Toast: " + message); // Uncomment for visual feedback
    }

    function showModal(message) {
        console.log("Modal: " + message);
        // alert("Modal: " + message); // Uncomment for visual feedback
    }

    document.addEventListener('click', function(event) {
        let target = event.target;

        // Rule 2 & 3: NEVER call preventDefault/stopPropagation when e.target.closest('a[href$=".html"]') is truthy
        let htmlLink = target.closest('a[href$=".html"]');
        if (htmlLink) {
            // Let the browser navigate naturally. Do nothing.
            return;
        }

        // Rule 4: For a[href^="#/"]: preventDefault + show a toast "not recorded yet"
        let hashLink = target.closest('a[href^="#/"]');
        if (hashLink) {
            event.preventDefault();
            showToast("This feature is not recorded yet.");
            return;
        }

        // Rule 6: .dropdown-toggle: toggle .show on .dropdown and .dropdown-menu.
        let dropdownToggle = target.closest('.dropdown-toggle');
        if (dropdownToggle) {
            event.preventDefault();
            let dropdown = dropdownToggle.closest('.dropdown');
            if (dropdown) {
                dropdown.classList.toggle('show');
                // Attempt to find a dropdown-menu child or sibling
                let dropdownMenu = dropdown.querySelector('.dropdown-menu');
                if (!dropdownMenu && dropdown.nextElementSibling && dropdown.nextElementSibling.classList.contains('dropdown-menu')) {
                    dropdownMenu = dropdown.nextElementSibling;
                }
                if (dropdownMenu) {
                    dropdownMenu.classList.toggle('show');
                }
            }
            return;
        }

        // Rule 7: .accordion-button / [aria-expanded][aria-controls]: toggle submenu visibility
        // This targets the sidebar navigation's expandable sections (e.g., Items, Sales, Purchases)
        let accordionHeaderButton = target.closest('h3 > button');
        if (accordionHeaderButton) {
            event.preventDefault();
            let parentLi = accordionHeaderButton.closest('li');
            if (parentLi) {
                let submenu = parentLi.querySelector('ul'); // The submenu is a child UL of the LI
                let arrowSvg = accordionHeaderButton.querySelector('svg.right-arrow'); // The arrow SVG for rotation

                if (submenu) {
                    const isHidden = submenu.style.display === 'none';
                    submenu.style.display = isHidden ? '' : 'none'; // Toggle display
                    if (arrowSvg) {
                        arrowSvg.classList.toggle('rotate-90', isHidden); // Add rotate-90 if showing, remove if hiding
                    }
                }
            }
            return;
        }
        
        // Rule 5: [role=tab]: switch active tab + show/hide tabpanel (aria-controls / *-panel id)
        let tab = target.closest('[role="tab"]');
        if (tab) {
            event.preventDefault();
            let tablist = tab.closest('[role="tablist"]');
            if (tablist) {
                // Deactivate current active tab
                let currentActiveTab = tablist.querySelector('[role="tab"][aria-selected="true"]');
                if (currentActiveTab && currentActiveTab !== tab) {
                    currentActiveTab.setAttribute('aria-selected', 'false');
                    let currentPanelId = currentActiveTab.getAttribute('aria-controls');
                    let currentPanel = document.getElementById(currentPanelId);
                    if (currentPanel) {
                        currentPanel.setAttribute('hidden', 'true');
                    }
                }

                // Activate clicked tab
                tab.setAttribute('aria-selected', 'true');
                let panelId = tab.getAttribute('aria-controls');
                let panel = document.getElementById(panelId);
                if (panel) {
                    panel.removeAttribute('hidden');
                }
            }
            return;
        }

        // Rule 8: .btn-primary / buttons with "New|Create|Add": show a simple modal overlay.
        let button = target.closest('button');
        if (button) {
            const buttonText = (button.textContent || '').trim().toLowerCase();
            const buttonTitle = (button.title || '').trim().toLowerCase();

            // Check if it's a button with specific keywords in text or title
            if (buttonText.includes('new') || buttonText.includes('create') || buttonText.includes('add') ||
                buttonTitle.includes('new') || buttonTitle.includes('create') || buttonTitle.includes('add')) {
                
                // Exclude the 'Verify Account' button as it's not a modal trigger in this context
                if (!buttonText.includes('verify account')) { 
                    event.preventDefault();
                    showModal("New/Create/Add modal or action triggered!");
                    return;
                }
            }
        }

    }, false); // Rule 1 & 9: Use bubble phase (false), not capture.

    // Initial setup for sidebar accordions: ensure only 'Items' is expanded and others are collapsed.
    // The HTML already reflects 'Items' as expanded and others collapsed via initial classes/styles.
    // This code ensures non-Items are collapsed and their arrows are correctly oriented if the HTML was inconsistent.
    document.querySelectorAll('nav ul > li').forEach(li => {
        let button = li.querySelector('h3 > button');
        let submenu = li.querySelector('ul');
        let arrowSvg = button ? button.querySelector('svg.right-arrow') : null;

        if (button && submenu && arrowSvg) {
            const isItemsSection = li.querySelector('span[data-agent-id="el-034"]')?.textContent.trim() === 'Items';
            if (!isItemsSection) {
                submenu.style.display = 'none';
                arrowSvg.classList.remove('rotate-90');
            } else {
                submenu.style.display = ''; // Ensure 'Items' is visible
                arrowSvg.classList.add('rotate-90'); // Ensure 'Items' arrow is rotated
            }
        }
    });

})();