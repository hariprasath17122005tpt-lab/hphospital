/**
 * Unified Login System - Advanced JavaScript
 * Enterprise-grade hospital authentication UI interactions
 */

document.addEventListener('DOMContentLoaded', function () {
    // Initialize the login system
    initUnifiedLogin();
});

function initUnifiedLogin() {
    // DOM Elements
    const loginCard = document.getElementById('login-card');
    const logoIcon = document.getElementById('logo-icon');
    const tabIndicator = document.getElementById('tab-indicator');
    const roleTabs = document.querySelectorAll('.role-tab');
    const roleInput = document.getElementById('role-input');
    const emailInput = document.getElementById('email-input');
    const emailPlaceholder = document.getElementById('email-placeholder');
    const passwordInput = document.getElementById('password-input');
    const passwordToggle = document.getElementById('password-toggle');
    const eyeIcon = document.getElementById('eye-icon');
    const loginForm = document.getElementById('login-form');
    const loginBtn = document.getElementById('login-btn');
    const signupText = document.getElementById('signup-text');
    const signupLink = document.getElementById('signup-link');
    const emergencyAccess = document.getElementById('emergency-access');

    // Role configurations
    const roleConfig = {
        patient: {
            placeholder: 'Email or Patient ID',
            signupText: 'New patient?',
            signupLink: '/patient/register',
            signupLinkText: 'Create an account',
            themeClass: '',
            icon: 'fa-user-injured'
        },
        doctor: {
            placeholder: 'Medical ID or Email',
            signupText: 'New doctor?',
            signupLink: '/doctor/register',
            signupLinkText: 'Register here',
            themeClass: 'doctor-theme',
            icon: 'fa-user-md'
        },
        admin: {
            placeholder: 'Admin Email',
            signupText: 'Admin access only',
            signupLink: '#',
            signupLinkText: 'Contact support',
            themeClass: 'admin-theme',
            icon: 'fa-shield-alt'
        }
    };

    // Current state
    let currentRole = 'patient';
    let isPasswordVisible = false;

    // ====================
    // Role Tab Switching
    // ====================

    roleTabs.forEach((tab, index) => {
        tab.addEventListener('click', function () {
            const role = this.dataset.role;
            if (role === currentRole) return;

            // Update active tab
            roleTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');

            // Move indicator
            const tabWidth = (100 / roleTabs.length);
            tabIndicator.style.left = `calc(${index * tabWidth}% + 6px)`;
            tabIndicator.style.width = `calc(${tabWidth}% - ${index === 0 ? '4px' : index === roleTabs.length - 1 ? '8px' : '6px'})`;

            // Update theme
            updateTheme(role);

            // Update form
            updateFormForRole(role);

            // Add ripple effect
            addRippleEffect(this, event);

            currentRole = role;
        });
    });

    function updateTheme(role) {
        const config = roleConfig[role];

        // Update login card theme
        loginCard.classList.remove('doctor-theme', 'admin-theme');
        if (config.themeClass) {
            loginCard.classList.add(config.themeClass);
        }

        // Update logo icon
        logoIcon.classList.remove('doctor-theme', 'admin-theme');
        if (config.themeClass) {
            logoIcon.classList.add(config.themeClass);
        }

        // Update tab indicator
        tabIndicator.classList.remove('doctor-theme', 'admin-theme');
        if (config.themeClass) {
            tabIndicator.classList.add(config.themeClass);
        }

        // Update login button
        loginBtn.classList.remove('doctor-theme', 'admin-theme');
        if (config.themeClass) {
            loginBtn.classList.add(config.themeClass);
        }

        // Update hero features if visible
        updateHeroTheme(role);
    }

    function updateFormForRole(role) {
        const config = roleConfig[role];

        // Update placeholder
        if (emailPlaceholder) {
            emailPlaceholder.textContent = config.placeholder;
        }

        // Update role input
        if (roleInput) {
            roleInput.value = role;
        }

        // Update signup text and link
        if (signupText) {
            signupText.textContent = config.signupText;
        }
        if (signupLink) {
            signupLink.href = config.signupLink;
            signupLink.textContent = config.signupLinkText;
        }

        // Clear validation states
        const emailGroup = emailInput?.closest('.form-group');
        const passwordGroup = passwordInput?.closest('.form-group');
        if (emailGroup) emailGroup.classList.remove('valid', 'invalid');
        if (passwordGroup) passwordGroup.classList.remove('valid', 'invalid');
    }

    function updateHeroTheme(role) {
        const featureIcons = document.querySelectorAll('.feature-icon');
        featureIcons.forEach(icon => {
            icon.classList.remove('doctor-theme', 'admin-theme');
            if (roleConfig[role].themeClass) {
                icon.classList.add(roleConfig[role].themeClass);
            }
        });
    }

    // ====================
    // Password Toggle
    // ====================

    if (passwordToggle) {
        passwordToggle.addEventListener('click', function () {
            isPasswordVisible = !isPasswordVisible;

            if (isPasswordVisible) {
                passwordInput.type = 'text';
                eyeIcon.classList.remove('fa-eye');
                eyeIcon.classList.add('fa-eye-slash');
            } else {
                passwordInput.type = 'password';
                eyeIcon.classList.remove('fa-eye-slash');
                eyeIcon.classList.add('fa-eye');
            }
        });
    }

    // ====================
    // Input Validation
    // ====================

    if (emailInput) {
        emailInput.addEventListener('input', function () {
            validateEmail(this);
        });

        emailInput.addEventListener('blur', function () {
            validateEmail(this);
        });
    }

    if (passwordInput) {
        passwordInput.addEventListener('input', function () {
            validatePassword(this);
        });

        passwordInput.addEventListener('blur', function () {
            validatePassword(this);
        });
    }

    function validateEmail(input) {
        const value = input.value.trim();
        const errorEl = document.getElementById('email-error');
        const group = input.closest('.form-group');

        if (value.length === 0) {
            if (group) group.classList.remove('valid', 'invalid');
            if (errorEl) errorEl.textContent = '';
            return false;
        }

        // Email or ID validation based on role
        let isValid = false;

        if (currentRole === 'patient') {
            // Accept email or patient ID (alphanumeric)
            isValid = /^[\w.+-]+@[\w.-]+\.\w{2,}$/.test(value) || /^\w{4,}$/.test(value);
        } else if (currentRole === 'doctor') {
            // Accept email or medical ID
            isValid = /^[\w.+-]+@[\w.-]+\.\w{2,}$/.test(value) || /^[A-Z]{2,}\d{4,}$/i.test(value);
        } else {
            // Admin - email only
            isValid = /^[\w.+-]+@[\w.-]+\.\w{2,}$/.test(value);
        }

        if (group) {
            if (isValid) {
                group.classList.add('valid');
                group.classList.remove('invalid');
            } else {
                group.classList.add('invalid');
                group.classList.remove('valid');
            }
        }
        if (errorEl) errorEl.textContent = isValid ? '' : 'Please enter a valid email or ID';

        return isValid;
    }

    function validatePassword(input) {
        const value = input.value;
        const errorEl = document.getElementById('password-error');
        const group = input.closest('.form-group');

        if (value.length === 0) {
            if (group) group.classList.remove('valid', 'invalid');
            if (errorEl) errorEl.textContent = '';
            return false;
        }

        if (value.length >= 6) {
            if (group) { group.classList.add('valid'); group.classList.remove('invalid'); }
            if (errorEl) errorEl.textContent = '';
            return true;
        } else {
            if (group) { group.classList.add('invalid'); group.classList.remove('valid'); }
            if (errorEl) errorEl.textContent = 'Password must be at least 6 characters';
            return false;
        }
    }

    // ====================
    // Form Submission
    // ====================

    if (loginForm) {
        loginForm.addEventListener('submit', function (e) {
            // Validate before submit
            const emailValid = validateEmail(emailInput);
            const passwordValid = validatePassword(passwordInput);

            if (!emailValid || !passwordValid) {
                e.preventDefault();

                // Shake the form
                loginCard.classList.add('shake');
                setTimeout(() => loginCard.classList.remove('shake'), 500);

                return;
            }

            // Show loading state
            loginBtn.classList.add('loading');
            loginBtn.disabled = true;
        });
    }

    // ====================
    // Emergency Access
    // ====================

    if (emergencyAccess) {
        emergencyAccess.addEventListener('click', function (e) {
            e.preventDefault();
            const modal = new bootstrap.Modal(document.getElementById('emergencyModal'));
            modal.show();
        });
    }

    // ====================
    // Utility Functions
    // ====================

    function addRippleEffect(element, event) {
        const ripple = document.createElement('span');
        ripple.classList.add('ripple');

        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);

        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = (event.clientX - rect.left - size / 2) + 'px';
        ripple.style.top = (event.clientY - rect.top - size / 2) + 'px';

        element.appendChild(ripple);

        setTimeout(() => ripple.remove(), 600);
    }

    // Add shake animation CSS
    const style = document.createElement('style');
    style.textContent = `
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
            20%, 40%, 60%, 80% { transform: translateX(5px); }
        }
        .shake {
            animation: shake 0.5s ease-in-out;
        }
    `;
    document.head.appendChild(style);

    // ====================
    // Account Lock Timer
    // ====================

    function startLockTimer(minutes) {
        const lockAlert = document.getElementById('account-locked-alert');
        const lockTimer = document.getElementById('lock-timer');

        if (!lockAlert || !lockTimer) return;

        lockAlert.style.display = 'flex';
        let remainingSeconds = minutes * 60;

        const interval = setInterval(() => {
            remainingSeconds--;
            const mins = Math.floor(remainingSeconds / 60);
            const secs = remainingSeconds % 60;

            lockTimer.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;

            if (remainingSeconds <= 0) {
                clearInterval(interval);
                lockAlert.style.display = 'none';
            }
        }, 1000);
    }

    // Check for lock status from server
    const lockDataEl = document.getElementById('lock-data');
    if (lockDataEl) {
        const lockMinutes = parseInt(lockDataEl.dataset.minutes);
        if (lockMinutes > 0) {
            startLockTimer(lockMinutes);
        }
    }

    // ====================
    // Keyboard Navigation
    // ====================

    document.addEventListener('keydown', function (e) {
        // Tab switching with arrow keys when focused on tabs
        if (document.activeElement.classList.contains('role-tab')) {
            const tabs = Array.from(roleTabs);
            const currentIndex = tabs.indexOf(document.activeElement);

            if (e.key === 'ArrowLeft' && currentIndex > 0) {
                e.preventDefault();
                tabs[currentIndex - 1].click();
                tabs[currentIndex - 1].focus();
            } else if (e.key === 'ArrowRight' && currentIndex < tabs.length - 1) {
                e.preventDefault();
                tabs[currentIndex + 1].click();
                tabs[currentIndex + 1].focus();
            }
        }
    });

    // ====================
    // Input Focus Effects
    // ====================

    const formInputs = document.querySelectorAll('.form-input');
    formInputs.forEach(input => {
        input.addEventListener('focus', function () {
            this.parentElement.classList.add('focused');
        });

        input.addEventListener('blur', function () {
            this.parentElement.classList.remove('focused');
        });
    });

    // Initialize tab indicator position
    if (tabIndicator) {
        tabIndicator.style.width = `calc(33.333% - 4px)`;
    }
}

// ====================
// Google OAuth
// ====================

function initiateGoogleLogin() {
    const role = document.getElementById('role-input').value;
    // Redirect to Google OAuth endpoint with role
    window.location.href = `/auth/google-login?role=${role}`;
}

// ====================
// Account Lock Check
// ====================

async function checkAccountLock(identifier) {
    try {
        const response = await fetch('/auth/check-lock', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name="csrf_token"]').value
            },
            credentials: 'include',
            body: JSON.stringify({ identifier })
        });

        const data = await response.json();

        if (data.is_locked) {
            const lockAlert = document.getElementById('account-locked-alert');
            const lockMessage = document.getElementById('lock-message');

            if (lockAlert && lockMessage) {
                lockMessage.innerHTML = `Account temporarily locked. Try again in <span id="lock-timer">${data.minutes_remaining}</span> minutes.`;
                lockAlert.style.display = 'flex';
                startLockTimer(data.minutes_remaining);
            }

            return true;
        }

        return false;
    } catch (error) {
        console.error('Error checking account lock:', error);
        return false;
    }
}

// ====================
// Remember Me Persistence
// ====================

(function () {
    const rememberCheckbox = document.getElementById('remember-me');
    const emailInput = document.getElementById('email-input');

    // Load saved email
    const savedEmail = localStorage.getItem('carepoint_remember_email');
    if (savedEmail && emailInput) {
        emailInput.value = savedEmail;
        if (rememberCheckbox) {
            rememberCheckbox.checked = true;
        }
    }

    // Save email on form submit
    const form = document.getElementById('login-form');
    if (form) {
        form.addEventListener('submit', function () {
            if (rememberCheckbox && rememberCheckbox.checked && emailInput) {
                localStorage.setItem('carepoint_remember_email', emailInput.value);
            } else {
                localStorage.removeItem('carepoint_remember_email');
            }
        });
    }
})();
