export class GenericWidget extends HTMLElement {
  protected limits: [number, number];
  protected template: HTMLTemplateElement;
  protected object!: HTMLDivElement;
  protected value!: HTMLSpanElement;
  protected suffix: string;

  constructor(templateId: string) {
    super();
    this.template = document.getElementById(templateId) as HTMLTemplateElement;
    this.suffix = this.getAttribute("suffix") || "";
    this.limits = [
      Number.parseInt(this.getAttribute("min") || "0"),
      Number.parseInt(this.getAttribute("max") || "100"),
    ];

    const clone = this.template.content.cloneNode(true);

    this.appendChild(clone);
    this.object = this.querySelector(".object") as HTMLDivElement;
    this.value = this.querySelector(".value") as HTMLSpanElement;
    this.object.style.setProperty("--clr", this.getAttribute("color"));
  }

  static get observedAttributes() {
    return ["value"];
  }

  attributeChangedCallback(name: string) {
    if (name === "value") this.render();
  }

  render() {}
}
