import { useEffect, useState } from "react";

export type Theme = "system" | "light" | "dark";
const THEMES: Theme[] = ["system", "light", "dark"];
const KEY = "hireview.theme";

function stored(): Theme {
  try {
    const value = localStorage.getItem(KEY);
    return THEMES.includes(value as Theme) ? (value as Theme) : "system";
  } catch {
    return "system";
  }
}

/** "system" follows the OS; light/dark pin it via html[data-theme] (index.html applies it before first paint). */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(stored);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") delete root.dataset.theme;
    else root.dataset.theme = theme;
    try {
      if (theme === "system") localStorage.removeItem(KEY);
      else localStorage.setItem(KEY, theme);
    } catch {
      /* the choice lasts for this page load only */
    }
  }, [theme]);

  const cycle = () => setTheme((t) => THEMES[(THEMES.indexOf(t) + 1) % THEMES.length]);
  return { theme, cycle };
}
