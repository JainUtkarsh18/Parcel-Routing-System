const singleForm = document.getElementById("singleForm");
const singleResult = document.getElementById("singleResult");
const batchForm = document.getElementById("batchForm");
const batchResult = document.getElementById("batchResult");

function showError(target, message) {
  target.classList.remove("hidden");
  target.classList.add("error");
  target.innerHTML = `<strong>Error:</strong> ${message}`;
}

function clearResult(target) {
  target.classList.remove("error");
  target.classList.add("hidden");
  target.innerHTML = "";
}

function renderDecision(decision) {
  const approvals = decision.approvals_required.length
    ? decision.approvals_required.join(", ")
    : "None";

  return `
    <p><strong>Department:</strong> <span class="badge">${decision.department}</span></p>
    <p><strong>Approvals required:</strong> ${approvals}</p>
    <p><strong>Insurance required:</strong> ${decision.insurance_required ? "Yes" : "No"}</p>
    <p><strong>Rule version:</strong> ${decision.rule_version}</p>
    <p><strong>Applied rules:</strong></p>
    <ul>${decision.applied_rules.map(rule => `<li>${rule}</li>`).join("")}</ul>
  `;
}

singleForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearResult(singleResult);

  const payload = {
    weight: Number(document.getElementById("weight").value),
    value: Number(document.getElementById("value").value),
    destination_country: document.getElementById("destination").value
  };

  try {
    const response = await fetch("/api/route", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail ? JSON.stringify(data.detail) : "Routing failed");
    }

    singleResult.classList.remove("hidden");
    singleResult.innerHTML = renderDecision(data.decision);
  } catch (error) {
    showError(singleResult, error.message);
  }
});

batchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearResult(batchResult);

  const fileInput = document.getElementById("batchFile");
  if (!fileInput.files.length) {
    showError(batchResult, "Please select a JSON file.");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    const response = await fetch("/api/route/batch", {
      method: "POST",
      body: formData
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Batch routing failed");
    }

    const rows = data.results.map(result => `
      <tr>
        <td>${result.row}</td>
        <td>${result.parcel.weight}</td>
        <td>€${result.parcel.value}</td>
        <td>${result.parcel.destination_country}</td>
        <td>${result.decision.department}</td>
        <td>${result.decision.approvals_required.length ? result.decision.approvals_required.join(", ") : "None"}</td>
      </tr>
    `).join("");

    const errors = data.errors.length
      ? `<h3>Validation Errors</h3><pre>${JSON.stringify(data.errors, null, 2)}</pre>`
      : "";

    batchResult.classList.remove("hidden");
    batchResult.innerHTML = `
      <p><strong>Total records:</strong> ${data.total_records}</p>
      <p><strong>Successfully routed:</strong> ${data.successfully_routed}</p>
      <p><strong>Failed validation:</strong> ${data.failed_validation}</p>
      <table>
        <thead>
          <tr>
            <th>Row</th>
            <th>Weight</th>
            <th>Value</th>
            <th>Destination</th>
            <th>Department</th>
            <th>Approvals</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
      ${errors}
    `;
  } catch (error) {
    showError(batchResult, error.message);
  }
});
