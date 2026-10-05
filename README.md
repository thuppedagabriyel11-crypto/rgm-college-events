# RGM College Events — Immersive Complete Portal

A Flask + MariaDB event-management portal for Rajeev Gandhi Memorial College of Engineering and Technology (Autonomous).

## What is included

- One login screen for everyone. Email/password determine the role automatically.
- Student registration, profile, event discovery, registration/cancellation, attendance, announcements and certificates.
- Organizer-only event management, approval workflow, participant/attendance management, announcements and certificate generation.
- Admin portal for users, event approvals, monitoring and reports.
- Responsive glassmorphism, soft UI/neomorphic depth, ambient glow, bento cards, cursor/magnetic micro-interactions, tilt, scroll reveal, scroll progress, command palette, optional Lenis/GSAP/Three.js enhancement and reduced-motion fallback.
- Optional event registration fees with two modes:
  - **Test purpose** — clicking Pay Registration Fee records a simulated successful payment.
  - **Real QR/UPI** — organizer enters a UPI ID and the portal generates an event-specific QR. The portal records a self-declared payment action and does not claim bank verification.
- Every recorded payment receives a unique payment reference and PDF fee receipt with event ID, event name, student, registration ID, amount, mode and timestamp.
- Supplied RGM certificate artwork is used as the master template. Student name, event title, event date and unique certificate ID are fitted into dedicated areas so they do not overlap the original artwork.
- Certificates are issued only after the event end date/time and only to students marked **Present**. Duplicate certificates are prevented.
- Public certificate verification route and QR code.
- Additive schema migration for older local MariaDB databases.

## Linux / Chromebook execution

```bash
cd ~/rgm_college_events
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl start mariadb
python -c "import app; print('APP DATABASE INITIALIZATION SUCCESS')"
python app.py
```

Open: `http://127.0.0.1:5000`

The application creates/updates its tables when imported.

## Default demo accounts

- Admin: `admin@rgmcollege.edu` / `Admin@12345`
- Organizer: `organizer@rgmcollege.edu` / `Organizer@12345`
- Student: `student@rgmcollege.edu` / `Student@12345`

Do not use these credentials in production.
