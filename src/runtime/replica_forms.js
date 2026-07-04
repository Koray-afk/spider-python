// Replica forms — generic client-side "create record" simulation for the
// stitched clone. There is no backend, so this layer intercepts form submits,
// stores the submitted data in window.ReplicaStore, and updates the DOM
// (table row, counters, pagination text, modal, success popup) so the app
// *feels* like the real thing even though nothing is persisted server-side.
//
// Entities (company, contact, lead, ...) are added via ReplicaFlows.register()
// with a small config object; the actual DOM wiring lives in the shared
// ReplicaHelpers functions below so new entities never need to duplicate it.
(function () {
  "use strict";

  window.ReplicaStore = window.ReplicaStore || {};

  function escapeHtml(str) {
    return String(str == null ? "" : str).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  // ── Generic helpers (reusable across entities) ──────────────────────────

  var ReplicaHelpers = {};

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

  ReplicaHelpers.updateCounters = function (counterConfigs, data) {
    (counterConfigs || []).forEach(function (c) {
      var delta = typeof c.deltaFor === "function" ? c.deltaFor(data) : (c.delta || 0);
      ReplicaHelpers.bumpCounterCard(c.label, delta);
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
    var store = window.ReplicaStore[entity.storeKey] || (window.ReplicaStore[entity.storeKey] = []);
    data.__id = "new-" + Date.now();
    store.unshift(data);

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

    var modalEl = entity.modalSelector ? document.querySelector(entity.modalSelector) : null;
    ReplicaHelpers.closeModal(modalEl);
    form.reset();

    ReplicaHelpers.showSuccessPopup({
      title: entity.successTitle || "Added",
      text: entity.successText || "The item has been successfully added.",
    });

    console.log("[STITCH] Replica create", entity.storeKey, data);
    return true;
  };

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
})();
