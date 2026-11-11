import os
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import uuid
from dotenv import load_dotenv
import time
import sys

load_dotenv()

app = Flask(__name__)
CORS(app)

# Database Configuration with retry logic
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://appuser:secure_password_123@localhost:5432/healthcare_appointments'
)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 3600,
    'connect_args': {'connect_timeout': 10}
}

db = SQLAlchemy(app)

# Models
class Appointment(db.Model):
    __tablename__ = 'appointments'
    
    appointment_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = db.Column(db.String(36), nullable=False, index=True)
    doctor_id = db.Column(db.String(36), nullable=False, index=True)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    reason = db.Column(db.String(500))
    status = db.Column(db.String(20), default='scheduled', index=True)  # scheduled, completed, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'appointment_id': self.appointment_id,
            'patient_id': self.patient_id,
            'doctor_id': self.doctor_id,
            'appointment_date': self.appointment_date.isoformat(),
            'appointment_time': self.appointment_time.isoformat(),
            'reason': self.reason,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class DoctorSlot(db.Model):
    __tablename__ = 'doctor_slots'
    
    slot_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = db.Column(db.String(36), nullable=False, index=True)
    available_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'slot_id': self.slot_id,
            'doctor_id': self.doctor_id,
            'available_date': self.available_date.isoformat(),
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'is_available': self.is_available,
            'created_at': self.created_at.isoformat()
        }

# Routes

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'appointment-service',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/api/v1/appointments', methods=['POST', 'GET'])
def appointments_handler():
    """Handle appointments - POST to create, GET to retrieve all or filtered"""
    if request.method == 'POST':
        return create_appointment()
    else:
        return get_all_appointments()

def get_all_appointments():
    """Get all appointments with optional filtering"""
    try:
        patient_id = request.args.get('patient_id', None)
        doctor_id = request.args.get('doctor_id', None)
        status = request.args.get('status', None)
        
        query = Appointment.query
        
        if patient_id:
            query = query.filter_by(patient_id=patient_id)
        if doctor_id:
            query = query.filter_by(doctor_id=doctor_id)
        if status:
            query = query.filter_by(status=status)
        
        appointments = query.all()
        return jsonify([apt.to_dict() for apt in appointments]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def create_appointment():
    """Create a new appointment"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['patient_id', 'doctor_id', 'appointment_date', 'appointment_time', 'reason']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if slot is available
        from datetime import datetime as dt
        appointment_date = dt.strptime(data['appointment_date'], '%Y-%m-%d').date()
        appointment_time = dt.strptime(data['appointment_time'], '%H:%M').time()
        
        existing_appointment = Appointment.query.filter_by(
            doctor_id=data['doctor_id'],
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status='scheduled'
        ).first()
        
        if existing_appointment:
            return jsonify({'error': 'Time slot already booked'}), 409
        
        appointment = Appointment(
            patient_id=data['patient_id'],
            doctor_id=data['doctor_id'],
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            reason=data['reason'],
            status='scheduled'
        )
        
        db.session.add(appointment)
        db.session.commit()
        
        return jsonify({
            'message': 'Appointment created successfully',
            'appointment': appointment.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/appointments/<appointment_id>', methods=['GET'])
def get_appointment(appointment_id):
    """Get appointment details"""
    try:
        appointment = Appointment.query.get(appointment_id)
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        return jsonify(appointment.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/appointments/patient/<patient_id>', methods=['GET'])
def get_patient_appointments(patient_id):
    """Get all appointments for a patient"""
    try:
        status = request.args.get('status', None)
        
        query = Appointment.query.filter_by(patient_id=patient_id)
        if status:
            query = query.filter_by(status=status)
        
        appointments = query.all()
        return jsonify([apt.to_dict() for apt in appointments]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/appointments/doctor/<doctor_id>', methods=['GET'])
def get_doctor_appointments(doctor_id):
    """Get all appointments for a doctor"""
    try:
        status = request.args.get('status', None)
        date = request.args.get('date', None)
        
        query = Appointment.query.filter_by(doctor_id=doctor_id)
        if status:
            query = query.filter_by(status=status)
        if date:
            from datetime import datetime as dt
            date_obj = dt.strptime(date, '%Y-%m-%d').date()
            query = query.filter_by(appointment_date=date_obj)
        
        appointments = query.all()
        return jsonify([apt.to_dict() for apt in appointments]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/appointments/<appointment_id>', methods=['PUT'])
def update_appointment(appointment_id):
    """Update appointment status"""
    try:
        data = request.get_json()
        appointment = Appointment.query.get(appointment_id)
        
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        if 'status' in data:
            appointment.status = data['status']
        if 'notes' in data:
            appointment.notes = data['notes']
        
        appointment.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Appointment updated successfully',
            'appointment': appointment.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/appointments/<appointment_id>', methods=['DELETE'])
def cancel_appointment(appointment_id):
    """Cancel an appointment"""
    try:
        appointment = Appointment.query.get(appointment_id)
        
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        appointment.status = 'cancelled'
        appointment.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Appointment cancelled successfully',
            'appointment': appointment.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/doctor-slots', methods=['POST'])
def create_doctor_slot():
    """Create doctor availability slot"""
    try:
        data = request.get_json()
        
        required_fields = ['doctor_id', 'available_date', 'start_time', 'end_time']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        from datetime import datetime as dt
        available_date = dt.strptime(data['available_date'], '%Y-%m-%d').date()
        start_time = dt.strptime(data['start_time'], '%H:%M').time()
        end_time = dt.strptime(data['end_time'], '%H:%M').time()
        
        slot = DoctorSlot(
            doctor_id=data['doctor_id'],
            available_date=available_date,
            start_time=start_time,
            end_time=end_time,
            is_available=True
        )
        
        db.session.add(slot)
        db.session.commit()
        
        return jsonify({
            'message': 'Slot created successfully',
            'slot': slot.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/doctor-slots/doctor/<doctor_id>', methods=['GET'])
def get_doctor_slots(doctor_id):
    """Get available slots for a doctor"""
    try:
        date = request.args.get('date', None)
        
        query = DoctorSlot.query.filter_by(doctor_id=doctor_id, is_available=True)
        if date:
            from datetime import datetime as dt
            date_obj = dt.strptime(date, '%Y-%m-%d').date()
            query = query.filter_by(available_date=date_obj)
        
        slots = query.all()
        return jsonify([slot.to_dict() for slot in slots]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Retry logic for database initialization
    max_retries = 10
    retry_delay = 3
    
    for attempt in range(max_retries):
        try:
            with app.app_context():
                print(f"[Attempt {attempt + 1}/{max_retries}] Attempting to connect to database...")
                db.create_all()
                print("✓ Database initialized successfully!")
                break
        except Exception as e:
            print(f"✗ Database connection failed: {str(e)}")
            if attempt < max_retries - 1:
                print(f"  Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"✗ Failed to connect after {max_retries} attempts. Exiting.")
                sys.exit(1)
    
    print(f"Starting Appointment Service on 0.0.0.0:5000...")
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
