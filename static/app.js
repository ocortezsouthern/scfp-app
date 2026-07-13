// Renders and manages the dynamic add/remove-row tables used in inspection forms.
(function () {
  function buildInput(field, col, rowIdx, prefill) {
    var name = "tbl_" + field + "_" + rowIdx + "_" + col.key;
    var value = prefill !== undefined && prefill !== null ? String(prefill) : "";
    if (col.type === "select") {
      var opts = (col.options || [""]).map(function (o) {
        var sel = o === value ? " selected" : "";
        return "<option value=\"" + o + "\"" + sel + ">" + (o || "—") + "</option>";
      }).join("");
      return "<select name=\"" + name + "\">" + opts + "</select>";
    }
    if (col.type === "date") {
      return "<input type=\"date\" name=\"" + name + "\" value=\"" + value + "\">";
    }
    if (col.type === "number") {
      return "<input type=\"number\" step=\"any\" name=\"" + name + "\" value=\"" + value + "\">";
    }
    return "<input type=\"text\" name=\"" + name + "\" value=\"" + value.replace(/"/g, "&quot;") + "\">";
  }

  // rowData: either a plain string (prefills just the first column, used for
  // brand-new inspections seeded from default_rows) or an object keyed by
  // column key (used to fully restore a saved row when editing).
  function addRow(container, field, columns, rowIdx, rowData) {
    var tbody = container.querySelector("tbody");
    var tr = document.createElement("tr");
    var isObject = rowData && typeof rowData === "object";
    columns.forEach(function (col, i) {
      var td = document.createElement("td");
      var prefill;
      if (isObject) {
        prefill = rowData[col.key];
      } else if (i === 0 && rowData) {
        prefill = rowData;
      }
      td.innerHTML = buildInput(field, col, rowIdx, prefill);
      tr.appendChild(td);
    });
    var removeTd = document.createElement("td");
    removeTd.innerHTML = "<button type=\"button\" class=\"remove-row-btn\" title=\"Remove row\">&times;</button>";
    removeTd.querySelector("button").addEventListener("click", function () {
      tr.remove();
    });
    tr.appendChild(removeTd);
    tbody.appendChild(tr);
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".table-field").forEach(function (container) {
      var field = container.getAttribute("data-field");
      var columns = JSON.parse(container.getAttribute("data-columns"));
      var defaultRows = JSON.parse(container.getAttribute("data-default-rows") || "[]");
      var existingRows = JSON.parse(container.getAttribute("data-existing-rows") || "[]");
      var rowIdx = 0;

      if (existingRows.length) {
        existingRows.forEach(function (row) {
          addRow(container, field, columns, rowIdx++, row);
        });
      } else if (defaultRows.length) {
        defaultRows.forEach(function (label) {
          addRow(container, field, columns, rowIdx++, label);
        });
      } else {
        addRow(container, field, columns, rowIdx++);
        addRow(container, field, columns, rowIdx++);
      }

      var btn = container.querySelector(".add-row-btn");
      btn.addEventListener("click", function () {
        addRow(container, field, columns, rowIdx++);
      });
    });

    // Manager sign-off signature pads — draw with mouse or touch, hidden
    // input carries the PNG data URL along with the rest of the form.
    document.querySelectorAll(".signature-pad").forEach(function (wrap) {
      var canvas = wrap.querySelector(".signature-canvas");
      var input = wrap.querySelector(".signature-data-input");
      var clearBtn = wrap.querySelector(".sig-clear-btn");
      if (!canvas || !input) { return; }
      var ctx = canvas.getContext("2d");
      var ratio = window.devicePixelRatio || 1;
      var cssWidth = canvas.clientWidth || canvas.offsetWidth || 500;
      var cssHeight = canvas.clientHeight || 150;
      canvas.width = cssWidth * ratio;
      canvas.height = cssHeight * ratio;
      ctx.scale(ratio, ratio);
      ctx.lineWidth = 2;
      ctx.lineCap = "round";
      ctx.strokeStyle = "#1a1a1a";

      var drawing = false;
      var hasStroke = false;

      function pos(evt) {
        var rect = canvas.getBoundingClientRect();
        var point = evt.touches ? evt.touches[0] : evt;
        return { x: point.clientX - rect.left, y: point.clientY - rect.top };
      }
      function start(evt) {
        drawing = true;
        var p = pos(evt);
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        evt.preventDefault();
      }
      function move(evt) {
        if (!drawing) { return; }
        var p = pos(evt);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();
        hasStroke = true;
        evt.preventDefault();
      }
      function end() {
        if (!drawing) { return; }
        drawing = false;
        input.value = hasStroke ? canvas.toDataURL("image/png") : "";
      }
      canvas.addEventListener("mousedown", start);
      canvas.addEventListener("mousemove", move);
      window.addEventListener("mouseup", end);
      canvas.addEventListener("touchstart", start, { passive: false });
      canvas.addEventListener("touchmove", move, { passive: false });
      canvas.addEventListener("touchend", end);

      if (clearBtn) {
        clearBtn.addEventListener("click", function () {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          hasStroke = false;
          input.value = "";
        });
      }
    });
  });

  // Simple tab switcher used by dashboard/expenses/profile pages:
  // buttons carry data-tab-group + data-tab-target, panels carry
  // data-tab-group + data-tab-name.
  window.switchTab = function (group, name) {
    document.querySelectorAll('[data-tab-group="' + group + '"]').forEach(function (el) {
      if (el.hasAttribute("data-tab-target")) {
        el.classList.toggle("active", el.getAttribute("data-tab-target") === name);
      } else if (el.hasAttribute("data-tab-name")) {
        el.classList.toggle("active", el.getAttribute("data-tab-name") === name);
      }
    });
  };
})();
