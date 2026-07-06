// Demo flow replay for key Likwid create/filter actions (static clone).
(function () {
  "use strict";

  var CFG = window.__LIKWID_FLOWS__ || { toasts: {}, redirects: {} };

  function isFlowPage() {
    var p = location.pathname;
    return (
      p.indexOf("flow-ai-customers-list") >= 0 ||
      p.indexOf("flow-ai-orders-orders-list") >= 0 ||
      p.indexOf("flow-ai-orders-sales-order-create") >= 0 ||
      p.indexOf("flow-ai-vendors-add-vendor") >= 0 ||
      p.indexOf("flow-ai-vendors-vendor-list") >= 0 ||
      p.indexOf("flow-ai-inventory-stock-list") >= 0
    );
  }
  if (!isFlowPage()) return;

  function tpl(text, data) {
    return String(text || "").replace(/\{\{(\w+)\}\}/g, function (_, k) {
      return data[k] != null ? String(data[k]) : "";
    });
  }

  function formFields(form) {
    var data = {};
    form.querySelectorAll("input, select, textarea").forEach(function (el) {
      if (!el.name || el.name === "csrfmiddlewaretoken") return;
      if (el.type === "checkbox") data[el.name] = el.checked;
      else if (el.type === "radio") {
        if (el.checked) data[el.name] = el.value;
      } else data[el.name] = el.value;
    });
    return data;
  }

  function selectLabel(form, name) {
    if (!form) return "";
    var sel = form.querySelector('[name="' + name + '"]');
    if (!sel || sel.selectedIndex < 0) return "";
    var opt = sel.options[sel.selectedIndex];
    return opt ? opt.text.trim() : "";
  }

  function showToast(msg) {
    var wrap = document.createElement("div");
    wrap.style.cssText =
      "position:fixed;top:80px;right:24px;z-index:100000;max-width:420px;";
    wrap.innerHTML =
      '<div class="alert alert-success alert-dismissible fade show" role="alert">' +
      msg +
      '<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>';
    document.body.appendChild(wrap);
    setTimeout(function () {
      if (wrap.parentNode) wrap.parentNode.removeChild(wrap);
    }, 4500);
  }

  function hideModal(modal) {
    if (!modal) return;
    modal.classList.remove("show");
    modal.style.display = "none";
    modal.setAttribute("aria-hidden", "true");
    document.querySelectorAll('[data-stitch-modal-backdrop="' + (modal.id || "") + '"]').forEach(
      function (el) {
        if (el.parentNode) el.parentNode.removeChild(el);
      }
    );
    document.querySelectorAll(".modal-backdrop").forEach(function (el) {
      if (el.parentNode) el.parentNode.removeChild(el);
    });
    if (!document.querySelector(".modal.show")) {
      document.body.classList.remove("modal-open");
      document.body.style.removeProperty("overflow");
      document.body.style.removeProperty("padding-right");
    }
  }

  function fakeId(prefix) {
    return prefix + "-69-" + String(Math.floor(10000 + Math.random() * 89999));
  }

  function prependCustomerRow(fields) {
    var tbody = document.querySelector("table.cst-table tbody");
    if (!tbody) return;
    var name = fields.cust_comname || "New Customer";
    var email = fields.cust_email || "";
    var cat = selectLabel(
      document.querySelector("#addCustomerModal form") || document.body,
      "category"
    ) || "—";
    var tr = document.createElement("tr");
    tr.innerHTML =
      '<td><a href="#" class="fw-semibold text-gray-800 text-hover-primary fs-7">' +
      name +
      "</a>" +
      (email ? '<div class="text-gray-400 fs-8">' + email + "</div>" : "") +
      '</td><td class="text-gray-500 fs-7">CLI-new</td><td><span class="badge badge-light fw-semibold fs-8">' +
      cat +
      '</span></td><td class="text-gray-500 fs-7">' +
      (fields.city || "—") +
      '</td><td class="text-gray-600 fs-7 fw-semibold">0</td><td class="text-gray-700 fs-7 fw-semibold">₹0</td>' +
      '<td><span class="btn btn-sm btn-light-primary fw-semibold fs-8">View</span></td>';
    tbody.insertBefore(tr, tbody.firstChild);
  }

  function prependOrderRow(fields, custName, itemName) {
    var tbody = document.querySelector("#kt_ecommerce_sales_table tbody");
    if (!tbody) return;
    var oid = fields.order_id || fakeId("ORD");
    var qty = fields.order_quantity || "1";
    var rate = fields.order_rate || "0";
    var value = (parseFloat(qty) * parseFloat(rate) || 0).toFixed(2);
    var spec = fields.order_specification || "—";
    var tr = document.createElement("tr");
    tr.className = "orders-row";
    tr.innerHTML =
      '<td style="padding-left:24px;"><div class="form-check form-check-sm form-check-custom form-check-solid">' +
      '<input class="form-check-input" type="checkbox" value="1"></div></td>' +
      '<td><a href="#" class="orders-order-link">' +
      oid +
      '</a><div style="margin-top:3px;"><span class="badge badge-light-warning" style="font-size:10px;">No Plan</span></div></td>' +
      '<td><a href="#" class="orders-customer-link">' +
      (custName || "Customer") +
      '</a></td><td><span class="orders-td-main">—</span></td>' +
      '<td><span class="orders-td-main"></span><div style="margin-top:2px;font-size:11px;color:#888;font-style:italic;">' +
      (itemName || "Product") +
      '</div></td><td class="text-end"><span class="orders-td-main">—</span></td>' +
      '<td class="text-end"><span class="orders-td-main">—</span></td>' +
      '<td class="text-end dt-type-numeric"><span class="orders-td-main">' +
      qty +
      '</span></td><td class="text-end dt-type-numeric"><span class="orders-td-main fw-semibold">' +
      value +
      '</span></td><td class="text-end"><span class="orders-status"><span class="orders-dot" style="background:#f1bc00;"></span>Pending</span></td>' +
      '<td class="text-end" style="padding-right:24px;"><div class="d-flex justify-content-end gap-2">' +
      '<span class="btn btn-icon btn-sm btn-light btn-active-light-primary" title="View"><i class="ki-duotone ki-eye fs-4"></i></span></div></td>';
    tbody.insertBefore(tr, tbody.firstChild);
  }

  function prependVendorRow(fields) {
    var tbody = document.getElementById("vndTableBody");
    if (!tbody) return;
    var name = fields.vend_comname || "New Vendor";
    var email = fields.vend_email || "";
    var code = fakeId("VEN");
    var cat = fields.inv_cat_label || fields.inv_cat || "Raw Materials";
    var tr = document.createElement("tr");
    tr.className = "vnd-row";
    tr.setAttribute("data-search", (name + " " + code).toLowerCase());
    tr.innerHTML =
      '<td><a href="#" class="fw-semibold text-gray-700 text-hover-primary fs-7">' +
      code +
      '</a></td><td><a href="#" class="fw-semibold text-gray-800 text-hover-primary fs-7">' +
      name +
      "</a>" +
      (email ? '<div class="text-gray-400 fs-8">' + email + "</div>" : "") +
      '</td><td><span class="badge badge-light fw-semibold fs-8">' +
      cat +
      '</span></td><td class="text-gray-500 fs-7">' +
      (fields.city || "—") +
      '</td><td class="fw-semibold text-gray-700 fs-7">₹0</td><td class="text-gray-400 fs-7">—</td>' +
      '<td><span class="btn btn-sm btn-light-primary fw-semibold fs-8">View</span></td>';
    tbody.insertBefore(tr, tbody.firstChild);
  }

  function prependInvRow(fields) {
    var tbody = document.getElementById("invTableBody");
    if (!tbody) return;
    var name = fields.item_name || "New Item";
    var code = fakeId("STOCK");
    var cat = selectLabel(
      document.querySelector("#kt_modal_add_inv_item form") || document.body,
      "inv_cat"
    ) || "—";
    var store = selectLabel(
      document.querySelector("#kt_modal_add_inv_item form") || document.body,
      "store"
    ) || "—";
    var stock = fields.current_stock || "0";
    var tr = document.createElement("tr");
    tr.className = "inv-row";
    tr.setAttribute("data-search", (name + " " + code).toLowerCase());
    tr.innerHTML =
      '<td><a href="#" class="fw-semibold text-gray-700 text-hover-primary fs-7">' +
      code +
      '</a></td><td><span class="inv-dot" style="background:#50cd89;"></span><span class="fs-8 text-gray-500">FG</span></td>' +
      '<td class="fw-semibold text-gray-800 fs-7">' +
      name +
      '</td><td class="text-gray-500 fs-7">' +
      cat +
      '</td><td class="text-gray-500 fs-7">' +
      store +
      '</td><td class="fw-semibold text-gray-700 fs-7">' +
      stock +
      '</td><td><span class="fw-bold fs-7" style="color:#50cd89;">' +
      stock +
      '</span></td><td class="text-gray-500 fs-7">0</td><td class="text-gray-500 fs-7">—</td>' +
      '<td><span class="btn btn-sm btn-light-primary fw-semibold fs-8">View</span></td>';
    tbody.insertBefore(tr, tbody.firstChild);
  }

  function filterOrderRows(form) {
    var fields = formFields(form);
    var cust = selectLabel(form, "customer").toLowerCase();
    var item = selectLabel(form, "inv_item").toLowerCase();
    var status = fields.status || "all";
    document.querySelectorAll("#kt_ecommerce_sales_table tbody tr.orders-row").forEach(function (row) {
      var text = (row.textContent || "").toLowerCase();
      var show = true;
      if (cust && text.indexOf(cust) < 0) show = false;
      if (item && text.indexOf(item) < 0) show = false;
      if (status && status !== "all" && text.indexOf(status.toLowerCase()) < 0) show = false;
      row.style.display = show ? "" : "none";
    });
  }

  function filterInvRows(form) {
    var fields = formFields(form);
    var type = (fields.filter_type || "").toLowerCase();
    var cat = selectLabel(form, "filter_cat").toLowerCase();
    var store = selectLabel(form, "filter_store").toLowerCase();
    document.querySelectorAll("#invTableBody tr.inv-row").forEach(function (row) {
      var text = (row.textContent || "").toLowerCase();
      var show = true;
      if (type && text.indexOf(type) < 0) show = false;
      if (cat && text.indexOf(cat) < 0) show = false;
      if (store && text.indexOf(store) < 0) show = false;
      row.style.display = show ? "" : "none";
    });
  }

  function wireForms() {
    document
      .querySelectorAll(
        "#addCustomerModal form, #add_order_form, #so-form, #kt_modal_add_customer_form, " +
          "#kt_modal_add_inv_item form, #kt_modal_filter_orders form, #kt_modal_filter_inv form"
      )
      .forEach(function (f) {
        f.setAttribute("novalidate", "novalidate");
      });
  }

  function wireSearch() {
    var inp = document.querySelector('[data-kt-ecommerce-order-filter="search"]');
    if (!inp || inp.__stitchFlowSearch) return;
    inp.__stitchFlowSearch = true;
    inp.addEventListener("input", function () {
      var q = (inp.value || "").toLowerCase();
      document.querySelectorAll("#kt_ecommerce_sales_table tbody tr.orders-row").forEach(function (row) {
        row.style.display = !q || (row.textContent || "").toLowerCase().indexOf(q) >= 0 ? "" : "none";
      });
    });
    var invSearch = document.querySelector('#invTableBody') &&
      document.querySelector('input[placeholder*="Search"]');
    if (invSearch && !invSearch.__stitchFlowSearch) {
      invSearch.__stitchFlowSearch = true;
      invSearch.addEventListener("input", function () {
        var q = (invSearch.value || "").toLowerCase();
        document.querySelectorAll("#invTableBody tr.inv-row").forEach(function (row) {
          row.style.display = !q || (row.textContent || "").toLowerCase().indexOf(q) >= 0 ? "" : "none";
        });
      });
    }
  }

  window.__stitchLikwidFlowSubmit = function (form, e) {
    if (!form || !form.closest) return false;
    var fields = formFields(form);
    var method = (form.getAttribute("method") || "get").toLowerCase();

    if (form.closest("#addCustomerModal")) {
      e.preventDefault();
      e.stopPropagation();
      hideModal(document.getElementById("addCustomerModal"));
      prependCustomerRow(fields);
      showToast(tpl(CFG.toasts.add_customer, fields));
      form.reset();
      return true;
    }

    if (form.id === "add_order_form" || form.closest("#kt_modal_add_order")) {
      e.preventDefault();
      e.stopPropagation();
      fields.order_id = fakeId("ORD");
      var custName = selectLabel(form, "cust");
      var itemName = selectLabel(form, "item");
      hideModal(document.getElementById("kt_modal_add_order"));
      prependOrderRow(fields, custName, itemName);
      showToast(tpl(CFG.toasts.add_order, fields));
      form.reset();
      return true;
    }

    if (form.id === "so-form") {
      e.preventDefault();
      e.stopPropagation();
      showToast(tpl(CFG.toasts.add_sale_order, fields));
      setTimeout(function () {
        location.href = CFG.redirects.after_sale_order || "../flow-ai-orders-orders-list/page.html";
      }, 800);
      return true;
    }

    if (form.id === "kt_modal_add_customer_form" || form.closest("#kt_modal_add_customer_form")) {
      e.preventDefault();
      e.stopPropagation();
      fields.inv_cat_label = selectLabel(form, "inv_cat");
      showToast(tpl(CFG.toasts.add_vendor, fields));
      setTimeout(function () {
        location.href = CFG.redirects.after_vendor || "../flow-ai-vendors-vendor-list/page.html";
      }, 800);
      try {
        sessionStorage.setItem("stitch_pending_vendor", JSON.stringify(fields));
      } catch (err) {}
      return true;
    }

    if (form.closest("#kt_modal_add_inv_item")) {
      e.preventDefault();
      e.stopPropagation();
      hideModal(document.getElementById("kt_modal_add_inv_item"));
      prependInvRow(fields);
      showToast(tpl(CFG.toasts.add_item, fields));
      form.reset();
      return true;
    }

    if (form.closest("#kt_modal_filter_orders")) {
      e.preventDefault();
      e.stopPropagation();
      hideModal(document.getElementById("kt_modal_filter_orders"));
      filterOrderRows(form);
      showToast(CFG.toasts.apply_filters || "Filters applied.");
      return true;
    }

    if (form.closest("#kt_modal_filter_inv")) {
      e.preventDefault();
      e.stopPropagation();
      hideModal(document.getElementById("kt_modal_filter_inv"));
      filterInvRows(form);
      showToast(CFG.toasts.apply_filters || "Filters applied.");
      return true;
    }

    return false;
  };

  // Vendor list: prepend row saved from add-vendor redirect.
  if (location.pathname.indexOf("flow-ai-vendors-vendor-list") >= 0) {
    try {
      var pending = sessionStorage.getItem("stitch_pending_vendor");
      if (pending) {
        sessionStorage.removeItem("stitch_pending_vendor");
        prependVendorRow(JSON.parse(pending));
      }
    } catch (err) {}
  }

  wireForms();
  wireSearch();
  console.log("[STITCH] likwid flows ready");
})();
