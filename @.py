#!/usr/bin/env python2.7
from os import path
from re import escape
from sys import argv, stdout, stderr
from uuid import uuid1
from getpass import getpass
from paramiko import AuthenticationException, AutoAddPolicy, SSHClient, SSHConfig


def lookup(configfile):
    config = SSHConfig()
    config.parse(open(configfile))
    res = config.lookup(login)
    if res.get('user'):
        res['username'] = res['user']
        del res['user']
    return res


def parse(login):
    usrhost = login.split('@')

    if len(usrhost) == 2:
        return {'username': usrhost[0], 'hostname': usrhost[1]}

    configfile = path.expanduser('~/.ssh/config')
    if path.exists(configfile):
        return lookup(configfile)

    return {'hostname': login}


def connect(login):
    client = SSHClient()
    args = parse(login)

    client.set_missing_host_key_policy(AutoAddPolicy())
    try:
        client.connect(**args)
    except AuthenticationException:
        args['password'] = getpass()
    try:
        client.connect(**args)
    except AuthenticationException:
        print 'Authentication error'
        exit(0)

    return (client, client.open_sftp())


def islocalfile(arg):
    return arg.startswith('@') and path.exists(path.expanduser(arg[1:]))


def sendfiles(cmd, verbose=False):
    tempdir = '@-' + str(uuid1())
    files = [(i, x[1:]) for i, x in enumerate(cmd) if islocalfile(x)]
    remotefiles = [(i, tempdir + '/' + f) for i, f in files]

    if not files:
        return cmd, lambda: None

    sftp.mkdir(tempdir)

    for (f, r) in zip(files, remotefiles):
        cmd[r[0]] = escape(r[1])
        sftp.put(f[1], r[1])
        if verbose:
            print '{0: <50}{1}'.format(f[1], '100%')

    if verbose:
        print '-' * 54

    def cleanup():
        map(lambda f: sftp.remove(f[1]), remotefiles)
        sftp.rmdir(tempdir)
        sftp.close()

    return cmd, cleanup


if __name__ == "__main__":

    if len(argv) < 3:
        print 'usage: %s LOGIN cmd ...' % argv[0]
        exit(1)

    login = argv[1]

    (client, sftp) = connect(login)

    cmd, cleanup = sendfiles(argv[2:], True)
    _, out, err = client.exec_command(' '.join(cmd))

    stderr.write(err.read())
    stdout.write(out.read())

    cleanup()
    client.close()
