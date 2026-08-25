const popups = document.getElementsByClassName("window-popup");

for (const popup of popups) {
  if (popup.id === "results-popup") continue;
  popup.addEventListener("click", (ev) => {
    const content = popup.querySelector(".popup-content") as HTMLDivElement;
    if (!popup.classList.contains("hidden") && !content.contains(ev.target as any)) {
      popup.classList.toggle("hidden", true);
    }
  });
}
