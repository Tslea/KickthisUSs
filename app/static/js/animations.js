/* app/static/js/animations.js */

document.addEventListener('DOMContentLoaded', function() {
    // Animazione fade-in per elementi che entrano nel viewport
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    });

    // Seleziona elementi da animare quando entrano nel viewport
    const animateElements = document.querySelectorAll('.card, .form-container, .content-section');
    animateElements.forEach(el => {
        el.classList.add('opacity-0'); // Inizialmente invisibili
        observer.observe(el);
    });

    // Animazione per pulsanti
    const buttons = document.querySelectorAll('.btn-primary, .btn-secondary, .btn-accent');
    buttons.forEach(button => {
        button.addEventListener('mousedown', function() {
            this.classList.add('scale-95');
        });
        button.addEventListener('mouseup', function() {
            this.classList.remove('scale-95');
        });
        button.addEventListener('mouseleave', function() {
            this.classList.remove('scale-95');
        });
    });

    // Effetto hover per carte e sezioni
    const hoverElements = document.querySelectorAll('.card-hover');
    hoverElements.forEach(el => {
        el.addEventListener('mouseenter', function() {
            this.style.transition = 'transform 0.3s ease, box-shadow 0.3s ease';
        });
    });

    // Gestione drag and drop per file input
    const fileDropZones = document.querySelectorAll('.form-file-wrapper');
    fileDropZones.forEach(zone => {
        ['dragenter', 'dragover'].forEach(eventName => {
            zone.addEventListener(eventName, function(e) {
                e.preventDefault();
                e.stopPropagation();
                this.classList.add('drag-active');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            zone.addEventListener(eventName, function(e) {
                e.preventDefault();
                e.stopPropagation();
                this.classList.remove('drag-active');
            }, false);
        });
        
        zone.addEventListener('drop', function(e) {
            const fileInput = this.querySelector('input[type="file"]');
            if (fileInput) {
                fileInput.files = e.dataTransfer.files;
                
                // Trigger change event
                const event = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(event);
            }
        }, false);
    });
});

// Funzione per animare contatori numerici
function animateCounter(element, start, end, duration = 2000) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const value = Math.floor(progress * (end - start) + start);
        element.textContent = value;
        
        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
            element.textContent = end;
        }
    };
    window.requestAnimationFrame(step);
}

// Funzione per creare effetti di brillamento su elementi
function addSparkleEffect(element) {
    const sparkle = document.createElement('span');
    sparkle.classList.add('sparkle');
    
    // Posiziona la scintilla in un punto casuale dell'elemento
    const x = Math.random() * 100;
    const y = Math.random() * 100;
    
    sparkle.style.left = `${x}%`;
    sparkle.style.top = `${y}%`;
    
    element.appendChild(sparkle);
    
    // Rimuovi la scintilla dopo l'animazione
    setTimeout(() => {
        sparkle.remove();
    }, 1000);
}

// Animazione al caricamento della pagina
window.addEventListener('load', function() {
    document.body.classList.add('page-loaded');
});
