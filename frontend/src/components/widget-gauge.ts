import "./widget-gauge.css";
import { applyPercentage, getPercentage } from "../main";
import { GenericWidget } from "./widget";

class WidgetGauge extends GenericWidget {
  constructor() {
    super("temp-gauge");
    this.render();
  }

  render() {
    const val = Number.parseFloat(this.getAttribute("value") || "0");
    const percentage = getPercentage(val, ...this.limits);
    const degrees = applyPercentage(percentage, 0, 180);

    this.object.style.setProperty("--rotation", `${degrees}deg`);
    this.value.textContent = `${val.toFixed(2)} ${this.suffix}`;
  }
}

customElements.define("widget-gauge", WidgetGauge);
