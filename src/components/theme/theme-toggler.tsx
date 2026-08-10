import { Moon, Sun } from "lucide-react";

import { useTheme } from "./theme-provider";

interface ThemeToggleProps {
  showLabel?: boolean;
}

export function ThemeToggle({ showLabel = false }: ThemeToggleProps) {
  const { theme, setTheme, resolvedTheme } = useTheme();

  // Effective theme: if system, use resolved; otherwise use stored (light/dark only in UI)
  const effective = theme === "system" ? resolvedTheme ?? "light" : theme;
  const isDark = effective === "dark";

  const handleClick = () => {
    setTheme(isDark ? "light" : "dark");
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-foreground/70 hover:text-foreground hover:bg-accent rounded-none transition-all"
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
    >
      {isDark ? (
        <Sun className="w-4 h-4" aria-hidden />
      ) : (
        <Moon className="w-4 h-4" aria-hidden />
      )}
      {showLabel && (
        <span>{isDark ? "Light" : "Dark"}</span>
      )}
    </button>
  );
}