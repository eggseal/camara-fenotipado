import "./widget-thermo.css";
import { applyPercentage, getPercentage } from "../main";
import { GenericWidget } from "./widget";

class WidgetThermo extends GenericWidget {
  constructor() {
    super("temp-thermometer");
    this.render();
  }

  render() {
    const val = Number.parseFloat(this.getAttribute("value") || "0");
    const percentage = getPercentage(val, ...this.limits);
    const y = applyPercentage(1 - percentage, 42.333336, 118.77084);
    const height = applyPercentage(percentage, 0, 79.375);

    this.object.style.setProperty("--y", `${y}px`);
    this.object.style.setProperty("--height", `${height}px`);
    this.value.textContent = `${val.toFixed(2)} ${this.suffix}`;
  };
}

customElements.define("widget-thermo", WidgetThermo);
