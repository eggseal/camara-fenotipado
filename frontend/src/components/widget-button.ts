import "./widget-button.css";
import { GenericWidget } from "./widget";

class WidgetButton extends GenericWidget {
  private stateOff: string;
  private stateOn: string;
  private previousState!: number;

  constructor() {
    super("temp-button");
    this.stateOff = this.getAttribute("off") || "Off";
    this.stateOn = this.getAttribute("on") || "On";

    this.render();
    const button = this.querySelector("button") as HTMLButtonElement;
    button.addEventListener("click", async () => {
      button.disabled = true;
      const rawValue = this.getAttribute("value")
      if (!rawValue) {
        button.disabled = false;
        return;
      }

      const value = rawValue == "true" || Number.parseInt(rawValue) == 1;
      const newValue = !value ? 1 : 0;

      await fetch(`/api/dashboard/${this.id}?value=${newValue}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
      });
      button.disabled = false;
    });
  }

  render() {
    const rawValue = this.getAttribute("value") || "false"
    const parsedValue = rawValue == "true" || Number.parseInt(rawValue) == 1;
    const value = parsedValue ? 1 : 0;

    if (this.previousState === 1 && value === 0) {
      document.dispatchEvent(new CustomEvent(`${this.id}Finished`));
    }

    if (value === 1) {
      this.value.textContent = this.stateOn;
      this.style.setProperty("--clr", "hsl(0, 70%, 60%)");
    } else {
      this.value.textContent = this.stateOff;
      this.style.setProperty("--clr", "hsl(120, 70%, 60%)");
    }
    this.previousState = value;
  }
}

customElements.define("widget-button", WidgetButton);
