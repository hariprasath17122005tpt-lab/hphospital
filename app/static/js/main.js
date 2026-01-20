// Main JavaScript functions

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initTooltips();
    
    // Initialize popovers
    initPopovers();
    
    // Initialize progress bars
    initProgressBars();
    
    // Initialize appointment buttons
    initAppointmentButtons();
});

function initAppointmentButtons() {
    // Approve appointment buttons
    document.querySelectorAll('.approve-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const appointmentId = this.getAttribute('data-appointment-id');
            approveAppointment(appointmentId);
        });
    });
    
    // Reject appointment buttons
    document.querySelectorAll('.reject-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const appointmentId = this.getAttribute('data-appointment-id');
            rejectAppointment(appointmentId);
        });
    });
}

function initProgressBars() {
    // Set width for progress bars from aria-valuenow
    const progressBars = document.querySelectorAll('[role="progressbar"][aria-valuenow]');
    progressBars.forEach(bar => {
        const value = parseFloat(bar.getAttribute('aria-valuenow')) || 0;
        const maxValue = parseFloat(bar.getAttribute('aria-valuemax')) || 100;
        const percentage = (value / maxValue) * 100;
        bar.style.width = percentage + '%';
    });
}

function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function initPopovers() {
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// API Helper
async function makeRequest(url, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Request failed:', error);
        throw error;
    }
}

// Send message function for chat
function sendMessage(doctorId) {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();

    if (message === '') {
        alert('Please enter a message');
        return;
    }

    makeRequest(`/patient/api/send-message/${doctorId}`, 'POST', { message: message })
        .then(response => {
            if (response.success) {
                messageInput.value = '';
                location.reload(); // Reload to show new message
            }
        })
        .catch(error => console.error('Error sending message:', error));
}

// Doctor functions
function approveAppointment(appointmentId) {
    makeRequest(`/doctor/appointments/${appointmentId}/approve`, 'POST')
        .then(response => {
            if (response.success) {
                location.reload();
            }
        })
        .catch(error => console.error('Error approving appointment:', error));
}

function rejectAppointment(appointmentId) {
    if (confirm('Are you sure you want to reject this appointment?')) {
        makeRequest(`/doctor/appointments/${appointmentId}/reject`, 'POST')
            .then(response => {
                if (response.success) {
                    location.reload();
                }
            })
            .catch(error => console.error('Error rejecting appointment:', error));
    }
}

function completeAppointment(appointmentId) {
    makeRequest(`/doctor/appointments/${appointmentId}/complete`, 'POST')
        .then(response => {
            if (response.success) {
                location.reload();
            }
        })
        .catch(error => console.error('Error completing appointment:', error));
}

// Doctor send message
function doctorSendMessage(patientId) {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();

    if (message === '') {
        alert('Please enter a message');
        return;
    }

    makeRequest(`/doctor/api/send-message/${patientId}`, 'POST', { message: message })
        .then(response => {
            if (response.success) {
                messageInput.value = '';
                location.reload();
            }
        })
        .catch(error => console.error('Error sending message:', error));
}

// Utility function to show alerts
function showAlert(message, type = 'info') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    const alertContainer = document.querySelector('[data-alert-container]') || document.body;
    alertContainer.insertAdjacentHTML('beforeend', alertHtml);
}

// Format date
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    return new Date(dateString).toLocaleDateString('en-US', options);
}
