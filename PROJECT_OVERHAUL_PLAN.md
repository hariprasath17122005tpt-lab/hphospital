# Hospital Management System - Project Overhaul Plan

This document tracks the progress of finalizing the HMS application to production quality.

## 1. Remove Hardcoded Data (DB Integration)
- [x] **Pharmacy Module**: Replace hardcoded inventory list with `Medicine` model and DB queries.
- [x] **Blood Bank Module**: Replace hardcoded blood stock with `BloodInventory` model and DB queries.
- [ ] **Hospital Operations**: Replace hardcoded bed/ward data with `Bed` model.
- [ ] **Doctor Schedule**: Replace hardcoded events with `DoctorSchedule` model.
- [ ] **Nurse Tasks**: Replace hardcoded task list with `NurseTask` model.
- [ ] **HR & Payroll**: Replace hardcoded staff stats with dynamic counts from `User`/`Staff` models.

## 2. End-to-End Testing & UI Fixes
- [x] **Doctor Registration**: Fixed registration code flow and field validation.
- [x] **Appointment Approval**: Fixed "Approve/Reject" buttons with CSRF protection and JS logic.
- [ ] **Patient Dashboard**: Verify all links (Bills, Lab Reports, Prescriptions) work with real data.
- [ ] **Doctor Dashboard**: Verify "Pending Requests" processing fully updates status.
- [ ] **Lab Reports**: Implement actual file upload and status tracking.
- [ ] **Billing**: Implement "Pay Now" flow (mock) and status updates.

## 3. Patient Communication (Notifications)
- [ ] **Email Integration**: Setup `Flask-Mail` or similar for transactional emails.
- [ ] **SMS Integration**: Setup mock SMS service if Twilio keys absent.
- [ ] **Triggers**:
    - Appointment Confirmation
    - Appointment Reminder (24h before)
    - Lab Result Ready
    - Bill Generated

## 4. Role-Based Access Control (RBAC)
- [x] **Basic Decorators**: `doctor_required`, `patient_required` already exist.
- [ ] **Audit**: Verify no horizontal escalation (Patient A viewing Patient B's data).
- [ ] **Admin Panel**: Ensure only Admins can manage doctors/users.

## 5. Automated Testing
- [ ] **Unit Tests**: Add tests for Models (`test_models.py`).
- [ ] **Integration Tests**: Add tests for Routes (`test_routes.py`).
- [ ] **E2E Tests**: Add Playwright/Selenium scripts for critical flows.

## 6. Deployment & Docs
- [ ] **Config**: Ensure all secrets are env variables.
- [ ] **Seeders**: Ensure robust seeding scripts for demo data.
- [ ] **Documentation**: Updated `README.md` with full setup instructions.

---

### Current Status
- **Date**: 2025-12-12
- **Completed**: Pharmacy & Blood Bank DB integration, Appointment Button Fixes.
- **Next Steps**: Hospital Operations & Doctor Schedule DB integration.
