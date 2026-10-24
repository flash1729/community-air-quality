import type { Metadata, Viewport } from "next";

import "@fontsource-variable/geist";
import "@fontsource-variable/geist-mono";
import "@fontsource/instrument-serif/400.css";
import "@fontsource/instrument-serif/400-italic.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Community Air",
  description: "Local air quality, Indian AQI, and environmental health guidance.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#060a0e" },
    { media: "(prefers-color-scheme: light)", color: "#f2f6f5" },
  ],
};

// Runs before first paint so a saved light theme never flashes dark.
const THEME_SCRIPT = `(function(){var t="dark";try{var s=localStorage.getItem("community-air-theme");if(s==="light"||s==="dark")t=s}catch(e){}document.documentElement.dataset.theme=t})()`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
