/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html"],
  theme: {
    extend: {
      fontFamily: {
        serif: ["Georgia", "Times New Roman", "serif"],
        sans: ["Segoe UI", "Calibri", "sans-serif"],
      },
      colors: {
        ink: { 900: "#0c1c2e", 800: "#143049", 700: "#1d4463" },
        gold: { 400: "#d4b45a", 500: "#c9a227" },
      },
    },
  },
  plugins: [],
};
