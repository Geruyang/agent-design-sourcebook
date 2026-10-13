(function () {
  const INSTALL_REF = "47902b0bbffdb229992c543038aa57578eedfb5f";
  const REPOSITORY = "https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering.git";
  const INSTALL_COMMAND = [
    'tmp="$(mktemp -d)"',
    `git init -q "$tmp"`,
    `git -C "$tmp" fetch -q --depth 1 ${REPOSITORY} ${INSTALL_REF}`,
    'git -C "$tmp" checkout -q --detach FETCH_HEAD',
    "mkdir -p .cursor/skills",
    "rm -rf .cursor/skills/long-horizon-prompting",
    'cp -R "$tmp/skills/long-horizon-prompting" .cursor/skills/',
    'rm -rf "$tmp"',
  ].join(" && ");

  async function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }

    const active = document.activeElement;
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.left = "-9999px";
    document.body.appendChild(area);
    area.select();
    const copied = document.execCommand("copy");
    area.remove();
    if (active && typeof active.focus === "function") active.focus();
    if (!copied) throw new Error("Clipboard unavailable");
    return true;
  }

  function statusFor(button) {
    const id = button.getAttribute("aria-describedby");
    return id ? document.getElementById(id) : null;
  }

  async function handleCopy(button, text) {
    const original = button.textContent;
    const status = statusFor(button);
    try {
      await copyText(text);
      button.textContent = "Copied";
      if (status) status.textContent = "Copied to clipboard.";
    } catch (_) {
      button.textContent = "Copy failed";
      if (status) status.textContent = "Clipboard access failed. Select and copy the text manually.";
    }
    window.setTimeout(() => {
      button.textContent = original;
      if (status) status.textContent = "";
    }, 1800);
  }

  document.addEventListener("click", (event) => {
    const installButton = event.target.closest("[data-copy-install]");
    if (installButton) {
      handleCopy(installButton, INSTALL_COMMAND);
      return;
    }

    const targetButton = event.target.closest("[data-copy-target]");
    if (targetButton) {
      const target = document.getElementById(targetButton.dataset.copyTarget);
      if (target) handleCopy(targetButton, target.textContent.trim());
    }
  });

  window.copySiteText = copyText;
})();
