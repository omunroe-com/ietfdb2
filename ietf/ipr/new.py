# Copyright The IETF Trust 2007, All Rights Reserved

import re
import models
import ietf.utils
import django.newforms as forms

from datetime import datetime
from django.shortcuts import render_to_response as render, get_object_or_404
from django.template import RequestContext
from django.http import Http404
from ietf.utils import log
from ietf.utils.mail import send_mail
from ietf.ipr.view_sections import section_table
from ietf.idtracker.models import Rfc, InternetDraft

# ----------------------------------------------------------------
# Callback methods for special field cases.
# ----------------------------------------------------------------

def ipr_detail_form_callback(field, **kwargs):
    if field.name == "licensing_option":
        return forms.IntegerField(widget=forms.RadioSelect(choices=models.LICENSE_CHOICES), required=False, **kwargs)
    if field.name in ["is_pending", "applies_to_all"]:
        return forms.IntegerField(widget=forms.RadioSelect(choices=((1, "YES"), (2, "NO"))), required=False, **kwargs)
    if field.name in ["rfc_number", "id_document_tag"]:
        log(field.name)
        return forms.CharFieldField(required=False, **kwargs)
    return field.formfield(**kwargs)

def ipr_contact_form_callback(field, **kwargs):
    phone_re = re.compile(r'^\+?[0-9 ]*(\([0-9]+\))?[0-9 -]+$')
    error_message = """Phone numbers may have a leading "+", and otherwise only contain
                numbers [0-9]; dash, period or space; parentheses, and an optional
                extension number indicated by 'x'. """

    if field.name in ['ipr', 'contact_type']:
	return None
    if field.name == "telephone":
        return forms.RegexField(phone_re, error_message=error_message, **kwargs)
    if field.name == "fax":
        return forms.RegexField(phone_re, error_message=error_message, required=False, **kwargs)
    return field.formfield(**kwargs)
    # TODO:
    #   Add rfc existence validation for RFC field
    #   Add draft existence validation for Drafts field

# ----------------------------------------------------------------
# Classes
# ----------------------------------------------------------------    

# Get a form class which renders fields using a given template
CustomForm = ietf.utils.makeFormattingForm(template="ipr/formfield.html")

# Get base form classes for our models
BaseIprForm = forms.form_for_model(models.IprDetail, form=CustomForm, formfield_callback=ipr_detail_form_callback)
BaseContactForm = forms.form_for_model(models.IprContact, form=CustomForm, formfield_callback=ipr_contact_form_callback)

# Some subclassing:

# The contact form will be part of the IprForm, so it needs a widget.
# Define one.
class MultiformWidget(forms.Widget):
   def value_from_datadict(self, data, name):
       return data

class ContactForm(BaseContactForm):
    widget = MultiformWidget()

    def add_prefix(self, field_name):
        return self.prefix and ('%s_%s' % (self.prefix, field_name)) or field_name
    def clean(self, *value):
        if value:
            return self.full_clean()
        else:
            return self.clean_data


# ----------------------------------------------------------------
# Form processing
# ----------------------------------------------------------------

def new(request, type, update=None, submitter=None):
    """Make a new IPR disclosure.

    This is a big function -- maybe too big.  Things would be easier if we didn't have
    one form containing fields from 4 tables -- don't build something like this again...

    """
    debug = ""

    section_list = section_table[type].copy()
    section_list.update({"title":False, "new_intro":False, "form_intro":True,
        "form_submit":True, "form_legend": True, })

    class IprForm(BaseIprForm):
        holder_contact = None
        rfclist = forms.CharField(required=False)
        draftlist = forms.CharField(required=False)
        stdonly_license = forms.BooleanField(required=False)
        hold_contact_is_submitter = forms.BooleanField(required=False)
        ietf_contact_is_submitter = forms.BooleanField(required=False)
        if "holder_contact" in section_list:
            holder_contact = ContactForm(prefix="hold")
        if "ietf_contact" in section_list:
            ietf_contact = ContactForm(prefix="ietf")
        if "submitter" in section_list:
            submitter = ContactForm(prefix="subm")
        def __init__(self, *args, **kw):
            contact_type = {1:"holder_contact", 2:"ietf_contact", 3:"submitter"}
            contact_initial = {}
            if update:
                for contact in update.contact.all():
                    contact_initial[contact_type[contact.contact_type]] = contact.__dict__
		if submitter:
		    if type == "third-party":
			contact_initial["ietf_contact"] = submitter
		    else:
			contact_initial["submitter"] = submitter
            kwnoinit = kw.copy()
            kwnoinit.pop('initial', None)
            for contact in ["holder_contact", "ietf_contact", "submitter"]:
                if contact in section_list:
                    self.base_fields[contact] = ContactForm(prefix=contact[:4], initial=contact_initial.get(contact, {}), *args, **kwnoinit)
            rfclist_initial = ""
            if update:
                rfclist_initial = " ".join(["RFC%d" % rfc.document_id for rfc in update.rfcs.all()])
            self.base_fields["rfclist"] = forms.CharField(required=False, initial=rfclist_initial)
            draftlist_initial = ""
            if update:
                draftlist_initial = " ".join([draft.document.filename + (draft.revision and "-%s" % draft.revision or "") for draft in update.drafts.all()])
            self.base_fields["draftlist"] = forms.CharField(required=False, initial=draftlist_initial)
            if "holder_contact" in section_list:
                self.base_fields["hold_contact_is_submitter"] = forms.BooleanField(required=False)
            if "ietf_contact" in section_list:
                self.base_fields["ietf_contact_is_submitter"] = forms.BooleanField(required=False)
            self.base_fields["stdonly_license"] = forms.BooleanField(required=False)

            BaseIprForm.__init__(self, *args, **kw)
        # Special validation code
        def clean(self):
            if section_list.get("ietf_doc", False):
                # would like to put this in rfclist to get the error
                # closer to the fields, but clean_data["draftlist"]
                # isn't set yet.
                rfclist = self.clean_data.get("rfclist", None)
                draftlist = self.clean_data.get("draftlist", None)
                other = self.clean_data.get("other_designations", None)
                if not rfclist and not draftlist and not other:
                    raise forms.ValidationError("One of the Document fields below must be filled in")
            return self.clean_data
        def clean_rfclist(self):
            rfclist = self.clean_data.get("rfclist", None)
            if rfclist:
                rfclist = re.sub("(?i) *[,;]? *rfc[- ]?", " ", rfclist)
                rfclist = rfclist.strip().split()
                for rfc in rfclist:
                    try:
                        Rfc.objects.get(rfc_number=int(rfc))
                    except:
                        raise forms.ValidationError("Unknown RFC number: %s - please correct this." % rfc)
                rfclist = " ".join(rfclist)
            return rfclist
        def clean_draftlist(self):
            draftlist = self.clean_data.get("draftlist", None)
            if draftlist:
                draftlist = re.sub(" *[,;] *", " ", draftlist)
                draftlist = draftlist.strip().split()
                drafts = []
                for draft in draftlist:
                    if draft.endswith(".txt"):
                        draft = draft[:-4]
                    if re.search("-[0-9][0-9]$", draft):
                        filename = draft[:-3]
                        rev = draft[-2:]
                    else:
                        filename = draft
                        rev = None
                    try:
                        id = InternetDraft.objects.get(filename=filename)
                    except Exception, e:
                        log("Exception: %s" % e)
                        raise forms.ValidationError("Unknown Internet-Draft: %s - please correct this." % filename)
                    if rev and id.revision != rev:
                        raise forms.ValidationError("Unexpected revision '%s' for draft %s - the current revision is %s.  Please check this." % (rev, filename, id.revision))
                    drafts.append("%s-%s" % (filename, id.revision))
                return " ".join(drafts)
            return ""
        def clean_holder_contact(self):
            return self.holder_contact.full_clean()
        def clean_ietf_contact(self):
            return self.ietf_contact.full_clean()
        def clean_submitter(self):
            return self.submitter.full_clean()
        def clean_licensing_option(self):
            licensing_option = self.clean_data['licensing_option']
            if section_list.get('licensing', False):
                if licensing_option in (None, ''):
                    raise forms.ValidationError, 'This field is required.'
            return licensing_option


    # If we're POSTed, but we got passed a submitter, it was the
    # POST of the "get updater" form, so we don't want to validate
    # this one.  When we're posting *this* form, submitter is None,
    # even when updating.
    if request.method == 'POST' and not submitter:
        data = request.POST.copy()
        data["submitted_date"] = datetime.now().strftime("%Y-%m-%d")
        data["third_party"] = section_list["third_party"]
        data["generic"] = section_list["generic"]
        data["status"] = "0"
        data["comply"] = "1"
        
        for src in ["hold", "ietf"]:
            if "%s_contact_is_submitter" % src in data:
                for subfield in ["name", "title", "department", "address1", "address2", "telephone", "fax", "email"]:
                    try:
                        data[ "subm_%s" % subfield ] = data[ "%s_%s" % (src,subfield) ]
                    except Exception, e:
                        #log("Caught exception: %s"%e)
                        pass
        form = IprForm(data)
        if form.is_valid():
            # Save data :
            #   IprDetail, IprUpdate, IprContact+, IprDraft+, IprRfc+, IprNotification

            # Save IprDetail
            instance = form.save(commit=False)

            if type == "generic":
                instance.title = """%(legal_name)s's General License Statement""" % data
            if type == "specific":
                data["ipr_summary"] = get_ipr_summary(form.clean_data)
                instance.title = """%(legal_name)s's Statement about IPR related to %(ipr_summary)s""" % data
            if type == "third-party":
                data["ipr_summary"] = get_ipr_summary(form.clean_data)
                instance.title = """%(ietf_name)s's Statement about IPR related to %(ipr_summary)s belonging to %(legal_name)s""" % data

            # A long document list can create a too-long title;
            # saving a too-long title raises an exception,
            # so prevent truncation in the database layer by
            # performing it explicitly.
            if len(instance.title) > 255:
                instance.title = instance.title[:252] + "..."

            instance.save()

            if update:
                updater = models.IprUpdate(ipr=instance, updated=update, status_to_be=1, processed=0)
                updater.save()
            contact_type = {"hold":1, "ietf":2, "subm": 3}

            # Save IprContact(s)
            for prefix in ["hold", "ietf", "subm"]:
#                cdata = {"ipr": instance.ipr_id, "contact_type":contact_type[prefix]}
                cdata = {"ipr": instance, "contact_type":contact_type[prefix]}
                for item in data:
                    if item.startswith(prefix+"_"):
                        cdata[item[5:]] = data[item]
                try:
                    del cdata["contact_is_submitter"]
                except KeyError:
                    pass
                contact = models.IprContact(**cdata)
                contact.save()
                # store this contact in the instance for the email
                # similar to what views.show() does
                if   prefix == "hold":
                    instance.holder_contact = contact
                elif prefix == "ietf":
                    instance.ietf_contact = contact
                elif prefix == "subm":
                    instance.submitter = contact
#                contact = ContactForm(cdata)
#                if contact.is_valid():
#                    contact.save()
#                else:
#                    log("Invalid contact: %s" % contact)

            # Save IprDraft(s)
            for draft in form.clean_data["draftlist"].split():
                id = InternetDraft.objects.get(filename=draft[:-3])
                iprdraft = models.IprDraft(document=id, ipr=instance, revision=draft[-2:])
                iprdraft.save()

            # Save IprRfc(s)
            for rfcnum in form.clean_data["rfclist"].split():
                rfc = Rfc.objects.get(rfc_number=int(rfcnum))
                iprrfc = models.IprRfc(document=rfc, ipr=instance)
                iprrfc.save()

            send_mail(request, ['ietf-ipr@ietf.org', 'sunny.lee@neustar.biz'], ('IPR Submitter App', 'ietf-ipr@ietf.org'), 'New IPR Submission Notification', "ipr/new_update_email.txt", {"ipr": instance, "update": update})
            return render("ipr/submitted.html", {"update": update}, context_instance=RequestContext(request))
        else:
            if form.ietf_contact_is_submitter:
                form.ietf_contact_is_submitter_checked = "checked"

            for error in form.errors:
                log("Form error for field: %s: %s"%(error, form.errors[error]))
            # Fall through, and let the partially bound form, with error
            # indications, be rendered again.
            pass
    else:
        if update:
            form = IprForm(initial=update.__dict__)
        else:
            form = IprForm()
        form.unbound_form = True

    # ietf.utils.log(dir(form.ietf_contact_is_submitter))
    return render("ipr/details.html", {"ipr": form, "section_list":section_list, "debug": debug}, context_instance=RequestContext(request))

def update(request, ipr_id=None):
    """Update a specific IPR disclosure"""
    ipr = get_object_or_404(models.IprDetail, ipr_id=ipr_id)
    if not ipr.status in [1,3]:
	raise Http404        
    type = "specific"
    if ipr.generic:
	type = "generic"
    if ipr.third_party:
	type = "third-party"
    # We're either asking for initial permission or we're in
    # the general ipr form.  If the POST argument has the first
    # field of the ipr form, then we must be dealing with that,
    # so just pass through - otherwise, collect the updater's
    # info first.
    submitter = None
    if not(request.POST.has_key('legal_name')):
	class UpdateForm(BaseContactForm):
	    def __init__(self, *args, **kwargs):
		self.base_fields["update_auth"] = forms.BooleanField("I am authorized to update this IPR disclosure, and I understand that notification of this update will be provided to the submitter of the original IPR disclosure and to the Patent Holder's Contact.")
		super(UpdateForm, self).__init__(*args, **kwargs)
	if request.method == 'POST':
	    form = UpdateForm(request.POST)
	else:
	    form = UpdateForm()

	if not(form.is_valid()):
            for error in form.errors:
                log("Form error for field: %s: %s"%(error, form.errors[error]))
	    return render("ipr/update.html", {"form": form, "ipr": ipr, "type": type}, context_instance=RequestContext(request))
	else:
	    submitter = form.clean_data

    return new(request, type, ipr, submitter)


def get_ipr_summary(data):

    rfc_ipr = [ "RFC %s" % item for item in data["rfclist"].split() ]
    draft_ipr = data["draftlist"].split()
    ipr = rfc_ipr + draft_ipr
    if data["other_designations"]:
        ipr += [ data["other_designations"] ]

    if len(ipr) == 1:
        ipr = ipr[0]
    elif len(ipr) == 2:
        ipr = " and ".join(ipr)
    else:
        ipr = ", ".join(ipr[:-1]) + ", and " + ipr[-1]

    return ipr
