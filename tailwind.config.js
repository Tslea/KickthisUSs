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
        // Sistema di colori primari
        'primary': {
          50: '#FFF3E6',
          100: '#FFE0C2',
          200: '#FFC999',
          300: '#FFB170',
          400: '#FF9A47',
          500: '#FF8100', // Colore principale (mclaren-orange)
          600: '#E07000', // Hover state
          700: '#B85C00',
          800: '#8F4700',
          900: '#663300',
        },
        // Sistema di colori secondari (accento)
        'accent': {
          50: '#E6F6FF',
          100: '#B8E7FF',
          200: '#8AD8FF',
          300: '#5CC8FF',
          400: '#2EB9FF',
          500: '#00AAFF',
          600: '#0088CC',
          700: '#006699',
          800: '#004466',
          900: '#002233',
        },
        // Mantengo compatibilità con i nomi vecchi
        'mclaren-orange': '#FF8100',
        'mclaren-orange-darker': '#E07000',
        'stitch-blue': '#00AAFF',
        'stitch-blue-darker': '#0088CC',
      },
      borderRadius: {
        'xl': '0.75rem',
        '2xl': '1rem',
      },
      boxShadow: {
        'card': '0 4px 20px -5px rgba(0, 0, 0, 0.1)',
        'card-hover': '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05)',
        'button': '0 2px 4px rgba(0, 0, 0, 0.05)',
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