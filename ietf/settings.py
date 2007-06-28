# Copyright The IETF Trust 2007, All Rights Reserved

# Django settings for ietf project.
# BASE_DIR and "settings_local" are from
# http://code.djangoproject.com/wiki/SplitSettings

import os

import syslog
syslog.openlog("django", syslog.LOG_PID, syslog.LOG_USER)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('IETF Django Developers', 'django-project@ietf.org'),
    ('GMail Tracker Archive', 'ietf.tracker.archive+errors@gmail.com'),
)

# Override this in the settings_local.py file:
SERVER_EMAIL = 'Django Server<django@tools.ietf.org>'


DEFAULT_FROM_EMAIL = 'IETF Secretariat <ietf-secretariat-reply@ietf.org>'

MANAGERS = ADMINS

DATABASE_ENGINE = 'mysql'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'ado_mssql'.
DATABASE_NAME = 'django_idtracker'             # Or path to database file if using sqlite3.
DATABASE_USER = 'django'             # Not used with sqlite3.
DATABASE_PASSWORD = 'playing'         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://www.postgresql.org/docs/8.1/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
# although not all variations may be possible on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = BASE_DIR + "/../static/"

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Link django user to IETF user
AUTH_PROFILE_MODULE = 'ietfauth.UserMap'

# Allow specification of email address as username,
# and handle htpasswd crypt() format passwords.
AUTHENTICATION_BACKENDS = (
    "ietf.ietfauth.auth.EmailBackend",
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
#    'ietf.middleware.PrettifyMiddleware',
    'ietf.middleware.SQLLogMiddleware',
    'ietf.middleware.SMTPExceptionMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
)

ROOT_URLCONF = 'ietf.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    BASE_DIR + "/templates"
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'ietf.context_processors.server_mode',
    'ietf.context_processors.revision_info',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.humanize',
    'ietf.agenda',
    'ietf.announcements',
    'ietf.idindex',
    'ietf.idtracker',
    'ietf.ietfauth',
    'ietf.iesg',
    'ietf.ipr',
    'ietf.liaisons',
    'ietf.mailinglists',
    'ietf.my',
    'ietf.proceedings',
    'ietf.redirects',
)

INTERNAL_IPS = (
# llama in san jose
	'135.207.33.119',
# fenestro
	'67.188.114.134',
# shiraz and marsanne
        '81.232.110.214',
        '2001:16d8:ff54::1',
# merlot
        '194.146.105.14',
        '2001:698:9:31:214:22ff:fe21:bb',
# local
        '127.0.0.1',
        '::1',
)

# Valid values:
# 'production', 'test', 'development'
# Override this in settings_local.py if it's not true
SERVER_MODE = 'production'

# The name of the method to use to invoke the test suite
TEST_RUNNER = 'ietf.tests.run_tests'

IPR_DOCUMENT_PATH = '/home/master-site/ftp/data/ietf/IPR'

# Put SECRET_KEY in here, or any other sensitive or site-specific
# changes.  DO NOT commit settings_local.py to svn.
from settings_local import *
