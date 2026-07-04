// Likwid demo layer — localStorage saves + home chart placeholders (no backend).
(function () {
  var STORE = "likwid_demo_v1";

  function loadStore() {
    try {
      return JSON.parse(localStorage.getItem(STORE) || "{}");
    } catch (e) {
      return {};
    }
  }

  function saveStore(data) {
    localStorage.setItem(STORE, JSON.stringify(data));
  }

  function toast(msg) {
    var el = document.createElement("div");
    el.textContent = msg;
    el.style.cssText =
      "position:fixed;bottom:24px;right:24px;z-index:99999;background:#111;color:#fff;" +
      "padding:10px 18px;border-radius:8px;font:13px system-ui,sans-serif;opacity:0;transition:opacity .2s";
    document.body.appendChild(el);
    requestAnimationFrame(function () {
      el.style.opacity = "1";
    });
    setTimeout(function () {
      el.style.opacity = "0";
      setTimeout(function () {
        if (el.parentNode) el.parentNode.removeChild(el);
      }, 250);
    }, 2200);
  }

  function customerId() {
    var m = location.pathname.match(/flow-ai-customer-view-([^/]+)/);
    return m ? m[1] : null;
  }

  function applyFormData(form, data) {
    Object.keys(data).forEach(function (name) {
      var el = form.querySelector('[name="' + name + '"]');
      if (el && data[name] != null) el.value = data[name];
    });
  }

  function collectFormData(form) {
    var patch = {};
    form.querySelectorAll("input[name], select[name], textarea[name]").forEach(function (el) {
      if (!el.name || el.name === "csrfmiddlewaretoken") return;
      patch[el.name] = el.value;
    });
    return patch;
  }

  function setupCustomerView() {
    var id = customerId();
    if (!id) return;
    var store = loadStore();
    var form =
      document.querySelector("#cvEditDrawer form") ||
      (function () {
        var inp = document.querySelector('form input[name="cust_comname"]');
        return inp ? inp.closest("form") : null;
      })();
    if (!form) return;

    if (store.customers && store.customers[id]) {
      applyFormData(form, store.customers[id]);
      var title = document.querySelector(".cv-drawer-header .text-gray-400.fs-8, h1.page-heading");
      if (title && store.customers[id].cust_comname) {
        title.textContent = store.customers[id].cust_comname;
      }
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      e.stopPropagation();
      var patch = collectFormData(form);
      var all = loadStore();
      if (!all.customers) all.customers = {};
      all.customers[id] = patch;
      saveStore(all);
      toast("Changes saved");
    });
  }

  function patchCustomerList() {
    if (location.pathname.indexOf("flow-ai-customers-list") < 0) return;
    var customers = loadStore().customers || {};
    document.querySelectorAll('a[data-stitch-page^="flow-ai-customer-view-"]').forEach(function (a) {
      var slug = a.getAttribute("data-stitch-page") || "";
      var id = slug.replace("flow-ai-customer-view-", "");
      var row = customers[id];
      if (row && row.cust_comname && a.classList.contains("fw-semibold")) {
        a.textContent = row.cust_comname.trim();
      }
    });
  }

  function svgDonut(colors, size) {
    var r = size * 0.32;
    var cx = size / 2;
    var cy = size / 2;
    var total = colors.length;
    var paths = "";
    var start = 0;
    colors.forEach(function (c, i) {
      var angle = (360 / total) * (i + 1);
      var end = start + 360 / total;
      var large = end - start > 180 ? 1 : 0;
      var x1 = cx + r * Math.cos((Math.PI * start) / 180);
      var y1 = cy + r * Math.sin((Math.PI * start) / 180);
      var x2 = cx + r * Math.cos((Math.PI * end) / 180);
      var y2 = cy + r * Math.sin((Math.PI * end) / 180);
      paths +=
        '<path d="M' +
        cx +
        " " +
        cy +
        " L" +
        x1 +
        " " +
        y1 +
        " A" +
        r +
        " " +
        r +
        " 0 " +
        large +
        " 1 " +
        x2 +
        " " +
        y2 +
        ' Z" fill="' +
        c +
        '"/>';
      start = end;
    });
    return (
      '<svg viewBox="0 0 ' +
      size +
      " " +
      size +
      '" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">' +
      paths +
      '<circle cx="' +
      cx +
      '" cy="' +
      cy +
      '" r="' +
      r * 0.55 +
      '" fill="#fff"/>' +
      "</svg>"
    );
  }

  function svgRadar(size) {
    var cx = size / 2;
    var cy = size / 2;
    var r = size * 0.38;
    var labels = ["Awareness", "Interest", "Decision", "Purchase", "Retain"];
    var vals = [0.9, 0.7, 0.55, 0.4, 0.3];
    var grid = "";
    for (var ring = 1; ring <= 4; ring++) {
      grid += '<circle cx="' + cx + '" cy="' + cy + '" r="' + (r * ring) / 4 + '" fill="none" stroke="#e4e6ef"/>';
    }
    var poly = "";
    labels.forEach(function (_, i) {
      var a = (-90 + (360 / labels.length) * i) * (Math.PI / 180);
      var x = cx + r * vals[i] * Math.cos(a);
      var y = cy + r * vals[i] * Math.sin(a);
      poly += (i ? "L" : "M") + x + " " + y;
    });
    poly += " Z";
    return (
      '<svg viewBox="0 0 ' +
      size +
      " " +
      size +
      '" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">' +
      grid +
      '<path d="' +
      poly +
      '" fill="rgba(27,132,255,0.25)" stroke="#1B84FF" stroke-width="2"/>' +
      "</svg>"
    );
  }

  function renderHomeCharts() {
    if (location.pathname.indexOf("home-v2") < 0) return;
    var pies = [
      { id: "dealsPieChart", colors: ["#1B84FF", "#50CD89", "#FFC700", "#F1416C", "#7239EA"] },
      { id: "dealsAmountPieChart", colors: ["#50CD89", "#1B84FF", "#FFC700", "#7239EA"] },
    ];
    pies.forEach(function (p) {
      var el = document.getElementById(p.id);
      if (!el) return;
      el.innerHTML = svgDonut(p.colors, 200);
      el.style.minHeight = "200px";
    });
    var radar = document.getElementById("funnelRadarChart");
    if (radar) {
      radar.innerHTML = svgRadar(400);
      radar.style.minHeight = "400px";
    }
  }

  function init() {
    setupCustomerView();
    patchCustomerList();
    renderHomeCharts();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
