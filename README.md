# Hotel Management Backend

Backend for Hotel Management System built with Django and DRF.

## Installation

```bash
git clone your-repo-url
cd hotel-management-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Fill your environment variables
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

