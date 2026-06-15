(function() {
    function showToast(message) {
        let toast = document.getElementById('myToast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'myToast';
            toast.style.cssText = `
                position: fixed;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                background-color: #333;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                z-index: 9999;
                opacity: 0;
                transition: opacity 0.3s ease-in-out;
            `;
            document.body.appendChild(toast);
        }
        toast.textContent = message;
        toast.style.opacity = '1';
        setTimeout(() => {
            toast.style.opacity = '0';
        }, 3000);
    }

    function showModal() {
        let modalOverlay = document.getElementById('myModalOverlay');
        if (!modalOverlay) {
            modalOverlay = document.createElement('div');
            modalOverlay.id = 'myModalOverlay';
            modalOverlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            `;

            const modalContent = document.createElement('div');
            modalContent.style.cssText = `
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                text-align: center;
            `;
            modalContent.innerHTML = `
                <h3>Simple Modal</h3>
                <p>This is a placeholder for a new item/entry form.</p>
                <button id="closeModal" style="margin-top: 15px; padding: 8px 15px; cursor: pointer;">Close</button>
            `;

            modalOverlay.appendChild(modalContent);
            document.body.appendChild(modalOverlay);

            document.getElementById('closeModal').addEventListener('click', () => {
                modalOverlay.style.display = 'none';
            });
            modalOverlay.addEventListener('click', (e) => {
                if (e.target === modalOverlay) {
                    modalOverlay.style.display = 'none';
                }
            });
        }
        modalOverlay.style.display = 'flex';
    }

    // --- Initialization for navigation active states and accordion visibility ---
    const currentPageFilename = window.location.pathname.split('/').pop();

    document.querySelectorAll('nav a[href]').forEach(link => {
        const linkHref = link.getAttribute('href').split('/').pop();
        if (linkHref === currentPageFilename) {
            link.classList.add('active'); // Mark the link as active
            const parentLi = link.closest('li');
            if (parentLi) {
                parentLi.classList.add('active'); // Mark its parent li as active

                // For accordion parents, if a child is active, ensure parent is expanded
                const parentNavLi = parentLi.closest('li[data-agent-id="el-029"], li[data-agent-id="el-042"], li[data-agent-id="el-088"], li[data-agent-id="el-135"]');
                if (parentNavLi) {
                    const parentUl = parentNavLi.querySelector('ul');
                    const parentArrowSvg = parentNavLi.querySelector('h3 > button > .right-arrow');
                    if (parentUl) {
                        parentUl.style.display = 'block';
                    }
                    if (parentArrowSvg) {
                        parentArrowSvg.classList.add('rotate-90');
                    }
                }
            }
        }
    });

    // Explicitly set initial accordion states based on arrow rotation (if present)
    const accordionParents = document.querySelectorAll('li[data-agent-id="el-029"], li[data-agent-id="el-042"], li[data-agent-id="el-088"], li[data-agent-id="el-135"]');
    accordionParents.forEach(parentLi => {
        const arrowSvg = parentLi.querySelector('h3 > button > .right-arrow');
        const ulElement = parentLi.querySelector('ul');
        if (arrowSvg && ulElement) {
            ulElement.style.display = arrowSvg.classList.contains('rotate-90') ? 'block' : 'none';
        }
    });

    // --- Event Delegation ---
    document.addEventListener('click', function(e) {
        // Rule 2 & 3: Handle .html links FIRST
        const htmlLink = e.target.closest('a[href$=".html"]');
        if (htmlLink) {
            // Do nothing, let browser navigate
            return;
        }

        // Rule 4: Handle #/ links
        const hashLink = e.target.closest('a[href^="#/"]');
        if (hashLink) {
            e.preventDefault();
            showToast("not recorded yet");
            return;
        }

        // Rule 6: .dropdown-toggle
        let dropdownToggle = e.target.closest('.dropdown-toggle');
        if (dropdownToggle) {
            e.preventDefault();
            const parentDropdown = dropdownToggle.closest('.dropdown');
            if (parentDropdown) {
                parentDropdown.classList.toggle('show');
                const dropdownMenu = parentDropdown.querySelector('.dropdown-menu');
                if (dropdownMenu) {
                    dropdownMenu.classList.toggle('show');
                }
            }
            return;
        }

        // Custom dropdown toggles identified by data-agent-id without .dropdown-toggle class
        const el006Button = e.target.closest('[data-agent-id="el-006"]');
        if (el006Button) {
            e.preventDefault();
            const parentDropdown = el006Button.closest('.dropdown');
            if (parentDropdown) {
                parentDropdown.classList.toggle('show');
            }
            return;
        }

        const el015Button = e.target.closest('[data-agent-id="el-015"]');
        if (el015Button) {
            e.preventDefault();
            const parentDropdown = el015Button.closest('.dropdown');
            if (parentDropdown) {
                parentDropdown.classList.toggle('show');
            }
            return;
        }

        // Handle buttons with role=menu but no clear dropdown parent or dropdown-toggle class -> toast
        const el002Button = e.target.closest('[data-agent-id="el-002"]');
        if (el002Button) {
            e.preventDefault();
            showToast("Verify Account clicked!");
            return;
        }

        const el003Button = e.target.closest('[data-agent-id="el-003"]');
        if (el003Button) {
            e.preventDefault();
            showToast("Navigate To clicked!");
            return;
        }
         const el008Button = e.target.closest('[data-agent-id="el-008"]');
        if (el008Button) {
            e.preventDefault();
            showToast("Search options clicked!"); // Treat as toast as dropdown structure is not explicitly provided.
            return;
        }

        // Rule 7: .accordion-button / [aria-expanded][aria-controls]
        // Failed elements el-030 and el-043, which are H3 containing buttons (el-031 and el-044).
        // Also handling other similar accordion buttons for consistency: el-090 (Purchases), el-137 (Time Tracking), el-157 (Accountant)
        const accordionButton = e.target.closest('button[data-agent-id="el-031"], button[data-agent-id="el-044"], button[data-agent-id="el-090"], button[data-agent-id="el-137"], button[data-agent-id="el-157"]');
        if (accordionButton) {
            e.preventDefault();
            const parentDiv = accordionButton.closest('div'); // The div containing h3 and ul
            if (parentDiv) {
                const siblingUl = parentDiv.querySelector('ul');
                const arrowSvg = accordionButton.querySelector('.right-arrow');

                if (siblingUl) {
                    siblingUl.style.display = siblingUl.style.display === 'none' ? 'block' : 'none';
                    if (arrowSvg) {
                         arrowSvg.classList.toggle('rotate-90');
                    }
                }
            }
            return;
        }

        // Rule 8: .btn-primary / buttons with "New|Create|Add"
        // Target generic "New" buttons, or buttons with text content "New", "Create", "Add".
        // el-214 is a specific button with "New" text.
        const newButtonCandidate = e.target.closest('button.btn-primary, button[data-agent-id="el-214"], button.icon-button.add-new');

        if (newButtonCandidate) {
            // Check text content or title if it has a plus icon and is not an <a> tag (already handled)
            const buttonText = newButtonCandidate.textContent || newButtonCandidate.title;
            if (buttonText && (buttonText.includes('New') || buttonText.includes('Create') || buttonText.includes('Add'))) {
                e.preventDefault();
                showModal();
                return;
            }
        }
        
        // Rule 5: [role=tab] - no elements with role="tab" found in the provided HTML context or failed elements.

    }, false); // Rule 1 & 9: Use event delegation on document (bubble phase, NOT capture)

})();