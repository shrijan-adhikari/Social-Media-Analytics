import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#070709",
        card: {
          DEFAULT: "#111014",
          elevated: "#16151B",
          dark: "#0D0C11",
          border: "#222027",
          borderLight: "#3A3445",
        },
        intel: {
          gold: "#E5B95C",
          goldLight: "#F5D78E",
          green: "#00E575",
          red: "#FF3B5C",
          sky: "#38BDF8",
          purple: "#A78BFA",
          text: "#F3F0E8",
          muted: "#85817B",
        },
      },
      fontFamily: {
        sans: ["Outfit", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
