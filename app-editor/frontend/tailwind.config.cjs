/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        cream: '#FFFFF5',
        purple: {
          DEFAULT: '#7C3AED',
          light: '#A78BFA',
          bg: '#F3F0FF',
        },
      },
    },
  },
  plugins: [],
}
