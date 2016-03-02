#!/usr/bin/env python2.7
from os import path
from sys import argv, stdout
from uuid import uuid1
from paramiko import AutoAddPolicy, SSHClient, SSHConfig


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
    client.connect(**args)

    return (client, client.open_sftp())


if __name__ == "__main__":

    if len(argv) < 3:
        print 'usage: %s LOGIN cmd ...' % argv[0]
        exit(1)

    login = argv[1]
    cmd = ' '.join(argv[2:])

    (client, sftp) = connect(login)

    tempdir = 'at-' + str(uuid1())
    sftp.mkdir(tempdir)

    files = filter(lambda x: path.exists(x), cmd.split())
    remotefiles = map(lambda f: tempdir + '/' + f, files)

    map(lambda (f, r): sftp.put(f, r), zip(files, remotefiles))

    _, out, _ = client.exec_command('cd ' + tempdir + ' ; ' + cmd)

    stdout.write(out.read())

    map(lambda f: sftp.remove(f), remotefiles)
    sftp.rmdir(tempdir)

    sftp.close()
    client.close()
