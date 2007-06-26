from django.conf import settings
from ietf import __date__, __rev__, __version__, __id__
from ietf.utils import log

def server_mode(request):
    return {'server_mode': settings.SERVER_MODE}
    
def revision_info(request):
    return {'revision_time': __date__[7:32], 'revision_date': __date__[34:-3], 'revision_num': __rev__[6:-2], "revision_id": __id__[5:-2], "version_num": __version__ }
