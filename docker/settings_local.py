import os

SECRET_KEY = 'jzv$o93h_lzw4a0%0oz-5t5lk+ai=3f8x@uo*9ahu8w4i300o6'

DATABASES = {
    'default': {
        'NAME': 'ietf_utf8',
        'ENGINE': 'django.db.backends.mysql',
        'USER': 'django',
        'PASSWORD': 'RkTkDPFnKpko',
        },
    }

DATABASE_TEST_OPTIONS = {
    'init_command': 'SET storage_engine=InnoDB',
    }

IDSUBMIT_IDNITS_BINARY = "/usr/local/bin/idnits"
IDSUBMIT_REPOSITORY_PATH = "test/id/"
IDSUBMIT_STAGING_PATH = "test/staging/"
INTERNET_DRAFT_ARCHIVE_DIR = "test/archive/"

AGENDA_PATH = 'test/data/proceedings/'

USING_DEBUG_EMAIL_SERVER=True
EMAIL_HOST='localhost'
EMAIL_PORT=2025

TRAC_WIKI_DIR_PATTERN = "test/wiki/%s"
TRAC_SVN_DIR_PATTERN = "test/svn/%s"
