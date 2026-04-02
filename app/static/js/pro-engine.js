/* ═══════════════════════════════════════════════════════════════════
   CAREPOINT PRO ENGINE — LEGEND-LEVEL INTERACTIONS
   3D Tilt, Magnetic Hover, Immersive Scroll, Page Transitions
   Inspired by: Barba.js, Rive, Spline, Awwwards Winners
   Target: 60fps across all interactions
   ═══════════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    // ── INIT ON DOM READY ──
    document.addEventListener('DOMContentLoaded', () => {
        ProEngine.init();
    });

    const ProEngine = {
        init() {
            this.initCursorSpotlight();
            this.init3DTilt();
            this.initMagneticHover();
            this.initImmersiveScroll();
            this.initStaggerGrids();
            this.initProgressBars();
            this.initParallax();
            this.initSmoothCounters();
            this.initPageTransitions();
            this.initHoloEffect();
            console.log('%c🚀 CarePoint Pro Engine Loaded', 'color: #818cf8; font-size: 14px; font-weight: bold;');
        },

        // ═══════════════════════════════════════════════════
        // 1. CURSOR SPOTLIGHT — Follows mouse with glow
        // ═══════════════════════════════════════════════════
        initCursorSpotlight() {
            const spotlight = document.querySelector('.pro-spotlight');
            if (!spotlight) return;

            let mouseX = 0, mouseY = 0;
            let spotlightX = 0, spotlightY = 0;
            let isMoving = false;
            
            // Set static top/left and use transform for hardware acceleration to avoid layout lag
            spotlight.style.left = '0px';
            spotlight.style.top = '0px';

            document.addEventListener('mousemove', (e) => {
                mouseX = e.clientX;
                mouseY = e.clientY;
                if (!isMoving) {
                    isMoving = true;
                    requestAnimationFrame(updateSpotlight);
                }
            });

            const updateSpotlight = () => {
                // Smooth lerp
                const diffX = mouseX - spotlightX;
                const diffY = mouseY - spotlightY;
                
                spotlightX += diffX * 0.15; // increased speed slightly
                spotlightY += diffY * 0.15;
                
                spotlight.style.transform = `translate(${spotlightX}px, ${spotlightY}px) translate(-50%, -50%)`;
                
                if (Math.abs(diffX) > 0.5 || Math.abs(diffY) > 0.5) {
                    requestAnimationFrame(updateSpotlight);
                } else {
                    isMoving = false;
                }
            };
        },

        // ═══════════════════════════════════════════════════
        // 2. 3D TILT CARDS — Realistic perspective on hover
        // ═══════════════════════════════════════════════════
        init3DTilt() {
            const cards = document.querySelectorAll('.pro-tilt-card');

            cards.forEach(card => {
                card.addEventListener('mousemove', (e) => {
                    const rect = card.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    const y = e.clientY - rect.top;
                    const centerX = rect.width / 2;
                    const centerY = rect.height / 2;

                    const rotateX = ((y - centerY) / centerY) * -8;
                    const rotateY = ((x - centerX) / centerX) * 8;

                    card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;

                    // Update shine position
                    const shine = card.querySelector('.tilt-shine');
                    if (shine) {
                        const percentX = (x / rect.width) * 100;
                        const percentY = (y / rect.height) * 100;
                        shine.style.setProperty('--mouse-x', percentX + '%');
                        shine.style.setProperty('--mouse-y', percentY + '%');
                    }
                });

                card.addEventListener('mouseleave', () => {
                    card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) scale3d(1, 1, 1)';
                    card.style.transition = 'transform 0.6s cubic-bezier(0.16, 1, 0.3, 1)';
                    setTimeout(() => { card.style.transition = ''; }, 600);
                });

                card.addEventListener('mouseenter', () => {
                    card.style.transition = 'none';
                });
            });
        },

        // ═══════════════════════════════════════════════════
        // 3. MAGNETIC HOVER — Elements pulled toward cursor
        // ═══════════════════════════════════════════════════
        initMagneticHover() {
            const magnets = document.querySelectorAll('.pro-magnetic');

            magnets.forEach(magnet => {
                magnet.addEventListener('mousemove', (e) => {
                    const rect = magnet.getBoundingClientRect();
                    const x = e.clientX - rect.left - rect.width / 2;
                    const y = e.clientY - rect.top - rect.height / 2;

                    magnet.style.transform = `translate(${x * 0.3}px, ${y * 0.3}px)`;

                    // Move inner content slightly more
                    const inner = magnet.querySelector('.magnetic-inner');
                    if (inner) {
                        inner.style.transform = `translate(${x * 0.15}px, ${y * 0.15}px)`;
                    }
                });

                magnet.addEventListener('mouseleave', () => {
                    magnet.style.transform = 'translate(0, 0)';
                    const inner = magnet.querySelector('.magnetic-inner');
                    if (inner) inner.style.transform = 'translate(0, 0)';
                });
            });
        },

        // ═══════════════════════════════════════════════════
        // 4. IMMERSIVE SCROLL REVEAL — IntersectionObserver
        // ═══════════════════════════════════════════════════
        initImmersiveScroll() {
            const revealElements = document.querySelectorAll(
                '.pro-reveal, .pro-reveal-zoom, .pro-reveal-left, .pro-reveal-right'
            );

            if (revealElements.length === 0) return;

            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('visible');

                        // Also trigger counters inside
                        const counters = entry.target.querySelectorAll('[data-count-to]:not([data-counted])');
                        counters.forEach(el => this.animateCounterPro(el));

                        // Trigger progress bars
                        const fills = entry.target.querySelectorAll('.pro-progress-fill:not(.animated)');
                        fills.forEach(fill => {
                            requestAnimationFrame(() => fill.classList.add('animated'));
                        });

                        observer.unobserve(entry.target);
                    }
                });
            }, {
                threshold: 0.15,
                rootMargin: '0px 0px -60px 0px'
            });

            revealElements.forEach(el => observer.observe(el));
        },

        // ═══════════════════════════════════════════════════
        // 5. STAGGER GRID ANIMATION
        // ═══════════════════════════════════════════════════
        initStaggerGrids() {
            const grids = document.querySelectorAll('.pro-stagger-grid');

            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('visible');
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.1 });

            grids.forEach(grid => observer.observe(grid));
        },

        // ═══════════════════════════════════════════════════
        // 6. ANIMATED PROGRESS BARS
        // ═══════════════════════════════════════════════════
        initProgressBars() {
            const fills = document.querySelectorAll('.pro-progress-fill');

            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        setTimeout(() => {
                            entry.target.classList.add('animated');
                        }, 300);
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.5 });

            fills.forEach(fill => observer.observe(fill));
        },

        // ═══════════════════════════════════════════════════
        // 7. PARALLAX SCROLL — Subtle depth effect
        // ═══════════════════════════════════════════════════
        initParallax() {
            const parallaxElements = document.querySelectorAll('[data-parallax]');
            if (parallaxElements.length === 0) return;

            let ticking = false;

            window.addEventListener('scroll', () => {
                if (!ticking) {
                    requestAnimationFrame(() => {
                        const scrollY = window.pageYOffset;
                        parallaxElements.forEach(el => {
                            const speed = parseFloat(el.dataset.parallax) || 0.3;
                            const offset = scrollY * speed;
                            el.style.transform = `translateY(${offset}px)`;
                        });
                        ticking = false;
                    });
                    ticking = true;
                }
            });
        },

        // ═══════════════════════════════════════════════════
        // 8. SMOOTH ANIMATED COUNTERS (Enhanced)
        // ═══════════════════════════════════════════════════
        initSmoothCounters() {
            const counters = document.querySelectorAll('[data-count-to]');

            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        this.animateCounterPro(entry.target);
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.5 });

            counters.forEach(counter => observer.observe(counter));
        },

        animateCounterPro(el) {
            if (el.dataset.counted) return;
            el.dataset.counted = 'true';

            const target = parseFloat(el.dataset.countTo);
            const duration = parseInt(el.dataset.countDuration) || 2000;
            const decimals = parseInt(el.dataset.countDecimals) || 0;
            const start = 0;
            const startTime = performance.now();

            const update = (currentTime) => {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);

                // Easing: easeOutExpo
                const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
                const current = start + (target - start) * eased;

                el.textContent = decimals > 0 ? current.toFixed(decimals) : Math.round(current);

                if (progress < 1) {
                    requestAnimationFrame(update);
                }
            };

            requestAnimationFrame(update);
        },

        // ═══════════════════════════════════════════════════
        // 9. PAGE TRANSITIONS (Barba.js Inspired)
        // ═══════════════════════════════════════════════════
        initPageTransitions() {
            // Disabled to remove the "shutted" effect on page switch
            return;
            
            // Create transition overlay if not present
            if (!document.querySelector('.pro-page-transition')) {
                const overlay = document.createElement('div');
                overlay.className = 'pro-page-transition';
                for (let i = 0; i < 5; i++) {
                    const slice = document.createElement('div');
                    slice.className = 'pt-slice';
                    overlay.appendChild(slice);
                }
                document.body.appendChild(overlay);
            }

            // Intercept internal navigation links
            const internalLinks = document.querySelectorAll('a[href^="/"]');

            internalLinks.forEach(link => {
                // Skip special links
                if (link.getAttribute('target') === '_blank' ||
                    link.getAttribute('download') ||
                    link.classList.contains('no-transition') ||
                    link.getAttribute('href').startsWith('#') ||
                    link.getAttribute('href').includes('logout')) return;

                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    const href = link.getAttribute('href');
                    const overlay = document.querySelector('.pro-page-transition');

                    if (overlay) {
                        overlay.classList.add('active');
                        setTimeout(() => {
                            window.location.href = href;
                        }, 700);
                    } else {
                        window.location.href = href;
                    }
                });
            });
        },

        // ═══════════════════════════════════════════════════
        // 10. HOLOGRAPHIC BORDER ANIMATION TRIGGER
        // ═══════════════════════════════════════════════════
        initHoloEffect() {
            const holoCards = document.querySelectorAll('.pro-holo-border');

            holoCards.forEach(card => {
                card.addEventListener('mousemove', (e) => {
                    const rect = card.getBoundingClientRect();
                    const x = ((e.clientX - rect.left) / rect.width) * 100;
                    const y = ((e.clientY - rect.top) / rect.height) * 100;

                    card.style.setProperty('--holo-x', x + '%');
                    card.style.setProperty('--holo-y', y + '%');
                });
            });
        }
    };

    // ── Expose globally for external use ──
    window.ProEngine = ProEngine;

})();
