document.getElementById("year").textContent = new Date().getFullYear();

const root = document.documentElement;
const toggle = document.getElementById("theme-toggle");
const stored = localStorage.getItem("theme");
const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

function applyTheme(theme) {
  root.setAttribute("data-theme", theme);
  toggle.textContent = theme === "dark" ? "☀️" : "🌙";
}

applyTheme(stored || (prefersDark ? "dark" : "light"));

toggle.addEventListener("click", () => {
  const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
  applyTheme(next);
  localStorage.setItem("theme", next);
});

function setupCopyButton(buttonId, textId) {
  const button = document.getElementById(buttonId);
  button.addEventListener("click", async () => {
    const text = document.getElementById(textId).textContent.trim();
    try {
      await navigator.clipboard.writeText(text);
      const original = button.textContent;
      button.textContent = "Copied!";
      setTimeout(() => (button.textContent = original), 1500);
    } catch {
      /* clipboard access blocked (e.g. insecure context); user can select the text manually */
    }
  });
}

setupCopyButton("mc-copy", "mc-address");

const accessForm = document.getElementById("access-form");
const accessFormStatus = document.getElementById("access-form-status");

accessForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitButton = accessForm.querySelector("button[type=submit]");
  const payload = Object.fromEntries(new FormData(accessForm).entries());

  submitButton.disabled = true;
  accessFormStatus.textContent = "Sending...";

  try {
    const response = await fetch("/api/request-access", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok || !result.ok) throw new Error(result.error || "Request failed");
    accessFormStatus.textContent = "Request sent — you'll hear back soon!";
    accessForm.reset();
  } catch (err) {
    accessFormStatus.textContent = err.message || "Something went wrong. Please try again in a moment.";
  } finally {
    submitButton.disabled = false;
  }
});
