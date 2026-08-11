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

const mcCopyBtn = document.getElementById("mc-copy");
mcCopyBtn.addEventListener("click", async () => {
  const address = document.getElementById("mc-address").textContent.trim();
  try {
    await navigator.clipboard.writeText(address);
    const original = mcCopyBtn.textContent;
    mcCopyBtn.textContent = "Copied!";
    setTimeout(() => (mcCopyBtn.textContent = original), 1500);
  } catch {
    /* clipboard access blocked (e.g. insecure context); user can select the text manually */
  }
});
