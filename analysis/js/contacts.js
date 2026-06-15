(function() {
    function showToast(message) {
        const toast = document.createElement('div');
        toast.className = 'offline-toast';
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
            fontFamily: 'sans-serif'
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

    function showModal() {
        if (document.getElementById('simpleModalOverlay')) {
            return;
        }

        const modalOverlay = document.createElement('div');
        modalOverlay.id = 'simpleModalOverlay';
        Object.assign(modalOverlay.style, {
            position: 'fixed',
            top: '0',
            left: '0',
            width: '100%',
            height: '100%',
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: '9999',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center'
        });

        const modalContent = document.createElement('div');
        modalContent.id = 'simpleModalContent';
        modalContent.innerHTML = `
            <h3 style="margin-top: 0;">Action Not Supported Offline</h3>
            <p>This feature requires an active connection.</p>
            <button class="modal-close-btn" style="padding: 8px 15px; border: none; border-radius: 4px; background-color: #007bff; color: white; cursor: pointer; margin-top: 15px; font-size: 1rem;">Close</button>
        `;
        Object.assign(modalContent.style, {
            backgroundColor: 'white',
            padding: '30px',
            borderRadius: '8px',
            maxWidth: '500px',
            textAlign: 'center',
            boxShadow: '0 4px 10px rgba(0, 0, 0, 0.2)',
            fontFamily: 'sans-serif'
        });

        modalOverlay.appendChild(modalContent);
        document.body.appendChild(modalOverlay);

        const closeButton = modalContent.querySelector('.modal-close-btn');
        if (closeButton) {
            closeButton.onclick = () => modalOverlay.remove();
        }

        modalOverlay.onclick = (e) => {
            if (e.target === modalOverlay) {
                modalOverlay.remove();
            }
        };
    }

    document.body.addEventListener('click', function(e) {
        let target = e.target;

        // Rule 1, 8, 3: For a[href$=".html"] links, do nothing.
        const htmlLink = target.closest('a[href$=".html"]');
        if (htmlLink) {
            return;
        }

        // Rule 4: For a[href^="#/"] links
        const hashLink = target.closest('a[href^="#/"]');
        if (hashLink) {
            e.preventDefault();
            showToast('Not recorded yet');
            return;
        }

        // Rule 5: [role=tab]
        const tab = target.closest('[role="tab"]');
        if (tab) {
            e.preventDefault();

            const currentActiveTab = document.querySelector('[role="tab"][aria-selected="true"]');
            
            if (currentActiveTab && currentActiveTab !== tab) {
                currentActiveTab.classList.remove('active');
                currentActiveTab.setAttribute('aria-selected', 'false');
                const currentActivePanelId = currentActiveTab.getAttribute('aria-controls');
                const currentActivePanel = currentActivePanelId ? document.getElementById(currentActivePanelId) : null;
                if (currentActivePanel) {
                    currentActivePanel.style.display = 'none';
                }
            }

            // Toggle active state for the clicked tab
            const isActive = tab.classList.contains('active');
            tab.classList.toggle('active', !isActive);
            tab.setAttribute('aria-selected', String(!isActive));

            const targetPanelId = tab.getAttribute('aria-controls');
            const targetPanel = targetPanelId ? document.getElementById(targetPanelId) : null;
            if (targetPanel) {
                targetPanel.style.display = isActive ? 'none' : ''; // Toggle display
            }
            return;
        }

        // Rule 6: .dropdown-toggle
        const dropdownToggle = target.closest('.dropdown-toggle');
        if (dropdownToggle) {
            e.preventDefault();

            const dropdown = dropdownToggle.closest('.dropdown');
            let dropdownMenu = dropdown ? dropdown.querySelector('.dropdown-menu') : null;
            // Additional check if dropdown menu is a direct sibling of the toggle's parent div (common for some structures)
            if (!dropdownMenu && dropdownToggle.parentElement && dropdownToggle.parentElement.nextElementSibling && dropdownToggle.parentElement.nextElementSibling.classList.contains('dropdown-menu')) {
                dropdownMenu = dropdownToggle.parentElement.nextElementSibling;
            }

            const isActive = dropdown ? dropdown.classList.contains('show') : false;

            // Close all other dropdowns
            document.querySelectorAll('.dropdown.show').forEach(openDropdown => {
                if (openDropdown !== dropdown) {
                    openDropdown.classList.remove('show');
                    const toggle = openDropdown.querySelector('.dropdown-toggle');
                    if (toggle) toggle.setAttribute('aria-expanded', 'false');
                    const menu = openDropdown.querySelector('.dropdown-menu');
                    if (menu) menu.classList.remove('show');
                }
            });
            // Also explicitly check for dropdown menus not within a .dropdown container
            document.querySelectorAll('.dropdown-menu.show').forEach(openMenu => {
                if (openMenu !== dropdownMenu) {
                    openMenu.classList.remove('show');
                }
            });

            // Toggle current dropdown
            if (dropdown) {
                dropdown.classList.toggle('show', !isActive);
            }
            dropdownToggle.setAttribute('aria-expanded', String(!isActive));
            if (dropdownMenu) {
                dropdownMenu.classList.toggle('show', !isActive);
            }
            return;
        } else {
            // If clicked outside a dropdown or dropdown-toggle, close all open dropdowns
            document.querySelectorAll('.dropdown.show').forEach(openDropdown => {
                openDropdown.classList.remove('show');
                const toggle = openDropdown.querySelector('.dropdown-toggle');
                if (toggle) toggle.setAttribute('aria-expanded', 'false');
                const menu = openDropdown.querySelector('.dropdown-menu');
                if (menu) menu.classList.remove('show');
            });
            document.querySelectorAll('.dropdown-menu.show').forEach(openMenu => {
                openMenu.classList.remove('show');
            });
        }

        // Rule 7: .accordion-button / [aria-expanded][aria-controls] and sidebar navigation toggles
        const accordionButton = target.closest('.accordion-button') || target.closest('[aria-expanded][aria-controls]');
        const sidebarToggleButton = target.closest('li > div > h3 > button'); // Specific for left nav

        if (accordionButton || sidebarToggleButton) {
            e.preventDefault();

            let buttonToToggle = accordionButton || sidebarToggleButton;
            let contentToToggle = null;

            if (accordionButton) {
                // Standard accordion behavior
                const isExpanded = buttonToToggle.getAttribute('aria-expanded') === 'true';
                buttonToToggle.setAttribute('aria-expanded', String(!isExpanded));
                const controlsId = buttonToToggle.getAttribute('aria-controls');
                contentToToggle = controlsId ? document.getElementById(controlsId) : null;
            } else if (sidebarToggleButton) {
                // Left navigation toggle logic
                const parentLi = buttonToToggle.closest('li');
                // The collapsible UL is a direct sibling of the H3, which is a child of a DIV within the LI
                const h3Parent = buttonToToggle.closest('h3');
                contentToToggle = h3Parent ? h3Parent.nextElementSibling : null; 
                
                const arrowIcon = buttonToToggle.querySelector('.right-arrow.lpanel'); 
                if (arrowIcon) {
                    arrowIcon.classList.toggle('rotate-90');
                }
            }

            if (contentToToggle) {
                const isHidden = contentToToggle.style.display === 'none';
                contentToToggle.style.display = isHidden ? '' : 'none';
            }
            return;
        }

        // Rule 9: .btn-primary / buttons with "New|Create|Add"
        const button = target.closest('button');
        if (button) {
            const buttonText = button.textContent.trim().toLowerCase();
            const buttonTitle = button.title ? button.title.trim().toLowerCase() : '';

            const isPrimary = button.classList.contains('btn-primary');
            const isNew = buttonText.includes('new') || buttonTitle.includes('new');
            const isCreate = buttonText.includes('create') || buttonTitle.includes('create');
            const isAdd = buttonText.includes('add') || buttonTitle.includes('add');
            
            const specificAgentIds = [
                'el-214', 'el-219', 'el-058', 'el-067', 'el-072', 'el-077', 'el-082', 'el-087', 
                'el-100', 'el-104', 'el-109', 'el-114', 'el-119', 'el-124', 'el-129', 'el-134', 'el-149'
            ];
            const hasSpecificAgentId = button.hasAttribute('data-agent-id') && specificAgentIds.includes(button.getAttribute('data-agent-id'));

            if (isPrimary || isNew || isCreate || isAdd || hasSpecificAgentId) {
                e.preventDefault();
                showModal();
                return;
            }
        }
    }, false);

    document.body.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.querySelectorAll('.dropdown.show').forEach(openDropdown => {
                openDropdown.classList.remove('show');
                const toggle = openDropdown.querySelector('.dropdown-toggle');
                if (toggle) toggle.setAttribute('aria-expanded', 'false');
                const menu = openDropdown.querySelector('.dropdown-menu');
                if (menu) menu.classList.remove('show');
            });
            document.querySelectorAll('.dropdown-menu.show').forEach(openMenu => {
                openMenu.classList.remove('show');
            });

            const modalOverlay = document.getElementById('simpleModalOverlay');
            if (modalOverlay) {
                modalOverlay.remove();
            }
        }
    });

})();