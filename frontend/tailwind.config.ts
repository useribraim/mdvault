import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#151914",
        moss: "#6f8f72",
        paper: "#f7f3e8",
        line: "#ded7c7",
        clay: "#d77a4a",
        night: "#111610",
        sage: "#cfe0c3",
        butter: "#f3d58a",
      },
    },
  },
  plugins: [],
};

export default config;
