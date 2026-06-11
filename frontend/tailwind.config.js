/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: { 500: "#4f72d9" },
        surface: {
          DEFAULT: "#0f1117",
          card: "#1a1d27",
          border: "#2a2d3a",
        },
      },
    },
  },
  plugins: [],
}