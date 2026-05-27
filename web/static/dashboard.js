const statusNode = document.querySelector("#live-status");
const currentGeneratedAt = document.body.dataset.generatedAt || "";

function setStatus(message) {
  if (statusNode) {
    statusNode.textContent = message;
  }
}

async function refreshIfChanged() {
  try {
    const response = await fetch("/api/latest-verdict", { cache: "no-store" });
    if (response.status === 404) {
      setStatus("No verdict yet");
      return;
    }
    if (!response.ok) {
      setStatus("Waiting for verdict");
      return;
    }
    const verdict = await response.json();
    if (!currentGeneratedAt && verdict.generated_at) {
      window.location.reload();
      return;
    }
    if (currentGeneratedAt && verdict.generated_at && verdict.generated_at !== currentGeneratedAt) {
      window.location.reload();
      return;
    }
    setStatus(`Live | ${verdict.decision.replace("_", " ")} | risk ${verdict.risk.score}`);
  } catch {
    setStatus("Live poll paused");
  }
}

async function runScenario(scenario, button) {
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Running";
  setStatus(`Running ${scenario}`);
  try {
    const response = await fetch("/api/demo-run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario }),
    });
    if (!response.ok) {
      setStatus("Scenario failed");
      return;
    }
    window.location.reload();
  } catch {
    setStatus("Scenario failed");
  } finally {
    button.disabled = false;
    button.textContent = original;
  }
}

document.querySelectorAll("[data-scenario]").forEach((button) => {
  button.addEventListener("click", () => runScenario(button.dataset.scenario, button));
});

refreshIfChanged();
window.setInterval(refreshIfChanged, 4000);
