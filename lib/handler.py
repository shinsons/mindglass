import Cookie
import cPickle
from datetime import datetime, timedelta
import os, sys
import json
import logging
from hashlib import sha1
import traceback
import urlparse
from utils import Session, PersistentDict, format_ext, MyEnv, DOC_CODE
from uuid import uuid4
from settings import HOSTNAME, CONFIGURED_DOCS

class UnauthorizedException(Exception): pass
class BadCredentialsException(Exception): pass

class RequestHandler(object):
    
    def __init__(self, environ):
        self.environ = environ
        self.dispatch_map = {}
        self.request_path = self.environ.get('PATH_INFO',u'/')
        self.default_header = [('Content-type', 'application/json')]
        self.request_method = self.environ.get('REQUEST_METHOD', '').upper()
        if self.request_method == "GET":
            self._get_query_params()
        else:
            self.get_params = {}

        if self.request_method == "POST":
            self._get_post_data()
        else:
            self.post_params = {}
    
    def _get_query_params(self):
        if not self.environ.get('QUERY_STRING',None):
            self.get_params = {}
            return True
        self.get_params = dict(tuple(urlparse.parse_qsl(self.environ.get('QUERY_STRING'))))

    def _get_post_data(self):
        try:
            content_length = int(self.environ.get('CONTENT_LENGTH', 0))
            wsgi_socket = self.environ.get('wsgi.input')
        except (ValueError, TypeError):
            content_length = 0
        
        if content_length:
            self._raw_post_data = wsgi_socket.read(content_length)
        else:
            self._raw_post_data = wsgi_socket.read()

        self.post_params = self.make_post_dict()

    def make_post_dict(self):
        parsed = urlparse.parse_qs(self._raw_post_data,True,True)
        rdict = {}
        for k,v in parsed.items():
            if isinstance(v,list):
                rdict[k] = v[0]
                continue
            rdict[k] = v

        return rdict
            
    def handleNotAllowed(self):
        return ("405 METHOD NOT ALLOWED", self.default_header, "{}")

    def handleNotFound(self):
        return ("404 NOT FOUND", self.default_header, "{}")

    def dispatch(self):
        return self.dispatch_map.get(self.request_path, self.handleNotFound)()

class AuthHandler(object):
    """
        MixIn for classes that inherit from RequestHandler
        Later this will need to allow for writing
        to this file.
    """
    auth_initialized = False

    def auth_initialize(self, session_dict, app_dir=os.getcwd()):
        self.passwd_fname = app_dir + '/user.db'
        self._make_user_db()
        self.sessions = session_dict 
        self.auth_initialized = True

    def handleNotAuthorized(self, msg=None):
        rstruct = {}
        if msg:
            rstruct = {'msg' : msg} 

        return ("401 UNAUTHORIZED", self.default_header, format_ext(rstruct, success=False))

    def _make_user_db(self):
        self._user_db = {}
        entries = file(self.passwd_fname,'r').read().split('\n')
        self._user_db = dict(tuple([(entry.split(':')[0], entry.split(':')[1]) for entry in entries if entry]))

    def set_session(self,user):
        sess_id = str(uuid4())
        current_session = Session(
            username=user,
            sess_id = sess_id,
            created = datetime.now()
        )
        session_cookie = Cookie.SimpleCookie()
        session_cookie['session_id'] = sess_id
        session_cookie['session_id']['path'] = "/"
        # set the session
        self.sessions[sess_id] = current_session
        self.default_header.append(('Set-Cookie',session_cookie.output(header='').strip()))

    def get_session(self):
        try:
            session_cookie = Cookie.SimpleCookie(self.environ.get('HTTP_COOKIE', ""))
            session_morsel = session_cookie.get('session_id', Cookie.Morsel())
            current_session = self.sessions.get(session_morsel.value,
                Session(created=datetime(1970, 1,1)))
            if current_session.created < (datetime.now() - timedelta(hours=2)):
                self.sessions.pop(current_session.sess_id,None) 
            return bool(self.sessions.get(session_morsel.value, False))
        except:
            sys.stderr.write(traceback.format_exc())
            return False 

    def auth(self):
        if not self.auth_initialized:
            raise ImplementationError("Call initialize first")
        if self.get_session():
            return True
        user = self.post_params.get('user',None)
        passwd = self.post_params.get('passwd',None)
        if not self._user_db.get(user,False):
            raise UnauthorizedException
        if self._user_db.get(user,"") != sha1(passwd).hexdigest():
            raise BadCredentialsException

        self.set_session(user)
        return True

class AppHandler(RequestHandler, AuthHandler):
    
    def __init__(self, environ, interp, app_dir=os.getcwd(), enable_log=True):
        super(AppHandler, self).__init__(environ)
        self.interp = interp
        self.dispatch_map = {
            u'/auth/' : self.authRequest,
            u'/docs/' : self.docRequest,
            u'/files/' : self.filesRequest,
            u'/command/' : self.commandRequest
        }
        self.app_dir = app_dir
        self.enable_log = enable_log

        if enable_log:
            log_file = os.path.join(self.app_dir, 'log','process_log')
            logging.basicConfig(filename=log_file, level=logging.INFO)

    def filesRequest(self):
        if self.request_method != 'GET':
            return self.handelNotAllowed()

        data_files = [{'filename' : i, 'path' : ''.join((self.app_dir + '/data','/',i))} for i in os.listdir(self.app_dir + '/data')]
        return ("200 OK", self.default_header, format_ext(data_files))
            
    def docRequest(self):
        if self.request_method != 'GET':
            return self.handelNotAllowed()

        struct=[]
        node = self.get_params.get('node','')
        if not node or node == 'root':
            struct = [{
                'id'   : 'pyplot',
                'text' : 'pyplot',
                'root' : False
            },{
                'id'   : 'mlab',
                'text' : 'mlab',
                'root' : False
            },{
                'text' : 'show_inline',
                'cmd'  : 'show_inline(pyplot)',
                'leaf' : True
            },{
                'text' : 'reset_all',
                'cmd'  : 'reset_all()',
                'leaf' :  True
            }]
            return ("200 OK", self.default_header, format_ext(struct))

        doc_request = None
        pkg_parent = ''
        if node == 'pyplot':
            from matplotlib import pyplot as doc_request
            pkg_parent = 'pyplot'
        if node == 'mlab':
            from matplotlib import mlab as doc_request
            pkg_parent = 'mlab'
        if doc_request:
            for i in dir(doc_request):
                if i.startswith('_'):
                    continue
                struct.append(
                    {'text' : i,
                     'cmd'  : ''.join((pkg_parent,'.',i,'()')),
                     'leaf' : True
                })
        return ("200 OK", self.default_header, format_ext(struct))
   
    def commandRequest(self):
        cmd = self.post_params.get('cmd','')
        if 'reset_all' in cmd:
            self.interp.reinit()
            return ("200 OK", self.default_header, "")
       
        if self.enable_log:
            ip = self.environ.get('REMOTE_ADDR', 'Unknown')
            session_cookie = Cookie.SimpleCookie(self.environ.get('HTTP_COOKIE', ""))
            session_morsel = session_cookie.get('session_id', Cookie.Morsel())
            current_session = self.sessions.get(session_morsel.value,
                Session(created=datetime(1970, 1,1)))
            interp_id = id(self.interp)
            logging.info("[%s] %s - InterpID:%s PID:%s" % (ip,
                str(current_session),
                interp_id, 
                os.getpid()))

        res = self.interp.run(cmd)
        return ("200 OK", self.default_header, res)

    def authRequest(self):
        return ("200 OK", self.default_header, format_ext({}))
        
    def dispatch(self, session_dict):
        if not self.auth_initialized:
            self.auth_initialize(session_dict, app_dir=self.app_dir)
        try:
            if not self.auth():
                return self.handleNotAuthorized()
        except UnauthorizedException: 
            return self.handleNotAuthorized(msg="Unknown user")
        except BadCredentialsException:
            return self.handleNotAuthorized(msg="Bad Password")
        return self.dispatch_map.get(self.request_path, self.handleNotFound)()

