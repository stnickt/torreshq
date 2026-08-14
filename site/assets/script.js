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

const ACCESS_REQUEST_EMAIL = "stnickt@gmail.com";
const accessForm = document.getElementById("access-form");
const accessFormStatus = document.getElementById("access-form-status");

accessForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitButton = accessForm.querySelector("button[type=submit]");
  submitButton.disabled = true;
  accessFormStatus.textContent = "Sending...";

  try {
    const response = await fetch(`https://formsubmit.co/ajax/${ACCESS_REQUEST_EMAIL}`, {
      method: "POST",
      headers: { Accept: "application/json" },
      body: new FormData(accessForm),
    });
    if (!response.ok) throw new Error("Request failed");
    accessFormStatus.textContent = "Request sent — you'll hear back soon!";
    accessForm.reset();
  } catch {
    accessFormStatus.textContent = "Something went wrong. Please try again in a moment.";
  } finally {
    submitButton.disabled = false;
  }
});
