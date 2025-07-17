# 🧩 SDP Bereke

## Быстрый старт

```bash
git clone https://github.com/SabirzhanovN/SDP-Bereke.git
cd SDP-Bereke
python3 -m venv venv
pip install -r requirements.txt
# EDIT .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
