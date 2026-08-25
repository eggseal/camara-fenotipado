import { dispatchToast } from "./toast";
import "./controls.css";

const popups = {
  delete: {
    popup: document.getElementById("delete-popup") as HTMLDivElement,
    confirm: document.querySelector("#delete-popup .primary-btn") as HTMLButtonElement,
    cancel: document.querySelector("#delete-popup .secondary-btn") as HTMLButtonElement,
  },
  turnOff: {
    popup: document.getElementById("turnoff-popup") as HTMLDivElement,
    confirm: document.querySelector("#turnoff-popup .primary-btn") as HTMLButtonElement,
    cancel: document.querySelector("#turnoff-popup .secondary-btn") as HTMLButtonElement,
  },
};
const buttons = {
  download: document.getElementById("download") as HTMLButtonElement,
  openResults: document.getElementById("open-results") as HTMLButtonElement,
  delete: document.getElementById("delete") as HTMLButtonElement,
  turnOff: document.getElementById("turn-off") as HTMLButtonElement,
};

function toggleDisabled(button: HTMLButtonElement, disabled: boolean) {
  button.disabled = disabled;
  button.classList.toggle("disabled", disabled);
}

buttons.download.addEventListener("click", async () => {
  toggleDisabled(buttons.download, true);

  try {
    dispatchToast("Preparing files for download...");
    window.location.assign("/api/session")

    // const res = await fetch("/api/session");
    // if (!res.ok) return dispatchToast("Error while downloading.");

    // const blob = await res.blob();
    // const url = URL.createObjectURL(blob);
    // const a = document.createElement("a");
    // a.href = url;

    // document.body.appendChild(a);
    // a.click();
    // a.remove();
    // URL.revokeObjectURL(url);
  } finally {
    toggleDisabled(buttons.download, false);
  }
});

buttons.delete.addEventListener("click", async () => {
  popups.delete.popup.classList.toggle("hidden", false);
});
popups.delete.confirm.addEventListener("click", async () => {
  toggleDisabled(popups.delete.confirm, false);
  toggleDisabled(buttons.delete, true);
  try {
    const res = await fetch("/api/session", { method: "DELETE" });
    if (!res.ok) return dispatchToast("Failed to delete stored files. Try again");

    const data = await res.json();
    if (data.ok) dispatchToast("Deleted stored sessions.");
    else dispatchToast(`Error deleting files. ${data.reason}`);
  } finally {
    toggleDisabled(popups.delete.confirm, false);
    toggleDisabled(buttons.delete, false);
    popups.delete.popup.classList.toggle("hidden", true);
  }
});
popups.delete.cancel.addEventListener("click", async () => {
  popups.delete.popup.classList.toggle("hidden", true);
});

buttons.turnOff.addEventListener("click", async () => {
  popups.turnOff.popup.classList.toggle("hidden", false);
});
popups.turnOff.confirm.addEventListener("click", async () => {
  toggleDisabled(popups.turnOff.confirm, false);
  toggleDisabled(buttons.turnOff, true);
  try {
    const res = await fetch("/api/turn-off", { method: "POST" });
    if (!res.ok) return dispatchToast("Failed to turn off the system. Try again");

    const data = await res.json();
    if (data.ok) dispatchToast("Turning off the system.");
    else dispatchToast(`Error closing the system. ${data.reason}`);
  } finally {
    toggleDisabled(popups.turnOff.confirm, false);
    toggleDisabled(buttons.turnOff, false);
    popups.turnOff.popup.classList.toggle("hidden", true);
  }
});
popups.turnOff.cancel.addEventListener("click", async () => {
  popups.turnOff.popup.classList.toggle("hidden", true);
});

buttons.openResults.addEventListener("click", () => {
  console.log("Showing popup");
  const resultsPopup = document.getElementById("results-popup") as HTMLDivElement;
  resultsPopup.classList.toggle("hidden", false);
});
