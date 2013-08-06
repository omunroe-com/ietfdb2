from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.http import urlquote

from ietf.ietfauth.decorators import passes_test_decorator

from ietf.nomcom.utils import get_nomcom_by_year


def nomcom_member_required(role=None):
    def _is_nomcom_member(user, *args, **kwargs):
        year = kwargs.get('year', None)
        if year:
            nomcom = get_nomcom_by_year(year=year)
            if role == 'chair':
                return nomcom.group.is_chair(user)
            else:
                return nomcom.group.is_member(user)
        return False
    return passes_test_decorator(_is_nomcom_member, 'Restricted to NomCom %s' % role)


def nomcom_private_key_required(view_func):
    def inner(request, *args, **kwargs):
        year = kwargs.get('year', None)
        if not year:
            raise Exception, 'View decorated with nomcom_private_key_required must receive a year argument'
        if not 'NOMCOM_PRIVATE_KEY_%s' % year in request.session:
            return HttpResponseRedirect('%s?back_to=%s' % (reverse('nomcom_private_key', None, args=(year, )), urlquote(request.get_full_path())))
        else:
            return view_func(request, *args, **kwargs)
    return inner
