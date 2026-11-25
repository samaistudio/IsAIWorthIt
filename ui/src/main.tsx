import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

// Theme: ?theme=dark or #dark forces dark, ?theme=light or #light forces light,
// otherwise follow the system light/dark setting.
const q = new URLSearchParams(location.search).get("theme") ?? location.hash.slice(1);
const forced = q === "dark" || q === "light" ? q : null;
const dark = window.matchMedia("(prefers-color-scheme: dark)");
const apply = () => document.documentElement.classList.toggle("dark", forced ? forced === "dark" : dark.matches);
apply();
if (!forced) dark.addEventListener("change", apply);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
