# Notes

A note-taking web app I started in 2023 while learning Django. It is a small
monolithic Django project with server-rendered pages and a jQuery frontend for
updating notes without full page reloads. The interface was refreshed later,
while the original project structure remained in place.

Users can create and edit notes, mark favorites, move notes to the archive or
trash, and filter them by hashtags. The app also includes registration, email
verification and optional Google OAuth login.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

The default development configuration prints verification emails to the
terminal. To use Gmail or Google OAuth, add the corresponding credentials to
`.env`.

Run the Django tests with:

```bash
python manage.py test
```
