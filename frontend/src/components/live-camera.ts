import "./live-camera.css";
import "./widget.css";

class LiveCamera extends HTMLElement {
  private img: HTMLImageElement | undefined;

  constructor() {
    super();
    this.render();
  }

  render = () => {
    const src = this.getAttribute("src") || "";
    this.innerHTML = "";

    this.img = document.createElement("img");
    this.img.src = `${src}?t=${Date.now()}`;

    setInterval(() => {
      this.img!.src = `${src}?t=${Date.now()}`;
    }, 2000);

    this.appendChild(this.img);
  };
}

customElements.define("live-camera", LiveCamera);
