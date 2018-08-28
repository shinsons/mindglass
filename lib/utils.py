import os, sys
from datetime import datetime
import code
import cPickle
import json
from StringIO import StringIO

DOC_CODE = """
from matplotlib import pyplot
r={}
for i in dir(pyplot):
    r[i]=pyplot.__dict__[i].__doc__
print r
"""
def format_ext(struct, success=True):
    ext_struct = {
        'success' : success,
        'total'   : len(struct),
        'data'    : ''
    }
    # assumes that the string is a
    # json data structure. Allow encoding
    # errors to fall through.
    if isinstance(struct, str):
        struct = json.loads(struct)

    ext_struct['data'] = struct
    return json.dumps(ext_struct)

class Session(object):
    def __init__(self,**kwargs):
        self.username = kwargs.get('username','')
        self.sess_id = kwargs.get('sess_id', 0)
        self.interp_id = kwargs.get('interp_id',0)
        self.created = kwargs.get('created', datetime.now())

    def __str__(self):
        return "<%s - %s>" % (self.username, self.sess_id)

class PersistentDict(dict):

    def __init__(self, name):
        self.name = name
        self._set_file()
        super(PersistentDict, self).__init__()

    def __del__(self):
        self._file.close()

    def dump(self):
        return format_ext(self)

    def load(self,struct):
        outd = {}
        self.clear()
        for key,value in struct.items():
            self[key] = value
            outd[key] = value

        self._file.seek(0)
        self._file.write('')
        cPickle.dump(outd, self._file)
        self._file.flush()

    def _set_file(self):
        
        # error handling is implemented back up the stack.
        pickle_name = self.name + '.pickle'
        if os.path.exists(pickle_name):
            self._file = file(pickle_name,'rb+')
            try:
                contents = cPickle.load(self._file)
            except EOFError:
                contents = {}
            for key,value in contents.items():
                self[key] = value
        else:
            self._file = file(pickle_name, 'wb+')

class MyEnv(object):

    def __init__(self, bootstrap=[], fmt='html'):
        self.interp = code.InteractiveConsole()
        self.orig_stdout = sys.stdout
        self.orig_stderr = sys.stderr

        self.bootstrap_config = bootstrap
        self.interp_out = StringIO()

        if fmt == 'html':
            self.LINE_ENDING = '<br />'
        else:
            self.LINE_ENDING = '\n'

        self._bootstrapenv()

    def _bootstrapenv(self):
        for line in self.bootstrap_config:
            self.run(line, echo=False)

    def reinit(self):
        del self.interp
        self.interp = code.InteractiveConsole()
        self._bootstrapenv()

    def run(self,cmd, echo=True, report_last=True):
        interp_out = StringIO()
        sys.stdout = interp_out
        sys.stderr = interp_out
        if echo:
            interp_out.write(">>> " + cmd + "\n")
        self.interp.push(cmd)
        out = interp_out.getvalue()
        out = out.replace("\n",self.LINE_ENDING)
        sys.stdout = self.orig_stdout
        sys.stderr = self.orig_stderr
        return out
