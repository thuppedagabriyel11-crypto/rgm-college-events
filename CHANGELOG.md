# Changelog — Complete Updated Build

## 2026-10-05
- Replaced the previous certificate artwork with the newly supplied RGM Certificate of Participation template.
- Certificate renderer now inserts student name, event title, event date and unique certificate ID into isolated regions with font fitting.
- Certificate generation remains locked until the event end date/time and requires Present attendance.
- Added automatic eligible-certificate generation when attendance is saved after event completion and dashboard/event workflows run after completion.
- Reworked authentication to one public login field; role portals are never selected explicitly in the login UI.
- Added optional event registration-fee configuration: fee enabled, amount, test mode or real QR/UPI mode, UPI ID and payment instructions.
- Added generated event-specific UPI QR for real payment mode.
- Added student payment action and unique PDF fee receipt.
- Added payment status/reference fields to event registrations and payment visibility for organizer/admin.
- Added additive MariaDB schema migration for older databases.
- Upgraded visual layer with glass/frosted panels, soft UI depth, ambient glow, bento architecture, 3D tilt, magnetic cursor, liquid button feedback, click particles, scroll progress, command palette, Lenis/GSAP/Three.js progressive enhancement and responsive/reduced-motion fallbacks.
