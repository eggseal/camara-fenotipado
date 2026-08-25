import "./widget-picker.css";
import { GenericWidget } from "./widget";

class NumberPicker extends GenericWidget {
  constructor() {
    super("temp-picker");

    this.render();
    const subBtn = this.querySelector(".sub") as HTMLButtonElement;
    const addBtn = this.querySelector(".add") as HTMLButtonElement;

    subBtn.addEventListener("click", async () => {
      subBtn.disabled = true;
      const storedValue = this.getAttribute("value");
      if (storedValue === null) return;

      let value = Number.parseInt(storedValue);
      if (value <= 0) return;
      value -= 1;
      await fetch(`/api/dashboard/${this.id}?value=${value}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
      });
    });
    addBtn.addEventListener("click", async () => {
      addBtn.disabled = true;
      const storedValue = this.getAttribute("value");
      if (storedValue === null) return;

      let value = Number.parseInt(storedValue);
      value += 1;
      await fetch(`/api/dashboard/${this.id}?value=${value}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
      });
      addBtn.disabled = false;
    });
  }

  render() {
    const val = Number.parseInt(this.getAttribute("value") || "11");
    const subBtn = this.querySelector(".sub") as HTMLButtonElement;
    subBtn.disabled = val <= 0;
    this.value.textContent = val.toString();
  }
}

customElements.define("widget-picker", NumberPicker);
