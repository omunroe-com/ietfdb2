from email.Utils import *
from email.MIMEText import MIMEText
from email.MIMEMessage import MIMEMessage
from email.MIMEMultipart import MIMEMultipart
import smtplib
from django.conf import settings
from django.template.loader import render_to_string
from django.template import RequestContext

def add_headers(msg):
    if not(msg.has_key('Message-ID')):
	msg['Message-ID'] = make_msgid('idtracker')
    if not(msg.has_key('Date')):
	msg['Date'] = formatdate(time.time(), True)
    if not(msg.has_key('From')):
	msg['From'] = settings.DEFAULT_FROM_EMAIL
    return msg

def send_smtp(msg):
    '''
    Send a Message via SMTP, based on the django email server settings.
    The destination list will be taken from the To:/Cc: headers in the
    Message.  The From address will be used if present or will default
    to the django setting DEFAULT_FROM_EMAIL
    '''
    add_headers(msg)
    (fname, frm) = parseaddr(msg.get('From'))
    to = [addr for name, addr in getaddresses(msg.get_all('To') + msg.get_all('Cc', []))]
    # todo: exception handling
    server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
    if settings.DEBUG:
	server.set_debuglevel(1)
    if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
	server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
    server.sendmail(frm, to, msg.as_string())
    server.quit()

def copy_email(msg, to):
    '''
    Send a copy of the given email message to the given recipient.
    '''
    add_headers(msg)
    new = MIMEMultipart()
    # get info for first part.
    # Mode: if it's production, then "copy of a message", otherwise
    #  "this is a message that would have been sent from"
    # hostname?
    # django settings if debugging?
    # Should this be a template?
    if settings.SERVER_MODE == 'production':
	new.attach(MIMEText("This is a copy of a message sent from the I-D tracker."))
    else:
	new.attach(MIMEText("The attached message would have been sent, but the tracker is in %s mode.\nIt was not sent to anybody.\n" % settings.SERVER_MODE))
    new.attach(MIMEMessage(msg))
    new['From'] = msg['From']
    new['Subject'] = '[Django %s] %s' % (settings.SERVER_MODE, msg.get('Subject', '[no subject]'))
    new['To'] = to
    send_smtp(new)

def send_mail_subj(request, to, frm, stemplate, template, context, cc=None, extra=None):
    '''
    Send an email message, exactly as send_mail(), but the
    subject field is a template.
    '''
    subject = render_to_string(template, context, context_instance=RequestContext(request))
    return send_mail(request, to, frm, subject, template, context, cc, extra)

def send_mail(request, to, frm, subject, template, context, cc=None, extra=None):
    '''
    Send an email to the destination [list], with the given return
    address (or "None" to use the default in settings.py).
    The body is a text/plain rendering of the template with the context.
    extra is a dict of extra headers to add.
    '''
    txt = render_to_string(template, context, context_instance=RequestContext(request))
    return send_mail_text(request, to, frm, subject, txt, cc, extra)

def send_mail_text(request, to, frm,subject, txt, cc=None, extra=None):
    msg = MIMEText(txt)
    if isinstance(frm, tuple):
	frm = formataddr(frm)
    if isinstance(to, list) or isinstance(to, tuple):
        to = ", ".join([isinstance(addr, tuple) and formataddr(addr) or addr for addr in to])
    if isinstance(cc, list) or isinstance(cc, tuple):
        cc = ", ".join([isinstance(addr, tuple) and formataddr(addr) or addr for addr in cc])
    if frm:
	msg['From'] = frm
    msg['To'] = to
    if cc:
	msg['Cc'] = cc
    msg['Subject'] = subject
    msg['X-Test-IDTracker'] = (settings.SERVER_MODE == 'production') and 'no' or 'yes'
    if extra:
	for k, v in extra.iteritems():
	    msg[k] = v
    if settings.SERVER_MODE == 'production':
	send_smtp(msg)
    copy_email(msg, "ietf.tracker.archive+%s@gmail.com" % settings.SERVER_MODE)
