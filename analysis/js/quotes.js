(function() {
  function showToast(message) {
    const toast = document.createElement('div');
    toast.textContent = message;
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
      font-family: sans-serif;
      font-size: 14px;
    `;
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
    let modal = document.getElementById('simple-modal-overlay');
    if (!modal) {
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
        z-index: 9999;
      `;
      modal.innerHTML = `
        <div style="background-color: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); text-align: center; max-width: 90%; font-family: sans-serif;">
          <h3 style="margin-top: 0; color: #333;">Action Triggered!</h3>
          <p style="margin-bottom: 20px; color: #555;">This is a simple modal overlay for "New", "Create", or "Add" actions.</p>
          <button id="close-simple-modal" style="background-color: #007bff; color: white; padding: 8px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">Close</button>
        </div>
      `;
      document.body.appendChild(modal);

      document.getElementById('close-simple-modal').addEventListener('click', () => {
        modal.style.display = 'none';
      });

      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          modal.style.display = 'none';
        }
      });
    } else {
      modal.style.display = 'flex';
    }
  }

  // --- Sidebar Accordion Initialization ---
  document.querySelectorAll('li[data-agent-id][role="menu"] > div').forEach(parentDiv => {
    const button = parentDiv.querySelector('h3 > button');
    const submenu = parentDiv.querySelector('ul[role="menu"]');
    if (button && submenu) {
      const submenuId = submenu.id || 'submenu-' + Math.random().toString(36).substr(2, 9);
      submenu.id = submenuId;
      button.setAttribute('aria-controls', submenuId);
      button.setAttribute('aria-expanded', 'false');
      submenu.setAttribute('aria-hidden', 'true');
      submenu.style.display = 'none';

      if (!button.classList.contains('accordion-button')) {
        button.classList.add('accordion-button');
      }
    }
  });

  // Highlight current page (quotes.html) and expand its parent menu (Sales)
  const quotesLink = document.querySelector('a[href="quotes.html"]');
  if (quotesLink) {
    quotesLink.classList.add('active');
    const parentLi = quotesLink.closest('li[role="menu"]');
    if (parentLi) {
      parentLi.classList.add('active');
    }

    const salesMenuItemParentDiv = quotesLink.closest('li[data-agent-id="el-042"] > div');
    if (salesMenuItemParentDiv) {
      const salesAccordionButton = salesMenuItemParentDiv.querySelector('h3 > button');
      const salesSubmenu = salesMenuItemParentDiv.querySelector('ul[role="menu"]');
      const salesArrowIcon = salesAccordionButton ? salesAccordionButton.querySelector('.right-arrow') : null;

      if (salesAccordionButton) {
        salesAccordionButton.setAttribute('aria-expanded', 'true');
        if (salesArrowIcon) {
          salesArrowIcon.classList.add('rotate-90');
        }
      }
      if (salesSubmenu) {
        salesSubmenu.style.display = 'block';
        salesSubmenu.setAttribute('aria-hidden', 'false');
      }
    }
  }

  // --- Main Event Listener ---
  document.addEventListener('click', function(e) {
    const target = e.target;

    // Rule 2 & 3: Anchor links ending with .html
    if (target.closest('a[href$=".html"]')) {
      return;
    }

    // Rule 4: Anchor links starting with #/
    const hashLink = target.closest('a[href^="#/"]');
    if (hashLink) {
      e.preventDefault();
      showToast("not recorded yet");
      return;
    }

    // Rule 5: [role=tab]
    const tab = target.closest('[role="tab"]');
    if (tab) {
      e.preventDefault();
      const tabGroup = tab.closest('[role="tablist"]');
      if (tabGroup) {
        tabGroup.querySelectorAll('[role="tab"].active').forEach(activeTab => {
          activeTab.classList.remove('active');
          activeTab.setAttribute('aria-selected', 'false');
          const panelId = activeTab.getAttribute('aria-controls');
          if (panelId) {
            const panel = document.getElementById(panelId);
            if (panel) {
              panel.style.display = 'none';
              panel.setAttribute('aria-hidden', 'true');
            }
          }
        });

        tab.classList.add('active');
        tab.setAttribute('aria-selected', 'true');
        const panelId = tab.getAttribute('aria-controls');
        if (panelId) {
          const panel = document.getElementById(panelId);
          if (panel) {
            panel.style.display = '';
            panel.setAttribute('aria-hidden', 'false');
          }
        }
      }
      return;
    }

    // Rule 6: .dropdown-toggle
    const dropdownToggle = target.closest('.dropdown-toggle');
    if (dropdownToggle) {
      e.preventDefault();
      const dropdown = dropdownToggle.closest('.dropdown');
      if (dropdown) {
        const isShowing = dropdown.classList.contains('show');

        document.querySelectorAll('.dropdown.show').forEach(openDropdown => {
          if (openDropdown !== dropdown) {
            openDropdown.classList.remove('show');
            const openMenu = openDropdown.querySelector('.dropdown-menu');
            if (openMenu) {
              openMenu.classList.remove('show');
            }
          }
        });

        dropdown.classList.toggle('show', !isShowing);
        const dropdownMenu = dropdown.querySelector('.dropdown-menu');
        if (dropdownMenu) {
          dropdownMenu.classList.toggle('show', !isShowing);
        }
      }
      return;
    }

    // Rule 7: .accordion-button / [aria-expanded][aria-controls]
    const accordionButton = target.closest('.accordion-button, [aria-expanded][aria-controls]');
    if (accordionButton) {
      e.preventDefault();
      const isExpanded = accordionButton.getAttribute('aria-expanded') === 'true';
      accordionButton.setAttribute('aria-expanded', String(!isExpanded));

      const controlsId = accordionButton.getAttribute('aria-controls');
      if (controlsId) {
        const controlledElement = document.getElementById(controlsId);
        if (controlledElement) {
          controlledElement.style.display = isExpanded ? 'none' : 'block';
          controlledElement.setAttribute('aria-hidden', String(isExpanded));
        }
      }

      const arrowIcon = accordionButton.querySelector('.right-arrow');
      if (arrowIcon) {
        if (isExpanded) {
          arrowIcon.classList.remove('rotate-90');
        } else {
          arrowIcon.classList.add('rotate-90');
        }
      }
      return;
    }

    // Rule 8: .btn-primary / buttons with "New|Create|Add"
    const button = target.closest('button');
    if (button) {
        if (button.classList.contains('btn-primary')) {
            e.preventDefault();
            showModal();
            return;
        }

        const buttonText = button.textContent.trim().toLowerCase();
        if (buttonText.includes('new') || buttonText.includes('create') || buttonText.includes('add')) {
            e.preventDefault();
            showModal();
            return;
        }
    }
  });

  // Event listener to close dropdowns when clicking outside
  document.addEventListener('click', function(e) {
    const isClickInsideDropdown = e.target.closest('.dropdown');
    if (!isClickInsideDropdown) {
      document.querySelectorAll('.dropdown.show').forEach(openDropdown => {
        openDropdown.classList.remove('show');
        const openMenu = openDropdown.querySelector('.dropdown-menu');
        if (openMenu) {
          openMenu.classList.remove('show');
        }
      });
    }
  }, false);
})();