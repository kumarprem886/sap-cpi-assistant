/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        sap: {
          blue: '#0070F2',
          dark: '#1C2B33',
          light: '#E8F4FD',
          accent: '#00B4D8',
        },
      },
    },
  },
  plugins: [],
}
