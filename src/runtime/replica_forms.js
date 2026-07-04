// Replica forms — generic client-side "create record" simulation for the
// stitched clone. There is no backend, so this layer intercepts form submits,
// stores the submitted data in window.ReplicaStore (persisted to
// localStorage so records survive full-page navigation), and updates the DOM
// (table row, counters, pagination text, modal, success popup) so the app
// *feels* like the real thing even though nothing is persisted server-side.
//
// Entities (company, contact, lead, quotation, ...) are added via
// ReplicaFlows.register() with a small config object; the actual DOM wiring
// lives in the shared ReplicaHelpers functions below so new entities never
// need to duplicate it.
(function () {
  "use strict";

  var STORAGE_KEY = "__stitchReplicaStore__";

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

  ReplicaHelpers.showSuccessPopup = function (opts) {
    opts = opts || {};
    var title = opts.title || "Success";
    var text = opts.text || "";

    if (window.Swal && typeof window.Swal.fire === "function") {
      window.Swal.fire({ icon: "success", title: title, text: text });
      return;
    }

    // Lightweight clone matching the swal2 markup/classes already styled by
    // the page's bundled CSS (used elsewhere for captured confirm dialogs).
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
      '<div class="swal2-html-container" style="display:block;">' + escapeHtml(text) + "</div>" +
      '<div class="swal2-actions" style="display:flex;">' +
      '<button type="button" class="swal2-confirm btn btn-primary">Ok, got it!</button>' +
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
    if (!form || !form.id) return false;
    var entity = ReplicaFlows.findByForm(form);
    if (!entity) return false;

    e.preventDefault();
    e.stopPropagation();

    var data = ReplicaHelpers.readForm(form);
    data.__id = newId();
    if (typeof entity.beforeSave === "function") entity.beforeSave(data, form);

    var store = window.ReplicaStore[entity.storeKey] || (window.ReplicaStore[entity.storeKey] = []);
    store.unshift(data);
    persistStore();

    var modalEl = entity.modalSelector ? document.querySelector(entity.modalSelector) : null;

    // Pattern B: the form lives on its own page (no table to update here) —
    // save + redirect to the real list page, which re-renders every
    // persisted record (including this one) on load.
    if (entity.redirectTo) {
      ReplicaHelpers.closeModal(modalEl);
      form.reset();
      location.href = typeof entity.redirectTo === "function" ? entity.redirectTo(data) : entity.redirectTo;
      return true;
    }

    // Pattern A: modal + table live on the same page — update in place.
    var rowEl = ReplicaHelpers.buildRow(entity, data, store.length);
    if (rowEl) ReplicaHelpers.prependTableRow(entity.tableBodySelector, rowEl);

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

    ReplicaHelpers.closeModal(modalEl);
    form.reset();

    ReplicaHelpers.showSuccessPopup({
      title: entity.successTitle || "Added",
      text: entity.successText || "The item has been successfully added.",
    });

    console.log("[STITCH] Replica create", entity.storeKey, data);
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
      if (!cfg.tableBodySelector || !cfg.storeKey) continue;
      var tbody = document.querySelector(cfg.tableBodySelector);
      if (!tbody) continue;
      var records = window.ReplicaStore[cfg.storeKey] || [];
      if (!records.length) continue;

      for (var i = records.length - 1; i >= 0; i--) {
        var rowEl = ReplicaHelpers.buildRow(cfg, records[i]);
        if (rowEl) ReplicaHelpers.prependTableRow(cfg.tableBodySelector, rowEl);
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
    successTitle: "Company Added",
    successText: "The company has been successfully added.",
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

    var checkbox = row.querySelector('input.contact-checkbox');
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
    successTitle: "Contact Added",
    successText: "The contact has been successfully added.",
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
  });

  function collectQuoteItems() {
    var items = [];
    document.querySelectorAll('input[name^="form-"][name$="-item_name"]').forEach(function (input) {
      var m = /^form-(\d+)-item_name$/.exec(input.name);
      if (!m) return;
      var idx = m[1];
      var name = (input.value || "").trim();
      if (!name) return;
      var qtyEl = document.querySelector('[name="form-' + idx + '-quantity"]');
      var priceEl = document.querySelector('[name="form-' + idx + '-price"]');
      var taxEl = document.querySelector('[name="form-' + idx + '-tax_rate"]');
      var qty = parseFloat(qtyEl && qtyEl.value) || 0;
      var price = parseFloat(priceEl && priceEl.value) || 0;
      var taxRate = parseFloat(taxEl && taxEl.value) || 0;
      var value = qty * price;
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

  function handleGenerateQuote() {
    var customerSel = document.getElementById("id_customer");
    var leadSel = document.getElementById("id_lead");
    var customerLabel = selectLabel(customerSel) || selectLabel(leadSel) || "Walk-in Customer";
    var titleEl = document.getElementById("id_title");
    var termsEl = document.getElementById("id_terms");
    var leadTimeEl = document.getElementById("id_lead_time");

    var items = collectQuoteItems();
    var subtotal = 0, gst = 0;
    items.forEach(function (item) {
      subtotal += item.value;
      gst += item.taxValue;
    });

    var data = {
      __id: newId(),
      __code: fakeCode("QUO"),
      __customerLabel: customerLabel,
      __dateLabel: formatDateLong(new Date()),
      __grandTotal: subtotal + gst,
      title: (titleEl && titleEl.value.trim()) || "Quotation for " + customerLabel,
      terms: termsEl ? termsEl.value.trim() : "",
      lead_time: leadTimeEl ? leadTimeEl.value : "0",
      items: items,
    };

    var store = window.ReplicaStore.quotations || (window.ReplicaStore.quotations = []);
    store.unshift(data);
    persistStore();

    location.href = "../rise-crm-quotations-date-wise/page.html";
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
        handleGenerateQuote();
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
        gst += item.taxValue;
        var tr = document.createElement("tr");
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

    var titleEl = document.getElementById("replicaQuoteTitle");
    if (titleEl) titleEl.textContent = "Title: " + (data.title || "");
    var termsEl = document.getElementById("replicaQuoteTerms");
    if (termsEl) termsEl.textContent = "Terms & Conditions: " + (data.terms || "");
  }

  (function bootstrapReplicaView() {
    var params = new URLSearchParams(location.search);
    var raw = params.get("replica");
    if (!raw) return;
    var sepIdx = raw.indexOf(":");
    if (sepIdx < 0) return;
    var storeKey = raw.slice(0, sepIdx);
    var id = raw.slice(sepIdx + 1);
    var records = window.ReplicaStore[storeKey] || [];
    var record = null;
    for (var i = 0; i < records.length; i++) {
      if (records[i].__id === id) {
        record = records[i];
        break;
      }
    }
    if (!record) return;
    if (storeKey === "quotations") renderQuotationView(record);
  })();

  renderPersistedOnLoad();

  console.log("[STITCH] replica forms ready");
})();
