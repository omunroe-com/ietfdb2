# various authentication and authorization utilities

from django.utils.http import urlquote
from django.conf import settings
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.contrib.auth import REDIRECT_FIELD_NAME

from ietf.doc.models import Document
from ietf.person.models import Person
from ietf.group.models import Role

def user_is_person(user, person):
    """Test whether user is associated with person."""
    if not user.is_authenticated() or not person:
        return False

    if person.user_id == None:
        return False

    return person.user_id == user.id

def has_role(user, role_names):
    """Determines whether user has any of the given standard roles
    given. Role names must be a list or, in case of a single value, a
    string."""
    if isinstance(role_names, str) or isinstance(role_names, unicode):
        role_names = [ role_names ]
    
    if not user or not user.is_authenticated():
        return False

    # use cache to avoid checking the same permissions again and again
    if not hasattr(user, "roles_check_cache"):
        user.roles_check_cache = {}

    key = frozenset(role_names)
    if key not in user.roles_check_cache:
        try:
            person = user.get_profile()
        except Person.DoesNotExist:
            return False

        role_qs = {
	    "Area Director": Q(person=person, name__in=("pre-ad", "ad"), group__type="area", group__state="active"),
	    "Secretariat": Q(person=person, name="secr", group__acronym="secretariat"),
	    "IANA": Q(person=person, name="auth", group__acronym="iana"),
            "RFC Editor": Q(person=person, name="auth", group__acronym="rfceditor"),
	    "IAD": Q(person=person, name="admdir", group__acronym="ietf"),
	    "IETF Chair": Q(person=person, name="chair", group__acronym="ietf"),
	    "IAB Chair": Q(person=person, name="chair", group__acronym="iab"),
	    "WG Chair": Q(person=person,name="chair", group__type="wg", group__state="active"),
	    "WG Secretary": Q(person=person,name="secr", group__type="wg", group__state="active"),
            }

        filter_expr = Q()
        for r in role_names:
            filter_expr |= role_qs[r]

        user.roles_check_cache[key] = bool(Role.objects.filter(filter_expr)[:1])

    return user.roles_check_cache[key]


# convenient decorator

def passes_test_decorator(test_func, message):
    """Decorator creator that creates a decorator for checking that
    user passes the test, redirecting to login or returning a 403
    error. The test function should be on the form fn(user) ->
    true/false."""
    def decorate(view_func):
        def inner(request, *args, **kwargs):
            if not request.user.is_authenticated():
                return HttpResponseRedirect('%s?%s=%s' % (settings.LOGIN_URL, REDIRECT_FIELD_NAME, urlquote(request.get_full_path())))
            elif test_func(request.user):
                return view_func(request, *args, **kwargs)
            else:
                return HttpResponseForbidden(message)
        return inner
    return decorate

def role_required(*role_names):
    """View decorator for checking that the user is logged in and
    has one of the listed roles."""
    return passes_test_decorator(lambda u: has_role(u, role_names),
                                 "Restricted to role%s %s" % ("s" if len(role_names) != 1 else "", ", ".join(role_names)))

# specific permissions

def is_authorized_in_doc_stream(user, doc):
    """Return whether user is authorized to perform stream duties on
    document."""
    if has_role(user, ["Secretariat"]):
        return True

    if not doc.stream or not user.is_authenticated():
        return False

    # must be authorized in the stream or group

    group_req = None

    if doc.stream.slug == "ietf":
        if has_role(user, ["Area Director"]):
            return True
        if not doc.group.type == "individ":
            group_req = Q(group=doc.group)
    elif doc.stream.slug == "irtf":
        group_req = Q(group__acronym=doc.stream.slug) | Q(group=doc.group)
    elif doc.stream.slug in ("iab", "ise"):
        group_req = Q(group__acronym=doc.stream.slug)

    if not group_req:
        return False

    return bool(Role.objects.filter(Q(name__in=("chair", "delegate", "auth"), person__user=user) & group_req))

