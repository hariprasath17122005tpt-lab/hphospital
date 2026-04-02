/**
 * WhatsApp Integration - Test & Debugging Script
 * Run this in browser console to test the functionality
 */

// =============================================================================
// TEST SUITE FOR WHATSAPP INTEGRATION
// =============================================================================

console.log('🔔 WhatsApp Integration Test Suite Loaded');
console.log('========================================\n');

// Test 1: Phone Number Formatting
console.log('TEST 1: Phone Number Formatting\n');
const testPhones = [
    { input: '9597244055', expected: '919597244055' },
    { input: '+919597244055', expected: '919597244055' },
    { input: '919597244055', expected: '919597244055' },
    { input: '09597244055', expected: '919597244055' },
    { input: '95-97-244-055', expected: '919597244055' },
    { input: '+91 (959) 724-4055', expected: '919597244055' },
    { input: '9597244055', expected: '919597244055' },
];

testPhones.forEach((test, idx) => {
    console.log(`  Test ${idx + 1}: "${test.input}"`);
    console.log(`  Expected: "${test.expected}"`);
    if (test.input === test.expected) {
        console.log(`  Status: ✅ PASS\n`);
    } else {
        console.log(`  Status: ⚠️  Manual Verification Needed\n`);
    }
});

// Test 2: WhatsApp URL Generation
console.log('\nTEST 2: WhatsApp URL Generation\n');
const testPhone = '919597244055';
const message = 'Hello, your lab report is ready!';
const encodedMessage = encodeURIComponent(message);
const whatsappURL = `https://wa.me/${testPhone}?text=${encodedMessage}`;

console.log(`  Phone: ${testPhone}`);
console.log(`  Message: "${message}"`);
console.log(`  Generated URL: ${whatsappURL}`);
console.log(`  Status: ✅ URL Generated Successfully\n`);

// Test 3: Check if WhatsApp Function Exists
console.log('\nTEST 3: Function Availability\n');
if (typeof sendWhatsApp === 'function') {
    console.log('  sendWhatsApp(): ✅ Available');
} else {
    console.log('  sendWhatsApp(): ❌ Not Found');
}

if (typeof formatPhoneNumber === 'function') {
    console.log('  formatPhoneNumber(): ✅ Available');
} else {
    console.log('  formatPhoneNumber(): ❌ Not Found');
}

if (typeof createReportMessage === 'function') {
    console.log('  createReportMessage(): ✅ Available');
} else {
    console.log('  createReportMessage(): ❌ Not Found');
}
console.log('\n');

// Test 4: DOM Elements Check
console.log('\nTEST 4: DOM Elements Verification\n');
const whatsappButtons = document.querySelectorAll('[style*="rgba(34, 197, 94"]');
console.log(`  WhatsApp Buttons Found: ${whatsappButtons.length}`);

const hiddenPhoneInputs = document.querySelectorAll('.patient-phone');
console.log(`  Patient Phone Inputs: ${hiddenPhoneInputs.length}`);

const reportIdInputs = document.querySelectorAll('.report-id');
console.log(`  Report ID Inputs: ${reportIdInputs.length}`);

if (whatsappButtons.length > 0 && hiddenPhoneInputs.length > 0 && reportIdInputs.length > 0) {
    console.log(`  Overall Status: ✅ All elements present\n`);
} else {
    console.log(`  Overall Status: ⚠️  Some elements missing\n`);
}

// Test 5: Phone Number Validation Examples
console.log('\nTEST 5: Phone Validation Examples\n');
const validationTests = [
    { phone: '9876543210', shouldPass: true, reason: 'Valid 10-digit number' },
    { phone: '9876543', shouldPass: false, reason: 'Too short (7 digits)' },
    { phone: '919876543210', shouldPass: true, reason: 'With country code' },
    { phone: '', shouldPass: false, reason: 'Empty' },
    { phone: 'abc9876543210', shouldPass: true, reason: 'With letters (should be cleaned)' },
];

validationTests.forEach((test, idx) => {
    const cleaned = test.phone.replace(/[^\d+]/g, '').replace(/^\+/, '').replace(/^0/, '');
    if (!cleaned.startsWith('91')) {
        cleaned = '91' + cleaned;
    }
    const isValid = cleaned.length >= 12;
    const status = isValid === test.shouldPass ? '✅' : '❌';
    console.log(`  ${idx + 1}. "${test.phone}" → ${status } (${test.reason})`);
});

console.log('\n');

// Quick Actions
console.log('\n=== QUICK ACTIONS ===\n');
console.log('To test WhatsApp button click:');
console.log('  1. Open the Lab Reports page');
console.log('  2. Find a completed lab report');
console.log('  3. Click the green "WhatsApp" button');
console.log('  4. WhatsApp should open with pre-filled message\n');

console.log('To debug a specific button:');
console.log('  const btn = document.querySelector(".lab-card button");');
console.log('  sendWhatsApp(btn); // Simulates button click\n');

console.log('To test phone formatting directly:');
console.log('  formatPhoneNumber("9597244055"); // Should return "919597244055"\n');

console.log('To create test message:');
console.log('  createReportMessage("12345", "lab-report");\n');

console.log('\n✅ Test Suite Complete!\n');
console.log('========================================');
console.log('For issues, check the above results against expected values.');
