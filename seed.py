"""
ConnectED Seed Data Script
Run with: python manage.py shell < seed.py
Or:       python seed.py (if Django is configured)
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'connected.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import Profile, EmployerProfile
from universities.models import University
from challenges.models import Challenge, Submission
from notifications.models import Notification
from django.contrib.sites.models import Site

User = get_user_model()

print("🌱 Starting ConnectED seed...")


# ── 1. Fix Site record ──────────────────────────────────────────────────────
site, _ = Site.objects.get_or_create(pk=2)
site.domain = '127.0.0.1:8000'
site.name = 'ConnectED Local'
site.save()
print("✅ Site record fixed")


# ── 2. Universities ──────────────────────────────────────────────────────────
uok, _ = University.objects.get_or_create(
    name='University of Kabianga',
    defaults={
        'location': 'Kericho, Kenya',
        'email_domain': 'students.kabianga.ac.ke',
        'is_active': True,
    }
)

jkuat, _ = University.objects.get_or_create(
    name='Jomo Kenyatta University',
    defaults={
        'location': 'Juja, Kenya',
        'email_domain': 'students.jkuat.ac.ke',
        'is_active': True,
    }
)

ku, _ = University.objects.get_or_create(
    name='Kenyatta University',
    defaults={
        'location': 'Nairobi, Kenya',
        'email_domain': 'students.ku.ac.ke',
        'is_active': True,
    }
)

print(f"✅ Universities: {University.objects.count()} created")


# ── 3. Super Admin ───────────────────────────────────────────────────────────
if not User.objects.filter(username='superadmin').exists():
    super_admin = User.objects.create_user(
        username='superadmin',
        email='admin@connected.co.ke',
        password='Connected@2024',
        user_type='super_admin',
        is_staff=True,
        is_superuser=True,
    )
    Profile.objects.get_or_create(user=super_admin)
    print("✅ Super admin created — username: superadmin / password: Connected@2024")
else:
    print("⏭️  Super admin already exists")


# ── 4. Campus Admins ─────────────────────────────────────────────────────────
campus_admins_data = [
    {
        'username': 'admin_kabianga',
        'email': 'admin@kabianga.ac.ke',
        'university': uok,
    },
    {
        'username': 'admin_jkuat',
        'email': 'admin@jkuat.ac.ke',
        'university': jkuat,
    },
]

for data in campus_admins_data:
    if not User.objects.filter(username=data['username']).exists():
        ca = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password='Connected@2024',
            user_type='campus_admin',
        )
        profile, _ = Profile.objects.get_or_create(user=ca)
        profile.university = data['university']
        profile.onboarding_complete = True
        profile.save()

print(f"✅ Campus admins created")


# ── 5. Students ──────────────────────────────────────────────────────────────
students_data = [
    # UoK students
    {'username': 'alice_sw', 'email': 'alice@students.kabianga.ac.ke',
     'discipline': 'software_eng', 'year': 3, 'github': 'alice-dev',
     'reg': 'COM/001/2022', 'university': uok},

    {'username': 'brian_cs', 'email': 'brian@students.kabianga.ac.ke',
     'discipline': 'cybersecurity', 'year': 2, 'github': 'brian-sec',
     'reg': 'COM/002/2023', 'university': uok},

    {'username': 'carol_ds', 'email': 'carol@students.kabianga.ac.ke',
     'discipline': 'data_science', 'year': 3, 'github': 'carol-data',
     'reg': 'COM/003/2022', 'university': uok},

    {'username': 'david_net', 'email': 'david@students.kabianga.ac.ke',
     'discipline': 'networking', 'year': 1, 'github': 'david-net',
     'reg': 'COM/004/2024', 'university': uok},

    # JKUAT students
    {'username': 'eve_uiux', 'email': 'eve@students.jkuat.ac.ke',
     'discipline': 'ui_ux', 'year': 2, 'github': 'eve-design',
     'reg': 'SCT/001/2023', 'university': jkuat},

    {'username': 'frank_ml', 'email': 'frank@students.jkuat.ac.ke',
     'discipline': 'ai_ml', 'year': 4, 'github': 'frank-ml',
     'reg': 'SCT/002/2021', 'university': jkuat},

    # KU students
    {'username': 'grace_sw', 'email': 'grace@students.ku.ac.ke',
     'discipline': 'software_eng', 'year': 2, 'github': 'grace-codes',
     'reg': 'I101/001/2023', 'university': ku},

    {'username': 'henry_cs', 'email': 'henry@students.ku.ac.ke',
     'discipline': 'cybersecurity', 'year': 3, 'github': 'henry-sec',
     'reg': 'I101/002/2022', 'university': ku},
]

created_students = []
for data in students_data:
    if not User.objects.filter(username=data['username']).exists():
        student = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password='Connected@2024',
            user_type='student',
        )
        profile, _ = Profile.objects.get_or_create(user=student)
        profile.university = data['university']
        profile.discipline = data['discipline']
        profile.year_of_study = data['year']
        profile.github_username = data['github']
        profile.reg_number = data['reg']
        profile.onboarding_complete = True
        profile.save()
        created_students.append(student)

print(f"✅ Students: {len(created_students)} created")


# ── 6. Employer ──────────────────────────────────────────────────────────────
if not User.objects.filter(username='techcorp_hr').exists():
    employer = User.objects.create_user(
        username='techcorp_hr',
        email='hr@techcorp.co.ke',
        password='Connected@2024',
        user_type='employer',
    )
    EmployerProfile.objects.create(
        user=employer,
        company_name='TechCorp Kenya',
        company_email='hr@techcorp.co.ke',
        company_website='https://techcorp.co.ke',
        industry='Software & Fintech',
        is_verified=True,
    )
    print("✅ Employer created — username: techcorp_hr / password: Connected@2024")


# ── 7. Challenges ─────────────────────────────────────────────────────────────
challenges_data = [
    # Software Engineering
    {
        'title': 'Password Strength Checker',
        'description': 'Build a program that evaluates password strength.',
        'objective': 'Implement a function that checks password strength and returns Weak, Medium, or Strong.',
        'requirements': (
            'Accept a password from the user\n'
            'Check minimum length of 8 characters\n'
            'Check for uppercase and lowercase letters\n'
            'Check for numbers\n'
            'Check for special characters\n'
            'Return Weak, Medium, or Strong'
        ),
        'expected_skills': 'Python, conditionals, strings, functions',
        'submission_instructions': 'Submit a GitHub repository with your code and a README explaining your approach.',
        'discipline': 'software_eng',
        'difficulty': 'beginner',
        'min_year': 1,
        'points': 50,
        'allows_github': True,
        'track': 'software',
    },
    {
        'title': 'Student Grade Management System',
        'description': 'Build a CRUD application for managing student grades.',
        'objective': 'Create a web app that allows a teacher to add, view, update and delete student grades.',
        'requirements': (
            'User authentication (login/logout)\n'
            'Add new student records\n'
            'View all students with their grades\n'
            'Update existing grades\n'
            'Delete student records\n'
            'Calculate class average\n'
            'Responsive UI'
        ),
        'expected_skills': 'Django or Flask, PostgreSQL, HTML/CSS, CRUD operations',
        'submission_instructions': 'Submit GitHub repo with README, setup instructions, and screenshots.',
        'discipline': 'software_eng',
        'difficulty': 'intermediate',
        'min_year': 2,
        'points': 100,
        'allows_github': True,
        'track': 'software',
    },
    {
        'title': 'RESTful API for Campus Events',
        'description': 'Design and build a REST API for a campus events management system.',
        'objective': 'Build a production-ready API with proper authentication, validation, and documentation.',
        'requirements': (
            'JWT authentication\n'
            'CRUD endpoints for events\n'
            'User registration and login\n'
            'Event filtering by date and category\n'
            'API documentation (Swagger or Postman collection)\n'
            'Deployed and accessible via public URL'
        ),
        'expected_skills': 'Django REST Framework, JWT, API design, Postman',
        'submission_instructions': 'GitHub repo + deployed URL + Postman collection.',
        'discipline': 'software_eng',
        'difficulty': 'advanced',
        'min_year': 3,
        'points': 150,
        'allows_github': True,
        'allows_external_url': True,
        'track': 'software',
    },
    # Cybersecurity
    {
        'title': 'Identify Phishing Emails',
        'description': 'Analyze 5 provided email samples and identify which are phishing attempts.',
        'objective': 'Demonstrate understanding of phishing indicators and social engineering techniques.',
        'requirements': (
            'Analyze all 5 email samples\n'
            'Identify phishing vs legitimate emails\n'
            'Explain your reasoning for each\n'
            'List red flags you found\n'
            'Write a short guide on how to spot phishing'
        ),
        'expected_skills': 'Email security, social engineering awareness, technical writing',
        'submission_instructions': 'Submit a PDF report (max 5 pages) with your analysis.',
        'discipline': 'cybersecurity',
        'difficulty': 'beginner',
        'min_year': 1,
        'points': 60,
        'allows_file_upload': True,
        'allows_text': True,
        'track': 'software',
    },
    {
        'title': 'Network Vulnerability Scan Report',
        'description': 'Use Nmap to scan a provided test network and document findings.',
        'objective': 'Perform a basic network scan and produce a professional vulnerability report.',
        'requirements': (
            'Scan the provided test IP range using Nmap\n'
            'Identify open ports and services\n'
            'Classify vulnerabilities by severity (High/Medium/Low)\n'
            'Recommend remediation steps\n'
            'Write a professional penetration testing report'
        ),
        'expected_skills': 'Nmap, network security, report writing, CVE awareness',
        'submission_instructions': 'Submit PDF report + include your Nmap command outputs.',
        'discipline': 'cybersecurity',
        'difficulty': 'intermediate',
        'min_year': 2,
        'points': 120,
        'allows_file_upload': True,
        'allows_github': True,
        'track': 'software',
    },
    # Data Science
    {
        'title': 'Kenya Maize Price Prediction',
        'description': 'Build a machine learning model to predict maize prices in Kenyan markets.',
        'objective': 'Apply regression techniques to real Kenyan agricultural data.',
        'requirements': (
            'Use the provided Kenya maize prices dataset (CSV)\n'
            'Perform exploratory data analysis (EDA)\n'
            'Clean and preprocess the data\n'
            'Build at least 2 regression models\n'
            'Compare model performance (RMSE, R²)\n'
            'Visualize predictions vs actual prices\n'
            'Write conclusions and recommendations'
        ),
        'expected_skills': 'Python, Pandas, Scikit-learn, Matplotlib, regression',
        'submission_instructions': 'Submit Jupyter notebook (.ipynb) + dataset used + brief report PDF.',
        'discipline': 'data_science',
        'difficulty': 'intermediate',
        'min_year': 2,
        'points': 130,
        'allows_github': True,
        'allows_file_upload': True,
        'track': 'software',
    },
    # UI/UX Design
    {
        'title': 'Redesign a Kenyan Bank App',
        'description': 'Redesign the mobile UI for a Kenyan bank app with focus on accessibility.',
        'objective': 'Apply UX principles to improve usability for Kenyan mobile banking users.',
        'requirements': (
            'Research 2 existing Kenyan bank apps\n'
            'Identify usability problems\n'
            'Create user personas (2 minimum)\n'
            'Design wireframes (low fidelity)\n'
            'Create high fidelity prototype in Figma\n'
            'Include accessibility considerations\n'
            'Present before/after comparison'
        ),
        'expected_skills': 'Figma, UX research, wireframing, accessibility, user personas',
        'submission_instructions': 'Submit Figma link (view access) + PDF presentation of your process.',
        'discipline': 'ui_ux',
        'difficulty': 'intermediate',
        'min_year': 2,
        'points': 110,
        'allows_external_url': True,
        'allows_file_upload': True,
        'track': 'software',
    },
    # Networking
    {
        'title': 'Design a University Network Topology',
        'description': 'Design and simulate a complete network for a 3-building university campus.',
        'objective': 'Apply networking concepts to design a scalable campus network.',
        'requirements': (
            'Design network for 3 buildings (Admin, Library, Labs)\n'
            'Include VLANs for different departments\n'
            'Configure DHCP, DNS, and routing\n'
            'Implement basic security (ACLs, firewall rules)\n'
            'Simulate in Cisco Packet Tracer\n'
            'Document IP addressing scheme\n'
            'Test connectivity between all buildings'
        ),
        'expected_skills': 'Cisco Packet Tracer, VLANs, routing protocols, IP addressing, ACLs',
        'submission_instructions': 'Submit .pkt file + PDF network documentation with IP table.',
        'discipline': 'networking',
        'difficulty': 'intermediate',
        'min_year': 2,
        'points': 120,
        'allows_file_upload': True,
        'track': 'software',
    },
    # AI/ML
    {
        'title': 'Swahili Sentiment Analysis',
        'description': 'Build a sentiment analysis model for Swahili social media text.',
        'objective': 'Apply NLP techniques to an African language with limited training data.',
        'requirements': (
            'Collect or use provided Swahili tweets dataset\n'
            'Preprocess Swahili text (tokenization, stopwords)\n'
            'Build a classifier (positive/negative/neutral)\n'
            'Achieve minimum 70% accuracy\n'
            'Handle code-switching (Swahili + English)\n'
            'Visualize results with confusion matrix\n'
            'Discuss challenges of low-resource NLP'
        ),
        'expected_skills': 'Python, NLP, Scikit-learn or HuggingFace, data preprocessing',
        'submission_instructions': 'GitHub repo with notebook + PDF report on methodology.',
        'discipline': 'ai_ml',
        'difficulty': 'advanced',
        'min_year': 3,
        'points': 160,
        'allows_github': True,
        'allows_file_upload': True,
        'track': 'software',
    },
]

# Get a campus admin to be the challenge creator
try:
    challenge_creator = User.objects.get(username='admin_kabianga')
except User.DoesNotExist:
    challenge_creator = User.objects.filter(user_type='campus_admin').first()

created_challenges = []
for data in challenges_data:
    if not Challenge.objects.filter(title=data['title']).exists():
        challenge = Challenge.objects.create(
            title=data['title'],
            description=data['description'],
            objective=data.get('objective', ''),
            requirements=data.get('requirements', ''),
            expected_skills=data.get('expected_skills', ''),
            submission_instructions=data.get('submission_instructions', ''),
            discipline=data['discipline'],
            difficulty=data['difficulty'],
            min_year=data['min_year'],
            points=data['points'],
            track=data.get('track', 'software'),
            allows_github=data.get('allows_github', False),
            allows_file_upload=data.get('allows_file_upload', False),
            allows_external_url=data.get('allows_external_url', False),
            allows_text=data.get('allows_text', False),
            is_active=True,
            created_by=challenge_creator,
        )
        created_challenges.append(challenge)

print(f"✅ Challenges: {len(created_challenges)} created")


# ── 8. Sample Submissions (passed) for leaderboard ───────────────────────────
submissions_data = [
    ('alice_sw', 'Password Strength Checker', 'https://github.com/alice-dev/password-checker', 45),
    ('alice_sw', 'Student Grade Management System', 'https://github.com/alice-dev/grade-system', 90),
    ('brian_cs', 'Identify Phishing Emails', '', 55),
    ('carol_ds', 'Kenya Maize Price Prediction', 'https://github.com/carol-data/maize-predict', 120),
    ('frank_ml', 'Swahili Sentiment Analysis', 'https://github.com/frank-ml/swahili-nlp', 150),
    ('grace_sw', 'Password Strength Checker', 'https://github.com/grace-codes/pw-checker', 42),
    ('henry_cs', 'Identify Phishing Emails', '', 50),
    ('eve_uiux', 'Redesign a Kenyan Bank App', '', 100),
]

for username, challenge_title, github_url, score in submissions_data:
    try:
        student = User.objects.get(username=username)
        challenge = Challenge.objects.get(title=challenge_title)

        if not Submission.objects.filter(student=student, challenge=challenge).exists():
            sub = Submission.objects.create(
                student=student,
                challenge=challenge,
                github_url=github_url,
                external_url='https://figma.com/sample' if username == 'eve_uiux' else '',
                text_answer='Phishing analysis completed.' if not github_url and username in ['brian_cs', 'henry_cs'] else '',
                status='passed',
                score=score,
                feedback='Well done! Clean implementation with good documentation.',
            )
    except (User.DoesNotExist, Challenge.DoesNotExist):
        pass

print(f"✅ Sample submissions created")


# ── 9. Done ───────────────────────────────────────────────────────────────────
print("\n🎉 Seed complete!")
print("\nTest accounts (all password: Connected@2024):")
print("  superadmin       — Super Admin")
print("  admin_kabianga   — Campus Admin (UoK)")
print("  admin_jkuat      — Campus Admin (JKUAT)")
print("  alice_sw         — Student, Software Eng, Year 3, UoK")
print("  brian_cs         — Student, Cybersecurity, Year 2, UoK")
print("  carol_ds         — Student, Data Science, Year 3, UoK")
print("  david_net        — Student, Networking, Year 1, UoK")
print("  eve_uiux         — Student, UI/UX, Year 2, JKUAT")
print("  frank_ml         — Student, AI/ML, Year 4, JKUAT")
print("  grace_sw         — Student, Software Eng, Year 2, KU")
print("  henry_cs         — Student, Cybersecurity, Year 3, KU")
print("  techcorp_hr      — Employer (verified)")