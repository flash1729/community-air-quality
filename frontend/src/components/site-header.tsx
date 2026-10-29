"use client";

import { History, Info, LayoutDashboard, Map, Moon, Radio, Sun, Wind } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const LINKS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/explore", label: "Explore", icon: Map },
  { href: "/community", label: "Community", icon: Radio },
  { href: "/history", label: "History", icon: History },
  { href: "/about", label: "About", icon: Info },
];

const THEME_KEY = "community-air-theme";

function ThemeToggle() {
  const [theme, setTheme] = useState<"dark" | "light" | null>(null);

  useEffect(() => {
    setTheme(document.documentElement.dataset.theme === "light" ? "light" : "dark");
  }, []);

  function toggle() {
    const next = theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    try {
      window.localStorage.setItem(THEME_KEY, next);
    } catch {
      // Private browsing can refuse storage. The theme still applies for this visit.
    }
    setTheme(next);
  }

  const next = theme === "light" ? "dark" : "light";
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`Switch to ${next} theme`}
      title={`Switch to ${next} theme`}
      className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-line bg-surface-2 text-muted transition duration-200 hover:border-line-strong hover:text-ink"
    >
      {theme === "light" ? <Moon size={17} /> : <Sun size={17} />}
    </button>
  );
}

export function SiteHeader() {
  const pathname = usePathname();
  return (
    <header
      className="sticky top-0 z-40 border-b border-line backdrop-blur-xl backdrop-saturate-150"
      style={{ background: "var(--header)" }}
    >
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-surface-solid focus:px-3 focus:py-2 focus:text-sm"
      >
        Skip to content
      </a>
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
        <Link href="/" className="group flex items-center gap-3">
          <span
            className="grid h-10 w-10 place-items-center rounded-2xl text-[#04201b] shadow-[0_10px_26px_-10px_rgb(var(--accent)/0.9)] transition duration-300 group-hover:rotate-[-6deg] group-hover:scale-105"
            style={{ background: "linear-gradient(135deg, #4fe3c1 0%, #3b9eff 100%)" }}
          >
            <Wind size={20} strokeWidth={2.4} />
          </span>
          <span>
            <span className="block text-[15px] font-semibold leading-tight tracking-tight text-ink">Community Air</span>
            <span className="block font-mono text-[10px] uppercase tracking-[0.18em] text-muted">Environmental health</span>
          </span>
        </Link>

        <div className="order-3 w-full sm:order-none sm:ml-auto sm:w-auto">
          <nav
            aria-label="Primary"
            className="no-scrollbar flex gap-1 overflow-x-auto rounded-full border border-line bg-surface-2 p-1"
          >
            {LINKS.map((link) => {
              const active = pathname === link.href;
              const Icon = link.icon;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  aria-current={active ? "page" : undefined}
                  className={`flex flex-1 items-center justify-center gap-2 whitespace-nowrap rounded-full px-3 py-2 text-sm transition duration-200 sm:flex-none sm:px-3.5 ${
                    active ? "bg-ink font-semibold text-paper shadow-sm" : "text-muted hover:text-ink"
                  }`}
                >
                  <Icon size={15} strokeWidth={active ? 2.4 : 2} className="hidden sm:block" />
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="ml-auto sm:ml-0">
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
