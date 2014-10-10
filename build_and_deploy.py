import os.path
import ConfigParser
import subprocess
import mimetypes
import json
import argparse
from boto.s3.connection import S3Connection

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

from build_index_files import build_nodes, build_index_files

def do_build(name):
    print subprocess.check_output('./build.py %s' % (name), shell=True)

class ChBuildDir(object):
    def __enter__(self):
        cwd = self.original_cwd = os.getcwd()
        if os.path.split(cwd)[1] != 'build':
            os.chdir('build')
    def __exit__(self, *args):
        if os.getcwd() != self.original_cwd:
            os.chdir(self.original_cwd)

def archive_mobile():
    with ChBuildDir():
        if os.path.exists('mobile/mobile.zip'):
            os.remove('mobile/mobile.zip')
        print subprocess.check_output('zip -r mobile.zip mobile/*', shell=True)
        os.rename('mobile.zip', 'mobile/mobile.zip')

def deploy_s3cmd(bucket, cfg=None):
    options = '--acl-public --guess-mime-type'
    if cfg is not None:
        options = ' '.join([options, '-c', cfg])
    base_cmdstr = 's3cmd %s' % (options)
    dirnames = ['local', 'mobile']
    cmddata = {'bucket':bucket, 'base_cmd':base_cmdstr}
    cmdstr = '%(base_cmd)s sync %(dirname)s s3://%(bucket)s/%(dirname)s/'
    with ChBuildDir():
        for dirname in dirnames:
            print 'syncing %s with s3'
            cmddata['dirname'] = dirname
            s = subprocess.check_output(cmdstr % cmddata, shell=True)
    print 's3 sync complete'



def deploy_boto(bucket, credentials_file=None, do_uploads=True):
    if credentials_file is not None:
        confparse = ConfigParser.RawConfigParser()
        confparse.read(credentials_file)
        key_id = confparse.get('Credentials', 'aws_access_key_id')
        secret_key = confparse.get('Credentials', 'aws_secret_access_key')
        c = S3Connection(aws_access_key_id=key_id, aws_secret_access_key=secret_key)
    else:
        c = S3Connection()
    b = c.get_bucket(bucket)
    dirnames = ['local', 'mobile']
    with ChBuildDir():
        root_node = build_nodes(dirnames)
        for node in root_node.all_children.itervalues():
            print node.full_path
            if node.node_type == 'dir':
                continue
            k = b.get_key(node.full_path)
            if k is None:
                k = b.new_key(node.full_path)
                for attr in ['content_type', 'content_encoding']:
                    mimeval = getattr(node, attr)
                    if mimeval is None:
                        continue
                    k.set_metadata('-'.join(attr.split('_')), mimeval)
            k.set_contents_from_filename(node.full_path)
            k.make_public()
            print '%s uploaded' % (node.full_path)
        index_files = build_index_files(root_node)
        for index_file in index_files.itervalues():
            k = b.get_key(index_file.filename)
            if k is None:
                k = b.new_key(index_file.filename)
                k.set_metadata('content-type', 'text/html')
            k.set_contents_from_string(index_file.get_html())
            k.make_public()
    return root_node, index_files
                

def build_localsettings(base_url):
    local_url = '%s/local' % (base_url)
    mobile_url = '%s/mobile' % (base_url)
    d = {
        'local':{
            'resourceUrlBase': local_url,
            'distUrlBase': local_url,
        },
        'mobile':{
            'resourceUrlBase': mobile_url,
            'distUrlBase': mobile_url,
        },
    }
    s = json.dumps(d, indent=2)
    with open('localbuildsettings.json', 'w') as f:
        f.write(s)
        
        

def main():
    p = argparse.ArgumentParser()
    buildChoices = buildSettings.keys()[:]
    buildChoices.append('all')
    p.add_argument('-b', dest='builds', action='append', choices=buildChoices)
    p.add_argument('--no-builds', dest='no_builds', action='store_true')
    p.add_argument('--aws-credentials-file', dest='aws_credentials_file', help='(optional) custom credentials file')
    p.add_argument('--s3-bucket', dest='s3_bucket')
    p.add_argument('--build-url', dest='build_url', help='(optional) will be generated given the s3 bucket')
    args, remaining = p.parse_known_args()
    o = vars(args)
    if not o['no_builds']:
        if not o['build_url']:
            o['build_url'] = 'http://s3.amazonaws.com/%s' % (o['s3_bucket'])
        build_localsettings(o['build_url'])
        if not o['builds']:
            o['builds'] = [defaultBuild]
        if 'all' in o['builds']:
            o['builds'] = buildSettings.keys()[:]
        print 'builds: %s' % (o['builds'])
        for name in o['builds']:
            do_build(name)
        if 'mobile' in o['builds']:
            archive_mobile()
    deploy_boto(o['s3_bucket'], o['aws_credentials_file'])


if __name__ == '__main__':
    main()
        
