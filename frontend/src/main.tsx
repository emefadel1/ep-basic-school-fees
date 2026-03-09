import React from "react";
import ReactDOM from "react-dom/client";
import App from "@/App";

function shouldRegisterServiceWorker() {
  if (typeof window === "undefined") {
    return false;
  }
  if (("serviceWorker" in navigator) === false) {
    return false;
  }
  const env: any = import.meta.env ? import.meta.env : {};
  if (env.PROD === true) {
    return true;
  }
  return env.VITE_ENABLE_SW === "true";
}

const container = document.getElementById("root");

if (container !== null) {
  ReactDOM.createRoot(container).render(
    React.createElement(React.StrictMode, null, React.createElement(App)),
  );
}

if (shouldRegisterServiceWorker() === true) {
  window.addEventListener("load", function onLoad() {
    navigator.serviceWorker.register("/sw.js").catch(function onError(error) {
      console.error("Service worker registration failed.", error);
    });
  });
}
