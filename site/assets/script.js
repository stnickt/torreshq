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
setupCopyButton("cal-copy", "cal-address");
