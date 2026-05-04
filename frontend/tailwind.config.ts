import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Design system issu du template Property (property-1.0.0)
        primary: {
          DEFAULT: '#00204a',
          50:  '#e6edf5',
          100: '#b3c4d9',
          200: '#809bbd',
          300: '#4d72a1',
          400: '#1a4985',
          500: '#00204a',
          600: '#001a3d',
          700: '#001430',
          800: '#000e22',
          900: '#000815',
        },
        secondary: {
          DEFAULT: '#005555',
          50:  '#e6f2f2',
          100: '#b3d9d9',
          200: '#80bfbf',
          300: '#4da6a6',
          400: '#1a8c8c',
          500: '#005555',
          600: '#004444',
          700: '#003333',
          800: '#002222',
          900: '#001111',
        },
        brand: {
          50:  '#f0f9ff',
          100: '#e0f2fe',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          900: '#0c4a6e',
        },
      },
      fontFamily: {
        // Police principale du template : Work Sans
        sans: ['"Work Sans"', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'gradient-accent': 'linear-gradient(270deg, #f82a7e 0%, #752a90 100%)',
      },
      boxShadow: {
        card: '0 1px 4px 0 rgba(0,0,0,0.05)',
        'card-hover': '0 15px 30px -10px rgba(0,0,0,0.10)',
      },
    },
  },
  plugins: [],
}

export default config
