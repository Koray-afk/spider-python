(function() {
    function showToast(message) {
        const toast = document.createElement('div');
        toast.textContent = message;
        toast.style.cssText = 'position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background-color: #333; color: white; padding: 10px 20px; border-radius: 5px; z-index: 10000; opacity: 0; transition: opacity 0.3s ease-in-out;';
        document.body.appendChild(toast);
        setTimeout(() => { toast.style.opacity = '1'; }, 10);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.addEventListener('transitionend', () => toast.remove(), { once: true });
        }, 3000);
    }

    function showModal(content) {
        const modalOverlay = document.createElement('div');
        modalOverlay.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); z-index: 9999; display: flex; justify-content: center; align-items: center;';

        const modalContent = document.createElement('div');
        modalContent.style.cssText = 'background-color: white; padding: 30px; border-radius: 8px; max-width: 500px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.2);';
        modalContent.innerHTML = `<p>${content}</p><button style="margin-top: 20px; padding: 8px 15px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">Close</button>`;

        modalContent.querySelector('button').addEventListener('click', () => {
            modalOverlay.remove();
        }, { once: true });

        modalOverlay.appendChild(modalContent);
        document.body.appendChild(modalOverlay);
    }

    document.addEventListener('click', function(e) {
        const targetElement = e.target;

        if (targetElement.closest('a[href$=".html"]')) {
            return;
        }

        if (targetElement.closest('a[href^="#/"]')) {
            e.preventDefault();
            showToast("Navigation not recorded yet.");
            return;
        }

        let isDropdownToggleHandled = false;
        
        const standardDropdownToggle = targetElement.closest('.dropdown-toggle');
        const genericDropdownButton = targetElement.closest('button');

        let dropdownToToggle = null;

        if (standardDropdownToggle) {
            dropdownToToggle = standardDropdownToggle.closest('.dropdown');
        } else if (genericDropdownButton) {
            const specificDropdownAgentIds = ['el-006', 'el-015']; // Buttons inside a .dropdown container
            if (specificDropdownAgentIds.includes(genericDropdownButton.dataset.agentId)) {
                dropdownToToggle = genericDropdownButton.closest('.dropdown');
            }
            if (genericDropdownButton.dataset.agentId === 'el-002') { // "Verify Account" button
                e.preventDefault();
                showToast("Account verification flow not recorded yet.");
                isDropdownToggleHandled = true;
            } else if (genericDropdownButton.dataset.agentId === 'el-003') { // "Navigate To" button
                e.preventDefault();
                showToast("Navigation menu not recorded yet.");
                isDropdownToggleHandled = true;
            }
        }
        
        if (dropdownToToggle) {
            e.preventDefault();
            document.querySelectorAll('.dropdown.show').forEach(openDropdown => {
                if (openDropdown !== dropdownToToggle) {
                    openDropdown.classList.remove('show');
                    const menu = openDropdown.querySelector('.dropdown-menu');
                    if (menu) menu.classList.remove('show');
                }
            });

            dropdownToToggle.classList.toggle('show');
            const dropdownMenu = dropdownToToggle.querySelector('.dropdown-menu');
            if (dropdownMenu) {
                dropdownMenu.classList.toggle('show');
            }
            isDropdownToggleHandled = true;
            return;
        }

        const acToggler = targetElement.closest('[ac-toggler]');
        const searchOptionButton = targetElement.closest('[data-agent-id="el-008"]'); // "Search" button with dropdown

        if ((acToggler || searchOptionButton) && !isDropdownToggleHandled) {
            e.preventDefault();
            const elementToToggleClass = acToggler || searchOptionButton;
            elementToToggleClass.classList.toggle('active-ac-toggler');
            
            document.querySelectorAll('[ac-toggler].active-ac-toggler, [data-agent-id="el-008"].active-ac-toggler').forEach(activeToggler => {
                if (activeToggler !== elementToToggleClass) {
                    activeToggler.classList.remove('active-ac-toggler');
                }
            });

            showToast("Selection/Search options functionality not recorded yet.");
            isDropdownToggleHandled = true;
            return;
        }
        
        const accordionButton = targetElement.closest('h3 > button');
        if (accordionButton) {
            e.preventDefault();
            const parentLi = accordionButton.closest('li');
            if (parentLi) {
                const arrowSvg = accordionButton.querySelector('svg.right-arrow');
                if (arrowSvg) {
                    arrowSvg.classList.toggle('rotate-90');
                }

                const targetUl = parentLi.querySelector('ul');
                if (targetUl) {
                    if (targetUl.style.display === 'block') {
                        targetUl.style.display = 'none';
                    } else {
                        targetUl.style.display = 'block';
                    }
                }
            }
            return;
        }

        const tabElement = targetElement.closest('[role="tab"]');
        if (tabElement) {
            e.preventDefault();
            document.querySelectorAll('[role="tab"].active').forEach(tab => {
                tab.classList.remove('active');
                tab.setAttribute('aria-selected', 'false');
                const controlledPanelId = tab.getAttribute('aria-controls');
                if (controlledPanelId) {
                    const controlledPanel = document.getElementById(controlledPanelId);
                    if (controlledPanel) {
                        controlledPanel.style.display = 'none';
                        controlledPanel.setAttribute('aria-hidden', 'true');
                    }
                }
            });

            tabElement.classList.add('active');
            tabElement.setAttribute('aria-selected', 'true');
            const controlledPanelId = tabElement.getAttribute('aria-controls');
            if (controlledPanelId) {
                const controlledPanel = document.getElementById(controlledPanelId);
                if (controlledPanel) {
                    controlledPanel.style.display = 'block';
                    controlledPanel.setAttribute('aria-hidden', 'false');
                }
            }
            return;
        }

        const button = targetElement.closest('button');
        if (button) {
            const buttonText = button.textContent ? button.textContent.trim() : '';
            const buttonTitle = button.title ? button.title.trim() : '';

            const isNewCreateAdd = /(New|Create|Add)/i.test(buttonText) || /(New|Create|Add)/i.test(buttonTitle);

            const relevantAgentIdsForModal = ['el-058', 'el-067', 'el-104', 'el-149'];
            const isRelevantModalButton = (button.dataset.agentId && relevantAgentIdsForModal.includes(button.dataset.agentId)) ||
                                         (button.classList.contains('btn-primary') && isNewCreateAdd);

            if (isRelevantModalButton) {
                e.preventDefault();
                showModal(`Functionality for "${buttonText || buttonTitle}" is not yet implemented.`);
                return;
            }

            if (buttonText === 'Save as Draft' || buttonText.startsWith('Save and Send') || buttonText === 'Cancel' || buttonText === 'Verify Account') {
                e.preventDefault();
                showToast(`Action "${buttonText}" not recorded yet.`);
                return;
            }
        }
    }, false);

    document.addEventListener('click', function(e) {
        document.querySelectorAll('.dropdown.show').forEach(openDropdown => {
            if (!e.target.closest('.dropdown') && !e.target.closest('.dropdown-toggle')) {
                openDropdown.classList.remove('show');
                const dropdownMenu = openDropdown.querySelector('.dropdown-menu');
                if (dropdownMenu) dropdownMenu.classList.remove('show');
            }
        });

        document.querySelectorAll('[ac-toggler].active-ac-toggler, [data-agent-id="el-008"].active-ac-toggler').forEach(activeToggler => {
            if (!e.target.closest('[ac-toggler]') && !e.target.closest('[data-agent-id="el-008"]')) {
                activeToggler.classList.remove('active-ac-toggler');
            }
        });
    }, false);
})();