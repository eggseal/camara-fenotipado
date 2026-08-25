import "./widget-bar.css";
import { getPercentage } from "../main";
import { GenericWidget } from "./widget";

class WidgetBar extends GenericWidget {
  constructor() {
    super("temp-bar");
    this.render();
  }

  render() {
    const val = Number.parseFloat(this.getAttribute("value") || "0");
    const percentage = getPercentage(val, ...this.limits);

    this.object.style.setProperty("--value", `${percentage * 100}%`);
    this.value.textContent = `${val.toFixed(2)} ${this.suffix}`;
  };
}

customElements.define("widget-bar", WidgetBar);
