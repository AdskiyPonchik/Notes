# 🗒️ Notes

A **Google Keep–style note-taking web app** built with Django. Create notes, star favorites, archive or trash them, filter by inline `#hashtags` — all with a dynamic AJAX frontend that updates without page reloads.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django)
![Auth](https://img.shields.io/badge/OAuth-Google-4285F4?logo=google&logoColor=white)

## ✨ Features

- 📝 **Notes CRUD** — create, edit and manage notes with title + text
- ⭐ **Statuses & lifecycle** — Active → Favorite → Archived → Trash, switchable with one click
- 🏷️ **Hashtag extraction** — `#tags` are parsed straight out of note text and can be used for filtering
- ⚡ **AJAX API** — the frontend fetches and updates notes via JSON endpoints (`get_notes`, `update_note`, `note_action`) without full page reloads
- 🔐 **Full auth flow**:
  - classic signup/login
  - **email verification** with tokenized confirmation links (invalid-token handling included)
  - **Sign in with Google** via `social-auth-app-django`
- 👤 **User profiles** — each user gets a `Participant` profile with an avatar image
- 🗃️ **Indexed queries** — notes ordered and indexed by creation date

## 🔌 Endpoints

| Route                              | Purpose                                  |
|------------------------------------|------------------------------------------|
| `/`                                | Notes dashboard (login required)         |
| `/get_notes/`                      | JSON list of the user's notes            |
| `/notes/update/<id>/`              | Update a note (AJAX)                     |
| `/notes/<id>/<action>/`            | Change status: favorite / archive / trash|
| `/signup/`, `/login/`, `/logout/`  | Authentication                          |
| `/verify_email/<uid>/<token>/`     | Email confirmation link                  |
| `/social_auth/…`                   | Google OAuth                             |

## 🚀 Getting started

```bash
git clone https://github.com/AdskiyPonchik/Notes.git
cd Notes

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file with your secrets:

```env
SECRET_KEY=your-django-secret
EMAIL_HOST_USER=you@example.com
EMAIL_HOST_PASSWORD=app-password
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=your-google-client-id
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=your-google-client-secret
```

Then:

```bash
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/` 🎉

## 🛠️ Tech stack

Django 5.2 · social-auth-app-django (Google OAuth2) · Pillow · vanilla JS (fetch-based AJAX) · CSS
