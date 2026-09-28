# ConnectED

> **The campus talent pipeline for Kenyan university students.**

ConnectED is a Django-powered platform that bridges the gap between university training and employer expectations. Students complete GitHub-verified technical challenges, build discipline-specific portfolios, compete on leaderboards, and get discovered by employers — all within a university-managed ecosystem.

---

## The Problem

Kenya's tech graduates enter the job market with theoretical knowledge but no verified practical experience. Employers consistently report graduates cannot demonstrate real-world skills. ConnectED gives students a structured, campus-integrated environment to build and verify those skills from Year 1.

---

## Who It's For

| User | Role |
|---|---|
| **Students** | Complete challenges, build portfolios, climb leaderboards |
| **Campus Admins** | Create challenges, review submissions, facilitate employer connections |
| **Super Admins** | Manage universities, verify employers, oversee the platform |
| **Employers** | Discover verified talent, express interest, sponsor challenges |

---

## Features

### Students
- Register with university email (domain-validated per institution)
- Complete onboarding (year, discipline, GitHub username, reg number)
- Browse challenges filtered by discipline
- Submit via GitHub, external URL (Figma, Wokwi), file upload (PDF, IPYNB, PKT, ZIP), or written answer
- Receive feedback and scores from reviewers
- Compete on leaderboards scoped by campus, discipline, year, or globally
- Get notified in-platform and by email when submissions are reviewed or new challenges are posted
- Settings: dark mode, font size, notification preferences, password change

### Campus Admins
- Manage challenges with structured fields (objective, requirements, expected skills, submission types)
- Review student submissions with scores and feedback
- View campus-specific student lists and statistics
- Get notified when students submit and when employers express interest
- Forward employer interest to students

### Super Admins
- Add and manage universities (with email domain for registration gating)
- Create campus admin accounts
- Verify or reject employer registrations
- View platform-wide statistics
- Get notified on new employer registrations and sponsorship inquiries

### Employers
- Register and await verification
- Browse the student leaderboard with discipline/year filters
- Express interest in specific students (routed through campus admin)
- Submit sponsorship inquiries for challenges
- Manage company profile and track interest requests

---

## Tech Stack

 Layer & Technology 

 Backend > Python 3.12, Django 6.1 
 Database > PostgreSQL (production), SQLite (development) 
 Frontend > Bootstrap 5, Vanilla JS 
 File Storage > Cloudinary (profile images), Local/Railway (submission files) 
 Email > Gmail SMTP via django.core.mail 
 Auth > Django auth + django-allauth (GitHub OAuth) 
 Rate Limiting > django-ratelimit 
 Deployment > Railway 

---

## Project Structure

```
connected/
├── connected/          # Project settings and root URLs
├── accounts/           # User model, auth, profile, settings
├── universities/       # University model and management
├── challenges/         # Challenges, submissions, file handling, employer interest
├── dashboard/          # Home, onboarding, leaderboard, employer dashboard
├── notifications/      # In-platform notifications and context processor
├── core/               # Public landing page, error handlers
├── management/         # Admin panels (super admin + campus admin)
├── templates/          # All HTML templates
├── static/             # CSS and JS
├── media/              # Uploaded files (local dev)
├── seed.py             # Sample data for development/demo
└── requirements.txt
```

---

## Disciplines Supported

- Software Engineering
- Cybersecurity
- Data Science / AI
- UI/UX Design
- Networking
- AI / Machine Learning
- Electrical Engineering
- Mechanical Engineering
- Civil Engineering
- Computer Engineering
- Agricultural Engineering

---

## Submission Types

Type & Allowed Files 

 GitHub Repository for Software, Cybersecurity, Data Science, AI/ML 
 External URL for UI/UX (Figma), Hardware (Wokwi/Tinkercad), Demo videos 
 File Upload for Networking (.pkt), Data Science (.ipynb, .csv), Reports (.pdf, .docx)  PDF, DOCX, PNG, JPG, IPYNB, CSV, PKT, ZIP (max 10MB) 
 Written Answer for Analysis, reflections, short-form responses 

---

## Getting Started (Local Development)

### Prerequisites
- Python 3.12+
- PostgreSQL
- Git

### Setup

```bash

git clone https://github.com/Decimalzero-dot/ConnectED
cd connected

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your values

# Run migrations
python manage.py migrate

# Load sample data
python seed.py

# Create your superuser (or use seed.py's superadmin account)
python manage.py createsuperuser

# Start the server
python manage.py runserver
```

### Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True

DATABASE_URL=postgresql://user:password@localhost/connected_db

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password

GITHUB_CLIENT_ID=your-github-oauth-client-id
GITHUB_CLIENT_SECRET=your-github-oauth-secret
```

---

## Security

- University email domain validation on registration
- Rate limiting on login (5/min), register (3/min), password reset (3/min)
- Session expiry (1 hour inactivity + browser close)
- CSRF protection on all forms
- File upload validation (extension + MIME type + 10MB limit)
- Randomized stored filenames for uploaded files
- Authorization checks on file downloads (IDOR prevention)
- Custom error pages (400, 403, 404, 429, 500)
- Django admin URL obscured
- Security headers (XSS filter, content type nosniff, X-Frame-Options)
- HTTPS-only cookies and HSTS in production

---

## Roadmap

### Phase 2 — Collaboration
- Cross-campus team formation for projects
- Shared project workspaces
- Peer code review within teams

### Phase 3 — Mentorship
- Senior student / alumni mentor matching
- Structured mentorship tracks per discipline
- Mentorship session scheduling

### Phase 4 — Employer Integration
- Direct employer-to-student messaging (post university-mediated phase)
- Verified internship and attachment listings
- Sponsored challenge tracks with employer branding

### Phase 5 — AI-Assisted Review
- GitHub repo analysis for automated feedback suggestions
- Reviewer dashboard with AI-suggested scores
- Plagiarism and AI-generated code detection

---

## Contributing

This project is currently in active development for the NEIL Africa Campus Spark 2026 competition. Contribution guidelines will be added post-launch.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Built By

Daniel — Computer Science student, University of Kabianga, Kenya.  
Advised by Mrs. Sarah, University of Kabianga.

*ConnectED — Build real skills. Get verified. Get discovered.*