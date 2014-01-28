'''
proc_utils.py

This module contains all the functions for generating static proceedings pages
'''
from django.conf import settings
from django.shortcuts import render_to_response
from ietf.group.models import Group, Role
from ietf.group.utils import get_charter_text
from ietf.meeting.helpers import get_schedule, meeting_updated
from ietf.meeting.models import Session, TimeSlot, Meeting, ScheduledSession
from ietf.doc.models import Document, RelatedDocument, DocEvent
from itertools import chain
from ietf.secr.proceedings.models import Registration
from ietf.secr.utils.document import get_rfc_num
from ietf.secr.utils.group import groups_by_session
from ietf.secr.utils.meeting import get_upload_root, get_proceedings_path, get_material, get_session
from models import InterimMeeting    # proxy model

from urllib2 import urlopen
import datetime
import glob
import os
import shutil
import stat

# -------------------------------------------------
# Helper Functions
# -------------------------------------------------
def mycomp(timeslot):
    '''
    This takes a timeslot object and returns a key to sort by the area acronym or None
    '''
    try:
        session = get_session(timeslot)
        group = session.group
        key = '%s:%s' % (group.parent.acronym, group.acronym)
    except AttributeError:
        key = None
    return key

def get_progress_stats(sdate,edate):
    '''
    This function takes a date range and produces a dictionary of statistics / objects for use
    in a progress report.
    '''
    data = {}
    data['sdate'] = sdate
    data['edate'] = edate

    # Activty Report Section
    new_docs = Document.objects.filter(type='draft').filter(docevent__type='new_revision',
                                                            docevent__newrevisiondocevent__rev='00',
                                                            docevent__time__gte=sdate,
                                                            docevent__time__lte=edate)
    data['new'] = new_docs.count()
    data['updated'] = 0
    data['updated_more'] = 0
    for d in new_docs:
        updates = d.docevent_set.filter(type='new_revision',time__gte=sdate,time__lte=edate).count()
        if updates > 1:
            data['updated'] += 1
        if updates > 2:
            data['updated_more'] +=1

    # calculate total documents updated, not counting new, rev=00
    result = set()
    events = DocEvent.objects.filter(doc__type='draft',time__gte=sdate,time__lte=edate)
    for e in events.filter(type='new_revision').exclude(newrevisiondocevent__rev='00'):
        result.add(e.doc)
    data['total_updated'] = len(result)

    # calculate sent last call
    data['last_call'] = events.filter(type='sent_last_call').count()

    # calculate approved
    data['approved'] = events.filter(type='iesg_approved').count()

    # get 4 weeks
    monday = Meeting.get_ietf_monday()
    cutoff = monday + datetime.timedelta(days=3)
    ff1_date = cutoff - datetime.timedelta(days=28)
    ff2_date = cutoff - datetime.timedelta(days=21)
    ff3_date = cutoff - datetime.timedelta(days=14)
    ff4_date = cutoff - datetime.timedelta(days=7)

    ff_docs = Document.objects.filter(type='draft').filter(docevent__type='new_revision',
                                                           docevent__newrevisiondocevent__rev='00',
                                                           docevent__time__gte=ff1_date,
                                                           docevent__time__lte=cutoff)
    ff_new_count = ff_docs.count()
    ff_new_percent = format(ff_new_count / float(data['new']),'.0%')

    # calculate total documents updated in final four weeks, not counting new, rev=00
    result = set()
    events = DocEvent.objects.filter(doc__type='draft',time__gte=ff1_date,time__lte=cutoff)
    for e in events.filter(type='new_revision').exclude(newrevisiondocevent__rev='00'):
        result.add(e.doc)
    ff_update_count = len(result)
    ff_update_percent = format(ff_update_count / float(data['total_updated']),'.0%')

    data['ff_new_count'] = ff_new_count
    data['ff_new_percent'] = ff_new_percent
    data['ff_update_count'] = ff_update_count
    data['ff_update_percent'] = ff_update_percent

    # Progress Report Section
    data['docevents'] = DocEvent.objects.filter(doc__type='draft',time__gte=sdate,time__lte=edate)
    data['action_events'] = data['docevents'].filter(type='iesg_approved')
    data['lc_events'] = data['docevents'].filter(type='sent_last_call')

    data['new_groups'] = Group.objects.filter(type='wg',
                                              groupevent__changestategroupevent__state='active',
                                              groupevent__time__gte=sdate,
                                              groupevent__time__lte=edate)

    data['concluded_groups'] = Group.objects.filter(type='wg',
                                                    groupevent__changestategroupevent__state='conclude',
                                                    groupevent__time__gte=sdate,
                                                    groupevent__time__lte=edate)

    data['new_docs'] = Document.objects.filter(type='draft').filter(docevent__type='new_revision',
                                                                    docevent__time__gte=sdate,
                                                                    docevent__time__lte=edate).distinct()

    data['rfcs'] = DocEvent.objects.filter(type='published_rfc',
                                           doc__type='draft',
                                           time__gte=sdate,
                                           time__lte=edate)

    # attach the ftp URL for use in the template
    for event in data['rfcs']:
        num = get_rfc_num(event.doc)
        event.ftp_url = 'ftp://ftp.ietf.org/rfc/rfc%s.txt' % num

    data['counts'] = {'std':data['rfcs'].filter(doc__intended_std_level__in=('ps','ds','std')).count(),
                      'bcp':data['rfcs'].filter(doc__intended_std_level='bcp').count(),
                      'exp':data['rfcs'].filter(doc__intended_std_level='exp').count(),
                      'inf':data['rfcs'].filter(doc__intended_std_level='inf').count()}

    return data

def write_html(path,content):
    f = open(path,'w')
    f.write(content)
    f.close()
    try:
        os.chmod(path, 0664)
    except OSError:
        pass
# -------------------------------------------------
# End Helper Functions
# -------------------------------------------------

def create_interim_directory():
    '''
    Create static Interim Meeting directory pages that will live in a different URL space than
    the secretariat Django project
    '''

    # produce date sorted output
    page = 'proceedings.html'
    meetings = InterimMeeting.objects.order_by('-date')
    response = render_to_response('proceedings/interim_directory.html',{'meetings': meetings})
    path = os.path.join(settings.SECR_INTERIM_LISTING_DIR, page)
    f = open(path,'w')
    f.write(response.content)
    f.close()

    # produce group sorted output
    page = 'proceedings-bygroup.html'
    qs = InterimMeeting.objects.all()
    meetings = sorted(qs, key=lambda a: a.group().acronym)
    response = render_to_response('proceedings/interim_directory.html',{'meetings': meetings})
    path = os.path.join(settings.SECR_INTERIM_LISTING_DIR, page)
    f = open(path,'w')
    f.write(response.content)
    f.close()

def create_proceedings(meeting, group, is_final=False):
    '''
    This function creates the  proceedings html document.  It gets called anytime there is an
    update to the meeting or the slides for the meeting.
    NOTE: execution is aborted if the meeting is older than 79 because the format changed.
    '''
    # abort, proceedings from meetings before 79 have a different format, don't overwrite
    if meeting.type_id == 'ietf' and int(meeting.number) < 79:
        return

    sessions = Session.objects.filter(meeting=meeting,group=group)
    if sessions:
        session = sessions[0]
        agenda,minutes,slides = get_material(session)
    else:
        agenda = None
        minutes = None
        slides = None

    chairs = group.role_set.filter(name='chair')
    secretaries = group.role_set.filter(name='secr')
    if group.parent:        # Certain groups like Tools Team do no have a parent
        ads = group.parent.role_set.filter(name='ad')
    else:
        ads = None
    tas = group.role_set.filter(name='techadv')

    docs = Document.objects.filter(group=group,type='draft').order_by('time')

    meeting_root = get_upload_root(meeting)
    if meeting.type.slug == 'ietf':
        url_root = "%sproceedings/%s/" % (settings.MEDIA_URL,meeting.number)
    else:
        url_root = "%sproceedings/interim/%s/%s/" % (
            settings.MEDIA_URL,
            meeting.date.strftime('%Y/%m/%d'),
            group.acronym)

    # Only do these tasks if we are running official proceedings generation,
    # otherwise skip them for expediency.  This procedure is called any time meeting
    # materials are uploaded/deleted, and we don't want to do all this work each time.

    if is_final:
        # ----------------------------------------------------------------------
        # Find active Drafts and RFCs, copy them to id and rfc directories

        drafts = docs.filter(states__slug='active')
        for draft in drafts:
            source = os.path.join(draft.get_file_path(),draft.filename_with_rev())
            target = os.path.join(meeting_root,'id')
            if not os.path.exists(target):
                os.makedirs(target)
            if os.path.exists(source):
                shutil.copy(source,target)
                draft.bytes = os.path.getsize(source)
            else:
                draft.bytes = 0
            draft.url = url_root + "id/%s" % draft.filename_with_rev()

        rfcs = docs.filter(states__slug='rfc')
        for rfc in rfcs:
            # TODO should use get_file_path() here but is incorrect for rfcs
            rfc_num = get_rfc_num(rfc)
            filename = "rfc%s.txt" % rfc_num
            alias = rfc.docalias_set.filter(name='rfc%s' % rfc_num)
            source = os.path.join(settings.RFC_PATH,filename)
            target = os.path.join(meeting_root,'rfc')
            rfc.rmsg = ''
            rfc.msg = ''

            if not os.path.exists(target):
                os.makedirs(target)
            try:
                shutil.copy(source,target)
                rfc.bytes = os.path.getsize(source)
            except IOError:
                pass
            rfc.url = url_root + "rfc/%s" % filename
            rfc.num = "RFC %s" % rfc_num
            # check related documents
            # check obsoletes
            related = rfc.relateddocument_set.all()
            for item in related.filter(relationship='obs'):
                rfc.msg += 'obsoletes %s ' % item.target.name
                #rfc.msg += ' '.join(item.__str__().split()[1:])
            updates_list = [x.target.name.upper() for x in related.filter(relationship='updates')]
            if updates_list:
                rfc.msg += 'updates ' + ','.join(updates_list)
            # check reverse related
            rdocs = RelatedDocument.objects.filter(target=alias)
            for item in rdocs.filter(relationship='obs'):
                rfc.rmsg += 'obsoleted by RFC %s ' % get_rfc_num(item.source)
            updated_list = ['RFC %s' % get_rfc_num(x.source) for x in rdocs.filter(relationship='updates')]
            if updated_list:
                rfc.msg += 'updated by ' + ','.join(updated_list)
        # ----------------------------------------------------------------------
        # check for blue sheets
        pattern = os.path.join(meeting_root,'bluesheets','bluesheets-%s-%s-*' % (meeting.number,group.acronym.lower()))
        files = glob.glob(pattern)
        bluesheets = []
        for name in files:
            basename = os.path.basename(name)
            obj = {'name': basename,
                   'url': url_root + "bluesheets/" + basename}
            bluesheets.append(obj)
        bluesheets = sorted(bluesheets, key = lambda x: x['name'])
        # ----------------------------------------------------------------------
    else:
        drafts = rfcs = bluesheets = None

    # the simplest way to display the charter is to place it in a <pre> block
    # however, because this forces a fixed-width font, different than the rest of
    # the document we modify the charter by adding replacing linefeeds with <br>'s
    if group.charter:
        charter = get_charter_text(group).replace('\n','<br />')
        ctime = group.charter.time
    else:
        charter = None
        ctime = None


    # rather than return the response as in a typical view function we save it as the snapshot
    # proceedings.html
    response = render_to_response('proceedings/proceedings.html',{
        'bluesheets': bluesheets,
        'charter': charter,
        'ctime': ctime,
        'drafts': drafts,
        'group': group,
        'chairs': chairs,
        'secretaries': secretaries,
        'ads': ads,
        'tas': tas,
        'meeting': meeting,
        'rfcs': rfcs,
        'slides': slides,
        'minutes': minutes,
        'agenda': agenda}
    )

    # save proceedings
    proceedings_path = get_proceedings_path(meeting,group)

    f = open(proceedings_path,'w')
    f.write(response.content)
    f.close()
    try:
        os.chmod(proceedings_path, 0664)
    except OSError:
        pass

    # rebuild the directory
    if meeting.type.slug == 'interim':
        create_interim_directory()

# -------------------------------------------------
# Functions for generating Proceedings Pages
# -------------------------------------------------

def gen_areas(context):
    meeting = context['meeting']
    gmet, gnot = groups_by_session(None,meeting)

    # append proceedings URL
    for group in gmet + gnot:
        group.proceedings_url = "%sproceedings/%s/%s.html" % (settings.MEDIA_URL,meeting.number,group.acronym)

    for (counter,area) in enumerate(context['areas'], start=1):
        groups_met = {'wg':filter(lambda a: a.parent==area and a.state.slug not in ('bof','bof-conc') and a.type_id=='wg',gmet),
                      'bof':filter(lambda a: a.parent==area and a.state.slug in ('bof','bof-conc') and a.type_id=='wg',gmet),
                      'ag':filter(lambda a: a.parent==area and a.type_id=='ag',gmet)}

        groups_not = {'wg':filter(lambda a: a.parent==area and a.state.slug not in ('bof','bof-conc') and a.type_id=='wg',gnot),
                      'bof':filter(lambda a: a.parent==area and a.state.slug=='bof' and a.type_id=='wg',gnot),
                      'ag':filter(lambda a: a.parent==area and a.type_id=='ag',gnot)}

        html = render_to_response('proceedings/area.html',{
            'area': area,
            'meeting': meeting,
            'groups_met': groups_met,
            'groups_not': groups_not,
            'index': counter}
        )

        path = os.path.join(settings.SECR_PROCEEDINGS_DIR,meeting.number,'%s.html' % area.acronym)
        write_html(path,html.content)

def gen_acknowledgement(context):
    meeting = context['meeting']

    html = render_to_response('proceedings/acknowledgement.html',{
        'meeting': meeting}
    )

    path = os.path.join(settings.SECR_PROCEEDINGS_DIR,meeting.number,'acknowledgement.html')
    write_html(path,html.content)

def gen_agenda(context):
    meeting = context['meeting']
    schedule = get_schedule(meeting)
    scheduledsessions = ScheduledSession.objects.filter(schedule=schedule).exclude(session__isnull=True)

    html = render_to_response('proceedings/agenda.html',{
        'meeting': meeting,
        'scheduledsessions': scheduledsessions}
    )

    path = os.path.join(settings.SECR_PROCEEDINGS_DIR,meeting.number,'agenda.html')
    write_html(path,html.content)

    # get the text agenda from datatracker
    url = 'https://datatracker.ietf.org/meeting/%s/agenda.txt' % meeting.number
    text = urlopen(url).read()
    path = os.path.join(settings.SECR_PROCEEDINGS_DIR,meeting.number,'agenda.txt')
    write_html(path,text)

def gen_attendees(context):
    meeting = context['meeting']

    attendees = Registration.objects.using('ietf' + meeting.number).all().order_by('lname')

    html = render_to_response('proceedings/attendee.html',{
        'meeting': meeting,
        'attendees': attendees}
    )

    path = os.path.join(settings.SECR_PROCEEDINGS_DIR,meeting.number,'attendee.html')
    write_html(path,html.content)

def gen_group_pages(context):
    meeting = context['meeting']

    for group in Group.objects.filter(type__in=('wg','ag','rg'), state__in=('bof','proposed','active')):
        create_proceedings(meeting,group,is_final=True)

def gen_index(context):
    index = render_to_response('proceedings/index.html',context)
    path = os.path.join(settings.SECR_PROCEEDINGS_DIR,context['meeting'].number,'index.html')
    write_html(path,index.content)

def gen_irtf(context):
    meeting = context['meeting']
    irtf_chair = Role.objects.filter(group__acronym='irtf',name='chair')[0]

    html = render_to_response('proceedings/irtf.html',{
        'irtf_chair':irtf_chair}
    )
    path = os.path.join(settings.SECR_PROCEEDINGS_DIR,meeting.number,'irtf.html')
    write_html(path,html.content)

def gen_overview(context):
    meeting = context['meeting']

    ietf_chair = Role.objects.get(group__acronym='ietf',name='chair')
    ads = Role.objects.filter(group__type='area',group__state='active',name='ad')
    sorted_ads = sorted(ads, key = lambda a: a.person.name_parts()[3])

    html = render_to_response('proceedings/overview.html',{
        'meeting': meeting,
        'ietf_chair': ietf_chair,
        'ads': sorted_ads}
    )

    path = os.path.join(settings.SECR_PROCEEDINGS_DIR,meeting.number,'overview.html')
    write_html(path,html.content)

def gen_plenaries(context):
    '''
    This function generates pages for the Plenaries.  At meeting 85 the Plenary sessions
    were combined into one, so we need to handle not finding one of the sessions.
    '''
    meeting = context['meeting']

    # Administration Plenary
    try:
        admin_session = Session.objects.get(meeting=meeting,name__contains='Administration Plenary')
        admin_slides = admin_session.materials.filter(type='slides')
        admin_minutes = admin_session.materials.filter(type='minutes')
        admin = render_to_response('proceedings/plenary.html',{
            'title': 'Administrative',
            'meeting': meeting,
            'slides': admin_slides,
            'minutes': admin_minutes}
        )
        path = os.path.join(settings.SECR_PROCEEDINGS_DIR,context['meeting'].number,'administrative-plenary.html')
        write_html(path,admin.content)
    except Session.DoesNotExist:
        pass

    # Technical Plenary
    try:
        tech_session = Session.objects.get(meeting=meeting,name__contains='Technical Plenary')
        tech_slides = tech_session.materials.filter(type='slides')
        tech_minutes = tech_session.materials.filter(type='minutes')
        tech = render_to_response('proceedings/plenary.html',{
            'title': 'Technical',
            'meeting': meeting,
            'slides': tech_slides,
            'minutes': tech_minutes}
        )
        path = os.path.join(settings.SECR_PROCEEDINGS_DIR,context['meeting'].number,'technical-plenary.html')
        write_html(path,tech.content)
    except Session.DoesNotExist:
        pass

def gen_progress(context, final=True):
    '''
    This function generates the Progress Report.  This report is actually produced twice.  First
    for inclusion in the Admin Plenary, then for the final proceedings.  When produced the first
    time we want to exclude the headers because they are broken links until all the proceedings
    are generated.
    '''
    meeting = context['meeting']

    # proceedings are run sometime after the meeting, so end date = the previous meeting
    # date and start date = the date of the meeting before that
    now = datetime.date.today()
    meetings = Meeting.objects.filter(type='ietf',date__lt=now).order_by('-date')
    start_date = meetings[1].date
    end_date = meetings[0].date
    data = get_progress_stats(start_date,end_date)
    data['meeting'] = meeting
    data['final'] = final

    html = render_to_response('proceedings/progress.html',data)

    path = os.path.join(settings.SECR_PROCEEDINGS_DIR,meeting.number,'progress-report.html')
    write_html(path,html.content)

def gen_research(context):
    meeting = context['meeting']
    gmet, gnot = groups_by_session(None,meeting)

    groups = filter(lambda a: a.type_id=='rg', gmet)

    # append proceedings URL
    for group in groups:
        group.proceedings_url = "%sproceedings/%s/%s.html" % (settings.MEDIA_URL,meeting.number,group.acronym)

    html = render_to_response('proceedings/rg_irtf.html',{
        'meeting': meeting,
        'groups': groups}
    )

    path = os.path.join(settings.SECR_PROCEEDINGS_DIR,meeting.number,'rg_irtf.html')
    write_html(path,html.content)

def gen_training(context):
    meeting = context['meeting']
    timeslots = context['others']
    sessions = [ get_session(t) for t in timeslots ]
    for counter,session in enumerate(sessions, start=1):
        slides = session.materials.filter(type='slides')
        minutes = session.materials.filter(type='minutes')
        html = render_to_response('proceedings/training.html',{
            'title': '4.%s %s' % (counter, session.name),
            'meeting': meeting,
            'slides': slides,
            'minutes': minutes}
        )
        path = os.path.join(settings.SECR_PROCEEDINGS_DIR,meeting.number,'train-%s.html' % counter )
        write_html(path,html.content)

