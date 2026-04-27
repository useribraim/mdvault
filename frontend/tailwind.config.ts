import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#17201a",
        moss: "#566b4f",
        paper: "#fbfaf5",
        line: "#d9d7cc",
        clay: "#b75f3a",
      },
    },
  },
  plugins: [],
};

export default config;
