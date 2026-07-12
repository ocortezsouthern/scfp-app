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
  });
})();
