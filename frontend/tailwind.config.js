/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          900: '#0B132B',
          800: '#1C2541',
          700: '#3A506B',
        },
        civic: {
          teal: '#00A896',
          amber: '#F4A261',
          red: '#E63946',
          green: '#2A9D8F',
          slate: '#64748B',
        }
      }
    },
  },
  plugins: [],
}
