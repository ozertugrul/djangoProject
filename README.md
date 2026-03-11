# MagiColorize

MagiColorize is a Django-based web application that colorizes black-and-white images and provides a gallery/account workflow around generated outputs.

## Features

- Grayscale image colorization pipeline
- Gallery and processed-image flow
- User account and social login integrations
- Payment-related integration points (Iyzico)

## Tech Stack

- Python 3
- Django
- MySQL
- uWSGI (deployment)

## Project Structure

```text
djangoProject/
	manage.py
	magiColorize/        # project settings and URLs
	imagecolorizer/      # main app (models, views, templates)
	static/              # static assets
	media/               # uploaded/generated files
```

## Local Setup

1. Clone the repository and enter the project folder.
2. Create and activate a virtual environment.
3. Install dependencies.
4. Create local environment file from the example.
5. Run migrations and start the server.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

## Environment Variables

The project now expects sensitive values from environment variables instead of hardcoded credentials.

Use [.env.example](.env.example) as the template:

- `DJANGO_SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `IYZICO_API_KEY`, `IYZICO_SECRET_KEY`, `IYZICO_BASE_URL`
- `SITE_ID`

## Security Notes

- Do not commit `.env` or any real secret values.
- Rotate previously exposed keys/secrets in provider panels (Django secret, DB password, Iyzico keys).
- Restrict `DEBUG=False` in production.
- Set strict `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` in production.

## Deployment Notes

- `uwsgi.ini` contains uWSGI process configuration.
- Collect static files before production release:

```bash
python manage.py collectstatic --noinput
```

## License

Add a license file if this project will be distributed publicly.