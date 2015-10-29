import os.path

DEBUG = True
TEMPLATE_DEBUG = DEBUG

SECRET_KEY = 'm-92)2et+&&m5f&#jld7-_1qanq*n9!z90xc@+wx6y8d6y#w6t'

BASE_DIR = os.path.dirname(__file__)

def absolute_path(path):
    return os.path.normpath(os.path.join(BASE_DIR, path))

SITE_ID = 1
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': absolute_path('database.sqlite3'),
    }
}

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'adv_cache_tag',
    'adv_cache_tag.tests.testproject.adv_cache_test_app',
]

MIDDLEWARE_CLASSES = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
