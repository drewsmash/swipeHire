// SwipeHire front end: card swiping (drag, buttons, arrow keys) and small UI helpers.
// Without JavaScript the ✕ / ✓ buttons still work as normal form posts.
(function () {
  "use strict";
  var csrf = document.querySelector('meta[name="csrf-token"]').content;
  var toastEl = document.getElementById("toast");
  var toastTimer;

  function toast(msg, big) {
    toastEl.textContent = msg;
    toastEl.className = "toast show" + (big ? " big" : "");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.className = "toast"; }, big ? 2200 : 1400);
  }

  // Close the Menu dropdown when clicking elsewhere.
  document.addEventListener("click", function (e) {
    document.querySelectorAll("details.menu[open]").forEach(function (d) {
      if (!d.contains(e.target)) d.removeAttribute("open");
    });
  });

  // Fade flash messages after a few seconds.
  document.querySelectorAll(".flash").forEach(function (el) {
    setTimeout(function () { el.classList.add("hide"); }, 4000);
  });

  var stack = document.querySelector("[data-stack]");
  if (!stack) return;
  var actions = document.querySelector("[data-actions]");
  var form = actions && actions.querySelector("form");
  var hint = document.querySelector(".hint");
  var busy = false;

  function cards() { return Array.prototype.slice.call(stack.querySelectorAll(".card")); }

  function layout() {
    var list = cards();
    list.forEach(function (c, i) {
      c.classList.toggle("top", i === 0);
      c.dataset.depth = Math.min(i, 3);
    });
    if (list.length && form) form.action = list[0].dataset.action;
    if (!list.length) {
      if (actions) actions.hidden = true;
      if (hint) hint.hidden = true;
    }
  }

  function send(card, liked) {
    var body = new FormData();
    body.append("csrf_token", csrf);
    body.append("liked", liked ? "1" : "0");
    return fetch(card.dataset.action, {
      method: "POST", body: body, credentials: "same-origin",
      headers: { "X-Requested-With": "fetch", "X-CSRF-Token": csrf }
    }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  function decide(liked) {
    var card = cards()[0];
    if (!card || busy) return;
    busy = true;
    card.classList.add(liked ? "fly-right" : "fly-left");
    send(card, liked).then(function (res) {
      toast(res.message, res.matched);
    }).catch(function () {
      toast("Could not save that swipe. Reloading…");
      setTimeout(function () { location.reload(); }, 900);
    });
    setTimeout(function () { card.remove(); busy = false; layout(); }, 260);
  }

  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var btn = e.submitter || document.activeElement;
      decide(btn && btn.value === "1");
    });
  }

  document.addEventListener("keydown", function (e) {
    if (/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) return;
    if (e.key === "ArrowRight") decide(true);
    if (e.key === "ArrowLeft") decide(false);
  });

  // Drag / swipe gestures on the top card.
  var start = null, dx = 0, dragging = null;
  stack.addEventListener("pointerdown", function (e) {
    var card = e.target.closest(".card.top");
    if (!card || busy || e.target.closest("a, button, input")) return;
    start = { x: e.clientX, y: e.clientY, id: e.pointerId };
    dragging = card;
    dx = 0;
  });
  stack.addEventListener("pointermove", function (e) {
    if (!dragging || e.pointerId !== start.id) return;
    dx = e.clientX - start.x;
    if (Math.abs(dx) < 6 && !dragging.classList.contains("dragging")) return;
    if (!dragging.classList.contains("dragging")) {
      dragging.classList.add("dragging");
      try { dragging.setPointerCapture(e.pointerId); } catch (_) {}
    }
    dragging.style.transform = "translateX(" + dx + "px) rotate(" + dx / 18 + "deg)";
    dragging.style.setProperty("--like", Math.max(0, Math.min(1, dx / 110)));
    dragging.style.setProperty("--pass", Math.max(0, Math.min(1, -dx / 110)));
  });
  function end() {
    if (!dragging) return;
    var card = dragging;
    dragging = null;
    card.classList.remove("dragging");
    card.style.removeProperty("--like");
    card.style.removeProperty("--pass");
    var threshold = Math.min(120, stack.clientWidth * 0.28);
    if (Math.abs(dx) > threshold) {
      card.style.transform = "";
      decide(dx > 0);
    } else {
      card.style.transform = "";
    }
  }
  stack.addEventListener("pointerup", end);
  stack.addEventListener("pointercancel", end);

  layout();
})();
