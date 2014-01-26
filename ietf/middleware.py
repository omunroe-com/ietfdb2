# Copyright The IETF Trust 2007, All Rights Reserved

from django.db import connection
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponsePermanentRedirect
from ietf.utils import log
import re
import smtplib
import sys
import traceback
import unicodedata

class SQLLogMiddleware(object):
    def process_response(self, request, response):
	for q in connection.queries:
	    if re.match('(update|insert)', q['sql'], re.IGNORECASE):
		log(q['sql'])
        return response

class SMTPExceptionMiddleware(object):
    def process_exception(self, request, exception):
	if isinstance(exception, smtplib.SMTPException):
	    type = sys.exc_info()[0]
	    value = sys.exc_info()[1]
	    # See if it's a non-smtplib exception that we faked
	    if type == smtplib.SMTPException and len(value.args) == 1 and isinstance(value.args[0], dict) and value.args[0].has_key('really'):
		orig = value.args[0]
		type = orig['really']
		tb = traceback.format_tb(orig['tb'])
		value = orig['value']
	    else:
		tb = traceback.format_tb(sys.exc_info()[2])
            log("SMTP Exception: %s" % type)
            log("SMTP Exception: args: %s" % value)
            log("SMTP Exception: tb: %s" % tb)
	    return render_to_response('email_failed.html', {'exception': type, 'args': value, 'traceback': "".join(tb)},
		context_instance=RequestContext(request))
	return None

class RedirectTrailingPeriod(object):
    def process_response(self, request, response):
	if response.status_code == 404 and request.path.endswith("."):
	    return HttpResponsePermanentRedirect(request.path.rstrip("."))
	return response

class UnicodeNfkcNormalization(object):
    def process_request(self, request):
        """Do Unicode NFKC normalization to turn ligatures into individual characters.
        This was prompted by somebody actually requesting an url for /wg/ipfix/charter
        where the 'fi' was composed of an \ufb01 ligature...

        There are probably other elements of a request which may need this normalization
        too, but let's put that in as it comes up, rather than guess ahead.
        """
        request.META["PATH_INFO"] = unicodedata.normalize('NFKC', request.META["PATH_INFO"])
        request.path_info = unicodedata.normalize('NFKC', request.path_info)
        return None

class FillInRemoteUserIfLoggedInMiddleware(object):
    def process_request(self, request):
        if request.user.is_authenticated() and "REMOTE_USER" not in request.META:
            request.META["REMOTE_USER"] = request.user.username

