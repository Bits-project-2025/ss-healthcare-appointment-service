# Appointment Service

Healthcare microservice for managing doctor appointments.

## Features

- Create and manage appointments
- View doctor availability slots
- Cancel appointments
- Track appointment status

## API Endpoints

### Appointments

- `POST /api/v1/appointments` - Create appointment
- `GET /api/v1/appointments/<appointment_id>` - Get appointment details
- `GET /api/v1/appointments/patient/<patient_id>` - Get patient appointments
- `GET /api/v1/appointments/doctor/<doctor_id>` - Get doctor appointments
- `PUT /api/v1/appointments/<appointment_id>` - Update appointment
- `DELETE /api/v1/appointments/<appointment_id>` - Cancel appointment

### Doctor Slots

- `POST /api/v1/doctor-slots` - Create availability slot
- `GET /api/v1/doctor-slots/doctor/<doctor_id>` - Get available slots

### Health

- `GET /health` - Health check

## Setup

### Local Development

```bash
pip install -r requirements.txt
python app.py
```

### Docker

```bash
docker build -t appointment-service:latest .
docker run -p 5000:5000 -e DATABASE_URL=postgresql://... appointment-service:latest
```

## Environment Variables

```
DATABASE_URL=postgresql://appuser:password@localhost:5432/healthcare_appointments
```
