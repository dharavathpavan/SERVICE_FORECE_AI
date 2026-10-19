/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f7ff',
          100: '#e0effe',
          200: '#bae0fd',
          300: '#7cc7fb',
          400: '#38aaf6',
          500: '#0e8fe7',
          600: '#0272c5',
          700: '#035ba0',
          800: '#074e84',
          900: '#0c426e',
          950: '#082a48',
        },
        navy: {
          800: '#0f172a',
          900: '#0b1120',
          950: '#060a13',
        }
      }
    },
  },
  plugins: [],
}
