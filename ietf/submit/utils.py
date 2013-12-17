import os
import re
import datetime

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse as urlreverse
from django.template.loader import render_to_string

from ietf.utils.mail import send_mail, send_mail_message
from ietf.utils.log import log
from ietf.utils import unaccent
from ietf.ietfauth.utils import has_role

from ietf.submit.models import Submission, SubmissionEvent, Preapproval, DraftSubmissionStateName
from ietf.doc.models import *
from ietf.person.models import Person, Alias, Email
from ietf.doc.utils import add_state_change_event, rebuild_reference_relations
from ietf.message.models import Message
from ietf.utils.pipe import pipe
from ietf.utils.log import log
from ietf.submit.mail import announce_to_lists, announce_new_version, announce_to_authors

def check_idnits(path):
    #p = subprocess.Popen([self.idnits, '--submitcheck', '--nitcount', path], stdout=subprocess.PIPE)
    cmd = "%s --submitcheck --nitcount %s" % (settings.IDSUBMIT_IDNITS_BINARY, path)
    code, out, err = pipe(cmd)
    if code != 0:
        log("idnits error: %s:\n  Error %s: %s" %( cmd, code, err))
    return out

def found_idnits(idnits_message):
    if not idnits_message:
        return False
    success_re = re.compile('\s+Summary:\s+0\s+|No nits found')
    if success_re.search(idnits_message):
        return True
    return False

def validate_submission(submission):
    errors = {}

    if submission.state_id not in ("cancel", "posted"):
        for ext in submission.file_types.split(','):
            source = os.path.join(settings.IDSUBMIT_STAGING_PATH, '%s-%s%s' % (submission.name, submission.rev, ext))
            if not os.path.exists(source):
                errors['files'] = '"%s" was not found in the staging area.<br />We recommend you that you cancel this submission and upload your files again.' % os.path.basename(source)
                break

    if not submission.title:
        errors['title'] = 'Title is empty or was not found'

    if submission.group and submission.group.state_id != "active":
        errors['group'] = 'Group exists but is not an active group'

    if not submission.abstract:
        errors['abstract'] = 'Abstract is empty or was not found'

    if not submission.authors_parsed():
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

    return None

def validate_submission_document_date(submission_date, document_date):
    if not document_date:
        return 'Document date is empty or not in a proper format'
    elif abs(submission_date - document_date) > datetime.timedelta(days=3):
        return 'Document date must be within 3 days of submission date'

    return None

def create_submission_event(request, submission, desc):
    by = None
    if request and request.user.is_authenticated():
        try:
            by = request.user.person
        except Person.DoesNotExist:
            pass

    SubmissionEvent.objects.create(submission=submission, by=by, desc=desc)


def post_submission(request, submission):
    system = Person.objects.get(name="(System)")

    try:
        draft = Document.objects.get(name=submission.name)
        save_document_in_history(draft)
    except Document.DoesNotExist:
        draft = Document(name=submission.name)
        draft.intended_std_level = None

    prev_rev = draft.rev

    draft.type_id = "draft"
    draft.time = datetime.datetime.now()
    draft.title = submission.title
    group = submission.group or Group.objects.get(type="individ")
    if not (group.type_id == "individ" and draft.group and draft.group.type_id == "area"):
        # don't overwrite an assigned area if it's still an individual
        # submission
        draft.group_id = group.pk
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
    draft.save()

    submitter_parsed = submission.submitter_parsed()
    if submitter_parsed["name"] and submitter_parsed["email"]:
        submitter = ensure_person_email_info_exists(submitter_parsed["name"], submitter_parsed["email"]).person
    else:
        submitter = system

    draft.set_state(State.objects.get(used=True, type="draft", slug="active"))
    DocAlias.objects.get_or_create(name=submission.name, document=draft)

    update_authors(draft, submission)

    rebuild_reference_relations(draft)

    # new revision event
    e = NewRevisionDocEvent(type="new_revision", doc=draft, rev=draft.rev)
    e.time = draft.time #submission.submission_date
    e.by = submitter
    e.desc = "New version available: <b>%s-%s.txt</b>" % (draft.name, draft.rev)
    e.save()

    if draft.stream_id == "ietf" and draft.group.type_id == "wg" and draft.rev == "00":
        # automatically set state "WG Document"
        draft.set_state(State.objects.get(used=True, type="draft-stream-%s" % draft.stream_id, slug="wg-doc"))

    if draft.get_state_slug("draft-iana-review") in ("ok-act", "ok-noact", "not-ok"):
        prev_state = draft.get_state("draft-iana-review")
        next_state = State.objects.get(used=True, type="draft-iana-review", slug="changed")
        draft.set_state(next_state)
        add_state_change_event(draft, submitter, prev_state, next_state)

    # clean up old files
    if prev_rev != draft.rev:
        from ietf.doc.expire import move_draft_files_to_archive
        move_draft_files_to_archive(draft, prev_rev)

    # automatic state changes
    state_change_msg = ""

    if not was_rfc and draft.tags.filter(slug="need-rev"):
        draft.tags.remove("need-rev")
        draft.tags.add("ad-f-up")

        e = DocEvent(type="changed_document", doc=draft)
        e.desc = "Sub state has been changed to <b>AD Followup</b> from <b>Revised ID Needed</b>"
        e.by = system
        e.save()

        state_change_msg = e.desc

    move_files_to_repository(submission)
    submission.state = DraftSubmissionStateName.objects.get(slug="posted")

    announce_to_lists(request, submission)
    announce_new_version(request, submission, draft, state_change_msg)
    announce_to_authors(request, submission)

    submission.save()


def get_person_from_name_email(name, email):
    # try email
    if email:
        persons = Person.objects.filter(email__address=email).distinct()
        if len(persons) == 1:
            return persons[0]
    else:
        persons = Person.objects.none()

    if not persons:
        persons = Person.objects.all()

    # try full name
    p = persons.filter(alias__name=name).distinct()
    if p:
        return p[0]

    return None

def ensure_person_email_info_exists(name, email):
    person = get_person_from_name_email(name, email)

    # make sure we have a person
    if not person:
        person = Person()
        person.name = name
        person.ascii = unaccent.asciify(person.name)
        person.save()

        Alias.objects.create(name=person.name, person=person)
        if person.name != person.ascii:
            Alias.objects.create(name=ascii, person=person)

    # make sure we have an email address
    if email:
        addr = email.lower()
    else:
        # we're in trouble, use a fake one
        addr = u"unknown-email-%s" % person.name.replace(" ", "-")

    try:
        email = person.email_set.get(address=addr)
    except Email.DoesNotExist:
        try:
            # maybe it's pointing to someone else
            email = Email.objects.get(address=addr)
        except Email.DoesNotExist:
            # most likely we just need to create it
            email = Email(address=addr)
            email.active = False

        email.person = person
        email.save()

    return email

def update_authors(draft, submission):
    authors = []
    for order, author in enumerate(submission.authors_parsed()):
        email = ensure_person_email_info_exists(author["name"], author["email"])

        a = DocumentAuthor.objects.filter(document=draft, author=email)
        if a:
            a = a[0]
        else:
            a = DocumentAuthor(document=draft, author=email)

        a.order = order
        a.save()

        authors.append(email)

    draft.documentauthor_set.exclude(author__in=authors).delete()

def cancel_submission(submission):
    submission.state = DraftSubmissionStateName.objects.get(slug="cancel")
    submission.save()

    remove_submission_files(submission)

def rename_submission_files(submission, prev_rev, new_rev):
    for ext in submission.file_types.split(','):
        source = os.path.join(settings.IDSUBMIT_STAGING_PATH, '%s-%s%s' % (submission.name, prev_rev, ext))
        dest = os.path.join(settings.IDSUBMIT_STAGING_PATH, '%s-%s%s' % (submission.name, new_rev, ext))
        os.rename(source, dest)

def move_files_to_repository(submission):
    for ext in submission.file_types.split(','):
        source = os.path.join(settings.IDSUBMIT_STAGING_PATH, '%s-%s%s' % (submission.name, submission.rev, ext))
        dest = os.path.join(settings.IDSUBMIT_REPOSITORY_PATH, '%s-%s%s' % (submission.name, submission.rev, ext))
        if os.path.exists(source):
            os.rename(source, dest)
        else:
            if os.path.exists(dest):
                log("Intended to move '%s' to '%s', but found source missing while destination exists.")
            else:
                raise ValueError("Intended to move '%s' to '%s', but found source and destination missing.")

def remove_submission_files(submission):
    for ext in submission.file_types.split(','):
        source = os.path.join(settings.IDSUBMIT_STAGING_PATH, '%s-%s%s' % (submission.name, submission.rev, ext))
        if os.path.exists(source):
            os.unlink(source)

def approvable_submissions_for_user(user):
    if not user.is_authenticated():
        return []

    res = Submission.objects.filter(state="grp-appr").order_by('-submission_date')
    if has_role(user, "Secretariat"):
        return res

    # those we can reach as chair
    return res.filter(group__role__name="chair", group__role__person__user=user)

def preapprovals_for_user(user):
    if not user.is_authenticated():
        return []

    posted = Submission.objects.distinct().filter(state="posted").values_list('name', flat=True)
    res = Preapproval.objects.exclude(name__in=posted).order_by("-time").select_related('by')
    if has_role(user, "Secretariat"):
        return res

    acronyms = [g.acronym for g in Group.objects.filter(role__person__user=user, type="wg")]

    res = res.filter(name__regex="draft-[^-]+-(%s)-.*" % "|".join(acronyms))

    return res

def recently_approved_by_user(user, since):
    if not user.is_authenticated():
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

    SubmissionEvent.objects.create(submission=submission, by=by, desc="Canceled expired submission")
