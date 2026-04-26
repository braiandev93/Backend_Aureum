document.addEventListener("DOMContentLoaded", () => {
  const analyzeBtn = document.getElementById("analyzeBtn");
  const tickersInput = document.getElementById("tickers");
  const dateInput = document.getElementById("date");
  const loadingEl = document.getElementById("loading");
  const errorEl = document.getElementById("error");
  const resultsTable = document.getElementById("resultsTable");
  const resultsBody = resultsTable.querySelector("tbody");

  analyzeBtn.addEventListener("click", async () => {
    const tickers = tickersInput.value.trim();
    const date = dateInput.value;

    errorEl.textContent = "";
    resultsTable.classList.add("hidden");
    resultsBody.innerHTML = "";

    if (!tickers || !date) {
      errorEl.textContent = "Introduce tickers y fecha.";
      return;
    }

    loadingEl.classList.remove("hidden");

    try {
      const res = await fetch("/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ tickers, date }),
      });

      const data = await res.json();
      loadingEl.classList.add("hidden");

      if (!res.ok) {
        errorEl.textContent = data.error || "Error desconocido";
        return;
      }

      const results = data.results || [];
      if (!results.length) {
        errorEl.textContent = "Sin resultados.";
        return;
      }

      results.forEach((row) => {
        const tr = document.createElement("tr");

        if (row.error) {
          tr.innerHTML = `
            <td>${row.symbol}</td>
            <td colspan="5" style="color:#f97373;">${row.error}</td>
          `;
        } else {
          tr.innerHTML = `
            <td>${row.symbol}</td>
            <td>${row.price}</td>
            <td>${row.ia1}</td>
            <td>${row.ia2}</td>
            <td>${row.ia3}</td>
            <td><strong>${row.total}</strong></td>
          `;
        }

        resultsBody.appendChild(tr);
      });

      resultsTable.classList.remove("hidden");
    } catch (err) {
      loadingEl.classList.add("hidden");
      errorEl.textContent = "Error de red o del servidor.";
      console.error(err);
    }
  });
});
