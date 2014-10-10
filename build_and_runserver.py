import os.path
import subprocess
import argparse
import SocketServer
import SimpleHTTPServer

# load settings file
from buildsettings import buildSettings

# load option local settings file
try:
    from localbuildsettings import buildSettings as localBuildSettings
    buildSettings.update(localBuildSettings)
except ImportError:
    pass

# load default build
try:
    from localbuildsettings import defaultBuild
except ImportError:
    defaultBuild = None


buildName = defaultBuild

def do_build(name):
    print subprocess.check_output('./build.py %s' % (name), shell=True)

def archive_mobile():
    cwd = os.getcwd()
    if os.path.split(cwd)[1] != 'build':
        os.chdir('build')
    if os.path.exists('mobile.zip'):
        os.remove('mobile.zip')
    print subprocess.check_output('zip -r mobile.zip mobile/*', shell=True)
    os.chdir(cwd)

def run_server(port):
    os.chdir('build')
    h = SimpleHTTPServer.SimpleHTTPRequestHandler
    httpd = SocketServer.TCPServer(('', port), h)
    print 'running server...'
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print 'shutting down..'
        httpd.shutdown()

def main():
    p = argparse.ArgumentParser()
    buildChoices = buildSettings.keys()[:]
    buildChoices.append('all')
    p.add_argument('-b', dest='builds', action='append', choices=buildChoices)
    p.add_argument('--no-builds', dest='no_builds', action='store_true')
    p.add_argument('--no-server', dest='no_server', action='store_true')
    p.add_argument('-p', dest='port', type=int, default=8000, help='HTTP Port (default is 8000)')
    args, remaining = p.parse_known_args()
    o = vars(args)
    if not o['no_builds']:
        if not o['builds']:
            o['builds'] = [defaultBuild]
        if 'all' in o['builds']:
            o['builds'] = buildSettings.keys()[:]
        print 'builds: %s' % (o['builds'])
        for name in o['builds']:
            do_build(name)
        if 'mobile' in o['builds']:
            archive_mobile()
    if o['no_server']:
        return
    run_server(o['port'])


if __name__ == '__main__':
    main()
        
