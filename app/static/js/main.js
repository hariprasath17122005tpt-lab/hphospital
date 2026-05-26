/* ═══════════════════════════════════════════════════════════
   CAREPOINT — PREMIUM DASHBOARD JAVASCRIPT
   Animations, Counters, Theme Toggle, Notifications
   ═══════════════════════════════════════════════════════════ */

const safeStorage = {
    getItem: (key) => {
        try {
            return localStorage.getItem(key);
        } catch (e) {
            console.warn('Storage read error', e);
            return null;
        }
    },
    setItem: (key, value) => {
        try {
            localStorage.setItem(key, value);
        } catch (e) {
            console.warn('Storage write error', e);
        }
    },
    get(key) {
        return this.getItem(key);
    },
    set(key, value) {
        this.setItem(key, value);
    }
};

document.addEventListener('DOMContentLoaded', function () {
    const initializers = [
        ['Tooltips', initTooltips],
        ['Popovers', initPopovers],
        ['Progress bars', initProgressBars],
        ['Appointment buttons', initAppointmentButtons],
        ['Theme init', initThemeToggle],
        ['Notifications', initNotificationDropdown],
        ['Scroll animations', initScrollAnimations],
        ['Animated counters', initAnimatedCounters],
        ['Sidebar collapse', initSidebarCollapse],
        ['Command palette', initCommandPalette]
    ];

    initializers.forEach(([name, fn]) => {
        try {
            fn();
        } catch (e) {
            console.error(`${name} failed:`, e);
        }
    });
});

/* ─── TOOLTIPS & POPOVERS ──────────────────────────────────── */
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (el) { return new bootstrap.Tooltip(el); });
}

function initPopovers() {
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (el) { return new bootstrap.Popover(el); });
}

/* ─── PROGRESS BARS ─────────────────────────────────────────── */
function initProgressBars() {
    const progressBars = document.querySelectorAll('[role="progressbar"][aria-valuenow]');
    progressBars.forEach(bar => {
        const value = parseFloat(bar.getAttribute('aria-valuenow')) || 0;
        const maxValue = parseFloat(bar.getAttribute('aria-valuemax')) || 100;
        const percentage = (value / maxValue) * 100;
        bar.style.width = '0%';
        setTimeout(() => {
            bar.style.transition = 'width 1.2s cubic-bezier(0.16, 1, 0.3, 1)';
            bar.style.width = percentage + '%';
        }, 300);
    });
}

/* ─── APPOINTMENT BUTTONS ───────────────────────────────────── */
function initAppointmentButtons() {
    document.querySelectorAll('.approve-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const id = this.getAttribute('data-appointment-id');
            approveAppointment(id);
        });
    });

    document.querySelectorAll('.reject-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const id = this.getAttribute('data-appointment-id');
            rejectAppointment(id);
        });
    });
}

/* ─── DARK/LIGHT MODE TOGGLE ────────────────────────────────── */
function initThemeToggle() {
    const themeBtn = document.getElementById('themeToggleBtn');
    const root = document.documentElement;

    // Read current theme from data-theme attribute (set by inline script in <head>)
    function getCurrentTheme() {
        return root.getAttribute('data-theme') || 'light';
    }

    // Apply theme
    function applyTheme(theme) {
        root.setAttribute('data-theme', theme);
        safeStorage.set('cp-theme', theme);
        if (themeBtn) {
            themeBtn.innerHTML = theme === 'dark'
                ? '<i class="fas fa-sun"></i>'
                : '<i class="fas fa-moon"></i>';
        }
    }

    // Set initial icon based on current theme
    var currentTheme = getCurrentTheme();
    if (themeBtn) {
        themeBtn.innerHTML = currentTheme === 'dark'
            ? '<i class="fas fa-sun"></i>'
            : '<i class="fas fa-moon"></i>';
    }

    // Toggle on click
    if (themeBtn) {
        themeBtn.addEventListener('click', function() {
            var newTheme = getCurrentTheme() === 'dark' ? 'light' : 'dark';

            // Animate icon change
            themeBtn.style.transform = 'rotate(360deg) scale(0)';
            setTimeout(function() {
                applyTheme(newTheme);
                themeBtn.style.transform = 'rotate(0deg) scale(1)';
            }, 200);

            window.dispatchEvent(new Event('themeChanged'));
        });
    }

    // Listen for OS theme changes
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
            // Only auto-switch if user hasn't manually set a preference
            var saved = safeStorage.get('cp-theme');
            if (!saved) {
                applyTheme(e.matches ? 'dark' : 'light');
            }
        });
    }
}

/* ─── NOTIFICATION DROPDOWN ─────────────────────────────────── */
function initNotificationDropdown() {
    const notifBtn = document.getElementById('notifBellBtn');
    const notifDropdown = document.getElementById('notifDropdown');
    const markReadBtn = document.getElementById('markAllRead');

    if (notifBtn && notifDropdown) {
        notifBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            notifDropdown.classList.toggle('show');

            // Animate bell
            notifBtn.style.transform = 'rotate(-15deg)';
            setTimeout(() => { notifBtn.style.transform = 'rotate(10deg)'; }, 100);
            setTimeout(() => { notifBtn.style.transform = 'rotate(0deg)'; }, 200);
        });

        document.addEventListener('click', (e) => {
            if (!notifDropdown.contains(e.target) && !notifBtn.contains(e.target)) {
                notifDropdown.classList.remove('show');
            }
        });

        if (markReadBtn) {
            markReadBtn.addEventListener('click', (e) => {
                e.preventDefault();
                document.querySelectorAll('.notif-item.unread').forEach(item => {
                    item.style.transition = 'all 0.3s ease';
                    item.style.opacity = '0.5';
                    setTimeout(() => {
                        item.classList.remove('unread');
                        item.style.opacity = '1';
                    }, 300);
                });
                const dot = notifBtn.querySelector('.notif-dot');
                if (dot) {
                    dot.style.transition = 'all 0.3s ease';
                    dot.style.transform = 'scale(0)';
                    setTimeout(() => { dot.style.display = 'none'; }, 300);
                }
            });
        }

        refreshTopbarNotifications();
    }
}

async function refreshTopbarNotifications() {
    const notifList = document.querySelector('.notif-list');
    const notifBtn = document.getElementById('notifBellBtn');
    if (!notifList || !notifBtn) return;

    // Only fetch doctor notifications if the current user is a doctor
    const topbar = document.querySelector('.app-topbar');
    const userRole = topbar ? topbar.getAttribute('data-user-role') : '';
    if (userRole !== 'DOCTOR') {
        notifList.innerHTML = '<div class="notif-item"><div class="notif-item-info"><div class="notif-item-text">No new notifications</div></div></div>';
        const dot = notifBtn.querySelector('.notif-dot');
        if (dot) dot.style.display = 'none';
        return;
    }

    try {
        const response = await fetch('/doctor/api/portal/summary', { credentials: 'include' });
        const data = await response.json();
        const items = (data.notifications || []).slice(0, 6);

        if (!items.length) {
            notifList.innerHTML = '<div class="notif-item"><div class="notif-item-info"><div class="notif-item-text">No new notifications</div></div></div>';
        } else {
            notifList.innerHTML = items.map(n => {
                const sev = (n.severity || 'info').toLowerCase();
                const icon = sev === 'warning' ? 'fa-exclamation-triangle' : sev === 'danger' ? 'fa-bell' : 'fa-info-circle';
                return `
                    <div class="notif-item ${sev !== 'info' ? 'unread' : ''}">
                      <div class="notif-item-icon ${sev}"><i class="fas ${icon}"></i></div>
                      <div class="notif-item-info">
                        <div class="notif-item-text">${n.message || 'Update available'}</div>
                        <div class="notif-item-time">${n.time || ''}</div>
                      </div>
                    </div>`;
            }).join('');
        }

        const unreadCount = items.filter(n => n.severity && n.severity !== 'info').length;
        const dot = notifBtn.querySelector('.notif-dot');
        if (dot) {
            if (unreadCount > 0) {
                dot.style.display = 'inline-block';
                dot.style.transform = 'scale(1)';
            } else {
                dot.style.display = 'none';
            }
        }
    } catch (error) {
        console.warn('Unable to refresh topbar notifications', error);
    }

    // poll updates every minute
    setTimeout(refreshTopbarNotifications, 60000);
}

/* ─── SCROLL-TRIGGERED ANIMATIONS ───────────────────────────── */
function initScrollAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                // Trigger counter animation if present
                const counters = entry.target.querySelectorAll('[data-count-to]');
                counters.forEach(el => animateCounter(el));
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    document.querySelectorAll('.animate-on-scroll, .pd-animate').forEach(el => {
        observer.observe(el);
    });
}

/* ─── ANIMATED NUMBER COUNTERS ──────────────────────────────── */
function initAnimatedCounters() {
    document.querySelectorAll('[data-count-to]').forEach(el => {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        observer.observe(el);
    });
}

function animateCounter(el) {
    if (el.dataset.counted) return;
    el.dataset.counted = 'true';

    const target = parseFloat(el.dataset.countTo);
    const duration = parseInt(el.dataset.countDuration) || 1500;
    const decimals = (el.dataset.countDecimals) ? parseInt(el.dataset.countDecimals) : 0;
    const start = parseFloat(el.textContent) || 0;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Ease out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = start + (target - start) * eased;

        el.textContent = decimals > 0 ? current.toFixed(decimals) : Math.round(current);

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

/* ─── SIDEBAR COLLAPSE PERSISTENCE ──────────────────────────── */
function initSidebarCollapse() {
    const sidebar = document.getElementById('appSidebar');
    if (sidebar && safeStorage.get('sidebar-collapsed') === 'true') {
        sidebar.classList.add('collapsed');
    }
}

/* ─── API HELPER ────────────────────────────────────────────── */
async function makeRequest(url, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include'
        };
        if (data) options.body = JSON.stringify(data);
        const response = await fetch(url, options);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('Request failed:', error);
        throw error;
    }
}

/* ─── MESSAGING ─────────────────────────────────────────────── */
function sendMessage(doctorId) {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();
    if (message === '') { alert('Please enter a message'); return; }

    makeRequest(`/patient/api/send-message/${doctorId}`, 'POST', { message: message })
        .then(response => { if (response.success) { messageInput.value = ''; location.reload(); } })
        .catch(error => console.error('Error sending message:', error));
}

/* ─── DOCTOR FUNCTIONS ──────────────────────────────────────── */
function approveAppointment(appointmentId) {
    makeRequest(`/doctor/appointments/${appointmentId}/approve`, 'POST')
        .then(response => { if (response.success) location.reload(); })
        .catch(error => console.error('Error approving appointment:', error));
}

function rejectAppointment(appointmentId) {
    if (confirm('Are you sure you want to reject this appointment?')) {
        makeRequest(`/doctor/appointments/${appointmentId}/reject`, 'POST')
            .then(response => { if (response.success) location.reload(); })
            .catch(error => console.error('Error rejecting appointment:', error));
    }
}

function completeAppointment(appointmentId) {
    makeRequest(`/doctor/appointments/${appointmentId}/complete`, 'POST')
        .then(response => { if (response.success) location.reload(); })
        .catch(error => console.error('Error completing appointment:', error));
}

function doctorSendMessage(patientId) {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();
    if (message === '') { alert('Please enter a message'); return; }

    makeRequest(`/doctor/api/send-message/${patientId}`, 'POST', { message: message })
        .then(response => { if (response.success) { messageInput.value = ''; location.reload(); } })
        .catch(error => console.error('Error sending message:', error));
}

/* ─── UTILITY ───────────────────────────────────────────────── */
function showAlert(message, type = 'info') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert" style="animation: slideDown 0.4s ease;">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    const alertContainer = document.querySelector('[data-alert-container]') || document.querySelector('.flash-container') || document.body;
    alertContainer.insertAdjacentHTML('beforeend', alertHtml);
}

/* —— QUICK COMMAND PALETTE (CTRL+K) —— */
function initCommandPalette() {
    const root = document.getElementById('cpCommandPalette');
    const input = document.getElementById('cpCommandInput');
    const list = document.getElementById('cpCommandList');
    const links = Array.isArray(window.cpQuickLinks) ? window.cpQuickLinks : [];
    if (!root || !input || !list || !links.length) return;

    let activeIndex = 0;
    let filtered = links.slice();

    function render() {
        list.innerHTML = '';
        if (!filtered.length) {
            list.innerHTML = '<div class="cp-command-item"><span>No matches found.</span></div>';
            return;
        }
        filtered.forEach((item, idx) => {
            const a = document.createElement('a');
            a.className = 'cp-command-item' + (idx === activeIndex ? ' active' : '');
            a.href = item.url;
            a.innerHTML = `<span>${item.name}</span><small>${item.hint || ''}</small>`;
            list.appendChild(a);
        });
    }

    function openPalette() {
        root.classList.add('open');
        root.setAttribute('aria-hidden', 'false');
        input.value = '';
        filtered = links.slice();
        activeIndex = 0;
        render();
        setTimeout(() => input.focus(), 0);
    }

    function closePalette() {
        root.classList.remove('open');
        root.setAttribute('aria-hidden', 'true');
    }

    function move(delta) {
        if (!filtered.length) return;
        activeIndex = (activeIndex + delta + filtered.length) % filtered.length;
        render();
    }

    document.addEventListener('keydown', function (e) {
        const isOpen = root.classList.contains('open');
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            isOpen ? closePalette() : openPalette();
            return;
        }
        if (!isOpen) return;
        if (e.key === 'Escape') {
            e.preventDefault();
            closePalette();
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            move(1);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            move(-1);
        } else if (e.key === 'Enter' && filtered[activeIndex]) {
            window.location.href = filtered[activeIndex].url;
        }
    });

    input.addEventListener('input', function () {
        const q = input.value.trim().toLowerCase();
        filtered = links.filter(item =>
            item.name.toLowerCase().includes(q) ||
            (item.hint || '').toLowerCase().includes(q)
        );
        activeIndex = 0;
        render();
    });

    root.addEventListener('click', function (e) {
        const target = e.target;
        if (target.closest('[data-cp-close]')) closePalette();
    });
}

function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    return new Date(dateString).toLocaleDateString('en-US', options);
}
