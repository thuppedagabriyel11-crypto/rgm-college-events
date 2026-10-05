import os
import uuid
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, func, inspect, text, Numeric
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont
import qrcode

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'rgm-dev-secret-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///' + str(BASE_DIR / 'rgm_events.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024

db = SQLAlchemy(app)
CERT_DIR = BASE_DIR / 'static' / 'certificates'
RECEIPT_DIR = BASE_DIR / 'static' / 'receipts'
PAYMENT_QR_DIR = BASE_DIR / 'static' / 'payment_qr'
for _d in (CERT_DIR, RECEIPT_DIR, PAYMENT_QR_DIR):
    _d.mkdir(parents=True, exist_ok=True)
APP_TIMEZONE = ZoneInfo(os.getenv('APP_TIMEZONE', 'Asia/Kolkata'))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default='student', index=True)
    student_id = db.Column(db.String(80), unique=True, nullable=True)
    department = db.Column(db.String(120), nullable=True)
    year = db.Column(db.String(40), nullable=True)
    phone = db.Column(db.String(40), nullable=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    category = db.Column(db.String(100), nullable=False, default='General')
    description = db.Column(db.Text, nullable=False)
    event_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.String(20), nullable=False)
    end_time = db.Column(db.String(20), nullable=False)
    venue = db.Column(db.String(200), nullable=False)
    registration_start = db.Column(db.Date, nullable=False)
    registration_deadline = db.Column(db.Date, nullable=False)
    max_participants = db.Column(db.Integer, nullable=False, default=100)
    rules = db.Column(db.Text, nullable=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default='pending', index=True)
    banner = db.Column(db.String(255), nullable=True)
    fee_enabled = db.Column(db.Boolean, nullable=False, default=False)
    fee_amount = db.Column(Numeric(10, 2), nullable=False, default=0)
    payment_type = db.Column(db.String(20), nullable=False, default='test')  # test | real
    payment_upi_id = db.Column(db.String(160), nullable=True)
    payment_qr = db.Column(db.String(255), nullable=True)
    payment_note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    organizer = db.relationship('User', foreign_keys=[organizer_id])

class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    registration_code = db.Column(db.String(60), unique=True, nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    status = db.Column(db.String(30), default='registered')
    payment_status = db.Column(db.String(30), nullable=False, default='not_required')
    payment_reference = db.Column(db.String(100), unique=True, nullable=True, index=True)
    payment_paid_at = db.Column(db.DateTime, nullable=True)
    receipt_file_name = db.Column(db.String(255), nullable=True)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    event = db.relationship('Event', backref='registrations')
    student = db.relationship('User', foreign_keys=[student_id])
    __table_args__ = (UniqueConstraint('event_id', 'student_id', name='uq_event_student'),)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    status = db.Column(db.String(30), default='not_marked')
    marked_at = db.Column(db.DateTime, nullable=True)
    marked_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    event = db.relationship('Event')
    student = db.relationship('User', foreign_keys=[student_id])
    __table_args__ = (UniqueConstraint('event_id', 'student_id', name='uq_att_event_student'),)

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    event = db.relationship('Event')
    author = db.relationship('User')

class Certificate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    certificate_number = db.Column(db.String(80), unique=True, nullable=False, index=True)
    verification_code = db.Column(db.String(120), unique=True, nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    file_name = db.Column(db.String(255), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), default='issued')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    event = db.relationship('Event')
    student = db.relationship('User', foreign_keys=[student_id])
    __table_args__ = (UniqueConstraint('event_id', 'student_id', name='uq_cert_event_student'),)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(200), nullable=False)
    resource = db.Column(db.String(120), nullable=True)
    resource_id = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User')

@app.context_processor
def inject_globals():
    return {'current_user': current_user(), 'today': date.today()}

def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    return db.session.get(User, uid)

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped

def roles(*allowed):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for('login'))
            if user.role not in allowed:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator

def audit(action, resource=None, resource_id=None):
    user = current_user()
    db.session.add(AuditLog(user_id=user.id if user else None, action=action, resource=resource, resource_id=str(resource_id) if resource_id else None))

def parse_date(value, fallback=None):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except Exception:
        return fallback or date.today()

def unique_code(prefix):
    return f'{prefix}-{datetime.now().strftime("%Y%m%d")}-{uuid.uuid4().hex[:7].upper()}'

def event_owner_or_admin(event):
    user = current_user()
    return user and (user.role == 'admin' or (user.role == 'organizer' and event.organizer_id == user.id))

def local_now():
    return datetime.now(APP_TIMEZONE)

def local_today():
    return local_now().date()

def parse_event_end_time(value):
    value = (value or '').strip()
    for fmt in ('%H:%M', '%H:%M:%S', '%I:%M %p', '%I:%M%p'):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None

def event_end_datetime(event):
    end_time = parse_event_end_time(event.end_time)
    if not end_time:
        return None
    return datetime.combine(event.event_date, end_time).replace(tzinfo=APP_TIMEZONE)

def event_has_ended(event):
    end_at = event_end_datetime(event)
    return bool(end_at and local_now() >= end_at)

def refresh_event_status(event):
    if event.status == 'approved' and event_has_ended(event):
        event.status = 'completed'
        return True
    return False

def eligible_for_certificate(event_id, student_id):
    att = Attendance.query.filter_by(event_id=event_id, student_id=student_id).first()
    return bool(att and att.status == 'present')

def font(size, bold=False):
    candidates = [
        '/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()

def fit_font(draw, text, max_width, start_size, bold=True):
    size = start_size
    while size > 18:
        f = font(size, bold)
        if draw.textbbox((0, 0), text, font=f)[2] <= max_width:
            return f
        size -= 2
    return font(18, bold)

def generate_payment_receipt(event, student, registration):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.enums import TA_CENTER
    out_name=f'{registration.payment_reference}.pdf'
    out_path=RECEIPT_DIR/out_name
    doc=SimpleDocTemplate(str(out_path),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=42)
    styles=getSampleStyleSheet()
    title=ParagraphStyle('title',parent=styles['Title'],alignment=TA_CENTER,textColor=colors.HexColor('#b82f1b'),fontSize=22,leading=27)
    sub=ParagraphStyle('sub',parent=styles['Normal'],alignment=TA_CENTER,textColor=colors.HexColor('#59636e'),fontSize=9)
    body=ParagraphStyle('body',parent=styles['BodyText'],fontSize=10,leading=15)
    story=[Paragraph('RGM COLLEGE EVENTS',title),Paragraph('Rajeev Gandhi Memorial College of Engineering and Technology (Autonomous)',sub),Spacer(1,22),Paragraph('REGISTRATION FEE RECEIPT',title),Spacer(1,16)]
    mode='TEST PAYMENT • SIMULATION' if event.payment_type=='test' else 'PAYMENT RECORDED • QR/UPI SELF-DECLARED'
    data=[
      ['Receipt ID',registration.payment_reference],['Event ID',f'RGM-EVT-{event.id:04d}'],['Event',event.title],
      ['Student',student.name],['Student ID',student.student_id or '—'],['Registration ID',registration.registration_code],
      ['Amount',f'₹ {float(event.fee_amount):,.2f}'],['Payment Mode',mode],['Paid At',registration.payment_paid_at.strftime('%d %B %Y, %I:%M %p')],
      ['Status','PAID / RECORDED']]
    t=Table(data,colWidths=[120,360])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),colors.HexColor('#fff0ea')),('TEXTCOLOR',(0,0),(0,-1),colors.HexColor('#8e2a1b')),('FONTNAME',(0,0),(-1,-1),'Helvetica'),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),9),('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#ead9d3')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('ROWBACKGROUNDS',(1,0),(1,-1),[colors.white,colors.HexColor('#fbfaf8')]),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9)]))
    story += [t,Spacer(1,18),Paragraph('This receipt confirms that the portal recorded the registration-fee action. For real QR/UPI events, the portal does not independently verify the banking transaction.',body)]
    doc.build(story)
    return out_name

def generate_certificate(event, student, certificate_number):
    """Render the supplied RGM certificate artwork without disturbing its layout."""
    template_path = BASE_DIR / 'assets' / 'certificate-template.png'
    img = Image.open(template_path).convert('RGB')
    draw = ImageDraw.Draw(img)
    # The supplied master is 1536x1024. These masks cover only placeholder text.
    # The original borders, logo, headings, watermark and signatures remain untouched.
    paper = (252, 251, 247)
    draw.rectangle((475, 540, 1065, 607), fill=paper)       # Student Name
    draw.rectangle((545, 668, 1000, 716), fill=paper)       # Event title
    draw.rectangle((795, 738, 1005, 768), fill=paper)       # [Event Date]
    draw.rectangle((545, 780, 995, 813), fill=paper)        # Certificate ID area

    student_name = student.name.upper().strip()
    event_name = event.title.strip()
    event_date_text = event.event_date.strftime('%d %B %Y')

    def centered(text_value, y, fnt, fill=(185, 46, 24)):
        box = draw.textbbox((0, 0), text_value, font=fnt)
        x = (img.width - (box[2] - box[0])) / 2
        draw.text((x, y), text_value, font=fnt, fill=fill)

    centered(student_name, 544, fit_font(draw, student_name, 560, 54, True))
    centered(event_name, 671, fit_font(draw, event_name, 420, 32, True))
    # Date is inserted into the exact sentence position from the supplied template.
    date_font = fit_font(draw, event_date_text, 205, 20, True)
    draw.text((803, 740), event_date_text, font=date_font, fill=(45, 45, 45))
    id_text = f'Certificate ID: {certificate_number}'
    centered(id_text, 782, fit_font(draw, id_text, 440, 16, True), fill=(90, 31, 23))

    # QR verification code is placed in the open lower-left white area without covering signatures.
    base_url = os.getenv('BASE_URL', 'http://127.0.0.1:5000').rstrip('/')
    qr = qrcode.QRCode(box_size=3, border=1)
    qr.add_data(f'{base_url}/verify/{certificate_number}')
    qr.make(fit=True)
    qri = qr.make_image(fill_color='black', back_color='white').convert('RGB').resize((108, 108))
    img.paste(qri, (72, 835))

    out_name = f'{certificate_number}.pdf'
    out_path = CERT_DIR / out_name
    img.save(out_path, 'PDF', resolution=180.0)
    return out_name

@app.route('/')
def index():
    events = Event.query.filter(Event.status == 'approved', Event.event_date >= date.today()).order_by(Event.event_date.asc()).limit(6).all()
    return render_template('index.html', events=events)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Single login door. Role is determined only after credentials are verified."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter(func.lower(User.email) == email).first()
        if user and user.active and check_password_hash(user.password_hash, password):
            session.clear()
            session['user_id'] = user.id
            audit('Logged in')
            db.session.commit()
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            if user.role == 'organizer':
                return redirect(url_for('organizer_dashboard'))
            return redirect(url_for('student_dashboard'))
        flash('Invalid email/password or inactive account.', 'danger')
    return render_template('auth.html', mode='login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        student_id = request.form.get('student_id','').strip()
        department = request.form.get('department','').strip()
        year = request.form.get('year','').strip()
        phone = request.form.get('phone','').strip()
        if not name or not email or len(password) < 6:
            flash('Name, email and a password of at least 6 characters are required.', 'danger')
            return render_template('auth.html', mode='register')
        if User.query.filter(func.lower(User.email) == email).first():
            flash('An account with that email already exists.', 'danger')
            return render_template('auth.html', mode='register')
        u = User(name=name, email=email, password_hash=generate_password_hash(password), role='student', student_id=student_id or None, department=department or None, year=year or None, phone=phone or None)
        db.session.add(u); db.session.commit()
        flash('Student account created. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('auth.html', mode='register')

@app.route('/logout')
def logout():
    session.clear(); flash('You have been logged out.', 'info'); return redirect(url_for('index'))

@app.route('/events')
def public_events():
    q = request.args.get('q','').strip()
    query = Event.query.filter(Event.status == 'approved')
    if q: query = query.filter(Event.title.ilike(f'%{q}%'))
    events = query.order_by(Event.event_date.asc()).all()
    return render_template('events.html', events=events, q=q)

@app.route('/events/<int:event_id>')
def event_detail(event_id):
    event = db.get_or_404(Event, event_id)
    count = Registration.query.filter_by(event_id=event.id, status='registered').count()
    registered = False
    user = current_user()
    if user and user.role == 'student':
        registered = Registration.query.filter_by(event_id=event.id, student_id=user.id, status='registered').first() is not None
    return render_template('event_detail.html', event=event, count=count, registered=registered)

@app.route('/student/dashboard')
@roles('student')
def student_dashboard():
    user = current_user()
    regs = Registration.query.filter_by(student_id=user.id, status='registered').order_by(Registration.registered_at.desc()).all()
    changed = False
    for reg in regs:
        if event_has_ended(reg.event) and eligible_for_certificate(reg.event.id, user.id):
            _, created = create_certificate_for_student(reg.event, user)
            changed = changed or created
            if refresh_event_status(reg.event):
                changed = True
    if changed:
        db.session.commit()
    certs = Certificate.query.filter_by(student_id=user.id).order_by(Certificate.issue_date.desc()).all()
    announcements = Announcement.query.join(Event).join(Registration, Registration.event_id == Event.id).filter(Registration.student_id == user.id).order_by(Announcement.created_at.desc()).limit(5).all()
    return render_template('student_dashboard.html', registrations=regs, certs=certs, announcements=announcements)

@app.route('/student/profile', methods=['GET','POST'])
@roles('student')
def student_profile():
    user=current_user()
    if request.method=='POST':
        user.name=request.form.get('name','').strip() or user.name
        user.phone=request.form.get('phone','').strip() or None
        user.department=request.form.get('department','').strip() or None
        user.year=request.form.get('year','').strip() or None
        db.session.commit(); flash('Profile updated.', 'success'); return redirect(url_for('student_profile'))
    return render_template('profile.html', user=user)

@app.post('/events/<int:event_id>/register')
@roles('student')
def register_event(event_id):
    event=db.get_or_404(Event,event_id); user=current_user(); today=local_today()
    if event.status != 'approved':
        flash('This event is not currently open for registration.','warning')
        return redirect(url_for('event_detail',event_id=event.id))
    if today < event.registration_start or today > event.registration_deadline:
        flash('Registration is closed for this event.','warning')
        return redirect(url_for('event_detail',event_id=event.id))
    count=Registration.query.filter_by(event_id=event.id,status='registered').count()
    if count >= event.max_participants:
        flash('This event is full.','warning'); return redirect(url_for('event_detail',event_id=event.id))
    if Registration.query.filter_by(event_id=event.id,student_id=user.id,status='registered').first():
        flash('You are already registered.','info'); return redirect(url_for('event_detail',event_id=event.id))
    payment_status='pending' if event.fee_enabled else 'not_required'
    reg=Registration(registration_code=unique_code('REG'),event_id=event.id,student_id=user.id,payment_status=payment_status)
    db.session.add(reg); audit('Registered for event','event',event.id); db.session.commit()
    if event.fee_enabled:
        flash(f'Registration successful. ID: {reg.registration_code}. Please complete the registration fee payment below.','success')
    else:
        flash(f'Registration successful. ID: {reg.registration_code}','success')
    return redirect(url_for('student_dashboard'))

@app.post('/events/<int:event_id>/pay')
@roles('student')
def pay_registration_fee(event_id):
    event=db.get_or_404(Event,event_id); user=current_user()
    reg=Registration.query.filter_by(event_id=event.id,student_id=user.id,status='registered').first()
    if not reg:
        flash('Register for this event before paying the registration fee.','warning')
        return redirect(url_for('event_detail',event_id=event.id))
    if not event.fee_enabled:
        flash('This event does not require a registration fee.','info')
        return redirect(url_for('student_dashboard'))
    if reg.payment_status == 'paid' and reg.receipt_file_name:
        flash('Payment is already recorded for this registration.','info')
        return redirect(url_for('student_dashboard'))
    # Test mode intentionally simulates a successful payment. Real mode records a self-declared
    # QR/UPI payment; no banking verification is claimed by this demo portal.
    reg.payment_status='paid'
    reg.payment_reference=unique_code('PAY')
    reg.payment_paid_at=datetime.now(APP_TIMEZONE).replace(tzinfo=None)
    reg.receipt_file_name=generate_payment_receipt(event,user,reg)
    audit('Recorded registration fee payment','registration',reg.id)
    db.session.commit()
    flash(f'Fee payment recorded successfully. Receipt ID: {reg.payment_reference}','success')
    return redirect(url_for('student_dashboard'))

@app.route('/receipts/<path:file_name>')
@login_required
def receipt_file(file_name):
    reg=Registration.query.filter_by(receipt_file_name=file_name).first()
    user=current_user()
    if not reg or (user.role=='student' and reg.student_id != user.id): abort(404)
    return send_from_directory(RECEIPT_DIR,file_name,as_attachment=False)

@app.post('/events/<int:event_id>/cancel-registration')
@roles('student')
def cancel_registration(event_id):
    user=current_user(); reg=Registration.query.filter_by(event_id=event_id,student_id=user.id,status='registered').first()
    if not reg: flash('Registration not found.','warning'); return redirect(url_for('student_dashboard'))
    reg.status='cancelled'; audit('Cancelled event registration','registration',reg.id); db.session.commit(); flash('Registration cancelled.','success'); return redirect(url_for('student_dashboard'))

@app.route('/student/certificates')
@roles('student')
def student_certificates():
    user = current_user()
    regs = Registration.query.filter_by(student_id=user.id, status='registered').all()
    changed = False
    for reg in regs:
        if event_has_ended(reg.event) and eligible_for_certificate(reg.event.id, user.id):
            _, created = create_certificate_for_student(reg.event, user)
            changed = changed or created
            if refresh_event_status(reg.event):
                changed = True
    if changed:
        db.session.commit()
    certs = Certificate.query.filter_by(student_id=user.id).order_by(Certificate.issue_date.desc()).all()
    return render_template('certificates.html', certs=certs)

@app.route('/payment-qr/<path:file_name>')
def payment_qr_file(file_name):
    return send_from_directory(PAYMENT_QR_DIR, file_name, as_attachment=False)

@app.route('/certificates/<path:file_name>')
@login_required
def certificate_file(file_name):
    cert=Certificate.query.filter_by(file_name=file_name).first()
    user=current_user()
    if not cert or (user.role=='student' and cert.student_id != user.id): abort(404)
    return send_from_directory(CERT_DIR, file_name, as_attachment=False)

@app.route('/verify/<certificate_number>')
def verify_certificate(certificate_number):
    cert=Certificate.query.filter_by(certificate_number=certificate_number).first()
    return render_template('verify.html', cert=cert)

@app.route('/organizer/dashboard')
@roles('organizer')
def organizer_dashboard():
    user = current_user()
    events = Event.query.filter_by(organizer_id=user.id).order_by(Event.event_date.desc()).all()
    changed = False
    for event in events:
        if refresh_event_status(event):
            changed = True
        if event_has_ended(event):
            if generate_eligible_certificates(event):
                changed = True
    if changed:
        db.session.commit()
    participant_count = sum(Registration.query.filter_by(event_id=e.id, status='registered').count() for e in events)
    cert_count = sum(Certificate.query.filter_by(event_id=e.id).count() for e in events)
    return render_template('organizer_dashboard.html', events=events, participant_count=participant_count, cert_count=cert_count)

@app.route('/admin/events/new', methods=['GET','POST'])
@roles('admin')
def admin_new_event():
    organizers = User.query.filter_by(role='organizer', active=True).order_by(User.name.asc()).all()
    if request.method == 'POST':
        organizer_id = request.form.get('organizer_id', type=int)
        if not organizer_id or not db.session.get(User, organizer_id) or db.session.get(User, organizer_id).role != 'organizer':
            flash('Please select a valid organizer.', 'danger')
            return render_template('admin_event_form.html', organizers=organizers)
        e = Event(organizer_id=organizer_id, status='approved')
        event_from_form(e)
        db.session.add(e); db.session.flush(); audit('Created and approved event', 'event', e.id); db.session.commit()
        flash('Event created and published.', 'success')
        return redirect(url_for('admin_event', event_id=e.id))
    return render_template('admin_event_form.html', organizers=organizers)

@app.route('/organizer/events/new', methods=['GET','POST'])
@roles('organizer')
def organizer_new_event():
    if request.method=='POST':
        e=event_from_form(Event(organizer_id=current_user().id))
        db.session.add(e); db.session.flush(); audit('Created event','event',e.id); db.session.commit(); flash('Event submitted for admin approval.','success'); return redirect(url_for('organizer_dashboard'))
    return render_template('event_form.html', event=None, title='Create Event')

@app.route('/organizer/events/<int:event_id>/edit', methods=['GET','POST'])
@roles('organizer','admin')
def edit_event(event_id):
    e=db.get_or_404(Event,event_id)
    if current_user().role=='organizer' and e.organizer_id!=current_user().id: abort(403)
    if request.method=='POST':
        event_from_form(e); e.status='pending' if current_user().role=='organizer' else e.status; audit('Updated event','event',e.id); db.session.commit(); flash('Event updated.','success'); return redirect(url_for('admin_event',event_id=e.id) if current_user().role=='admin' else url_for('organizer_dashboard'))
    return render_template('event_form.html', event=e, title='Update Event')

def event_from_form(e):
    e.title=request.form.get('title','').strip()
    e.category=request.form.get('category','General').strip()
    e.description=request.form.get('description','').strip()
    e.event_date=parse_date(request.form.get('event_date'))
    e.start_time=request.form.get('start_time','09:00')
    e.end_time=request.form.get('end_time','17:00')
    e.venue=request.form.get('venue','').strip()
    e.registration_start=parse_date(request.form.get('registration_start'), date.today())
    e.registration_deadline=parse_date(request.form.get('registration_deadline'), e.event_date)
    e.max_participants=max(1,int(request.form.get('max_participants','100')))
    e.rules=request.form.get('rules','').strip() or None
    e.fee_enabled=request.form.get('fee_enabled') == 'on'
    try:
        e.fee_amount=max(0, float(request.form.get('fee_amount','0') or 0))
    except ValueError:
        e.fee_amount=0
    e.payment_type=request.form.get('payment_type','test') if e.fee_enabled else 'test'
    e.payment_upi_id=request.form.get('payment_upi_id','').strip() or None
    e.payment_note=request.form.get('payment_note','').strip() or None
    if e.fee_enabled and e.payment_type == 'real' and e.payment_upi_id:
        amount=f'{float(e.fee_amount):.2f}'
        payload=f'upi://pay?pa={e.payment_upi_id}&pn=RGM%20College%20Events&am={amount}&cu=INR&tn={secure_filename(e.title)[:60]}'
        qr_name=f'event-{e.id or uuid.uuid4().hex[:10]}.png'
        qpath=PAYMENT_QR_DIR/qr_name
        qrcode.make(payload).save(qpath)
        e.payment_qr=qr_name
    elif not e.fee_enabled or e.payment_type == 'test':
        e.payment_qr=None
    return e

@app.post('/organizer/events/<int:event_id>/cancel')
@roles('organizer','admin')
def cancel_event(event_id):
    e=db.get_or_404(Event,event_id)
    if current_user().role=='organizer' and e.organizer_id!=current_user().id: abort(403)
    e.status='cancelled'; audit('Cancelled event','event',e.id); db.session.commit(); flash('Event cancelled.','success'); return redirect(url_for('organizer_dashboard') if current_user().role=='organizer' else url_for('admin_events'))

@app.post('/admin/events/<int:event_id>/delete')
@roles('admin')
def delete_event(event_id):
    e=db.get_or_404(Event,event_id)
    if Registration.query.filter_by(event_id=e.id).count() or Attendance.query.filter_by(event_id=e.id).count() or Certificate.query.filter_by(event_id=e.id).count():
        flash('This event has historical records. Cancel/archive it instead of permanently deleting it.','warning')
        return redirect(url_for('admin_event',event_id=e.id))
    Announcement.query.filter_by(event_id=e.id).delete(); db.session.delete(e); audit('Deleted event','event',e.id); db.session.commit(); flash('Event deleted.','success'); return redirect(url_for('admin_events'))

@app.route('/organizer/events/<int:event_id>/participants')
@roles('organizer','admin')
def participants(event_id):
    e=db.get_or_404(Event,event_id)
    if current_user().role=='organizer' and e.organizer_id!=current_user().id: abort(403)
    regs=Registration.query.filter_by(event_id=e.id,status='registered').order_by(Registration.registered_at.desc()).all()
    attendance_map={a.student_id:a.status for a in Attendance.query.filter_by(event_id=e.id).all()}
    certificate_map={c.student_id:c for c in Certificate.query.filter_by(event_id=e.id).all()}
    return render_template('participants.html', event=e, regs=regs, admin=current_user().role=='admin', attendance_map=attendance_map, certificate_map=certificate_map)

@app.route('/admin/events/<int:event_id>/participants/<int:student_id>')
@roles('admin')
def admin_participant_detail(event_id, student_id):
    e = db.get_or_404(Event, event_id)
    student = db.get_or_404(User, student_id)
    reg = Registration.query.filter_by(event_id=e.id, student_id=student.id).first()
    att = Attendance.query.filter_by(event_id=e.id, student_id=student.id).first()
    cert = Certificate.query.filter_by(event_id=e.id, student_id=student.id).first()
    history = Registration.query.filter_by(student_id=student.id, status='registered').order_by(Registration.registered_at.desc()).all()
    return render_template('participant_detail.html', event=e, student=student, reg=reg, att=att, cert=cert, history=history)

@app.route('/student/attendance')
@roles('student')
def student_attendance():
    records=Attendance.query.filter_by(student_id=current_user().id).order_by(Attendance.marked_at.desc()).all()
    return render_template('student_attendance.html', records=records)

@app.post('/events/<int:event_id>/attendance')
@roles('organizer','admin')
def attendance(event_id):
    e=db.get_or_404(Event,event_id)
    if current_user().role=='organizer' and e.organizer_id!=current_user().id: abort(403)
    regs=Registration.query.filter_by(event_id=e.id,status='registered').all()
    for r in regs:
        value=request.form.get(f'att_{r.student_id}','not_marked')
        a=Attendance.query.filter_by(event_id=e.id,student_id=r.student_id).first()
        if not a:
            a=Attendance(event_id=e.id,student_id=r.student_id)
            db.session.add(a)
        a.status=value; a.marked_at=datetime.utcnow(); a.marked_by=current_user().id
    db.session.commit()
    auto_created = 0
    if event_has_ended(e):
        auto_created = generate_eligible_certificates(e)
        db.session.commit()
    audit('Updated attendance', 'event', e.id)
    db.session.commit()
    if auto_created:
        flash(f'Attendance saved. {auto_created} certificate(s) were generated automatically for Present students.', 'success')
    else:
        flash('Attendance saved. Certificates will be generated automatically after the event end time for Present students.', 'success')
    return redirect(url_for('participants', event_id=e.id))

@app.post('/events/<int:event_id>/announcements')
@roles('organizer','admin')
def announcement(event_id):
    e=db.get_or_404(Event,event_id)
    if current_user().role=='organizer' and e.organizer_id!=current_user().id: abort(403)
    a=Announcement(event_id=e.id,title=request.form.get('title','').strip(),message=request.form.get('message','').strip(),created_by=current_user().id)
    db.session.add(a); db.session.commit(); audit('Created announcement','event',e.id); db.session.commit(); flash('Announcement published.','success'); return redirect(url_for('admin_event',event_id=e.id) if current_user().role=='admin' else url_for('organizer_dashboard'))

def create_certificate_for_student(event, student):
    existing = Certificate.query.filter_by(event_id=event.id, student_id=student.id).first()
    if existing:
        return existing, False
    if not eligible_for_certificate(event.id, student.id):
        return None, False
    number = f'RGM-{event.event_date.year}-{event.id:03d}-{student.id:05d}'
    if Certificate.query.filter_by(certificate_number=number).first():
        number = unique_code('RGM-CERT')
    file_name = generate_certificate(event, student, number)
    cert = Certificate(
        certificate_number=number,
        verification_code=uuid.uuid4().hex,
        event_id=event.id,
        student_id=student.id,
        file_name=file_name,
        issue_date=local_today(),
        status='issued'
    )
    db.session.add(cert)
    return cert, True

def generate_eligible_certificates(event):
    if event.status not in {'approved', 'completed'} or not event_has_ended(event):
        return 0
    event.status = 'completed'
    created = 0
    regs = Registration.query.filter_by(event_id=event.id, status='registered').all()
    for reg in regs:
        _, was_created = create_certificate_for_student(event, reg.student)
        if was_created:
            created += 1
    return created

@app.post('/events/<int:event_id>/certificates/generate')
@roles('organizer','admin')
def generate_certificates(event_id):
    event = db.get_or_404(Event, event_id)
    if current_user().role == 'organizer' and event.organizer_id != current_user().id:
        abort(403)
    if not event_has_ended(event):
        end_at = event_end_datetime(event)
        if end_at:
            display = end_at.strftime('%d %B %Y at %I:%M %p')
            flash(f'Certificates become available after the event ends: {display}.', 'warning')
        else:
            flash('The event end time is invalid. Please edit the event first.', 'danger')
        return redirect(url_for('admin_event', event_id=event.id) if current_user().role == 'admin' else url_for('organizer_dashboard'))

    created = generate_eligible_certificates(event)
    db.session.commit()
    audit(f'Generated {created} certificates', 'event', event.id)
    db.session.commit()
    flash(f'{created} certificate(s) generated. Present participants receive certificates; duplicates are skipped.', 'success')
    return redirect(url_for('admin_event', event_id=event.id) if current_user().role == 'admin' else url_for('organizer_dashboard'))

@app.route('/admin/dashboard')
@roles('admin')
def admin_dashboard():
    all_events = Event.query.all()
    changed = False
    for event in all_events:
        if refresh_event_status(event):
            changed = True
        if event_has_ended(event):
            if generate_eligible_certificates(event):
                changed = True
    if changed:
        db.session.commit()
    stats={
        'students':User.query.filter_by(role='student').count(), 'organizers':User.query.filter_by(role='organizer').count(),
        'events':Event.query.count(), 'registrations':Registration.query.filter_by(status='registered').count(),
        'certificates':Certificate.query.count(), 'pending':Event.query.filter_by(status='pending').count(),
    }
    events=Event.query.order_by(Event.event_date.desc()).limit(8).all()
    return render_template('admin_dashboard.html',stats=stats,events=events)

@app.route('/admin/events')
@roles('admin')
def admin_events():
    q=request.args.get('q','').strip(); status=request.args.get('status','')
    query=Event.query
    if q: query=query.filter(Event.title.ilike(f'%{q}%'))
    if status: query=query.filter_by(status=status)
    events=query.order_by(Event.event_date.desc()).all()
    return render_template('admin_events.html',events=events,q=q,status=status)

@app.route('/admin/events/<int:event_id>')
@roles('admin')
def admin_event(event_id):
    e=db.get_or_404(Event,event_id)
    regs=Registration.query.filter_by(event_id=e.id,status='registered').all()
    present=Attendance.query.filter_by(event_id=e.id,status='present').count()
    absent=Attendance.query.filter_by(event_id=e.id,status='absent').count()
    certs=Certificate.query.filter_by(event_id=e.id).count()
    announcements=Announcement.query.filter_by(event_id=e.id).order_by(Announcement.created_at.desc()).all()
    return render_template('admin_event.html',event=e,regs=regs,present=present,absent=absent,certs=certs,announcements=announcements)

@app.post('/admin/events/<int:event_id>/approve')
@roles('admin')
def approve_event(event_id):
    e=db.get_or_404(Event,event_id); e.status='approved'; audit('Approved event','event',e.id); db.session.commit(); flash('Event approved and visible to students.','success'); return redirect(url_for('admin_event',event_id=e.id))

@app.post('/admin/events/<int:event_id>/reject')
@roles('admin')
def reject_event(event_id):
    e=db.get_or_404(Event,event_id); e.status='rejected'; audit('Rejected event','event',e.id); db.session.commit(); flash('Event rejected.','info'); return redirect(url_for('admin_event',event_id=e.id))

@app.route('/admin/users')
@roles('admin')
def admin_users():
    users=User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html',users=users)

@app.post('/admin/users/<int:user_id>/toggle')
@roles('admin')
def toggle_user(user_id):
    u=db.get_or_404(User,user_id)
    if u.id==current_user().id: flash('You cannot disable your own admin account.','warning'); return redirect(url_for('admin_users'))
    u.active=not u.active; audit('Toggled user active state','user',u.id); db.session.commit(); flash('User status updated.','success'); return redirect(url_for('admin_users'))

@app.route('/admin/reports')
@roles('admin')
def reports():
    event_rows=[]
    for e in Event.query.order_by(Event.event_date.desc()).all():
        event_rows.append((e, Registration.query.filter_by(event_id=e.id,status='registered').count(), Attendance.query.filter_by(event_id=e.id,status='present').count(), Certificate.query.filter_by(event_id=e.id).count()))
    return render_template('reports.html',rows=event_rows)

@app.route('/api/events')
def api_events():
    events=Event.query.filter_by(status='approved').order_by(Event.event_date.asc()).all()
    return jsonify([{'id':e.id,'title':e.title,'date':e.event_date.isoformat(),'venue':e.venue,'category':e.category,'status':e.status} for e in events])

@app.errorhandler(403)
def forbidden(_): return render_template('error.html',code=403,message='You are not authorized to access this resource.'),403
@app.errorhandler(404)
def not_found(_): return render_template('error.html',code=404,message='The requested page was not found.'),404

@app.cli.command('seed')
def seed_command():
    seed_data()
    print('Seed complete.')

def seed_data():
    if not User.query.filter_by(email='admin@rgmcollege.edu').first():
        db.session.add(User(name='RGM Administrator',email='admin@rgmcollege.edu',password_hash=generate_password_hash('Admin@12345'),role='admin'))
    if not User.query.filter_by(email='organizer@rgmcollege.edu').first():
        db.session.add(User(name='CSE Event Organizer',email='organizer@rgmcollege.edu',password_hash=generate_password_hash('Organizer@12345'),role='organizer',department='CSE'))
    if not User.query.filter_by(email='student@rgmcollege.edu').first():
        db.session.add(User(name='Demo Student',email='student@rgmcollege.edu',password_hash=generate_password_hash('Student@12345'),role='student',student_id='RGM-DEMO-001',department='CSE',year='3rd Year'))
    db.session.commit()
    organizer=User.query.filter_by(email='organizer@rgmcollege.edu').first()
    if organizer and Event.query.count()==0:
        today=date.today()
        e=Event(title='AI Workshop 2026',category='Technical',description='A practical workshop covering artificial intelligence concepts, tools, and responsible AI.',event_date=today, start_time='10:00', end_time='16:00', venue='CSE Seminar Hall',registration_start=today,registration_deadline=today,max_participants=150,rules='Carry college ID. Seats are limited.',organizer_id=organizer.id,status='approved')
        db.session.add(e); db.session.commit()

def ensure_schema():
    """Lightweight additive migration so this ZIP also upgrades an older local database."""
    db.create_all()
    inspector=inspect(db.engine)
    additions={
        'event': {
            'fee_enabled': "ALTER TABLE event ADD COLUMN fee_enabled BOOLEAN NOT NULL DEFAULT 0",
            'fee_amount': "ALTER TABLE event ADD COLUMN fee_amount DECIMAL(10,2) NOT NULL DEFAULT 0",
            'payment_type': "ALTER TABLE event ADD COLUMN payment_type VARCHAR(20) NOT NULL DEFAULT 'test'",
            'payment_upi_id': "ALTER TABLE event ADD COLUMN payment_upi_id VARCHAR(160) NULL",
            'payment_qr': "ALTER TABLE event ADD COLUMN payment_qr VARCHAR(255) NULL",
            'payment_note': "ALTER TABLE event ADD COLUMN payment_note TEXT NULL",
        },
        'registration': {
            'payment_status': "ALTER TABLE registration ADD COLUMN payment_status VARCHAR(30) NOT NULL DEFAULT 'not_required'",
            'payment_reference': "ALTER TABLE registration ADD COLUMN payment_reference VARCHAR(100) NULL",
            'payment_paid_at': "ALTER TABLE registration ADD COLUMN payment_paid_at DATETIME NULL",
            'receipt_file_name': "ALTER TABLE registration ADD COLUMN receipt_file_name VARCHAR(255) NULL",
        }
    }
    for table, cols in additions.items():
        existing={c['name'] for c in inspect(db.engine).get_columns(table)}
        for col, ddl in cols.items():
            if col not in existing:
                try:
                    db.session.execute(text(ddl)); db.session.commit()
                except Exception:
                    db.session.rollback()

with app.app_context():
    ensure_schema()
    seed_data()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
