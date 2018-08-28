import os, sys
import traceback
from mimetypes import guess_type
from wsgiref.util import FileWrapper
import eventlet
from eventlet import wsgi
# get the lib dir onto the path
sys.path.append("/var/www/mindglass")
# set the MPLCONFIGDIR env var to something www-data
# can write to.
from lib import AppHandler, MyEnv, settings

APP_DIR = settings.APP_DIR
HOST = settings.HOST
PORT = settings.PORT
os.environ['MPLCONFIGDIR'] = APP_DIR


"""
chat handler

participants = set()

def handle(ws):
    participants.add(ws)
    try:
        while True:
            m = ws.wait()
            if m is None:
                break
            for p in participants:
                p.send(m)
    finally:
        participants.remove(ws)
                  
"""
BOOTSTRAP_LIST = [
    "import matplotlib",
    "matplotlib.use('SVG')",
    "from matplotlib import pyplot",
    "from matplotlib import mlab",
    "import scipy.io",
    "import warnings",
    "warnings.filterwarnings('ignore',category=FutureWarning)",
    "from lib.env_helpers import show_inline"
]
class MindGlass(object):

    def __init__(self):
        self.interp = MyEnv(bootstrap=BOOTSTRAP_LIST)
        self.sessions = {}

    def _handle_500(self):
        status = "500 SERVER ERROR"
        headers = [('Content-type', 'text/plain')]
        body = ("500 Internal Server Error\n",)
        return (status, headers, body)

    def _handle_404(self):
        status = "404 NOT FOUND"
        headers = [('Content-type', 'text/plain')]
        body = ("404 Not Found\n",)
        return (status, headers, body)

    def _handle_401(self, start_response):
        status = "401 UNAUTHORIZED"
        headers = [('Content-type', 'text/plain')]
        body = ("401 Unauthorized\n",)

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', u'/')
        method = environ.get('REQUEST_METHOD', '').upper()

        # handle root app request. Serves index.html
        if method == "GET" and path == u'/':
            file_path = os.path.join(APP_DIR,'static','mg.html')
            try:
                file_handle = file(file_path, 'rb')
                headers = [('Content-type', 'text/html')]
                start_response("200 OK", headers)
                return FileWrapper(file_handle)

            except (OSError, IOError):
                sys.stderr.write(traceback.format_exc())
                status, headers, body = self._handle_500()
                start_response(status, headers)
                return body
                
        # handle a file request.
        elif method == "GET" and '.' in path:
            if path.startswith('/'):
                path = path[1:]

            file_path = os.path.join(path)
            mimetype = guess_type(file_path)
            try:
                file_handle = file(file_path, 'rb')
                headers = [('Content-type', mimetype[0])]
                start_response("200 OK", headers)
                return FileWrapper(file_handle)

            except (OSError, IOError):
                sys.stderr.write(traceback.format_exc())
                status, headers, body = self._handle_404()
                start_response(status, headers)
                return body
             
        # everything else is a application resource request (REST Request)
        else:
            try:
                d = AppHandler(environ, self.interp, app_dir=APP_DIR)
                status, headers, body = d.dispatch(self.sessions)
                start_response(status, headers)
                return body
            except:
                sys.stderr.write(traceback.format_exc())
                status, headers, body = self._handle_404()
                start_response(status, headers)
                return body
            

if __name__ == "__main__":
    mgapp = MindGlass()
    # run an example app from the command line            
    listener = eventlet.listen((HOST, PORT))
    print "Servering on port %s ...\n\n Use Ctrl-C to stop" % PORT
    wsgi.server(listener, mgapp)
else:
   application = MindGlass()    
