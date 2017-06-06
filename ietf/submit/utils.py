# Copyright The IETF Trust 2011, All Rights Reserved

import os
import datetime
import six
from unidecode import unidecode

from django.conf import settings

import debug                            # pyflakes:ignore

from ietf.doc.models import ( Document, State, DocAlias, DocEvent, SubmissionDocEvent,
    DocumentAuthor, AddedMessageEvent )
from ietf.doc.models import NewRevisionDocEvent
from ietf.doc.models import RelatedDocument, DocRelationshipName
from ietf.doc.utils import add_state_change_event, rebuild_reference_relations
from ietf.doc.utils import set_replaces_for_document
from ietf.doc.mails import send_review_possibly_replaces_request
from ietf.group.models import Group
from ietf.ietfauth.utils import has_role
from ietf.name.models import StreamName
from ietf.person.models import Person, Email
from ietf.community.utils import update_name_contains_indexes_with_new_doc
from ietf.submit.mail import announce_to_lists, announce_new_version, announce_to_authors
from ietf.submit.models import Submission, SubmissionEvent, Preapproval, DraftSubmissionStateName
from ietf.utils import log
from ietf.utils import unaccent
from ietf.utils.mail import is_valid_email


def validate_submission(submission):
    errors = {}

    if submission.state_id not in ("cancel", "posted"):
        for ext in submission.file_types.split(','):
            source = os.path.join(settings.IDSUBMIT_STAGING_PATH, '%s-%s%s' % (submission.name, submission.rev, ext))
            if not os.path.exists(source):
                errors['files'] = '"%s" was not found in the staging area. We recommend you that you cancel this submission and upload your files again.' % os.path.basename(source)
                break

    if not submission.title:
        errors['title'] = 'Title is empty or was not found'

    if submission.group and submission.group.state_id != "active":
        errors['group'] = 'Group exists but is not an active group'

    if not submission.abstract:
        errors['abstract'] = 'Abstract is empty or was not found'

    if not submission.authors:
        errors['authors'] = 'No authors found'

    # revision
    if submission.state_id != "posted":
        error = validate_submission_rev(submission.name, submission.rev)
        if error:
            errors['rev'] = error

    # draft date
    error = validate_submission_document_date(submission.submission_date, submission.document_date)
    if error:
        errors['document_date'] = error

    return errors

def has_been_replaced_by(name):
    docs=Document.objects.filter(name=name)

    if docs:
        doc=docs[0]
        return doc.related_that("replaces")

    return None

def validate_submission_rev(name, rev):
    if not rev:
        return 'Revision not found'

    try:
        rev = int(rev)
    except ValueError:
        return 'Revision must be a number'
    else:
        if not (0 <= rev <= 99):
            return 'Revision must be between 00 and 99'

        expected = 0
        existing_revs = [int(i.rev) for i in Document.objects.filter(name=name)]
        if existing_revs:
            expected = max(existing_revs) + 1

        if rev != expected:
            return 'Invalid revision (revision %02d is expected)' % expected

    replaced_by=has_been_replaced_by(name)
    if replaced_by:
        return 'This document has been replaced by %s' % ",".join(rd.name for rd in replaced_by)

    return None

def validate_submission_document_date(submission_date, document_date):
    if not document_date:
        return 'Document date is empty or not in a proper format'
    elif abs(submission_date - document_date) > datetime.timedelta(days=3):
        return 'Document date must be within 3 days of submission date'

    return None

def create_submission_event(request, submission, desc):
    by = None
    if request and request.user.is_authenticated:
        try:
            by = request.user.person
        except Person.DoesNotExist:
            pass

    SubmissionEvent.objects.create(submission=submission, by=by, desc=desc)

def docevent_from_submission(request, submission, desc, who=None):
    system = Person.objects.get(name="(System)")

    try:
        draft = Document.objects.get(name=submission.name)
    except Document.DoesNotExist:
        # Assume this is revision 00 - we'll do this later
        return

    if who:
        by = Person.objects.get(name=who)
    else:
        submitter_parsed = submission.submitter_parsed()
        if submitter_parsed["name"] and submitter_parsed["email"]:
            by, _ = ensure_person_email_info_exists(submitter_parsed["name"], submitter_parsed["email"])
        else:
            by = system

    e = SubmissionDocEvent.objects.create(
            doc=draft,
            by = by,
            type = "new_submission",
            desc = desc,
            submission = submission,
            rev = submission.rev,
        )
    return e

def post_rev00_submission_events(draft, submission, submitter):
    # Add previous submission events as docevents
    # For now we'll filter based on the description
    events = []
    for subevent in submission.submissionevent_set.all().order_by('id'):
        desc = subevent.desc
        if desc.startswith("Uploaded submission"):
            desc = "Uploaded new revision"
            e = SubmissionDocEvent(type="new_submission", doc=draft, submission=submission, rev=submission.rev )
        elif desc.startswith("Submission created"):
            e = SubmissionDocEvent(type="new_submission", doc=draft, submission=submission, rev=submission.rev)
        elif desc.startswith("Set submitter to"):
            pos = subevent.desc.find("sent confirmation email")
            e = SubmissionDocEvent(type="new_submission", doc=draft, submission=submission, rev=submission.rev)
            if pos > 0:
                desc = "Request for posting confirmation emailed %s" % (subevent.desc[pos + 23:])
            else:
                pos = subevent.desc.find("sent appproval email")
                if pos > 0:
                    desc = "Request for posting approval emailed %s" % (subevent.desc[pos + 19:])
        elif desc.startswith("Received message") or desc.startswith("Sent message"):
            e = AddedMessageEvent(type="added_message", doc=draft)
            e.message = subevent.submissionemailevent.message
            e.msgtype = subevent.submissionemailevent.msgtype
            e.in_reply_to = subevent.submissionemailevent.in_reply_to
        else:
            continue

        e.time = subevent.time #submission.submission_date
        e.by = submitter
        e.desc = desc
        e.save()
        events.append(e)
    return events


def post_submission(request, submission, approvedDesc):
    system = Person.objects.get(name="(System)")
    submitter_parsed = submission.submitter_parsed()
    if submitter_parsed["name"] and submitter_parsed["email"]:
        submitter, _ = ensure_person_email_info_exists(submitter_parsed["name"], submitter_parsed["email"])
        submitter_info = u'%s <%s>' % (submitter_parsed["name"], submitter_parsed["email"])
    else:
        submitter = system
        submitter_info = system.name

    # update draft attributes
    try:
        draft = Document.objects.get(name=submission.name)
    except Document.DoesNotExist:
        draft = Document.objects.create(name=submission.name, type_id="draft")

    prev_rev = draft.rev

    draft.type_id = "draft"
    draft.title = submission.title
    group = submission.group or Group.objects.get(type="individ")
    if not (group.type_id == "individ" and draft.group and draft.group.type_id == "area"):
        # don't overwrite an assigned area if it's still an individual
        # submission
        draft.group = group
    draft.rev = submission.rev
    draft.pages = submission.pages
    draft.abstract = submission.abstract
    was_rfc = draft.get_state_slug() == "rfc"

    if not draft.stream:
        stream_slug = None
        if draft.name.startswith("draft-iab-"):
            stream_slug = "iab"
        elif draft.name.startswith("draft-irtf-"):
            stream_slug = "irtf"
        elif draft.name.startswith("draft-ietf-") and (draft.group.type_id != "individ" or was_rfc):
            stream_slug = "ietf"

        if stream_slug:
            draft.stream = StreamName.objects.get(slug=stream_slug)

    draft.expires = datetime.datetime.now() + datetime.timedelta(settings.INTERNET_DRAFT_DAYS_TO_EXPIRE)

    events = []

    if draft.rev == '00':
        # Add all the previous submission events as docevents
        events += post_rev00_submission_events(draft, submission, submitter)

    # Add an approval docevent
    e = SubmissionDocEvent.objects.create(
        type="new_submission",
        doc=draft,
        by=system,
        desc=approvedDesc,
        submission=submission,
        rev=submission.rev,
    )
    events.append(e)

    # new revision event
    e = NewRevisionDocEvent.objects.create(
        type="new_revision",
        doc=draft,
        rev=draft.rev,
        by=submitter,
        desc="New version available: <b>%s-%s.txt</b>" % (draft.name, draft.rev),
    )
    events.append(e)

    # update related objects
    DocAlias.objects.get_or_create(name=submission.name, document=draft)

    draft.set_state(State.objects.get(used=True, type="draft", slug="active"))

    update_authors(draft, submission)

    draft.formal_languages = submission.formal_languages.all()

    trouble = rebuild_reference_relations(draft, filename=os.path.join(settings.IDSUBMIT_STAGING_PATH, '%s-%s.txt' % (submission.name, submission.rev)))
    if trouble:
        log.log('Rebuild_reference_relations trouble: %s'%trouble)
    
    if draft.stream_id == "ietf" and draft.group.type_id == "wg" and draft.rev == "00":
        # automatically set state "WG Document"
        draft.set_state(State.objects.get(used=True, type="draft-stream-%s" % draft.stream_id, slug="wg-doc"))

    # automatic state changes for IANA review
    if draft.get_state_slug("draft-iana-review") in ("ok-act", "ok-noact", "not-ok"):
        prev_state = draft.get_state("draft-iana-review")
        next_state = State.objects.get(used=True, type="draft-iana-review", slug="changed")
        draft.set_state(next_state)
        e = add_state_change_event(draft, system, prev_state, next_state)
        if e:
            events.append(e)

    state_change_msg = ""

    if not was_rfc and draft.tags.filter(slug="need-rev"):
        draft.tags.remove("need-rev")
        draft.tags.add("ad-f-up")

        e = DocEvent(type="changed_document", doc=draft, rev=draft.rev)
        e.desc = "Sub state has been changed to <b>AD Followup</b> from <b>Revised ID Needed</b>"
        e.by = system
        e.save()
        events.append(e)

        state_change_msg = e.desc

    if draft.stream_id == "ietf" and draft.group.type_id == "wg" and draft.rev == "00":
        # automatically set state "WG Document"
        draft.set_state(State.objects.get(used=True, type="draft-stream-%s" % draft.stream_id, slug="wg-doc"))

    # save history now that we're done with changes to the draft itself
    draft.save_with_history(events)

    # clean up old files
    if prev_rev != draft.rev:
        from ietf.doc.expire import move_draft_files_to_archive
        move_draft_files_to_archive(draft, prev_rev)

    move_files_to_repository(submission)
    submission.state = DraftSubmissionStateName.objects.get(slug="posted")

    new_replaces, new_possibly_replaces = update_replaces_from_submission(request, submission, draft)

    update_name_contains_indexes_with_new_doc(draft)

    announce_to_lists(request, submission)
    announce_new_version(request, submission, draft, state_change_msg)
    announce_to_authors(request, submission)

    if new_possibly_replaces:
        send_review_possibly_replaces_request(request, draft, submitter_info)

    submission.draft = draft
    submission.save()

def update_replaces_from_submission(request, submission, draft):
    if not submission.replaces:
        return [], []

    is_secretariat = has_role(request.user, "Secretariat")
    is_chair_of = []
    if request.user.is_authenticated:
        is_chair_of = list(Group.objects.filter(role__person__user=request.user, role__name="chair"))

    replaces = DocAlias.objects.filter(name__in=submission.replaces.split(",")).select_related("document", "document__group")
    existing_replaces = list(draft.related_that_doc("replaces"))
    existing_suggested = set(draft.related_that_doc("possibly-replaces"))

    submitter_email = submission.submitter_parsed()["email"]

    approved = []
    suggested = []
    for r in replaces:
        if r in existing_replaces:
            continue

        rdoc = r.document

        if rdoc == draft:
            continue

        if (is_secretariat
            or (draft.group in is_chair_of and (rdoc.group.type_id == "individ" or rdoc.group in is_chair_of))
            or (submitter_email and rdoc.documentauthor_set.filter(email__address__iexact=submitter_email).exists())):
            approved.append(r)
        else:
            if r not in existing_suggested:
                suggested.append(r)


    try:
        by = request.user.person if request.user.is_authenticated else Person.objects.get(name="(System)")
    except Person.DoesNotExist:
        by = Person.objects.get(name="(System)")
    set_replaces_for_document(request, draft, existing_replaces + approved, by,
                              email_subject="%s replacement status set during submit by %s" % (draft.name, submission.submitter_parsed()["name"]))


    if suggested:
        possibly_replaces = DocRelationshipName.objects.get(slug="possibly-replaces")
        for r in suggested:
            RelatedDocument.objects.create(source=draft, target=r, relationship=possibly_replaces)

        DocEvent.objects.create(doc=draft, rev=draft.rev, by=by, type="added_suggested_replaces",
                                desc="Added suggested replacement relationships: %s" % ", ".join(d.name for d in suggested))

    return approved, suggested

def get_person_from_name_email(name, email):
    # try email
    if email and (email.startswith('unknown-email-') or is_valid_email(email)):
        persons = Person.objects.filter(email__address=email).distinct()
        if len(persons) == 1:
            return persons[0]
    else:
        persons = Person.objects.none()

    if not persons.exists():
        persons = Person.objects.all()

    # try full name
    p = persons.filter(alias__name=name).distinct()
    if p.exists():
        return p.first()

    return None

def ensure_person_email_info_exists(name, email):
    addr = email
    email = None
    person = get_person_from_name_email(name, addr)

    # make sure we have a person
    if not person:
        person = Person()
        person.name = name
        if isinstance(person.name, six.text_type):
            person.ascii = unidecode(person.name).decode('ascii')
        else:
            person.ascii = unaccent.asciify(person.name).decode('ascii')
        person.save()

    # make sure we have an email address
    if addr and (addr.startswith('unknown-email-') or is_valid_email(addr)):
        active = True
        addr = addr.lower()
    else:
        # we're in trouble, use a fake one
        active = False
        addr = u"unknown-email-%s" % person.plain_ascii().replace(" ", "-")

    try:
        email = person.email_set.get(address=addr)
    except Email.DoesNotExist:
        try:
            # An Email object pointing to some other person will not exist
            # at this point, because get_person_from_name_email would have
            # returned that person, but it's possible that an Email record
            # not associated with any Person exists
            email = Email.objects.get(address=addr,person__isnull=True)
        except Email.DoesNotExist:
            # most likely we just need to create it
            email = Email(address=addr)
            email.active = active

        email.person = person
        if email.time is None:
            email.time = datetime.datetime.now()
        email.save()

    return person, email

def update_authors(draft, submission):
    persons = []
    for order, author in enumerate(submission.authors):
        person, email = ensure_person_email_info_exists(author["name"], author.get("email"))

        a = DocumentAuthor.objects.filter(document=draft, person=person).first()
        if not a:
            a = DocumentAuthor(document=draft, person=person)

        a.email = email
        a.affiliation = author.get("affiliation") or ""
        a.country = author.get("country") or ""
        a.order = order
        a.save()
        log.assertion('a.email_id != "none"')

        persons.append(person)

    draft.documentauthor_set.exclude(person__in=persons).delete()

def cancel_submission(submission):
    submission.state = DraftSubmissionStateName.objects.get(slug="cancel")
    submission.save()

    remove_submission_files(submission)

def rename_submission_files(submission, prev_rev, new_rev):
    from ietf.submit.forms import SubmissionUploadForm
    for ext in SubmissionUploadForm.base_fields.keys():
        source = os.path.join(settings.IDSUBMIT_STAGING_PATH, '%s-%s.%s' % (submission.name, prev_rev, ext))
        dest = os.path.join(settings.IDSUBMIT_STAGING_PATH, '%s-%s.%s' % (submission.name, new_rev, ext))
        if os.path.exists(source):
            os.rename(source, dest)

def move_files_to_repository(submission):
    from ietf.submit.forms import SubmissionUploadForm
    for ext in SubmissionUploadForm.base_fields.keys():
        source = os.path.join(settings.IDSUBMIT_STAGING_PATH, '%s-%s.%s' % (submission.name, submission.rev, ext))
        dest = os.path.join(settings.IDSUBMIT_REPOSITORY_PATH, '%s-%s.%s' % (submission.name, submission.rev, ext))
        if os.path.exists(source):
            os.rename(source, dest)
        else:
            if os.path.exists(dest):
                log.log("Intended to move '%s' to '%s', but found source missing while destination exists.")
            elif ext in submission.file_types.split(','):
                raise ValueError("Intended to move '%s' to '%s', but found source and destination missing.")

def remove_submission_files(submission):
    for ext in submission.file_types.split(','):
        source = os.path.join(settings.IDSUBMIT_STAGING_PATH, '%s-%s%s' % (submission.name, submission.rev, ext))
        if os.path.exists(source):
            os.unlink(source)

def approvable_submissions_for_user(user):
    if not user.is_authenticated:
        return []

    res = Submission.objects.filter(state="grp-appr").order_by('-submission_date')
    if has_role(user, "Secretariat"):
        return res

    # those we can reach as chair
    return res.filter(group__role__name="chair", group__role__person__user=user)

def preapprovals_for_user(user):
    if not user.is_authenticated:
        return []

    posted = Submission.objects.distinct().filter(state="posted").values_list('name', flat=True)
    res = Preapproval.objects.exclude(name__in=posted).order_by("-time").select_related('by')
    if has_role(user, "Secretariat"):
        return res

    acronyms = [g.acronym for g in Group.objects.filter(role__person__user=user, type__in=("wg", "rg"))]

    res = res.filter(name__regex="draft-[^-]+-(%s)-.*" % "|".join(acronyms))

    return res

def recently_approved_by_user(user, since):
    if not user.is_authenticated:
        return []

    res = Submission.objects.distinct().filter(state="posted", submission_date__gte=since, rev="00").order_by('-submission_date')
    if has_role(user, "Secretariat"):
        return res

    # those we can reach as chair
    return res.filter(group__role__name="chair", group__role__person__user=user)

def expirable_submissions(older_than_days):
    cutoff = datetime.date.today() - datetime.timedelta(days=older_than_days)
    return Submission.objects.exclude(state__in=("cancel", "posted")).filter(submission_date__lt=cutoff)

def expire_submission(submission, by):
    submission.state_id = "cancel"
    submission.save()

    SubmissionEvent.objects.create(submission=submission, by=by, desc="Cancelled expired submission")
