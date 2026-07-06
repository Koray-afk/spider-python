// Replica forms — generic client-side "create record" simulation for the
// stitched clone. There is no backend, so this layer intercepts form submits,
// stores the submitted data in window.ReplicaStore (persisted to
// localStorage so records survive full-page navigation), and updates the DOM
// (table row, counters, pagination text, modal, success toast) so the app
// *feels* like the real thing even though nothing is persisted server-side.
//
// Entities (company, contact, lead, quotation, ...) are added via
// ReplicaFlows.register() with a small config object; the actual DOM wiring
// lives in the shared ReplicaHelpers functions below so new entities never
// need to duplicate it.
(function () {
  "use strict";

  var STORAGE_KEY = "__stitchReplicaStore__";
  var FLASH_KEY   = "__stitchReplicaFlash__";
  var LOADING_MS  = 900;   // default fake-loading duration

  function loadStore() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (err) {
      return {};
    }
  }

  window.ReplicaStore = loadStore();

  function persistStore() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(window.ReplicaStore));
    } catch (err) {}
  }

  function escapeHtml(str) {
    return String(str == null ? "" : str).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  function pad2(n) {
    return n < 10 ? "0" + n : String(n);
  }

  var MONTHS_LONG = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];
  var MONTHS_SHORT = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];

  function formatDateShort(d) {
    return d.getDate() + " " + MONTHS_SHORT[d.getMonth()] + " " + d.getFullYear();
  }

  function formatDateLong(d) {
    var h = d.getHours();
    var ampm = h >= 12 ? "p.m." : "a.m.";
    var h12 = h % 12;
    if (h12 === 0) h12 = 12;
    return (
      MONTHS_LONG[d.getMonth()] + " " + d.getDate() + ", " + d.getFullYear() +
      ", " + h12 + ":" + pad2(d.getMinutes()) + " " + ampm
    );
  }

  function fakeCode(prefix) {
    return prefix + "-69-" + String(Math.floor(10000 + Math.random() * 90000));
  }

  function newId() {
    return "new-" + Date.now() + "-" + Math.floor(Math.random() * 1000);
  }

  function selectLabel(sel) {
    if (!sel || sel.selectedIndex < 0) return "";
    var opt = sel.options[sel.selectedIndex];
    return opt ? opt.text.trim() : "";
  }

  // ── Generic helpers (reusable across entities) ──────────────────────────

  var ReplicaHelpers = {};

  ReplicaHelpers.persistStore = persistStore;

  ReplicaHelpers.readForm = function (form) {
    var data = {};
    form.querySelectorAll("input, select, textarea").forEach(function (el) {
      if (!el.name || el.name === "csrfmiddlewaretoken") return;
      if (el.type === "checkbox") data[el.name] = el.checked;
      else if (el.type === "radio") {
        if (el.checked) data[el.name] = el.value;
      } else if (el.tagName === "SELECT" && el.multiple) {
        var vals = [];
        Array.prototype.forEach.call(el.options, function (o) {
          if (o.selected && o.value) vals.push(o.textContent.trim() || o.value);
        });
        data[el.name] = vals.join(", ");
      } else data[el.name] = el.value;
    });
    return data;
  };

  ReplicaHelpers.openModal = function (modalEl) {
    if (!modalEl) return;
    modalEl.classList.add("show");
    modalEl.style.display = "block";
    modalEl.removeAttribute("aria-hidden");
    modalEl.setAttribute("aria-modal", "true");
    document.body.classList.add("modal-open");
    if (!document.querySelector(".modal-backdrop")) {
      var backdrop = document.createElement("div");
      backdrop.className = "modal-backdrop fade show";
      backdrop.setAttribute("data-replica-backdrop", modalEl.id || "");
      document.body.appendChild(backdrop);
    }
  };

  ReplicaHelpers.closeModal = function (modalEl) {
    if (!modalEl) return;
    modalEl.classList.remove("show");
    modalEl.style.display = "none";
    modalEl.setAttribute("aria-hidden", "true");
    modalEl.removeAttribute("aria-modal");
    document
      .querySelectorAll(
        '[data-replica-backdrop="' + (modalEl.id || "") + '"], ' +
          '[data-stitch-modal-backdrop="' + (modalEl.id || "") + '"]'
      )
      .forEach(function (el) {
        if (el.parentNode) el.parentNode.removeChild(el);
      });
    if (!document.querySelector(".modal.show")) {
      document.body.classList.remove("modal-open");
      Array.prototype.forEach.call(document.querySelectorAll(".modal-backdrop"), function (el) {
        if (el.parentNode) el.parentNode.removeChild(el);
      });
    }
  };

  // Removes any existing text nodes from `el` (keeping element children such
  // as icons) and appends a single new trailing text node. Lets us update
  // "<i class='icon'></i> some text" cells without clobbering the icon.
  ReplicaHelpers.setTrailingText = function (el, text) {
    if (!el) return;
    for (var i = el.childNodes.length - 1; i >= 0; i--) {
      if (el.childNodes[i].nodeType === 3) el.removeChild(el.childNodes[i]);
    }
    el.appendChild(document.createTextNode(" " + text));
  };

  // Clones the first existing <tr> in a table body so the new row inherits
  // the exact same markup/classes as real rows, then lets the entity's
  // `fillRow` callback populate it with the submitted data.
  ReplicaHelpers.buildRow = function (entity, data, seq) {
    var tbody = document.querySelector(entity.tableBodySelector);
    if (!tbody) return null;
    var template = tbody.querySelector("tr");
    var row = template ? template.cloneNode(true) : document.createElement("tr");
    if (typeof entity.fillRow === "function") entity.fillRow(row, data, seq);
    return row;
  };

  ReplicaHelpers.prependTableRow = function (tableBodySelector, rowEl) {
    var tbody = document.querySelector(tableBodySelector);
    if (!tbody || !rowEl) return;
    tbody.insertBefore(rowEl, tbody.firstChild);
  };

  // Card-grid analogue of buildRow: clones the first existing card in a
  // container (so it inherits the exact markup/classes), then lets the
  // entity's `fillCard` callback populate it with the submitted data.
  ReplicaHelpers.buildCard = function (entity, data, seq) {
    var container = document.querySelector(entity.containerSelector);
    if (!container) return null;
    var template = container.firstElementChild;
    var card = template ? template.cloneNode(true) : document.createElement("div");
    if (typeof entity.fillCard === "function") entity.fillCard(card, data, seq);
    return card;
  };

  ReplicaHelpers.prependCard = function (containerSelector, cardEl) {
    var container = document.querySelector(containerSelector);
    if (!container || !cardEl) return;
    container.insertBefore(cardEl, container.firstChild);
  };

  ReplicaHelpers.countRows = function (tableBodySelector) {
    var tbody = document.querySelector(tableBodySelector);
    return tbody ? tbody.querySelectorAll("tr").length : 0;
  };

  // Stat cards are `<div class="...fw-bold">Label</div><div class="fs-2hx...">N</div>`
  // with no ids, so we match by the label text and bump the sibling number.
  ReplicaHelpers.bumpCounterCard = function (label, delta) {
    if (!delta) return;
    var labels = document.querySelectorAll(".fs-6.fw-bold");
    for (var i = 0; i < labels.length; i++) {
      if ((labels[i].textContent || "").trim() === label) {
        var valueEl = labels[i].nextElementSibling;
        if (valueEl) {
          var cur = parseInt((valueEl.textContent || "0").replace(/[^0-9-]/g, ""), 10) || 0;
          valueEl.textContent = String(cur + delta);
        }
        return;
      }
    }
  };

  // Variant for the Leads stat strip: `<div class="ll-stat-num">14</div>
  // <div class="ll-stat-lbl">Total Leads</div>` (value comes *before* label).
  ReplicaHelpers.bumpStatBox = function (label, delta) {
    if (!delta) return;
    var labels = document.querySelectorAll(".ll-stat-lbl");
    for (var i = 0; i < labels.length; i++) {
      if ((labels[i].textContent || "").trim() === label) {
        var valueEl = labels[i].previousElementSibling;
        if (valueEl) {
          var cur = parseInt((valueEl.textContent || "0").replace(/[^0-9-]/g, ""), 10) || 0;
          valueEl.textContent = String(cur + delta);
        }
        return;
      }
    }
  };

  ReplicaHelpers.updateCounters = function (counterConfigs, data) {
    (counterConfigs || []).forEach(function (c) {
      var delta = typeof c.deltaFor === "function" ? c.deltaFor(data) : (c.delta || 0);
      if (!delta) return;
      if (c.type === "stat-box") ReplicaHelpers.bumpStatBox(c.label, delta);
      else ReplicaHelpers.bumpCounterCard(c.label, delta);
    });
  };

  ReplicaHelpers.updatePaginationInfo = function (selector, total, singular, plural) {
    var el = selector ? document.querySelector(selector) : null;
    if (!el) return;
    var label = total === 1 ? singular : plural;
    el.textContent = "Showing 1 to " + total + " of " + total + " " + label;
  };

  // ── Green toast — matches the real site screenshot ──────────────────────
  // Fixed top-center, auto-dismiss after 4 s, X closes early.
  ReplicaHelpers.showToast = function (message) {
    var toast = document.createElement("div");
    toast.setAttribute("role", "alert");
    toast.style.cssText = [
      "position:fixed",
      "top:24px",
      "left:50%",
      "transform:translateX(-50%)",
      "z-index:99999",
      "display:flex",
      "align-items:center",
      "gap:12px",
      "min-width:260px",
      "max-width:480px",
      "padding:14px 18px",
      "border-radius:8px",
      "border:1.5px solid #28a745",
      "background:#d4edda",
      "color:#155724",
      "font-size:14px",
      "font-weight:500",
      "box-shadow:0 4px 16px rgba(0,0,0,0.12)",
      "cursor:default",
    ].join(";");

    var msg = document.createElement("span");
    msg.style.cssText = "flex:1;";
    msg.textContent = message;

    var close = document.createElement("button");
    close.type = "button";
    close.style.cssText = [
      "background:none",
      "border:none",
      "padding:0",
      "margin:0",
      "cursor:pointer",
      "line-height:1",
      "color:#6c757d",
      "font-size:18px",
    ].join(";");
    close.innerHTML = "&times;";
    close.setAttribute("aria-label", "Close");

    toast.appendChild(msg);
    toast.appendChild(close);
    document.body.appendChild(toast);

    var tid = setTimeout(remove, 4000);

    function remove() {
      clearTimeout(tid);
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }

    close.addEventListener("click", remove);
  };

  // ── Button loading state ─────────────────────────────────────────────────
  // Swaps the button to a spinner + "Please wait…" label and disables it.
  // The button is automatically re-enabled / restored if navigation is blocked
  // (e.g. validation fails), but in practice we always navigate away or close
  // the modal before needing to restore.
  ReplicaHelpers.setButtonLoading = function (btn) {
    if (!btn) return;
    btn.__replicaOrigHtml     = btn.innerHTML;
    btn.__replicaOrigDisabled = btn.disabled;
    btn.disabled = true;
    // Support indicator-label / indicator-progress pattern used by Company & Contact buttons.
    var label = btn.querySelector(".indicator-label");
    var progress = btn.querySelector(".indicator-progress");
    if (label && progress) {
      label.classList.add("d-none");
      progress.classList.remove("d-none");
    } else {
      btn.innerHTML =
        '<span class="spinner-border spinner-border-sm align-middle me-2"></span>Please wait…';
    }
  };

  ReplicaHelpers.restoreButton = function (btn) {
    if (!btn || btn.__replicaOrigHtml === undefined) return;
    btn.innerHTML = btn.__replicaOrigHtml;
    btn.disabled  = btn.__replicaOrigDisabled || false;
    delete btn.__replicaOrigHtml;
    delete btn.__replicaOrigDisabled;
  };

  // ── Session-storage flash: show a toast on the *next* page after redirect ─
  ReplicaHelpers.setFlash = function (message) {
    try {
      sessionStorage.setItem(FLASH_KEY, message);
    } catch (err) {}
  };

  ReplicaHelpers.readAndClearFlash = function () {
    try {
      var msg = sessionStorage.getItem(FLASH_KEY);
      if (msg) sessionStorage.removeItem(FLASH_KEY);
      return msg || null;
    } catch (err) {
      return null;
    }
  };

  // SweetAlert-style success modal (centered green check + "Ok, got it!"), used
  // for flows whose real-site confirmation is a dialog rather than a toast
  // (e.g. Add Company). Uses the native Swal if the page bundles it, otherwise
  // renders a clone styled by the page's bundled swal2 CSS.
  ReplicaHelpers.showSuccessPopup = function (opts) {
    opts = opts || {};
    var title = opts.title || "Success";
    var text = opts.text || "";
    var confirmText = opts.confirmButtonText || "Ok, got it!";

    if (window.Swal && typeof window.Swal.fire === "function") {
      window.Swal.fire({
        icon: "success",
        title: title,
        text: text,
        buttonsStyling: false,
        confirmButtonText: confirmText,
        customClass: { confirmButton: "btn btn-primary" },
      });
      return;
    }

    // Lightweight clone matching the swal2 markup/classes already styled by
    // the page's bundled CSS.
    var overlay = document.createElement("div");
    overlay.className = "swal2-container swal2-center swal2-backdrop-show replica-swal";
    overlay.innerHTML =
      '<div class="swal2-popup swal2-modal swal2-icon-success swal2-show" role="dialog" style="display:grid;">' +
      '<div class="swal2-icon swal2-success swal2-icon-show" style="display:flex;">' +
      '<div class="swal2-success-circular-line-left"></div>' +
      '<span class="swal2-success-line-tip"></span><span class="swal2-success-line-long"></span>' +
      '<div class="swal2-success-ring"></div><div class="swal2-success-fix"></div>' +
      '<div class="swal2-success-circular-line-right"></div>' +
      "</div>" +
      '<h2 class="swal2-title" style="display:block;">' + escapeHtml(title) + "</h2>" +
      (text
        ? '<div class="swal2-html-container" style="display:block;">' + escapeHtml(text) + "</div>"
        : "") +
      '<div class="swal2-actions" style="display:flex;">' +
      '<button type="button" class="swal2-confirm btn btn-primary">' + escapeHtml(confirmText) + "</button>" +
      "</div>" +
      "</div>";
    document.body.appendChild(overlay);

    function close() {
      if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
      document.removeEventListener("keydown", onKey, true);
    }
    function onKey(ev) {
      if (ev.key === "Escape" || ev.keyCode === 27) close();
    }
    overlay.querySelector(".swal2-confirm").addEventListener("click", close);
    overlay.addEventListener("click", function (ev) {
      if (ev.target === overlay) close();
    });
    document.addEventListener("keydown", onKey, true);
  };

  window.ReplicaHelpers = ReplicaHelpers;

  // ── Entity registry ─────────────────────────────────────────────────────

  var entities = {};

  var ReplicaFlows = {
    register: function (name, config) {
      entities[name] = config;
      if (config.storeKey && !window.ReplicaStore[config.storeKey]) {
        window.ReplicaStore[config.storeKey] = [];
      }
    },
    findByForm: function (form) {
      for (var name in entities) {
        if (!Object.prototype.hasOwnProperty.call(entities, name)) continue;
        var cfg = entities[name];
        if (cfg.formSelector && form.matches(cfg.formSelector)) return cfg;
      }
      return null;
    },
  };
  window.ReplicaFlows = ReplicaFlows;

  // ── Submit handler shared by every registered entity ────────────────────

  window.__stitchReplicaSubmit = function (form, e) {
    if (!form || !form.tagName || form.tagName.toUpperCase() !== "FORM") return false;
    var entity = ReplicaFlows.findByForm(form);
    if (!entity) return false;

    e.preventDefault();
    e.stopPropagation();

    // Grab the submit button before we do anything else.
    var btn = (e && e.submitter) ||
      form.querySelector("button[type='submit'], input[type='submit']");
    ReplicaHelpers.setButtonLoading(btn);

    // Read and store data immediately (before any async delay).
    var data = ReplicaHelpers.readForm(form);
    data.__id = newId();
    if (typeof entity.beforeSave === "function") entity.beforeSave(data, form);

    var store = window.ReplicaStore[entity.storeKey] || (window.ReplicaStore[entity.storeKey] = []);
    store.unshift(data);
    persistStore();

    var modalEl = entity.modalSelector ? document.querySelector(entity.modalSelector) : null;
    var delay   = entity.loadingMs !== undefined ? entity.loadingMs : LOADING_MS;
    var msg     = entity.successMessage || "Created successfully!";

    // Pattern B: the form lives on its own page — show loading, then redirect.
    // The destination list reads the flash and shows the toast next to the new row.
    if (entity.redirectTo) {
      var dest = typeof entity.redirectTo === "function" ? entity.redirectTo(data) : entity.redirectTo;
      setTimeout(function () {
        ReplicaHelpers.closeModal(modalEl);
        form.reset();
        ReplicaHelpers.setFlash(msg);
        location.href = dest;
      }, delay);
      return true;
    }

    // Pattern A: modal + table (or card grid) on the same page — update DOM
    // after the fake loading delay.
    setTimeout(function () {
      ReplicaHelpers.closeModal(modalEl);
      form.reset();
      ReplicaHelpers.restoreButton(btn);

      if (entity.tableBodySelector) {
        var rowEl = ReplicaHelpers.buildRow(entity, data, store.length);
        if (rowEl) ReplicaHelpers.prependTableRow(entity.tableBodySelector, rowEl);
      } else if (entity.containerSelector) {
        var cardEl = ReplicaHelpers.buildCard(entity, data, store.length);
        if (cardEl) ReplicaHelpers.prependCard(entity.containerSelector, cardEl);
      }

      if (entity.counters) ReplicaHelpers.updateCounters(entity.counters, data);

      if (entity.paginationInfoSelector) {
        var total = ReplicaHelpers.countRows(entity.tableBodySelector);
        ReplicaHelpers.updatePaginationInfo(
          entity.paginationInfoSelector,
          total,
          entity.singularLabel,
          entity.pluralLabel
        );
      }

      if (entity.successPopup) {
        ReplicaHelpers.showSuccessPopup({ title: entity.successPopupText || msg });
      } else {
        ReplicaHelpers.showToast(msg);
      }
      console.log("[STITCH] Replica create", entity.storeKey, data);
    }, delay);

    return true;
  };

  // Re-render every persisted record for every entity that has a matching
  // table on the *current* page. Runs once per page load — the DOM always
  // starts from the crawled snapshot, so this is how records created on a
  // previous page (redirect flows) or a previous visit reappear.
  function renderPersistedOnLoad() {
    for (var name in entities) {
      if (!Object.prototype.hasOwnProperty.call(entities, name)) continue;
      var cfg = entities[name];
      if (!cfg.storeKey) continue;
      if (!cfg.tableBodySelector && !cfg.containerSelector) continue;
      var host = document.querySelector(cfg.tableBodySelector || cfg.containerSelector);
      if (!host) continue;
      var records = window.ReplicaStore[cfg.storeKey] || [];
      if (!records.length) continue;

      for (var i = records.length - 1; i >= 0; i--) {
        if (cfg.tableBodySelector) {
          var rowEl = ReplicaHelpers.buildRow(cfg, records[i]);
          if (rowEl) ReplicaHelpers.prependTableRow(cfg.tableBodySelector, rowEl);
        } else if (cfg.containerSelector) {
          var cardEl = ReplicaHelpers.buildCard(cfg, records[i]);
          if (cardEl) ReplicaHelpers.prependCard(cfg.containerSelector, cardEl);
        }
      }

      if (cfg.counters) {
        records.forEach(function (rec) {
          ReplicaHelpers.updateCounters(cfg.counters, rec);
        });
      }

      if (cfg.paginationInfoSelector) {
        var total = ReplicaHelpers.countRows(cfg.tableBodySelector);
        ReplicaHelpers.updatePaginationInfo(cfg.paginationInfoSelector, total, cfg.singularLabel, cfg.pluralLabel);
      }
    }
  }

  // ── Entity: Rise CRM — Company ──────────────────────────────────────────

  function stageBadgeClass(stage) {
    switch ((stage || "").toLowerCase()) {
      case "warm":
        return "badge-light-warning";
      case "lead":
        return "badge-light-info";
      case "customer":
        return "badge-light-success";
      default:
        return "badge-light-primary";
    }
  }

  function fillCompanyRow(row, data) {
    var name = (data.company_name || "Untitled Company").trim();
    var industry = data.company_industry || "";
    var stage = data.company_stage || "Cold";
    var website = data.company_website || "";
    var email = data.company_email || "";
    var phone = data.company_phone || "";
    var address = data.company_address || "";

    row.removeAttribute("style");
    row.setAttribute("data-company-id", data.__id);
    row.setAttribute("data-name", name);
    row.setAttribute("data-industry", industry);
    row.setAttribute("data-email", email);
    row.setAttribute("data-phone", phone);
    row.setAttribute("data-website", website);
    row.setAttribute("data-address", address);
    row.setAttribute("data-stage", stage);
    row.setAttribute("data-deal-value", "0");

    var nameLink = row.querySelector("td:nth-child(1) a");
    if (nameLink) {
      nameLink.textContent = name;
      nameLink.setAttribute("href", "#");
      nameLink.removeAttribute("data-stitch-page");
      nameLink.removeAttribute("data-stitch-go");
    }
    var websiteSpan = row.querySelector("td:nth-child(1) .text-muted.fs-7");
    if (websiteSpan) websiteSpan.textContent = website;

    var industryCell = row.querySelector("td:nth-child(2)");
    if (industryCell) industryCell.textContent = industry;

    var emailSpan = row.querySelector("td:nth-child(3) .text-gray-800.mb-1");
    if (emailSpan) ReplicaHelpers.setTrailingText(emailSpan, email);
    var phoneSpan = row.querySelector("td:nth-child(3) .text-muted");
    if (phoneSpan) ReplicaHelpers.setTrailingText(phoneSpan, phone);

    var stageBadge = row.querySelector("td:nth-child(5) .badge");
    if (stageBadge) {
      stageBadge.className = "badge " + stageBadgeClass(stage);
      stageBadge.textContent = stage;
    }

    var dealCell = row.querySelector("td:nth-child(6)");
    if (dealCell) dealCell.textContent = "0.00";

    var dateCell = row.querySelector("td:nth-child(7)");
    if (dateCell) dateCell.textContent = new Date().toISOString().slice(0, 10);
  }

  ReplicaFlows.register("company", {
    formSelector: "#kt_modal_add_company_form",
    modalSelector: "#kt_modal_add_company",
    tableBodySelector: "#companiesTableBody",
    storeKey: "companies",
    paginationInfoSelector: "#companyPaginationInfo",
    singularLabel: "company",
    pluralLabel: "companies",
    successMessage: "Company created successfully!",
    successPopup: true,
    successPopupText: "Company has been successfully added!",
    fillRow: fillCompanyRow,
    counters: [
      { label: "All Companies", delta: 1 },
      { label: "Cold", deltaFor: function (d) { return (d.company_stage || "Cold") === "Cold" ? 1 : 0; } },
      { label: "Warm", deltaFor: function (d) { return d.company_stage === "Warm" ? 1 : 0; } },
      { label: "Leads", deltaFor: function (d) { return d.company_stage === "Lead" ? 1 : 0; } },
      { label: "Customers", deltaFor: function (d) { return d.company_stage === "Customer" ? 1 : 0; } },
    ],
  });

  // ── Entity: Rise CRM — Contact (Pattern A: modal + table, same page) ────

  function contactStatusBadgeClass(status) {
    switch ((status || "").toLowerCase()) {
      case "verified":
        return "badge-light-success";
      case "unverified":
        return "badge-light-danger";
      default:
        return "badge-light-info";
    }
  }

  function fillContactRow(row, data) {
    var name = (data.contact_name || "New Contact").trim();
    var email = data.contact_email || "";
    var phone = data.contact_phone || "";
    var source = data.contact_source || "";
    var status = data.contact_status || "Pending";

    row.removeAttribute("style");
    row.setAttribute("data-contact-id", data.__id);
    row.setAttribute("data-name", name);
    row.setAttribute("data-email", email);
    row.setAttribute("data-phone", phone);
    row.setAttribute("data-source", source);
    row.setAttribute("data-category-ids", "");
    row.setAttribute("data-category-names", "");

    var checkbox = row.querySelector("input.contact-checkbox");
    if (checkbox) checkbox.value = data.__id;

    var nameLink = row.querySelector("td:nth-child(2) a");
    if (nameLink) {
      nameLink.textContent = name;
      nameLink.setAttribute("href", "#");
      nameLink.removeAttribute("data-stitch-page");
    }

    var emailCell = row.querySelector("td:nth-child(3)");
    if (emailCell) emailCell.textContent = email || "-";

    var companyCell = row.querySelector("td:nth-child(4)");
    if (companyCell) companyCell.textContent = "-";

    var phoneCell = row.querySelector("td:nth-child(5)");
    if (phoneCell) phoneCell.textContent = phone || "-";

    var sourceCell = row.querySelector("td:nth-child(6)");
    if (sourceCell) sourceCell.textContent = source || "-";

    var dateCell = row.querySelector("td:nth-child(7)");
    if (dateCell) dateCell.textContent = new Date().toISOString().slice(0, 10);

    var statusBadge = row.querySelector("td:nth-child(8) .badge");
    if (statusBadge) {
      statusBadge.className = "badge " + contactStatusBadgeClass(status);
      statusBadge.textContent = status;
    }
  }

  ReplicaFlows.register("contact", {
    formSelector: "#kt_modal_add_contact_form",
    modalSelector: "#kt_modal_add_contact",
    tableBodySelector: "#contactsTableBody",
    storeKey: "contacts",
    paginationInfoSelector: "#paginationInfo",
    singularLabel: "contact",
    pluralLabel: "contacts",
    successMessage: "Contact created successfully!",
    successPopup: true,
    successPopupText: "Contact has been successfully added!",
    fillRow: fillContactRow,
  });

  // ── Entity: Rise CRM — Lead (Pattern B: modal lives on its own page, then
  //    redirects to the Leads list which re-renders persisted leads) ──────

  function fillLeadRow(row, data) {
    var name = ((data.first_name || "") + " " + (data.last_name || "")).trim() || "New Lead";
    var email = data.lead_email || "";
    var company = data.company_name || "-";
    var phone = data.phn_num || "-";

    var nameLink = row.querySelector("td:nth-child(1) a");
    if (nameLink) {
      nameLink.textContent = name;
      nameLink.setAttribute("href", "#");
      nameLink.removeAttribute("data-stitch-page");
    }
    var emailDiv = row.querySelector("td:nth-child(1) .text-muted.fs-7");
    if (emailDiv) emailDiv.textContent = email;

    var companyCell = row.querySelector("td:nth-child(2)");
    if (companyCell) companyCell.textContent = company;

    var phoneCell = row.querySelector("td:nth-child(3)");
    if (phoneCell) phoneCell.textContent = phone;

    var dateCell = row.querySelector("td:nth-child(4)");
    if (dateCell) dateCell.textContent = formatDateShort(new Date());

    var assignedCell = row.querySelector("td:nth-child(5)");
    if (assignedCell) assignedCell.textContent = "—";

    var statusBadge = row.querySelector("td:nth-child(6) .badge");
    if (statusBadge) {
      statusBadge.className = "badge badge-light-warning";
      statusBadge.textContent = "New";
    }

    var quoteCell = row.querySelector("td:nth-child(7)");
    if (quoteCell) quoteCell.innerHTML = '<span class="text-muted fs-8">—</span>';

    var viewLink = row.querySelector("td:nth-child(8) a");
    if (viewLink) {
      viewLink.setAttribute("href", "#");
      viewLink.removeAttribute("data-stitch-page");
    }
  }

  ReplicaFlows.register("lead", {
    formSelector: "#kt_modal_add_customer_form",
    modalSelector: "#kt_modal_add_customer",
    tableBodySelector: "#llTable tbody",
    storeKey: "leads",
    fillRow: fillLeadRow,
    redirectTo: "../rise-crm-leads-list/page.html",
    successMessage: "Lead created successfully!",
    counters: [
      { label: "Total Leads", delta: 1, type: "stat-box" },
      { label: "Open", delta: 1, type: "stat-box" },
    ],
  });

  // ── Entity: Rise CRM — Quotation ─────────────────────────────────────────
  // "Custom Quotation" / "Generate Quote" is a real <button type="submit">
  // but it sits *outside* the <form> that holds the customer/items/terms
  // fields (a pre-existing quirk of the crawled markup), so no "submit"
  // event ever fires for it. We wire it directly via a click handler
  // instead of going through the generic form-submit entity path.

  var QUOTE_VIEW_TEMPLATE = "rise-crm-quotations-97b29a31-94b4-4bdb-a6a6-7dc929777efe-view";

  function quotationViewHref(id) {
    return "../" + QUOTE_VIEW_TEMPLATE + "/page.html?replica=quotations:" + encodeURIComponent(id);
  }

  function fillQuotationRow(row, data) {
    var codeLink = row.querySelector("td:nth-child(2) a");
    if (codeLink) {
      codeLink.textContent = data.__code;
      codeLink.setAttribute("href", quotationViewHref(data.__id));
      codeLink.removeAttribute("data-stitch-page");
    }

    var customerCell = row.querySelector("td:nth-child(3)");
    if (customerCell) customerCell.textContent = data.__customerLabel || "Walk-in Customer";

    var dateCell = row.querySelector("td:nth-child(4)");
    if (dateCell) dateCell.textContent = data.__dateLabel;

    var overviewCell = row.querySelector("td:nth-child(5)");
    if (overviewCell) overviewCell.textContent = data.title || "Untitled Quotation";

    var valueBadge = row.querySelector("td:nth-child(6) .badge");
    if (valueBadge) valueBadge.textContent = data.__grandTotal.toFixed(2);

    var statusBadge = row.querySelector("td:nth-child(7) .badge");
    if (statusBadge) {
      statusBadge.className = "badge badge-light-warning me-auto";
      statusBadge.textContent = "Pending";
    }
  }

  ReplicaFlows.register("quotation", {
    tableBodySelector: "#kt_customers_table tbody",
    storeKey: "quotations",
    fillRow: fillQuotationRow,
    successMessage: "Quotation created successfully!",
  });

  // ── Entity: Account — User (Pattern A: modal + table, same page) ────────

  function setCellText(cell, text) {
    if (!cell) return;
    var span = cell.querySelector("span, a");
    if (span) span.textContent = text;
    else cell.textContent = text;
  }

  function fillUserRow(row, data) {
    row.removeAttribute("style");
    var cells = row.querySelectorAll("td");
    var name = ((data.first_name || "") + " " + (data.last_name || "")).trim() || "New User";
    var uid = "6" + Math.floor(100 + Math.random() * 900);

    if (cells[0]) {
      var idLink = cells[0].querySelector("a");
      if (idLink) { idLink.textContent = uid; idLink.setAttribute("href", "#"); }
    }
    setCellText(cells[2], name);            // Name
    setCellText(cells[3], data.email || "-"); // Email
    setCellText(cells[4], formatDateLong(new Date())); // Created
    setCellText(cells[5], data.user_type || "Employee"); // Category

    if (cells[6]) {                          // Access badge (from multi-select)
      var badge = cells[6].querySelector(".badge");
      if (badge) badge.textContent = data.app_access || "None";
    }
    if (cells[7]) {                          // Status badge → Active
      var sb = cells[7].querySelector(".badge");
      if (sb) { sb.className = "badge badge-success"; sb.textContent = "Active"; }
    }
    var delId = row.querySelector('input[name="user_id"]');
    if (delId) delId.value = uid;
  }

  ReplicaFlows.register("user", {
    formSelector: "#kt_modal_add_user_form",
    modalSelector: "#kt_modal_add_user",
    tableBodySelector: "#kt_ecommerce_sales_table tbody",
    storeKey: "users",
    successMessage: "User created successfully!",
    successPopup: true,
    successPopupText: "User has been successfully added!",
    fillRow: fillUserRow,
  });

  // ── Entity: Likwid — Employee (Pattern A: modal + table) ────────────────
  // The crawled form has no id (only the parent modal does), which is why
  // formSelector below is a descendant selector rather than a plain "#id".

  function fillEmployeeRow(row, data) {
    row.removeAttribute("style");
    var name = (data.emp_name || "New Employee").trim();
    var designation = (data.designation || "").trim();
    var initials = name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map(function (w) { return w.charAt(0).toUpperCase(); })
      .join("") || "NE";

    var avatar = row.querySelector(".ts-avatar");
    if (avatar) avatar.textContent = initials;

    var nameEl = row.querySelector(".fw-semibold");
    if (nameEl) nameEl.textContent = name;

    var statusBadge = row.querySelector("td:nth-child(1) .badge");
    if (statusBadge) {
      statusBadge.className = "badge badge-light-success mt-1";
      statusBadge.textContent = "Active";
    }

    var designationCell = row.querySelector("td:nth-child(2)");
    if (designationCell) designationCell.textContent = designation || "—";

    // Assigned / Converted / Not Converted start at zero for a brand-new employee.
    ["3", "4", "5", "6"].forEach(function (n) {
      var badge = row.querySelector("td:nth-child(" + n + ") .badge");
      if (badge) badge.textContent = "0";
    });
    var rateBadge = row.querySelector("td:nth-child(7) .badge");
    if (rateBadge) rateBadge.textContent = "0.0%";

    row.querySelectorAll('input[name="id"]').forEach(function (input) {
      input.value = data.__id;
    });
  }

  ReplicaFlows.register("employee", {
    formSelector: "#modalAddEmployee form",
    modalSelector: "#modalAddEmployee",
    tableBodySelector: "#ts-table tbody",
    storeKey: "employees",
    successMessage: "Employee added successfully!",
    fillRow: fillEmployeeRow,
  });

  // ── Entity: Rise CRM — Email Campaign (Pattern A: modal + table) ────────

  function fillCampaignRow(row, data) {
    row.removeAttribute("style");
    row.removeAttribute("data-campaign-url");
    var cells = row.querySelectorAll("td");
    var name = (data.campaign_name || "New Campaign").trim();
    var subject = data.email_subject || "";
    var type = data.campaign_type || "General";

    if (cells[0]) {
      var spans = cells[0].querySelectorAll("span");
      if (spans[0]) spans[0].textContent = name;
      if (spans[1]) spans[1].textContent = subject;
    }
    if (cells[1]) cells[1].textContent = type;
    if (cells[2]) {
      var badge = cells[2].querySelector(".badge");
      if (badge) { badge.className = "badge badge-light-warning"; badge.textContent = "Draft"; }
    }
    if (cells[3]) cells[3].textContent = "0"; // Recipients
    if (cells[4]) cells[4].textContent = "0"; // Sent
    if (cells[5]) cells[5].textContent = "0"; // Opens
    if (cells[6]) cells[6].textContent = "0"; // Replies
  }

  ReplicaFlows.register("campaign", {
    formSelector: "#kt_modal_create_campaign_form",
    modalSelector: "#kt_modal_create_campaign",
    tableBodySelector: "#campaignsTableBody",
    storeKey: "campaigns",
    successMessage: "Campaign created successfully!",
    fillRow: fillCampaignRow,
  });

  // ── Entity: Rise CRM — Email Template (Pattern A: modal + card grid) ────

  function fillTemplateCard(card, data) {
    card.removeAttribute("data-template-id");
    var name = (data.template_name || "New Template").trim();
    var subject = data.template_subject || "";
    var content = data.template_content || "";

    var title = card.querySelector(".card-title");
    if (title) title.textContent = name;

    // A from-scratch template has no logo — drop the cloned logo image.
    var logoImg = card.querySelector(".card-body img");
    if (logoImg) {
      var logoWrap = logoImg.closest(".text-center") || logoImg.parentNode;
      if (logoWrap && logoWrap.parentNode) logoWrap.parentNode.removeChild(logoWrap);
    }

    var paras = card.querySelectorAll(".card-body p");
    // paras: [0]="Subject:" label, [1]=subject value, [2]=content preview
    if (paras[1]) paras[1].textContent = subject;
    if (paras[2]) paras[2].textContent = content;

    var used = card.querySelector("small.text-muted");
    if (used) used.textContent = "Used 0 times";

    // Point the leftover action buttons at nothing meaningful.
    card.querySelectorAll(".use-template-btn, .delete-template-btn").forEach(function (b) {
      b.removeAttribute("data-template-id");
    });
  }

  ReplicaFlows.register("template", {
    formSelector: "#kt_modal_create_template_form",
    modalSelector: "#kt_modal_create_template",
    containerSelector: "#templatesContainer",
    storeKey: "templates",
    successMessage: "Template created successfully!",
    fillCard: fillTemplateCard,
  });

  // ── Entity: Flow AI — Customer Category (Pattern A: modal + table) ──────

  function fillCategoryRow(row, data) {
    row.removeAttribute("style");
    var cells = row.querySelectorAll("td");
    var name = (data.cust_category || "New Category").trim();

    if (cells[1]) {                          // Category name link
      var link = cells[1].querySelector("a");
      if (link) {
        link.textContent = name;
        link.setAttribute("href", "#");
        link.removeAttribute("data-stitch-page");
      } else {
        cells[1].textContent = name;
      }
    }
    if (cells[2]) {                          // Added date
      var dLink = cells[2].querySelector("a");
      if (dLink) dLink.textContent = formatDateLong(new Date());
      else cells[2].textContent = formatDateLong(new Date());
    }
    if (cells[3]) {                          // Orders percentage → 0
      var pctSpan = cells[3].querySelector("span");
      if (pctSpan) pctSpan.textContent = "0";
      var bar = cells[3].querySelector(".progress-bar");
      if (bar) { bar.style.width = "0%"; bar.setAttribute("aria-valuenow", "0"); }
    }
  }

  ReplicaFlows.register("customerCategory", {
    formSelector: "#kt_modal_add_customer_category_form",
    modalSelector: "#kt_modal_add_client_category",
    tableBodySelector: "#customerCategoriesTableBody",
    storeKey: "customerCategories",
    successMessage: "Customer category added successfully!",
    fillRow: fillCategoryRow,
  });

  // ── Generic fallback — handles any create-like form with no registered
  //    entity above. Reads whatever fields exist, fakes the loading delay,
  //    then best-effort matches each field to a table column by comparing
  //    its <label> text with the table's <th> text, and falls back to a
  //    plain toast + modal close when no reasonable table can be found.
  //    Runs *after* likwid_flows.js and the registered entities above, so it
  //    only ever sees forms nothing else already claimed. ────────────────

  var GENERIC_STORE_KEY = "genericForms";
  var GENERIC_SKIP_LABEL_RE =
    /^(activate|deactivate|delete|remove|archive|restore|approve|reject|decline|duplicate|clone|log ?out|sign ?out|filter|apply(\s+filters?)?|search|sort|export|print|download|cancel|close|reset|discard)$/i;
  var GENERIC_VERBS_RE = /^(add|create|save|new|generate|update|submit|ok|confirm|yes|done|continue|next|proceed)$/i;

  function submitLabel(form, e) {
    var btn = (e && e.submitter) || form.querySelector("button[type='submit'], input[type='submit']");
    if (!btn) return "";
    var indicator = btn.querySelector && btn.querySelector(".indicator-label");
    var text = indicator ? indicator.textContent : (btn.value || btn.textContent || "");
    return String(text || "").replace(/\s+/g, " ").trim();
  }

  function isGenericSkippable(form, label) {
    if (form.hasAttribute("data-stitch-skip-generic")) return true;

    var visible = Array.prototype.filter.call(
      form.querySelectorAll("input, select, textarea"),
      function (el) { return el.type !== "hidden" && !el.disabled; }
    );
    if (!visible.length) return true; // e.g. row-action forms — only a hidden id + a button.
    if (label && GENERIC_SKIP_LABEL_RE.test(label)) return true;

    var hasFreeText = visible.some(function (el) {
      return el.tagName === "TEXTAREA" ||
        (el.tagName === "INPUT" && !/^(checkbox|radio|hidden|submit|button)$/.test(el.type));
    });
    if (!hasFreeText && (form.getAttribute("method") || "get").toLowerCase() === "get") {
      return true; // select/checkbox-only GET form — almost certainly a filter.
    }
    if (visible.length === 1) {
      var el = visible[0];
      var name = (el.name || "").toLowerCase();
      var placeholder = (el.getAttribute("placeholder") || "").toLowerCase();
      if (el.type === "search" || /search|query|^q$|filter/.test(name) || /search|filter/.test(placeholder)) {
        return true;
      }
    }
    return false;
  }

  function humanizeFieldName(name) {
    return String(name || "")
      .replace(/^id_/, "")
      .replace(/[_-]+/g, " ")
      .replace(/\b\w/g, function (c) { return c.toUpperCase(); })
      .trim();
  }

  function labelForField(form, el) {
    if (el.id) {
      var lbl = form.querySelector('label[for="' + el.id + '"]');
      if (lbl) return (lbl.textContent || "").replace(/[*:\s]+$/, "").trim();
    }
    var wrap = el.closest("label");
    if (wrap) return (wrap.textContent || "").replace(/[*:\s]+$/, "").trim();
    return humanizeFieldName(el.name);
  }

  // Snapshot the form's meaningful fields *now* (label + display value) so the
  // row-fill step later can run safely after form.reset() without re-reading
  // stale/cleared inputs.
  function collectDisplayFields(form) {
    var fields = [];
    Array.prototype.forEach.call(form.querySelectorAll("input, select, textarea"), function (el) {
      if (!el.name || el.name === "csrfmiddlewaretoken" || el.type === "hidden" || el.type === "file") return;
      var value;
      if (el.type === "checkbox") {
        if (!el.checked) return;
        value = "Yes";
      } else if (el.type === "radio") {
        if (!el.checked) return;
        value = el.value;
      } else if (el.tagName === "SELECT") {
        value = el.multiple
          ? Array.prototype.filter.call(el.options, function (o) { return o.selected; })
              .map(function (o) { return o.textContent.trim(); }).join(", ")
          : selectLabel(el);
      } else {
        value = el.value;
      }
      value = (value == null ? "" : String(value)).trim();
      if (!value) return;
      fields.push({ name: el.name, label: labelForField(form, el), value: value });
    });
    return fields;
  }

  function guessToastMessage(label, fields) {
    var cleaned = label ? label.replace(/^(add|create|save|new|generate|update)\s+/i, "").trim() : "";
    if (cleaned && !GENERIC_VERBS_RE.test(cleaned) && cleaned.toLowerCase() !== (label || "").toLowerCase()) {
      return cleaned + " added successfully!";
    }
    var first = fields.length ? fields[0].value : "";
    if (first) {
      return (first.length > 40 ? first.slice(0, 40) + "…" : first) + " saved successfully!";
    }
    return "Saved successfully!";
  }

  function findTriggerFor(modalEl) {
    if (!modalEl || !modalEl.id) return null;
    try {
      return document.querySelector(
        '[data-bs-target="#' + modalEl.id + '"], [data-bs-toggle="modal"][href="#' + modalEl.id + '"]'
      );
    } catch (err) {
      return null;
    }
  }

  // Prefer the table that lives in the same card as whatever button opened
  // this modal (works for the common "card with toolbar button + table"
  // layout); fall back to the first non-empty table on the page.
  function findGenericTable(form, modalEl) {
    var trigger = findTriggerFor(modalEl);
    var scope = (trigger && trigger.closest(".card")) ||
      (modalEl && modalEl.closest(".card")) ||
      form.closest(".card");
    var tbody = scope ? scope.querySelector("table tbody") : null;
    if (tbody && tbody.querySelector("tr")) return tbody;
    var all = document.querySelectorAll("table tbody");
    for (var i = 0; i < all.length; i++) {
      if (all[i].querySelector("tr")) return all[i];
    }
    return null;
  }

  function tableHeaders(tbody) {
    var table = tbody.closest("table");
    var headRow = table ? table.querySelector("thead tr") : null;
    if (!headRow) return [];
    return Array.prototype.map.call(headRow.children, function (th) {
      return (th.textContent || "").trim().toLowerCase();
    });
  }

  // Blanks out badges/progress bars in columns we couldn't match a field to,
  // so a new row doesn't confusingly show stats copied from the cloned
  // template row. Leaves Actions/Details columns alone.
  function neutralizeUnmatchedCell(cell) {
    Array.prototype.forEach.call(cell.querySelectorAll(".badge"), function (b) {
      var t = (b.textContent || "").trim();
      if (/^[\d.,]+%?$/.test(t)) b.textContent = t.indexOf("%") >= 0 ? "0.0%" : "0";
    });
    Array.prototype.forEach.call(cell.querySelectorAll(".progress-bar"), function (bar) {
      bar.style.width = "0%";
      bar.setAttribute("aria-valuenow", "0");
    });
    Array.prototype.forEach.call(cell.querySelectorAll("span"), function (s) {
      var t = (s.textContent || "").trim();
      if (/^\d+(\.\d+)?%$/.test(t)) s.textContent = "0.0%";
    });
  }

  function fillGenericRow(row, headers, fields) {
    var cells = row.querySelectorAll("td");
    var usedCols = {};
    fields.forEach(function (f) {
      var words = f.label.toLowerCase().split(/\s+/).filter(function (w) { return w.length > 2; });
      if (!words.length) return;
      var bestIdx = -1, bestScore = 0;
      for (var i = 0; i < headers.length; i++) {
        if (usedCols[i] || !headers[i]) continue;
        var score = 0;
        words.forEach(function (w) { if (headers[i].indexOf(w) >= 0) score++; });
        if (score > bestScore) { bestScore = score; bestIdx = i; }
      }
      if (bestIdx >= 0 && cells[bestIdx]) {
        setCellText(cells[bestIdx], f.value);
        usedCols[bestIdx] = true;
      }
    });
    for (var ci = 0; ci < cells.length; ci++) {
      if (usedCols[ci]) continue;
      if (/action|detail|manage|option/i.test(headers[ci] || "")) continue;
      neutralizeUnmatchedCell(cells[ci]);
    }
  }

  function renderGenericRow(form, modalEl, fields) {
    var tbody = findGenericTable(form, modalEl);
    if (!tbody) return;
    var template = tbody.querySelector("tr");
    if (!template) return;
    var headers = tableHeaders(tbody);
    var row = template.cloneNode(true);
    fillGenericRow(row, headers, fields);
    tbody.insertBefore(row, tbody.firstChild);
  }

  // Best-effort stable key for a form that may have no id/name — index among
  // all forms on the page is deterministic for a given static page.html.
  function formIdentity(form) {
    var forms = document.forms;
    var idx = -1;
    for (var i = 0; i < forms.length; i++) {
      if (forms[i] === form) { idx = i; break; }
    }
    var key = form.id || form.getAttribute("name") || form.getAttribute("action") || ("form-" + idx);
    return location.pathname + "::" + key;
  }

  window.__stitchGenericSubmit = function (form, e) {
    if (!form || !form.tagName || form.tagName.toUpperCase() !== "FORM") return false;
    var label = submitLabel(form, e);
    if (isGenericSkippable(form, label)) return false;

    e.preventDefault();
    e.stopPropagation();

    var btn = (e && e.submitter) || form.querySelector("button[type='submit'], input[type='submit']");
    ReplicaHelpers.setButtonLoading(btn);

    var fields = collectDisplayFields(form);
    var rawData = ReplicaHelpers.readForm(form);
    rawData.__id = newId();
    rawData.__fields = fields;

    var identity = formIdentity(form);
    var store = window.ReplicaStore[GENERIC_STORE_KEY] || (window.ReplicaStore[GENERIC_STORE_KEY] = {});
    var bucket = store[identity] || (store[identity] = []);
    bucket.unshift(rawData);
    persistStore();

    var modalEl = form.closest(".modal");
    var msg = guessToastMessage(label, fields);

    setTimeout(function () {
      ReplicaHelpers.closeModal(modalEl);
      form.reset();
      ReplicaHelpers.restoreButton(btn);
      renderGenericRow(form, modalEl, fields);
      ReplicaHelpers.showToast(msg);
      console.log("[STITCH] Generic create", identity, rawData);
    }, LOADING_MS);

    return true;
  };

  function renderGenericPersistedOnLoad() {
    var store = window.ReplicaStore[GENERIC_STORE_KEY];
    if (!store) return;
    Array.prototype.forEach.call(document.forms, function (form) {
      var identity = formIdentity(form);
      var records = store[identity];
      if (!records || !records.length) return;
      var modalEl = form.closest(".modal");
      for (var i = records.length - 1; i >= 0; i--) {
        renderGenericRow(form, modalEl, records[i].__fields || []);
      }
    });
  }

  function collectQuoteItems() {
    var items = [];
    document.querySelectorAll('input[name^="form-"][name$="-item_name"]').forEach(function (input) {
      var m = /^form-(\d+)-item_name$/.exec(input.name);
      if (!m) return;
      var idx = m[1];
      var name = (input.value || "").trim();
      if (!name) return;
      var qtyEl   = document.querySelector('[name="form-' + idx + '-quantity"]');
      var priceEl = document.querySelector('[name="form-' + idx + '-price"]');
      var taxEl   = document.querySelector('[name="form-' + idx + '-tax_rate"]');
      var qty      = parseFloat(qtyEl && qtyEl.value) || 0;
      var price    = parseFloat(priceEl && priceEl.value) || 0;
      var taxRate  = parseFloat(taxEl && taxEl.value) || 0;
      var value    = qty * price;
      var taxValue = (value * taxRate) / 100;
      items.push({
        name: name,
        quantity: qty,
        price: price,
        taxRate: taxRate,
        value: value,
        taxValue: taxValue,
        itemTotal: value + taxValue,
      });
    });
    return items;
  }

  function handleGenerateQuote(btn) {
    var customerSel   = document.getElementById("id_customer");
    var leadSel       = document.getElementById("id_lead");
    var customerLabel = selectLabel(customerSel) || selectLabel(leadSel) || "Walk-in Customer";
    var titleEl       = document.getElementById("id_title");
    var termsEl       = document.getElementById("id_terms");
    var leadTimeEl    = document.getElementById("id_lead_time");

    var items = collectQuoteItems();
    var subtotal = 0, gst = 0;
    items.forEach(function (item) {
      subtotal += item.value;
      gst      += item.taxValue;
    });

    var data = {
      __id:           newId(),
      __code:         fakeCode("QUO"),
      __customerLabel: customerLabel,
      __dateLabel:    formatDateLong(new Date()),
      __grandTotal:   subtotal + gst,
      title:          (titleEl && titleEl.value.trim()) || "Quotation for " + customerLabel,
      terms:          termsEl ? termsEl.value.trim() : "",
      lead_time:      leadTimeEl ? leadTimeEl.value : "0",
      items:          items,
    };

    var store = window.ReplicaStore.quotations || (window.ReplicaStore.quotations = []);
    store.unshift(data);
    persistStore();

    ReplicaHelpers.setButtonLoading(btn);
    ReplicaHelpers.setFlash("Quotation created successfully!");

    setTimeout(function () {
      location.href = "../rise-crm-quotations-date-wise/page.html";
    }, LOADING_MS);
  }

  (function wireGenerateQuoteButton() {
    if (!document.getElementById("id_customer")) return; // only on the add-quotation page
    document.addEventListener(
      "click",
      function (e) {
        var btn = e.target.closest && e.target.closest("button[type='submit']");
        if (!btn || (btn.textContent || "").indexOf("Generate Quote") < 0) return;
        e.preventDefault();
        e.stopPropagation();
        if (e.stopImmediatePropagation) e.stopImmediatePropagation();
        handleGenerateQuote(btn);
      },
      true
    );
  })();

  // ── Quotation view template — rewrites the invoice card when the URL
  //    carries ?replica=quotations:<id> (see QUOTE_VIEW_TEMPLATE above).

  function renderQuotationView(data) {
    var idEl = document.getElementById("replicaQuoteId");
    if (!idEl) return;

    var h1 = document.querySelector(".page-heading");
    if (h1) h1.textContent = "Quotation: " + data.__code;

    var companyEl = document.getElementById("replicaQuoteCompany");
    if (companyEl) companyEl.textContent = data.__customerLabel || "Customer";

    var nameEl = document.getElementById("replicaQuoteCustomerName");
    if (nameEl) nameEl.textContent = data.__customerLabel || "Customer";
    var contactEl = document.getElementById("replicaQuoteCustomerContact");
    if (contactEl) contactEl.textContent = "(—) | (—)";
    var cityEl = document.getElementById("replicaQuoteCity");
    if (cityEl) cityEl.textContent = "—";
    var countryEl = document.getElementById("replicaQuoteCountry");
    if (countryEl) countryEl.textContent = "—";

    idEl.textContent = data.__code;
    var dateEl = document.getElementById("replicaQuoteDate");
    if (dateEl) dateEl.textContent = data.__dateLabel;
    var leadTimeEl = document.getElementById("replicaQuoteLeadTime");
    if (leadTimeEl) leadTimeEl.textContent = data.lead_time || "0";
    var statusEl = document.getElementById("replicaQuoteStatus");
    if (statusEl) statusEl.textContent = "Pending";

    var detailsEl = document.getElementById("replicaQuoteCustomerDetails");
    if (detailsEl) detailsEl.textContent = "(—) | (—)";

    var tbody = document.getElementById("replicaQuoteItems");
    if (tbody) {
      while (tbody.children.length > 3) tbody.removeChild(tbody.firstChild);
      var anchor = tbody.children[0];
      var items = data.items || [];
      var subtotal = 0, gst = 0;
      items.forEach(function (item) {
        subtotal += item.value;
        gst      += item.taxValue;
        var tr    = document.createElement("tr");
        tr.innerHTML =
          "<td>" + escapeHtml(item.name) + "</td>" +
          '<td class="text-end">' + item.quantity + "</td>" +
          '<td class="text-end">' + item.price.toFixed(2) + "</td>" +
          '<td class="text-end">' + item.taxRate + "</td>" +
          '<td class="text-end">' + item.value.toFixed(2) + "</td>" +
          '<td class="text-end">' + item.taxValue.toFixed(2) + "</td>" +
          '<td class="text-end">' + item.itemTotal.toFixed(2) + "</td>";
        tbody.insertBefore(tr, anchor);
      });
      var subtotalEl = document.getElementById("replicaQuoteSubtotal");
      if (subtotalEl) subtotalEl.textContent = subtotal.toFixed(2);
      var gstEl = document.getElementById("replicaQuoteGst");
      if (gstEl) gstEl.textContent = gst.toFixed(2);
      var grandEl = document.getElementById("replicaQuoteGrandTotal");
      if (grandEl) grandEl.textContent = (subtotal + gst).toFixed(2);
    }

    var titleEl2 = document.getElementById("replicaQuoteTitle");
    if (titleEl2) titleEl2.textContent = "Title: " + (data.title || "");
    var termsEl2 = document.getElementById("replicaQuoteTerms");
    if (termsEl2) termsEl2.textContent = "Terms & Conditions: " + (data.terms || "");
  }

  (function bootstrapReplicaView() {
    var params = new URLSearchParams(location.search);
    var raw    = params.get("replica");
    if (!raw) return;
    var sepIdx = raw.indexOf(":");
    if (sepIdx < 0) return;
    var storeKey = raw.slice(0, sepIdx);
    var id       = raw.slice(sepIdx + 1);
    var records  = window.ReplicaStore[storeKey] || [];
    var record   = null;
    for (var i = 0; i < records.length; i++) {
      if (records[i].__id === id) {
        record = records[i];
        break;
      }
    }
    if (!record) return;
    if (storeKey === "quotations") renderQuotationView(record);
  })();

  // ── Flash-on-load: show toast from a previous redirect flow ─────────────
  (function consumeFlash() {
    var msg = ReplicaHelpers.readAndClearFlash();
    if (!msg) return;
    // Small delay so the page DOM and rows render first.
    setTimeout(function () {
      ReplicaHelpers.showToast(msg);
    }, 150);
  })();

  // ── Select2 shim ────────────────────────────────────────────────────────
  // The crawler captured Select2 dropdowns in their already-initialized state:
  // the real <select> is hidden (.select2-hidden-accessible) and a fake
  // <span> box is shown in its place. The Select2 library / jQuery are not
  // present in the clone, so those boxes are inert. This shim revives them —
  // clicking a box opens a native-looking panel built from the <select>'s
  // options; picking one writes the value back, updates the box label, and
  // dispatches a real `change` event so downstream listeners (auto-fill) run.
  (function select2Shim() {
    var open = null; // { panel, container, box, select }

    function realSelectFor(container) {
      // Select2 inserts its container immediately after the <select>.
      var prev = container.previousElementSibling;
      if (prev && prev.tagName === "SELECT") return prev;
      return null;
    }

    function close() {
      if (!open) return;
      if (open.panel && open.panel.parentNode) {
        open.panel.parentNode.removeChild(open.panel);
      }
      if (open.container) open.container.classList.remove("select2-container--open");
      document.removeEventListener("mousedown", onDocDown, true);
      document.removeEventListener("keydown", onKey, true);
      window.removeEventListener("resize", close, true);
      window.removeEventListener("scroll", close, true);
      open = null;
    }

    function onDocDown(e) {
      if (open && (open.panel.contains(e.target) || open.box.contains(e.target))) return;
      close();
    }

    function onKey(e) {
      if (e.key === "Escape" || e.keyCode === 27) close();
    }

    function fireChange(select) {
      var evt;
      try {
        evt = new Event("change", { bubbles: true });
      } catch (err) {
        evt = document.createEvent("Event");
        evt.initEvent("change", true, false);
      }
      select.dispatchEvent(evt);
    }

    // Single-select: set the value and update the single rendered label.
    function commit(select, container, opt) {
      select.value = opt.value;
      var rendered = container.querySelector(".select2-selection__rendered");
      if (rendered) {
        var label = (opt.textContent || "").trim() || opt.value;
        rendered.setAttribute("title", label);
        rendered.textContent = label;
      }
      fireChange(select);
    }

    // Multi-select: toggle the option and rebuild the choice "chips" in the
    // rendered <ul>, preserving the inline search box Select2 keeps at the end.
    function commitMultiple(select, container, opt) {
      opt.selected = !opt.selected;
      var rendered = container.querySelector("ul.select2-selection__rendered");
      if (rendered) {
        var search = rendered.querySelector(".select2-search--inline");
        Array.prototype.slice
          .call(rendered.querySelectorAll(".select2-selection__choice"))
          .forEach(function (c) { rendered.removeChild(c); });
        Array.prototype.forEach.call(select.options, function (o) {
          if (!o.selected || !o.value) return;
          var li = document.createElement("li");
          li.className = "select2-selection__choice";
          li.setAttribute("title", o.textContent.trim());
          var disp = document.createElement("span");
          disp.className = "select2-selection__choice__display";
          disp.textContent = o.textContent.trim();
          li.appendChild(disp);
          rendered.insertBefore(li, search || null);
        });
      }
      fireChange(select);
    }

    function openFor(box) {
      var container = box.closest(".select2-container");
      if (!container) return;
      var select = realSelectFor(container);
      if (!select) return;

      // Toggle: clicking the same box that's already open just closes it.
      var wasSame = open && open.box === box;
      close();
      if (wasSame) return;

      var rect = box.getBoundingClientRect();
      var panel = document.createElement("span");
      panel.className =
        "select2-container select2-container--bootstrap5 select2-container--open replica-select2-panel";
      panel.style.cssText =
        "position:fixed;z-index:100000;left:" + rect.left + "px;top:" + rect.bottom +
        "px;width:" + rect.width + "px;";

      var dd = document.createElement("span");
      dd.className = "select2-dropdown select2-dropdown--below";
      dd.style.width = rect.width + "px";

      var results = document.createElement("span");
      results.className = "select2-results";
      var ul = document.createElement("ul");
      ul.className = "select2-results__options";
      ul.setAttribute("role", "listbox");

      Array.prototype.forEach.call(select.options, function (opt) {
        var li = document.createElement("li");
        li.className = "select2-results__option";
        li.setAttribute("role", "option");
        li.textContent = (opt.textContent || "").trim() || opt.value;
        if (opt.selected) li.classList.add("select2-results__option--selected");
        li.addEventListener("mouseenter", function () {
          Array.prototype.forEach.call(ul.children, function (c) {
            c.classList.remove("select2-results__option--highlighted");
          });
          li.classList.add("select2-results__option--highlighted");
        });
        li.addEventListener("click", function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          if (select.multiple) {
            commitMultiple(select, container, opt);
            li.classList.toggle("select2-results__option--selected", opt.selected);
            // keep the panel open so more can be picked
          } else {
            commit(select, container, opt);
            close();
          }
        });
        ul.appendChild(li);
      });

      results.appendChild(ul);
      dd.appendChild(results);
      panel.appendChild(dd);
      document.body.appendChild(panel);
      container.classList.add("select2-container--open");

      open = { panel: panel, container: container, box: box, select: select };
      document.addEventListener("mousedown", onDocDown, true);
      document.addEventListener("keydown", onKey, true);
      window.addEventListener("resize", close, true);
      window.addEventListener("scroll", close, true);
    }

    // Capture-phase click: runs before runtime.js's generic handler (this file
    // is injected first), and stopImmediatePropagation keeps that handler from
    // treating the click as an "unwired" control.
    document.addEventListener(
      "click",
      function (e) {
        var box = e.target && e.target.closest && e.target.closest(".select2-selection");
        if (!box) return;
        e.preventDefault();
        e.stopPropagation();
        if (e.stopImmediatePropagation) e.stopImmediatePropagation();
        openFor(box);
      },
      true
    );
  })();

  // ── Email-template auto-fill ────────────────────────────────────────────
  // When a template is chosen in the Create Email Campaign modal, populate the
  // subject / content / logo / hyperlink fields from the option's data-* attrs,
  // matching the real site. Selecting "Write from scratch" clears them.
  (function emailTemplateAutofill() {
    var sel = document.getElementById("email_template_select");
    if (!sel) return;

    function setVal(id, val) {
      var el = document.getElementById(id);
      if (el) el.value = val || "";
    }

    sel.addEventListener("change", function () {
      var opt = sel.options[sel.selectedIndex];
      if (!opt) return;

      var subject = opt.getAttribute("data-template-subject") || "";
      var content = opt.getAttribute("data-template-content") || "";
      var logo = opt.getAttribute("data-template-logo") || "";
      var hlUrl = opt.getAttribute("data-template-hyperlink-url") || "";
      var hlText = opt.getAttribute("data-template-hyperlink-text") || "";
      var type = opt.getAttribute("data-template-type") || "";

      setVal("email_subject", subject);
      setVal("email_content", content);
      setVal("campaign_logo_url", logo);
      setVal("campaign_hyperlink_url", hlUrl);
      setVal("campaign_hyperlink_text", hlText);

      var prev = document.getElementById("campaign_logo_preview");
      var img = document.getElementById("campaign_logo_preview_img");
      if (logo) {
        if (img) img.src = logo;
        if (prev) prev.style.display = "";
      } else {
        if (prev) prev.style.display = "none";
      }

      // Reflect the template's campaign type in its own Select2 box.
      if (type) {
        var typeSel = document.querySelector('select[name="campaign_type"]');
        if (typeSel) {
          typeSel.value = type;
          var typeContainer = typeSel.nextElementSibling;
          if (typeContainer && typeContainer.classList.contains("select2-container")) {
            var r = typeContainer.querySelector(".select2-selection__rendered");
            if (r) {
              r.setAttribute("title", type);
              r.textContent = type;
            }
          }
        }
      }
    });
  })();

  renderPersistedOnLoad();
  renderGenericPersistedOnLoad();

  console.log("[STITCH] replica forms ready");
})();
