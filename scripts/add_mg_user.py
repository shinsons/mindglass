#!/usr/bin/env python

import sys
from getpass import getpass
from hashlib import sha1

def new():
    try:
        db_file = file(sys.argv[1], 'a')
    except (IOError, AttributeError):
        print "Cannot read the db file."
        sys.exit(1)

    user = str(raw_input("User:"))
    passwd = getpass() 
    db_file.write("%s:%s\n" % (user,sha1(passwd).hexdigest()))
    db_file.close()

def modify(user):
    try:
        db_file = file(sys.argv[1], 'r')
        db = dict(tuple([tuple(l.split(":")) for l in db_file.read().split('\n') if len(l.split(":")) == 2]))
        db_file.close()
    except (IOError, AttributeError):
        print "Cannot read the db file."
        sys.exit(1)

    if user not in db:
        print "Cannot find user '%s'" % user
        sys.exit(1)

    db_file = file(sys.argv[1],'w')    
    new_pass = getpass('New Password:') 
    db[user] = sha1(new_pass).hexdigest()
    [db_file.write("%s:%s\n" % (k,v)) for k,v in db.items()]
    db_file.close()
    
if not len(sys.argv) >= 2:
    print "Takes an argument of the path to the db file."
    sys.exit(1)

if len(sys.argv) == 3:
    modify(sys.argv[2])
else:
    new()

     

