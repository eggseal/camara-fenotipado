import "./toast.css";

const toast = document.getElementById("popup");

let timeout: number | null = null;
function dispatchToast(msg: string) {
  if (!toast) return;

  if (timeout !== null) {
    clearTimeout(timeout);
  }

  toast.textContent = msg;
  toast.classList.toggle("hidden", false);
  timeout = setTimeout(() => {
    timeout = null;
    toast.classList.toggle("hidden", true);
  }, 5000);
}

export { dispatchToast };
