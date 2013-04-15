# Copyright The IETF Trust 2007, All Rights Reserved

# Django settings for ietf project.
# BASE_DIR and "settings_local" are from
# http://code.djangoproject.com/wiki/SplitSettings

import os
try:
    import syslog
    syslog.openlog("datatracker", syslog.LOG_PID, syslog.LOG_USER)
except ImportError:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

import sys
sys.path.append(os.path.abspath(BASE_DIR + "/.."))
sys.path.append(os.path.abspath(BASE_DIR + "/../redesign"))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

# Domain name of the IETF
IETF_DOMAIN = 'ietf.org'

ADMINS = (
    ('IETF Django Developers', 'django-project@' + IETF_DOMAIN),
    ('GMail Tracker Archive', 'ietf.tracker.archive+errors@gmail.com'),
    ('Henrik Levkowetz', 'henrik@levkowetz.com'),
    ('Ole Laursen', 'olau@iola.dk'),
)

# Server name of the tools server
TOOLS_SERVER = 'tools.' + IETF_DOMAIN

# Override this in the settings_local.py file:
SERVER_EMAIL = 'Django Server <django-project@' + TOOLS_SERVER + '>'

DEFAULT_FROM_EMAIL = 'IETF Secretariat <ietf-secretariat-reply@' + IETF_DOMAIN + '>'

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'NAME': 'ietf_utf8',
        'ENGINE': 'django.db.backends.mysql',
        'USER': 'ietf',
        #'PASSWORD': 'ietf',
    },
#    'legacy': {
#        'NAME': 'ietf',
#        'ENGINE': 'django.db.backends.mysql',
#        'USER': 'ietf',
#        #'PASSWORD': 'ietf',
#    },
}

# Local time zone for this installation. Choices can be found here:
# http://www.postgresql.org/docs/8.1/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
# although not all variations may be possible on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'PST8PDT'

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

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

AUTH_PROFILE_MODULE = 'person.Person'
AUTHENTICATION_BACKENDS = ( 'django.contrib.auth.backends.RemoteUserBackend', )

#DATABASE_ROUTERS = ["ietf.legacy_router.LegacyRouter"]

SESSION_COOKIE_AGE = 43200 # 12 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.RemoteUserMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'ietf.middleware.SQLLogMiddleware',
    'ietf.middleware.SMTPExceptionMiddleware',
    'ietf.middleware.RedirectTrailingPeriod',
    'django.middleware.transaction.TransactionMiddleware',
    'ietf.middleware.UnicodeNfkcNormalization',
    'ietf.secr.middleware.secauth.SecAuthMiddleware'
)

ROOT_URLCONF = 'ietf.urls'

TEMPLATE_DIRS = (
    BASE_DIR + "/templates",
    BASE_DIR + "/secr/templates",
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'ietf.context_processors.server_mode',
    'ietf.context_processors.revision_info',
    'ietf.secr.context_processors.secr_revision_info',
    'ietf.secr.context_processors.static',
    'ietf.context_processors.rfcdiff_prefix', 
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.humanize',
    'django.contrib.messages',
    'south',
    'workflows',
    'permissions',
    'ietf.person',
    'ietf.name',
    'ietf.group',
    'ietf.doc',
    'ietf.message',
    'ietf.announcements',
    'ietf.idindex',
    'ietf.idtracker',
    'ietf.ietfauth',
    'ietf.iesg',
    'ietf.ipr',
    'ietf.liaisons',
    'ietf.mailinglists',
    'ietf.meeting',
    #'ietf.proceedings',
    'ietf.redirects',
    'ietf.idrfc',
    'ietf.wginfo',
    'ietf.submit',
    'ietf.ietfworkflows',
    'ietf.wgchairs',
    'ietf.wgcharter',
    'ietf.sync',
    'ietf.community',
    'ietf.release',
    # secretariat apps
    'form_utils',
    'ietf.secr.announcement',
    'ietf.secr.areas',
    'ietf.secr.drafts',
    'ietf.secr.groups',
    'ietf.secr.ipradmin',
    'ietf.secr.meetings',
    'ietf.secr.proceedings',
    'ietf.secr.roles',
    'ietf.secr.rolodex',
    'ietf.secr.telechat',
    'ietf.secr.sreq',
)

INTERNAL_IPS = (
# AMS servers
	'64.170.98.32',
	'64.170.98.86',

# local
        '127.0.0.1',
        '::1',
)

# no slash at end
IDTRACKER_BASE_URL = "http://datatracker.ietf.org"
RFCDIFF_PREFIX = "//www.ietf.org/rfcdiff"

# Valid values:
# 'production', 'test', 'development'
# Override this in settings_local.py if it's not true
SERVER_MODE = 'development'

# The name of the method to use to invoke the test suite
TEST_RUNNER = 'ietf.utils.test_runner.run_tests'

# WG Chair configuration
MAX_WG_DELEGATES = 3

DATE_FORMAT = "Y-m-d"
DATETIME_FORMAT = "Y-m-d H:i"

# Override this in settings_local.py if needed
# *_PATH variables ends with a slash/ .
INTERNET_DRAFT_PATH = '/a/www/ietf-ftp/internet-drafts/'
INTERNET_DRAFT_PDF_PATH = '/a/www/ietf-datatracker/pdf/'
RFC_PATH = '/a/www/ietf-ftp/rfc/'
CHARTER_PATH = '/a/www/ietf-ftp/charter/'
CHARTER_TXT_URL = 'http://www.ietf.org/charter/'
CONFLICT_REVIEW_PATH = '/a/www/ietf-ftp/conflict-reviews'
CONFLICT_REVIEW_TXT_URL = 'http://www.ietf.org/cr/'
STATUS_CHANGE_PATH = '/a/www/ietf-ftp/status-changes'
STATUS_CHANGE_TXT_URL = 'http://www.ietf.org/sc/'
AGENDA_PATH = '/a/www/www6s/proceedings/'
AGENDA_PATH_PATTERN = '/a/www/www6s/proceedings/%(meeting)s/agenda/%(wg)s.%(ext)s'
MINUTES_PATH_PATTERN = '/a/www/www6s/proceedings/%(meeting)s/minutes/%(wg)s.%(ext)s'
SLIDES_PATH_PATTERN = '/a/www/www6s/proceedings/%(meeting)s/slides/%(wg)s-*'
IPR_DOCUMENT_PATH = '/a/www/ietf-ftp/ietf/IPR/'
IETFWG_DESCRIPTIONS_PATH = '/a/www/www6s/wg-descriptions/'
IESG_TASK_FILE = '/a/www/www6/iesg/internal/task.txt'
IESG_ROLL_CALL_FILE = '/a/www/www6/iesg/internal/rollcall.txt'
IESG_MINUTES_FILE = '/a/www/www6/iesg/internal/minutes.txt'
IESG_WG_EVALUATION_DIR = "/a/www/www6/iesg/evaluation"
INTERNET_DRAFT_ARCHIVE_DIR = '/a/www/www6s/draft-archive'

# Ideally, more of these would be local -- but since we don't support
# versions right now, we'll point to external websites
DOC_HREFS = {
    "agenda": "/meeting/{meeting}/agenda/{doc.group.acronym}/",
    #"charter": "/doc/{doc.name}-{doc.rev}/",
    "charter": "http://www.ietf.org/charter/{doc.name}-{doc.rev}.txt",
    #"draft": "/doc/{doc.name}-{doc.rev}/",
    "draft": "http://tools.ietf.org/html/{doc.name}-{doc.rev}",
    # I can't figure out the liaison maze. Hopefully someone
    # who understands this better can take care of it.
    #"liai-att": None
    #"liaison": None
    "minutes": "http://www.ietf.org/proceedings/{meeting}/minutes/{doc.name}",
    "slides": "http://www.ietf.org/proceedings/{meeting}/slides/{doc.name}",
}

# Override this in settings_local.py if needed
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = ''
if SERVER_MODE == 'production':
    CACHE_BACKEND= 'file://'+'/a/www/ietf-datatracker/cache/'
else:
    # Default to no caching in development/test, so that every developer
    # doesn't have to set CACHE_BACKEND in settings_local
    CACHE_BACKEND = 'dummy:///'

# For readonly database operation
# CACHE_BACKEND = 'memcached://127.0.0.1:11211/'
# SESSION_ENGINE = "django.contrib.sessions.backends.cache"

IPR_EMAIL_TO = ['ietf-ipr@ietf.org', ]
DOC_APPROVAL_EMAIL_CC = ["RFC Editor <rfc-editor@rfc-editor.org>", ]

# Put real password in settings_local.py
IANA_SYNC_PASSWORD = "secret"
IANA_SYNC_CHANGES_URL = "https://datatracker.iana.org:4443/data-tracker/changes"
IANA_SYNC_PROTOCOLS_URL = "http://www.iana.org/protocols/"

# Liaison Statement Tool settings
LIAISON_UNIVERSAL_FROM = 'Liaison Statement Management Tool <lsmt@' + IETF_DOMAIN + '>'
LIAISON_ATTACH_PATH = '/a/www/ietf-datatracker/documents/LIAISON/'
LIAISON_ATTACH_URL = '/documents/LIAISON/'

# ID Submission Tool settings
IDSUBMIT_FROM_EMAIL = 'IETF I-D Submission Tool <idsubmission@ietf.org>'
IDSUBMIT_TO_EMAIL = 'internet-drafts@ietf.org'
IDSUBMIT_ANNOUNCE_FROM_EMAIL = 'internet-drafts@ietf.org'
IDSUBMIT_ANNOUNCE_LIST_EMAIL = 'i-d-announce@ietf.org'

# Days from meeting to cut off dates on submit
FIRST_CUTOFF_DAYS = 19
SECOND_CUTOFF_DAYS = 12
CUTOFF_HOUR = 00                        # midnight UTC
SUBMISSION_START_DAYS = -90
SUBMISSION_CUTOFF_DAYS = 33
SUBMISSION_CORRECTION_DAYS = 52

INTERNET_DRAFT_DAYS_TO_EXPIRE = 185

IDSUBMIT_REPOSITORY_PATH = INTERNET_DRAFT_PATH
IDSUBMIT_STAGING_PATH = '/a/www/www6s/staging/'
IDSUBMIT_STAGING_URL = 'http://www.ietf.org/staging/'
IDSUBMIT_IDNITS_BINARY = '/a/www/ietf-datatracker/scripts/idnits'

MAX_PLAIN_DRAFT_SIZE = 6291456  # Max size of the txt draft in bytes

# DOS THRESHOLDS PER DAY (Sizes are in MB)
MAX_SAME_DRAFT_NAME = 20
MAX_SAME_DRAFT_NAME_SIZE = 50
MAX_SAME_SUBMITTER = 50
MAX_SAME_SUBMITTER_SIZE = 150
MAX_SAME_WG_DRAFT = 150
MAX_SAME_WG_DRAFT_SIZE = 450
MAX_DAILY_SUBMISSION = 1000
MAX_DAILY_SUBMISSION_SIZE = 2000
# End of ID Submission Tool settings

# Account settings
DAYS_TO_EXPIRE_REGISTRATION_LINK = 3
HTPASSWD_COMMAND = "/usr/bin/htpasswd2"
HTPASSWD_FILE = "/www/htpasswd"

# DB redesign
USE_DB_REDESIGN_PROXY_CLASSES = True

SOUTH_TESTS_MIGRATE = False 

# Generation of bibxml files for xml2rfc
BIBXML_BASE_PATH = '/a/www/ietf-ftp/xml2rfc'

# Timezone files for iCalendar
TZDATA_ICS_PATH = '/www/ietf-datatracker/tz/ics/'
CHANGELOG_PATH = '/www/ietf-datatracker/web/changelog'

# Secretariat Tool
# this is a tuple of regular expressions.  if the incoming URL matches one of
# these, than non secretariat access is allowed.
SECR_AUTH_UNRESTRICTED_URLS = (
    #(r'^/$'),
    (r'^/secr/announcement/'),
    (r'^/secr/proceedings/'),
    (r'^/secr/sreq/'),
)
SECR_BLUE_SHEET_PATH = '/a/www/ietf-datatracker/documents/blue_sheet.rtf'
SECR_BLUE_SHEET_URL = 'https://datatracker.ietf.org/documents/blue_sheet.rtf'
SECR_INTERIM_LISTING_DIR = '/a/www/www6/meeting/interim'
SECR_MAX_UPLOAD_SIZE = 40960000
SECR_PROCEEDINGS_DIR = '/a/www/www6s/proceedings/'
SECR_STATIC_URL = '/secr/'

# Put SECRET_KEY in here, or any other sensitive or site-specific
# changes.  DO NOT commit settings_local.py to svn.
from settings_local import *
