# Create your views here.
import models
from django.shortcuts import render_to_response as render
import django.newforms as forms
from django.utils.html import escape, linebreaks
import ietf.utils
from ietf.proceedings.models import Meeting, MeetingTime, WgMeetingSession, SessionName, NonSession, MeetingVenue
from django.views.generic.list_detail import object_list

def default(request):
    """Default page, with links to sub-pages"""
    return render("meeting/list.html", {})

def showlist(request):
    """Display a list of existing disclosures"""
    return meeting_list(request, 'meeting/list.html')


# don't hide Python's builtin list creation -- call this something else than 'list()'
def meeting_list(request, template):
    """ Get A List of All Meetings That are in the system """  
    meetings  = Meeting.objects.all()
    
    return render(template,
        {
            'meetings' : meetings.order_by(* ['-start_date', ] ),
        } )

# Details views

def show_html_materials(request, meeting_num=None):
	return render("meeting/list.html",{})

def show_html_agenda(request, meeting_num=None):
    meeting_info=Meeting.objects.get(meeting_num=meeting_num)
    nonsession_info=NonSession.objects.filter(meeting=meeting_num,day_id__gte='0').order_by("day_id")
    meetingvenue_info=MeetingVenue.objects.get(meeting_num=meeting_num)
    queryset_list=MeetingTime.objects.filter(meeting=meeting_num).exclude(day_id=0).order_by("day_id","time_desc") 
    op_ad_plenary_agenda = "17:00 Welcome\n17:05 NOC report (Wieslaw Blysz, Siemens Networks))\n Host presentation (Georg Haubs, CTO Innovations of Siemens Networks)\n 17:20 IETF Chair and IAD short reports\n 17:30 Jonathan B. Postel award\n 17:40 NomCom Chair (Andrew Lange)\n 17:45 Open Microphone\n 19:30 (latest) end" #only for testing. In production, this text will be pulled from actualy agenda file
    #queryset_list=WgMeetingSession.objects.filter(meeting_num=meeting_num, group_acronym_id > -3) 

    # Due to a bug in Django@0.96 we can't use foreign key lookup in
    # order_by(), see http://code.djangoproject.com/ticket/2076.  Changeset
    # [133] is broken because it requires a patched Django to run.  Work
    # around this instead.  Later: FIXME (revert to the straightforward code
    # when this bug has been fixed in the Django release we're running.)
    ## queryset_list_sun=WgMeetingSession.objects.filter(meeting=meeting_num, sched_time_id1__day_id=0).order_by('sched_time_id1__time_desc')
    queryset_list_sun=list(WgMeetingSession.objects.filter(meeting=meeting_num, sched_time_id1__day_id=0))
    queryset_list_sun.sort(key=(lambda item: item.sched_time_id1.time_desc))
    return object_list(request,queryset=queryset_list, template_name='meeting/agenda.html',allow_empty=True, extra_context={'qs_sun':queryset_list_sun, 'meeting_info':meeting_info, 'meeting_num':meeting_num, 'nonsession_info':nonsession_info, 'meetingvenue_info':meetingvenue_info, 'op_ad_plenary_agenda':op_ad_plenary_agenda})

def show(request):
    return 0
