import "./widget-bulb.css";
import { applyPercentage, getPercentage } from "../main";
import { GenericWidget } from "./widget";

class WidgetBulb extends GenericWidget {
  constructor() {
    super("temp-bulb");
    this.render();
  }

  render() {
    const val = Number.parseFloat(this.getAttribute("value") || "0");
    const percentage = getPercentage(val, ...this.limits);
    const radius = applyPercentage(percentage, 1, 8.598958);

    this.object.style.setProperty("--r", `${radius}px`);
    this.value.textContent = `${val.toFixed(2)} ${this.suffix}`;
  };
}

customElements.define("widget-bulb", WidgetBulb);
