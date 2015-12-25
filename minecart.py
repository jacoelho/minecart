#!/usr/bin/env python3
import os
import re
import sys
import time
import json
import stat
from shutil import rmtree
import tempfile
import subprocess

def log(msg):
  print("Log: {0}".format(msg))

def print_exit(msg):
  print("Failed: {0}".format(msg))
  sys.exit(1)

def test_command(command):
  return subprocess.call("command -v {0}".format(command),
    shell=True,
    stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0

def run_command(command, directory=None, logfile=subprocess.PIPE):
  log("running {0}".format(command))
  try:
    subprocess.check_call(command,
      shell=True,
      cwd=directory,
      stdout=logfile,
      stderr=logfile)
  except subprocess.CalledProcessError:
    print_exit("running command: {0}".format(command))

def install_packages(packages, logfile=subprocess.PIPE):
  log("installing {0}".format(packages))
  try:
    subprocess.check_call('apt-get update -q',
      shell=True,
      stdout=logfile,
      stderr=logfile)
  except subprocess.CalledProcessError:
    print_exit('running apt-get update')

  try:
    subprocess.check_call("apt-get install -y --no-install-recommends {0}".format(' '.join(packages)),
      env=dict(os.environ, DEBIAN_FRONTEND='noninteractive'),
      shell=True,
      stdout=logfile,
      stderr=logfile)
  except subprocess.CalledProcessError:
    print_exit('installing dependencies')

def install_fpm(logfile=subprocess.PIPE):
  if test_command('fpm'):
    return

  log("installing fpm")
  try:
    subprocess.check_call('gem install fpm --no-ri --no-rdoc --quiet',
      shell=True,
      stdout=logfile,
      stderr=logfile)
  except subprocess.CalledProcessError:
    print_exit('installing fpm')

def ruby_dev():
  if not test_command('ruby'):
    print_exit('ruby missing')

  version = subprocess.check_output('ruby -v', shell=True)

  match = re.search('(?P<major>\d\.\d)(?P<minor>\.\d)', str(version))

  if match.group('major') == "1.9":
    return "ruby1.9.1-dev"
  return "ruby{0}-dev".format(match.group('major'))

def ruby_version():
  if not test_command('ruby'):
    print_exit('ruby missing')

  version = subprocess.check_output('ruby -v', shell=True)

  match = re.search('(?P<major>\d\.\d)(?P<minor>\.\d)', str(version))

  if match.group('major') == "1.9":
    return "ruby{0}{1}".format(match.group('major'), match.group('minor'))
  return "ruby{0}".format(match.group('major'))

def disable_doc():
  with open('/etc/gemrc', 'w+') as stream:
    stream.write('install: --no-document\nupdate: --no-document\n')

def validate_file(data):
  paramvals = {
   'name': None,
   'maintainer': None,
   'vendor': None,
   'url': None,
   'user': None,
   'install_deps': None,
   'build_deps': None,
   'configuration_files': None,
   'install_directory': None,
   'instructions': None
  }

  for key in paramvals.keys():
     try:
       paramvals[key] = data[key]
     except KeyError as err:
       print("Missing parameter: {0}".format(err))
       sys.exit(1)

  for key in ['install_deps', 'build_deps', 'configuration_files', 'instructions']:
    if not isinstance(paramvals[key], list):
        print_exit("Invalid format \"{0}\" in dependencies".format(key))

  return paramvals

def capistrano_links(workdir=None, target=None, configs=None):
  shared = os.path.join(target, 'shared')

  os.makedirs(os.path.join(shared, 'tmp'), mode=0o755, exist_ok=True)
  os.symlink(os.path.join(shared, 'log', ''), os.path.join(workdir, 'log'))
  os.symlink(os.path.join(shared, 'pids', ''), os.path.join(workdir, 'tmp', 'pids'))

  if os.path.exists(os.path.join(workdir, 'public', 'system')):
    rmtree(os.path.join(workdir, 'public', 'system'), ignore_errors=True)
    os.symlink(os.path.join(shared, 'system', ''), os.path.join(workdir, 'public', 'system'))

  for config in configs:
    try:
      os.remove(os.path.join(workdir, config))
    except OSError:
      pass
    os.symlink(os.path.join(shared, config), os.path.join(workdir, config))

def post_install(workdir=None, user=None, path=None, name=None, version=None):
  script="""#!/bin/bash
set -e

case "$1" in
configure)
service_user="{user}"
service_home="{path}"

if ! id ${{service_user}} > /dev/null 2>&1 ; then
  adduser --system --group --no-create-home \
    --home ${{service_home}} --shell /bin/bash \
    --disabled-password \
    ${{service_user}}
fi

test -L {path}/{name}/current && rm {path}/{name}/current
ln -sf {path}/{name}/releases/{version}/ {path}/{name}/current
chown -R ${{service_user}}:${{service_user}} ${{service_home}}

# passenger restart
su -c "touch /{path}/{name}/current/tmp/restart.txt" -s /bin/sh {user}
;;
abort-upgrade|abort-remove|abort-deconfigure)
;;
esac
""".format(user=user, path=path, version=version, name=name)
  with open(os.path.join(workdir, 'postinst.sh'), 'w+') as stream:
    stream.write(script)

  os.chmod(os.path.join(workdir, 'postinst.sh'),  stat.S_IRWXU|stat.S_IRGRP|stat.S_IROTH)

def build_package(name=None, version=None, target=None, vendor=None, maintainer=None, url=None, workdir=None, dependencies=None, scripts_dir=None, logfile=subprocess.PIPE):
  command = """fpm -s dir -t deb -n {name} -v {version} -p {name}_{version}.deb \
--vendor {vendor} --maintainer {maintainer} --url "{url}" \
-C {workdir} \
--no-deb-use-file-permissions \
"""

  for dep in dependencies:
    command += "-d {0} ".format(dep)

  command += "--after-install={scripts_dir}/postinst.sh".format(scripts_dir=scripts_dir)
  command += " .={0}".format(os.path.join(target, name, 'releases', version))

  try:
    subprocess.check_call(command.format(
        name=name,
        version=version,
        vendor=vendor,
        maintainer=maintainer,
        url=url,
        workdir=workdir),
      shell=True,
      stdout=logfile,
      stderr=logfile)
  except subprocess.CalledProcessErr:
    print_exit('running fpm')

  log("created file {0}_{1}.deb".format(name, version))

if __name__ == "__main__":
  try:
    with open(sys.argv[1]) as stream:
      data = json.load(stream)
  except IndexError:
    print_exit("pass package manifest as argument: ./minecart.py <manifest>")
  except ValueError:
    print_exit("invalid file")
  except:
    print_exit("failed to process file")

  cfg = validate_file(data)
  buildtime = time.strftime("%Y%m%d%H%M%S", time.gmtime())
  logf = "build-{0}.log".format(buildtime)

  with open(logf, 'wb') as logfile:
    log("writing log to {0}".format(logf))

    install_packages(cfg['build_deps'] + [ruby_dev(), 'bundler', 'build-essential', 'git-core'], logfile=logfile)

    install_fpm(logfile=logfile)

    with tempfile.TemporaryDirectory() as tmpdir:
      fpm_dir = os.path.join(tmpdir, 'fpm')
      scripts_dir = os.path.join(tmpdir, 'scripts')
      os.makedirs(fpm_dir, mode=0o755)
      os.makedirs(scripts_dir, mode=0o755)

      for instruction in cfg['instructions']:
        run_command(instruction, directory=fpm_dir, logfile=logfile)

      # capistrano like directories
      capistrano_links(workdir=fpm_dir,
        target=os.path.join(cfg['install_directory'], cfg['name']),
        configs=cfg['configuration_files'])

      post_install(
        workdir=scripts_dir,
        user=cfg['user'],
        path=cfg['install_directory'],
        name=cfg['name'],
        version=buildtime
      )

      # unique entries only
      deps = list(set(cfg['install_deps'] + [ ruby_version(), 'bundler']))
      log("Package dependencies: {0}".format(deps))

      build_package(
        name=cfg['name'],
        version=buildtime,
        target=cfg['install_directory'],
        scripts_dir=scripts_dir,
        vendor=cfg['vendor'],
        maintainer=cfg['maintainer'],
        url=cfg['url'],
        workdir=fpm_dir,
        dependencies=deps,
        logfile=logfile
      )
