export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        obsidian: {
          950: '#0A0A0B',
          900: '#111113',
          850: '#1A1A1D',
          800: '#222225',
          700: '#2C2C30',
          600: '#404045',
        },
        platinum: {
          400: '#F0F0F0',
          500: '#E8E8E8',
          600: '#D0D0D0',
          700: '#B8B8B8',
        },
        purple: {
          400: '#A78BFA',
          500: '#8B5CF6',
          600: '#7C3AED',
        },
        rose: {
          400: '#FB7185',
          500: '#F43F5E',
          600: '#E11D48',
        },
        text: {
          primary: '#F8F8F8',
          secondary: '#C0C0C0',
          tertiary: '#808080',
          disabled: '#404040',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      fontSize: {
        'xs': ['12px', { lineHeight: '16px' }],
        'sm': ['14px', { lineHeight: '20px' }],
        'base': ['16px', { lineHeight: '24px' }],
        'lg': ['20px', { lineHeight: '28px' }],
        'xl': ['24px', { lineHeight: '32px' }],
        '2xl': ['30px', { lineHeight: '36px' }],
        '3xl': ['36px', { lineHeight: '40px' }],
        '4xl': ['48px', { lineHeight: '1' }],
        '5xl': ['60px', { lineHeight: '1' }],
      },
      letterSpacing: {
        tighter: '-0.02em',
        tight: '-0.01em',
        normal: '0',
        wide: '0.02em',
        wider: '0.05em',
      },
    },
  },
  plugins: [],
}
