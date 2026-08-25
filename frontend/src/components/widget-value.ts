import "./widget-value.css"
import { GenericWidget } from "./widget";

class WidgetValue extends GenericWidget {
  constructor() {
    super("temp-value");
    this.render();
  }

  render() {
    const val = Number.parseFloat(this.getAttribute("value") || "0");
    this.value.textContent = `${val.toFixed(2)} ${this.suffix}`;
  };
}

customElements.define("widget-value", WidgetValue);
