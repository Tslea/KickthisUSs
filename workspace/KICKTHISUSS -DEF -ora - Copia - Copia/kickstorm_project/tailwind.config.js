// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/templates/**/*.html', // Scansiona tutti i file .html nella cartella templates e sottocartelle
    './app/static/js/**/*.js'    // Includi anche file JS se usi classi Tailwind lì
  ],
  theme: {
    extend: {
      colors: {
        // NUOVA PALETTE DESIGN SYSTEM
        black: '#0A0A0A',
        white: '#FFFFFF',
        primary: {
          DEFAULT: '#0A0A0A', // Sfondo principale
          50: '#FAFAFA',
          100: '#F5F5F5',
          200: '#E5E5E5',
          300: '#D4D4D4',
          400: '#A3A3A3',
          500: '#737373',
          600: '#757575', // Testi secondari
          700: '#404040',
          800: '#262626',
          900: '#171717',
          950: '#0A0A0A',
        },
        accent: {
          DEFAULT: '#FF3D00', // Rosso azione
          50: '#FFF3E0',
          100: '#FFE0B2',
          200: '#FFCC80',
          300: '#FFB74D',
          400: '#FFA726',
          500: '#FF3D00', // Main Accent
          600: '#FB8C00',
          700: '#F57C00',
          800: '#EF6C00',
          900: '#E65100',
        },
        success: '#00E676',
        warning: '#FFD600',
        
        // Mantenimento compatibilità (ma mappati sui nuovi colori dove possibile o lasciati per non rompere)
        'mclaren-orange': '#FF3D00', // Mappato sul nuovo rosso
        'mclaren-orange-darker': '#D50000',
        'stitch-blue': '#00E676', // Mappato su success per ora, o lasciare blu se serve distinzione
        'stitch-blue-darker': '#00C853',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Clash Display', 'Cabinet Grotesk', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        'xl': '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      boxShadow: {
        'card': '0 4px 20px -5px rgba(0, 0, 0, 0.1)',
        'card-hover': '0 16px 32px -8px rgba(0, 0, 0, 0.2)',
        'button': '0 2px 4px rgba(0, 0, 0, 0.05)',
        'glow': '0 0 20px rgba(255, 61, 0, 0.3)',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),             // Plugin per stilizzare meglio i form
    require('@tailwindcss/container-queries'), // Plugin per container queries
    require('@tailwindcss/typography'),        // Per styling di contenuti ricchi
  ],
}