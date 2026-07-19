// ---------------------------------------------------------------------
// Config -- fill these in for your environment. In a real deploy these
// two values are the only things that differ between staging/production.
// ---------------------------------------------------------------------
const CONFIG = {
  LIFF_ID: "1234567890-abcdefgh", // from LINE Developers Console > LIFF tab
  API_BASE_URL: "https://your-api-domain.com/api/members", // your Django backend
};

// ---------------------------------------------------------------------
// Small DOM helpers
// ---------------------------------------------------------------------
const $ = (id) => document.getElementById(id);

function showScreen(name) {
  ["loading", "error", "form", "card"].forEach((s) => {
    $(`screen-${s}`).classList.toggle("hidden", s !== name);
  });
}

function formatThaiDate(isoDateString) {
  const d = new Date(isoDateString);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

// ---------------------------------------------------------------------
// API client -- every call attaches the current LIFF ID token so the
// backend can verify who is actually calling (see backend/members/line_client.py).
// ---------------------------------------------------------------------
async function apiRequest(path, options = {}) {
  const idToken = liff.getIDToken();
  if (!idToken) {
    throw new Error("No active LINE session. Please reopen the app from LINE.");
  }

  const res = await fetch(`${CONFIG.API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${idToken}`,
      ...(options.headers || {}),
    },
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const message =
      typeof data.detail === "string"
        ? data.detail
        : data.detail
        ? Object.values(data.detail).flat().join(" ")
        : "Something went wrong. Please try again.";
    const err = new Error(message);
    err.fieldErrors = typeof data.detail === "object" ? data.detail : null;
    throw err;
  }

  return data;
}

// ---------------------------------------------------------------------
// Boot sequence
// ---------------------------------------------------------------------
async function boot() {
  showScreen("loading");
  try {
    await liff.init({ liffId: CONFIG.LIFF_ID });

    if (!liff.isLoggedIn()) {
      // Redirects to LINE login and reloads this page with a session --
      // nothing after this line runs on this pass.
      liff.login();
      return;
    }

    const profile = await liff.getProfile();
    const status = await apiRequest("/status/", { method: "GET" });

    if (status.registered) {
      renderCard(status.member);
      showScreen("card");
    } else {
      renderForm(profile);
      showScreen("form");
    }
  } catch (err) {
    console.error(err);
    $("error-message").textContent = err.message || "Please try reopening the app from LINE.";
    showScreen("error");
  }
}

// ---------------------------------------------------------------------
// Registration form
// ---------------------------------------------------------------------
function renderForm(profile) {
  $("profile-picture").src = profile.pictureUrl || "";
  $("profile-name").textContent = profile.displayName || "";
}

function clearFieldErrors() {
  document.querySelectorAll(".field-error").forEach((el) => (el.textContent = ""));
  $("form-error").classList.add("hidden");
  $("form-error").textContent = "";
}

function applyFieldErrors(fieldErrors) {
  if (!fieldErrors) return;
  Object.entries(fieldErrors).forEach(([field, messages]) => {
    const el = document.querySelector(`[data-error-for="${field}"]`);
    if (el) el.textContent = Array.isArray(messages) ? messages.join(" ") : String(messages);
  });
}

function validateFormLocally(payload) {
  const errors = {};
  if (!payload.first_name.trim()) errors.first_name = ["First name is required."];
  if (!payload.last_name.trim()) errors.last_name = ["Last name is required."];
  if (!/^0\d{8,9}$/.test(payload.phone_number)) {
    errors.phone_number = ["Enter a valid Thai mobile number, e.g. 0812345678."];
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(payload.email)) {
    errors.email = ["Enter a valid email address."];
  }
  if (!payload.date_of_birth || new Date(payload.date_of_birth) >= new Date()) {
    errors.date_of_birth = ["Date of birth must be in the past."];
  }
  return errors;
}

$("registration-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  clearFieldErrors();

  const form = e.target;
  const payload = {
    first_name: form.first_name.value,
    last_name: form.last_name.value,
    phone_number: form.phone_number.value.trim(),
    email: form.email.value.trim(),
    date_of_birth: form.date_of_birth.value,
  };

  const localErrors = validateFormLocally(payload);
  if (Object.keys(localErrors).length > 0) {
    applyFieldErrors(localErrors);
    return;
  }

  const submitBtn = $("btn-submit");
  submitBtn.disabled = true;
  submitBtn.querySelector(".btn-label").textContent = "Creating your card…";
  submitBtn.querySelector(".btn-spinner").classList.remove("hidden");

  try {
    const member = await apiRequest("/register/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderCard(member);
    showScreen("card");
  } catch (err) {
    if (err.fieldErrors) {
      applyFieldErrors(err.fieldErrors);
    } else {
      $("form-error").textContent = err.message;
      $("form-error").classList.remove("hidden");
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.querySelector(".btn-label").textContent = "Create my card";
    submitBtn.querySelector(".btn-spinner").classList.add("hidden");
  }
});

// ---------------------------------------------------------------------
// Member card
// ---------------------------------------------------------------------
function renderCard(member) {
  $("card-welcome").textContent = `Welcome, ${member.full_name.split(" ")[0]}`;
  $("card-picture").src = member.picture_url || "";
  $("card-name").textContent = member.full_name;
  $("card-number").textContent = member.member_no;
  $("card-joined").textContent = formatThaiDate(member.created_at);
}

$("btn-retry").addEventListener("click", boot);
$("btn-close").addEventListener("click", () => {
  if (liff.isInClient()) {
    liff.closeWindow();
  }
});

boot();
