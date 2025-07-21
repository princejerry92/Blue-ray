document.addEventListener('DOMContentLoaded', function() {
            // Initialize GSAP animations
            gsap.registerPlugin();

            // Loading bar animation
            const loadingBar = document.getElementById('loadingBar');
            gsap.to(loadingBar, {
                width: '100%',
                duration: 1.5,
                ease: 'power2.out',
                onComplete: () => {
                    gsap.to(loadingBar, {opacity: 0, duration: 0.5, delay: 0.5});
                }
            });

            // Sidebar animation
            gsap.from('.sidebar', {
                x: -100,
                opacity: 0,
                duration: 0.8,
                ease: 'power2.out'
            });

            // Main content animation
            gsap.from('.main-content', {
                x: 100,
                opacity: 0,
                duration: 0.8,
                ease: 'power2.out',
                delay: 0.2
            });

            // Nav buttons animation
            gsap.from('.nav-button', {
                x: -50,
                opacity: 0,
                stagger: 0.1,
                duration: 0.6,
                ease: 'back.out(1.7)',
                delay: 0.5
            });

            // Folder cards animation
            gsap.from('.folder-card', {
                y: 100,
                opacity: 0,
                scale: 0.8,
                stagger: 0.2,
                duration: 0.8,
                ease: 'back.out(1.7)',
                delay: 0.8
            });

            // Load exam button animation
            gsap.from('.load-exam-btn', {
                y: 50,
                opacity: 0,
                duration: 0.6,
                ease: 'back.out(1.7)',
                delay: 1.2
            });

            // Hover animations for navigation buttons
            const navButtons = document.querySelectorAll('.nav-button');
            navButtons.forEach(button => {
                button.addEventListener('mouseenter', () => {
                    gsap.to(button, {
                        scale: 1.02,
                        duration: 0.2,
                        ease: 'power2.out'
                    });
                });
                
                button.addEventListener('mouseleave', () => {
                    gsap.to(button, {
                        scale: 1,
                        duration: 0.2,
                        ease: 'power2.out'
                    });
                });
            });

            // Folder card interactions
            const folderCards = document.querySelectorAll('.folder-card');
            folderCards.forEach(card => {
                card.addEventListener('mouseenter', () => {
                    gsap.to(card.querySelector('.folder-icon'), {
                        rotateY: 15,
                        scale: 1.1,
                        duration: 0.3,
                        ease: 'power2.out'
                    });
                });
                
                card.addEventListener('mouseleave', () => {
                    gsap.to(card.querySelector('.folder-icon'), {
                        rotateY: 0,
                        scale: 1,
                        duration: 0.3,
                        ease: 'power2.out'
                    });
                });
            });

            // Button click animations
            const buttons = document.querySelectorAll('button');
            buttons.forEach(button => {
                button.addEventListener('click', () => {
                    gsap.to(button, {
                        scale: 0.95,
                        duration: 0.1,
                        yoyo: true,
                        repeat: 1,
                        ease: 'power2.out'
                    });
                });
            });

            // Modal animations
            const modals = document.querySelectorAll('.modal');
            modals.forEach(modal => {
                const observer = new MutationObserver(mutations => {
                    mutations.forEach(mutation => {
                        if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                            if (modal.style.display === 'block') {
                                gsap.from(modal.querySelector('.modal-content'), {
                                    scale: 0.8,
                                    opacity: 0,
                                    duration: 0.3,
                                    ease: 'back.out(1.7)'
                                });
                            }
                        }
                    });
                });
                
                observer.observe(modal, { attributes: true });
            });

            // Preserve original functionality
            const startExamButton = document.getElementById('startExam');
            if (startExamButton) {
                startExamButton.addEventListener('click', function() {
                    window.location.href = '{{ url_for("examloader2") }}';
                });
            }

            // Add floating animation to background elements
            gsap.to('.sidebar', {
                y: -5,
                duration: 3,
                ease: 'power2.inOut',
                yoyo: true,
                repeat: -1
            });

            gsap.to('.main-content', {
                y: 5,
                duration: 4,
                ease: 'power2.inOut',
                yoyo: true,
                repeat: -1,
                delay: 0.5
            });

            // Continuous subtle animations
            gsap.to('.logo', {
                rotateY: 360,
                duration: 10,
                ease: 'none',
                repeat: -1
            });

            // Parallax effect on scroll
            window.addEventListener('scroll', () => {
                const scrolled = window.pageYOffset;
                const parallax = document.querySelector('.sidebar');
                const speed = scrolled * 0.5;
                parallax.style.transform = `translateY(${speed}px)`;
            });

            // Intersection Observer for scroll animations
            const observerOptions = {
                threshold: 0.1,
                rootMargin: '0px 0px -100px 0px'
            };

            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        gsap.from(entry.target, {
                            y: 50,
                            opacity: 0,
                            duration: 0.6,
                            ease: 'power2.out'
                        });
                    }
                });
            }, observerOptions);

            // Observe elements for scroll animations
            document.querySelectorAll('.glass-card, .nav-button').forEach(el => {
                observer.observe(el);
            });

            // Progressive enhancement for modern browsers
            if ('backdrop-filter' in document.documentElement.style) {
                document.body.classList.add('backdrop-support');
            }

            // Add ripple effect to buttons
            function createRipple(event) {
                const button = event.currentTarget;
                const circle = document.createElement('span');
                const diameter = Math.max(button.clientWidth, button.clientHeight);
                const radius = diameter / 2;

                circle.style.width = circle.style.height = `${diameter}px`;
                circle.style.left = `${event.clientX - button.offsetLeft - radius}px`;
                circle.style.top = `${event.clientY - button.offsetTop - radius}px`;
                circle.classList.add('ripple');

                const ripple = button.getElementsByClassName('ripple')[0];
                if (ripple) {
                    ripple.remove();
                }

                button.appendChild(circle);
            }

            // Add ripple styles
            const style = document.createElement('style');
            style.textContent = `
                .ripple {
                    position: absolute;
                    border-radius: 50%;
                    transform: scale(0);
                    animation: ripple 600ms linear;
                    background-color: rgba(255, 255, 255, 0.6);
                    pointer-events: none;
                }

                @keyframes ripple {
                    to {
                        transform: scale(4);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);

            // Apply ripple effect to buttons
            document.querySelectorAll('button').forEach(button => {
                button.addEventListener('click', createRipple);
            });

            // Enhanced typing animation for inputs
            const inputs = document.querySelectorAll('input[type="text"]');
            inputs.forEach(input => {
                input.addEventListener('focus', () => {
                    gsap.to(input, {
                        scale: 1.02,
                        duration: 0.2,
                        ease: 'power2.out'
                    });
                });
                
                input.addEventListener('blur', () => {
                    gsap.to(input, {
                        scale: 1,
                        duration: 0.2,
                        ease: 'power2.out'
                    });
                });
            });

            // Add smooth page transitions
            window.addEventListener('beforeunload', () => {
                gsap.to(document.body, {
                    opacity: 0,
                    duration: 0.3,
                    ease: 'power2.out'
                });
            });

            // Initialize theme particles (optional enhancement)
            function createParticles() {
                const particlesContainer = document.createElement('div');
                particlesContainer.className = 'particles-container';
                particlesContainer.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    pointer-events: none;
                    z-index: -1;
                `;
                document.body.appendChild(particlesContainer);

                for (let i = 0; i < 20; i++) {
                    const particle = document.createElement('div');
                    particle.className = 'particle';
                    particle.style.cssText = `
                        position: absolute;
                        width: 2px;
                        height: 2px;
                        background: rgba(79, 172, 254, 0.3);
                        border-radius: 50%;
                        animation: float-particle ${Math.random() * 10 + 5}s linear infinite;
                        left: ${Math.random() * 100}%;
                        top: ${Math.random() * 100}%;
                    `;
                    particlesContainer.appendChild(particle);
                }
            }

            // Add particle animation styles
            const particleStyle = document.createElement('style');
            particleStyle.textContent = `
                @keyframes float-particle {
                    0% {
                        transform: translateY(0px) rotate(0deg);
                        opacity: 1;
                    }
                    100% {
                        transform: translateY(-100vh) rotate(360deg);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(particleStyle);

            // Initialize particles
            createParticles();

            // Performance optimization: Reduce animations on lower-end devices
            const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
            if (prefersReducedMotion.matches) {
                gsap.globalTimeline.timeScale(0.5);
            }

            // Add custom cursor effect
            const cursor = document.createElement('div');
            cursor.className = 'custom-cursor';
            cursor.style.cssText = `
                position: fixed;
                width: 20px;
                height: 20px;
                background: rgba(79, 172, 254, 0.3);
                border-radius: 50%;
                pointer-events: none;
                z-index: 9999;
                mix-blend-mode: difference;
                transition: all 0.3s ease;
            `;
            document.body.appendChild(cursor);

            document.addEventListener('mousemove', (e) => {
                cursor.style.left = e.clientX - 10 + 'px';
                cursor.style.top = e.clientY - 10 + 'px';
            });

            document.addEventListener('mousedown', () => {
                cursor.style.transform = 'scale(0.8)';
            });

            document.addEventListener('mouseup', () => {
                cursor.style.transform = 'scale(1)';
            });

            // Enhanced hover effects for interactive elements
            document.querySelectorAll('button, .folder-card, .nav-button').forEach(element => {
                element.addEventListener('mouseenter', () => {
                    cursor.style.transform = 'scale(1.5)';
                    cursor.style.background = 'rgba(79, 172, 254, 0.6)';
                });
                
                element.addEventListener('mouseleave', () => {
                    cursor.style.transform = 'scale(1)';
                    cursor.style.background = 'rgba(79, 172, 254, 0.3)';
                });
            });

            console.log('🚀 Admin Dashboard UI Enhanced Successfully!');
        });