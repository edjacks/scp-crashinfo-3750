#! /usr/bin/env python

"""
This program will ssh through a jumphost to a Cisco 3750 switch.  It will then
look for any crashinfo files on that switch and SCP them to the home directory
of the user on the jumphost.
"""

import getpass
import pexpect
import sys
import re

jumphost = 'somehost.somewhere.com'

def get_credentials():
    print('\nGathering usernames and passwords for network access.')
    i_user = raw_input('Enter username for {}: '.format(jumphost))
    if i_user == '':
        i_user = 'user'

    la_user_temp = 'la-' + i_user

    i_pass = getpass.getpass('Enter password for {}: '.format(jumphost))

    la_user = raw_input('Enter LA username [' + la_user_temp + ']: ')
    if la_user == '':
        la_user = la_user_temp

    la_pass = getpass.getpass('Enter LA password: ')

    return i_user, i_pass, la_user, la_pass



def open_jumphost(iuser, ipass):
    print('\nOpening connection to {}.'.format(jumphost))
    c = pexpect.spawn('ssh ' + iuser + '@' + jumphost, timeout=300)
    # uncomment the next line if you want to debug.. NOTE: passwords will be shown
    # c.logfile = sys.stdout
    c.expect('assword')
    c.sendline(ipass)
    c.expect('\$')
    c.sendline('HISTCONTROL=ignoreboth; export HISTCONTROL; set | grep -i histcon')
    c.expect('\$')

    return c



def login_to_switch(host,c,lu,lp):
    print('\nLogging into switch ' + host)
    c.sendline(' ssh ' + lu + '@' + host)
    c.expect('assword')
    c.sendline(lp)
    c.expect('#')
    c.sendline('term len 0')
    c.expect('#')



def get_crash_dirs(c):
    print('\nGathering crashinfo directories on switch.')
    c.sendline('show file systems | inc crashinfo')
    c.expect('#')

    dirs = []

    for line in c.before.splitlines():
        m = re.match('.*(crashinfo-[0-9]):.*', line)
        if m:
            dirs.append(m.group(1))

    print('crashinfo directories found:')
    print dirs

    return dirs



def get_crash_files(c):
    print('Gathering non-zero byte files in each crashinfo directory')

    dirs = get_crash_dirs(c)

    files = {}

    for dir in dirs:
        print(' - getting files in ' + dir)
        files[dir] = []

        c.sendline('dir ' + dir + ':')
        c.expect('#')
        o = c.before.splitlines()

        for line in o:
            l = line.split()
            if len(l) == 9:
                if l[2] != '0':
                    m = re.match('.*:[0-9][0-9] -[0-9][0-9]:[0-9][0-9]  ([a-z].*$)', line)
                    if m:
                        files[dir].append(m.group(1))

    return files



def scp_crash_files(c, iu, ip, host):
    print('\nBegin SCP of crashinfo files to {}'.format(jumphost))
    files = get_crash_files(c)

    for key in files:
        for item in files[key]:
            line = 'copy ' + key + ':' + item + ' scp://' + iu + '@' + jumphost + '/' + \
                   host + '_' + key + '_' + item

            print('\nIssuing: ' + line)

            c.sendline(line)
            c.expect(']\?')
            c.sendline('')
            c.expect(']\?')
            c.sendline('')
            c.expect(']\?')
            c.sendline('')
            c.expect('assword:')
            c.sendline(ip)
            c.expect('#')



def check_argv(args):
    if len(args) == 2:
        return True
    else:
        print '\n\n----------------------------'
        print args[0] + ' called incorrectly.  Please run ' + args[0]
        print 'with a single argument that is the switch you wish to'
        print 'scp the crashinfo files from.\n\n'
        return False



if __name__ == '__main__':
    if not check_argv(sys.argv):
        sys.exit()

    host = str(sys.argv[1])

    iu, ip, lu, lp = get_credentials()
    c = open_jumphost(iu, ip)
    login_to_switch(host, c, lu, lp)

    # files = get_crash_files(c)
    # print '\n\n------------------------------'
    # print 'files:'
    # print files
    # print '\n\n\n'

    scp_crash_files(c, iu, ip, host)
