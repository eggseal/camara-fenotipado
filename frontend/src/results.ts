import { poll } from "./main";
import { dispatchToast } from "./toast";
import "./results.css";

const resultPopup = document.getElementById("results-popup") as HTMLDivElement;
const loader = resultPopup.querySelector(".loader") as HTMLDivElement;
const content = resultPopup.querySelector(".popup-main") as HTMLDivElement;

const currentPages = document.getElementById("current-page") as HTMLSpanElement;
const totalPages = document.getElementById("total-pages") as HTMLSpanElement;
const prevPage = document.getElementById("previous-page") as HTMLSpanElement;
const nextPage = document.getElementById("next-page") as HTMLSpanElement;

type Response = { filename: string; src: string };
type Data = {
  completed: boolean;
  photo_counts: { RGB: number; RGBT: number; RE: number; RGN: number };
  photos: { RGB: Response[]; RGBT: Response[]; RE: Response[]; RGN: Response[] };
};

class Result {
  public title: HTMLDivElement;
  public image: HTMLImageElement;
  public counter: HTMLSpanElement;
  public images: ({ title: string; image: string } | undefined)[] = [];
  public static index = 0;
  public static max = 0;

  constructor(id: string) {
    this.title = document.querySelector(`#${id}-view .image-name`) as HTMLDivElement;
    this.image = document.querySelector(`#${id}-view .image-preview`) as HTMLImageElement;
    this.counter = document.getElementById(`${id}-count`) as HTMLSpanElement;
  }

  display() {
    this.title.textContent = this.images[Result.index]?.title || "...";
    this.image.src = this.images[Result.index]?.image || "";
    this.counter.textContent = String(this.images.length);
  }

  reset() {
    this.images = [];
    this.display();
  }

  static mapResults(response: Response) {
    return {
      title: response ? response.filename : "",
      image: response ? response.src : "",
    };
  }
}

let transferring = false;

const results = {
  side: new Result("rgb"),
  top: new Result("rgbt"),
  rgn: new Result("rgn"),
  re: new Result("re"),
};

function preloadIndex(index: number) {
  Object.values(results).forEach((result) => {
    const item = result.images[index];
    if (!item?.image) return;

    const img = new Image();
    img.src = item.image;
  });
}

function updateDisplayAndPreload() {
  currentPages.textContent = String(Result.index + 1);

  Object.values(results).forEach((result) => result.display());

  // Preload current
  preloadIndex(Result.index);

  if (Result.max > 1) {
    preloadIndex((Result.index + 1) % Result.max);
    preloadIndex((Result.index - 1 + Result.max) % Result.max);
  }
}

document.addEventListener("runningFinished", async () => {
  Object.values(results).forEach((result) => result.reset());

  resultPopup?.classList.toggle("hidden", false);

  transferring = true;
  content.style.display = "none";
  loader.style.display = "flex";

  const data: Data | null = await poll("/api/photos");

  try {
    if (!data) {
      dispatchToast("Failed to fetch images.");
      return;
    }
  } finally {
    transferring = false;
    content.style.display = "grid";
    loader.style.display = "none";
  }

  results.top.images = data.photos.RGBT.map(Result.mapResults);
  results.side.images = data.photos.RGB.map(Result.mapResults);
  results.rgn.images = data.photos.RGN.map(Result.mapResults);
  results.re.images = data.photos.RE.map(Result.mapResults);

  Result.index = 0;
  Result.max = Math.max(
    ...Object.values(results).map((result) => result.images.length)
  );

  totalPages.textContent = String(Result.max);

  updateDisplayAndPreload();
});

resultPopup.addEventListener("click", (ev) => {
  const content = resultPopup.querySelector(".popup-content") as HTMLDivElement;

  if (
    !resultPopup.classList.contains("hidden") &&
    !content.contains(ev.target as any)
  ) {
    if (transferring) {
      dispatchToast("Wait for image transfer to finish before closing");
      return;
    }

    resultPopup.classList.toggle("hidden", true);
  }
});

nextPage.addEventListener("click", () => {
  Result.index = (Result.index + 1) % (Result.max || 1);
  updateDisplayAndPreload();
});

prevPage.addEventListener("click", () => {
  Result.index =
    (Result.index - 1 + (Result.max || 1)) % (Result.max || 1);
  updateDisplayAndPreload();
});