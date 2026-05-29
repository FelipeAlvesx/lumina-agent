import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#7C3D6E',
        'primary-light': '#9B5089',
        'primary-dark': '#5E2D53',
        gold: '#C5A87D',
        'gold-light': '#D4BB99',
        surface: '#FFFFFF',
        'surface-2': '#FAFAF8',
        bg: '#F0EFEC',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
} satisfies Config
