from __future__ import print_function

import argparse
import os
import re
import shutil
import ssl
import subprocess
import sys
try:
  from urllib.request import urlretrieve
except ImportError:
  from urllib import urlretrieve
import uuid
import zipfile

class CommonConfig:
  def __init__(self, root_dir, pd_path):
    self.root_dir = root_dir
    self.pd_path = pd_path

    self.flext_dir = os.path.join(self.root_dir, "flext")
    self.py_dir = os.path.join(self.root_dir, "py")
    self.build_dir = os.path.join(self.root_dir, "build")
    self.flext_prefix = os.path.join(self.build_dir, "flext")
    self.py_package_dir = os.path.join(self.build_dir, "py")
    self.python_exe = sys.executable
    self.python_version = sys.version
  
class MacConfig:
  def __init__(self, common_cfg):
    self.common_cfg = common_cfg

    self.platform = "darwin"
    self.platform_alt = "mac"
    self.compiler = "gcc"

    self.pd_path = self.common_cfg.pd_path or self.find_pd()
    
    # python executable is at {conda_root}/bin/python
    self.conda_root = os.path.dirname(os.path.dirname(self.common_cfg.python_exe))

    self.flext_build_env = {
      #"BUILDMODE": "debug",
      #"TARGETMODE": "debug",
      "FLEXT_PD_APP": self.pd_path,
      "FLEXT_INSTALL_PATH": self.common_cfg.py_package_dir,
      "FLEXTPREFIX": self.common_cfg.flext_prefix
    }
    
    self.py_build_env = {
      **self.flext_build_env,
      "PY_CONDA_ROOT": self.conda_root
    }

    self.build_cmd = ("bash", os.path.join(self.common_cfg.flext_dir, "build.sh"))

    self.platform_output_name = "pd-darwin"
    
  def find_pd(self):
    apps_dir = "/Applications"

    if not os.path.exists(apps_dir):
      return None
    
    pd_re = re.compile(r"^Pd-(\d+(?:[-.]\d+)*)\.app$")
    ver_delim_re = re.compile(r"[-.]")
    
    pd_apps = ((app, pd_re.match(app)) for app in os.listdir(apps_dir))
    pd_apps = ((app, map(int, ver_delim_re.split(m.group(1)))) for app, m in pd_apps if m != None)
    pd_apps = list(pd_apps)

    if len(pd_apps) == 0:
      return None

    max_app = max(pd_apps, key = lambda x: x[0])[0]
    return os.path.join(apps_dir, max_app)

class WinConfig:
  def __init__(self, common_cfg):
    self.common_cfg = common_cfg

    self.platform = "win"
    self.platform_alt = "win"
    self.compiler = "mingw"

    self.pd_path = self.common_cfg.pd_path or self.find_pd()

    # python executable is at {conda_root}/python.exe
    self.conda_root = os.path.dirname(self.common_cfg.python_exe)

    self.flext_build_env = {
      "FLEXT_INSTALL_PATH": self.common_cfg.py_package_dir,
      "FLEXTPREFIX": self.common_cfg.flext_prefix
    }
    
    self.py_build_env = {
      **self.flext_build_env
    }

    self.build_cmd = (os.path.join(self.common_cfg.flext_dir, "build.bat"),)

    self.platform_output_name = "pd-msvc"
    
  def find_pd(self):
    pd_dir = os.path.join(os.environ["ProgramFiles"], "Pd")

    if not os.path.exists(pd_dir):
      return None

    return pd_dir

class SetupError(Exception):
  def __init__(self, message=""):
    super().__init__(self.message)
  
class Setup:
  def __init__(self, common_cfg, platform_cfg_ctor, ):
    self.common_cfg = common_cfg
    self.platform_cfg = platform_cfg_ctor(self.common_cfg)

    self.flext_platform_config_path = os.path.join(
      self.common_cfg.flext_dir,
      "buildsys",
      "config-{}-pd-{}.txt".format(self.platform_cfg.platform_alt, self.platform_cfg.compiler)
    )

    self.flext_config_path = os.path.join(self.common_cfg.flext_dir, "config.txt")

    self.py_config_path = os.path.join(self.common_cfg.py_dir, "config.txt")

    self.flext_platform_output_path = os.path.join(self.common_cfg.flext_dir, self.platform_cfg.platform_output_name)

    self.py_platform_output_path = os.path.join(self.common_cfg.py_dir, self.platform_cfg.platform_output_name)

  def __getattr__(self, name):
    if hasattr(self.platform_cfg, name):
      return getattr(self.platform_cfg, name)
    elif hasattr(self.common_cfg, name):
      return getattr(self.common_cfg, name)
    else:
      raise AttributeError(name)
    
  def validate(self):
    if not self.pd_path:
      raise SetupError("no Pd found. please specify a path with --pd")

    if not os.path.exists(self.pd_path):
      raise SetupError("Pd path {} does not exist")

    if not os.path.isdir(os.path.join(self.conda_root, "conda-meta")):
      raise SetupError("a Conda environment does not seem to be active. did you forget to run `conda activate`?")
    
  def flext_build(self, ok_codes=(0,), args=()):
    all_args = ("pd", self.platform_cfg.compiler) + args
    return call_with_env(
      self.platform_cfg.build_cmd + all_args,
      self.platform_cfg.flext_build_env,
      ok_codes
    )

  def py_build(self, ok_codes=(0,), args=()):
    all_args = ("pd", self.platform_cfg.compiler) + args
    return call_with_env(
      self.platform_cfg.build_cmd + all_args,
      self.platform_cfg.py_build_env,
      ok_codes
    )

supported_platform_cfgs = {
  "darwin": MacConfig,
  "win32": WinConfig
}

flext_url = "https://github.com/SopiMlab/flext/archive/master.zip"
py_url = "https://github.com/SopiMlab/py/archive/python3.zip"

def flatten_dir(path):
    items = os.listdir(path)
    
    if len(items) != 1:
        return
    
    item = items[0]
    item_path = os.path.join(path, item)
    
    if not os.path.isdir(item_path):
        return

    subitems = os.listdir(item_path)

    item_path2 = item_path + "_" + str(uuid.uuid4())
    os.rename(item_path, item_path2)
    item_path = item_path2

    for subitem in subitems:
        os.rename(os.path.join(item_path, subitem), os.path.join(path, subitem))

    os.rmdir(item_path)

def download(url, path, ctx):
    try:
        urlretrieve(url, path, context = ctx)
    except TypeError:
        # no context support in python 3
        urlretrieve(url, path)
    
def download_and_unzip(root_dir, name, url, path, ctx):
    if os.path.exists(path):
        print(name, "already downloaded")
        return
    
    print("downloading", name)
    the_zip = os.path.join(root_dir, "{}.zip".format(name))
    download(url, the_zip, ctx)
    print("unzipping", name)
    os.mkdir(path)
    with zipfile.ZipFile(the_zip, "r") as zf:
        zf.extractall(path)
    flatten_dir(path)
    os.remove(the_zip)

def call_with_env(args, env, ok_codes=(0,)):
    env1 = os.environ.copy()
    for k in env:
        env1[k] = env[k]

    print("call_with_env")
    print("  args:", args)
    print("  env:", env)

    p = subprocess.Popen(args, env=env1)
    code = p.wait()

    if code not in ok_codes:
        raise Exception("command exited with unexpected code {}".format(code))

    if code != 0:
        print("command exited with nonzero code {}, but this is fine".format(code))
        
arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("--pd", help="path to Pd")
arg_parser.add_argument("--info", help="don't build, just display environment info", action="store_true")
args = arg_parser.parse_args()

if sys.platform not in supported_platform_cfgs:
  print("platform {} is not supported".format(sys.platform))
  sys.exit(1)

setup = Setup(
  common_cfg = CommonConfig(
    root_dir = os.path.dirname(os.path.realpath(__file__)),
    pd_path = args.pd
  ),
  platform_cfg_ctor = supported_platform_cfgs[sys.platform]
)
  
print("platform config:", type(setup.platform_cfg).__name__)
print("Python version:", setup.python_version)
print("Python executable:", setup.python_exe)

try:
  setup.validate()
except SetupError as e:
  print(e)
  sys.exit(1)
    
print("Pd path:", setup.pd_path)
#variant = "Purr Data" if is_purr_data else "vanilla"
#print("Pd variant:", variant)
print("Conda root:", setup.conda_root)
print()

if "--info" in sys.argv:
    sys.exit(0)

ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS)
ssl_ctx.verify_mode = ssl.CERT_REQUIRED
ssl_ctx.check_hostname = True
ssl_ctx.load_default_certs()

if sys.platform == "darwin":
    import certifi
    ssl_ctx.load_verify_locations(
        cafile = certifi.where(),
        capath = None,
        cadata = None
    )

os.chdir(setup.root_dir)

download_and_unzip(setup.root_dir, "flext", flext_url, setup.flext_dir, ssl_ctx)
download_and_unzip(setup.root_dir, "py", py_url, setup.py_dir, ssl_ctx)

print()

if os.path.exists(setup.build_dir):
    print("cleaning build directory")
    shutil.rmtree(setup.build_dir)

os.mkdir(setup.build_dir)

os.chdir(setup.flext_dir)

print("flext_prefix:", setup.flext_prefix)

if os.path.exists(setup.flext_prefix):
    print("directory", setup.flext_prefix, "exists, so assuming flext was already installed")
else:
    if not os.path.exists(setup.flext_platform_config_path):
        print("creating flext system config")
        setup.flext_build((0, 2))

    if not os.path.exists(setup.flext_config_path):
        print("creating flext package config")
        setup.flext_build((0, 2))

    if not os.path.exists(setup.flext_platform_output_path):
        print("building flext")
        setup.flext_build()

    print("installing flext")
    setup.flext_build(args=("install",))

os.chdir(setup.py_dir)

if os.path.exists(setup.py_platform_output_path):
    print("directory", setup.py_platform_output_path, "exists, so assuming py was already built")
else:
    if not os.path.exists(setup.py_config_path):
        print("creating py config")
        setup.py_build((0, 2))

    print("building py")
    setup.py_build()

print("packaging files")
os.mkdir(setup.py_package_dir)
setup.py_build(args=("install",))

print()
print("done:", setup.py_package_dir)

print("flext_platform_output_path:", setup.flext_platform_output_path)
print("py_platform_output_path:", setup.py_platform_output_path)
print("py_package_dir:",setup.py_package_dir)
