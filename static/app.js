// Renders and manages the dynamic add/remove-row tables used in inspection forms.
(function () {
  function buildInput(field, col, rowIdx, prefill) {
    var name = "tbl_" + field + "_" + rowIdx + "_" + col.key;
    var value = prefill !== undefined ? prefill : "";
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

  function addRow(container, field, columns, rowIdx, prefillFirst) {
    var tbody = container.querySelector("tbody");
    var tr = document.createElement("tr");
    columns.forEach(function (col, i) {
      var td = document.createElement("td");
      var prefill = (i === 0 && prefillFirst) ? prefillFirst : undefined;
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
      var rowIdx = 0;

      if (defaultRows.length) {
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
