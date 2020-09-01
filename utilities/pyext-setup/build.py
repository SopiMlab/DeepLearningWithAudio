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

if sys.platform != "darwin":
    print("platform {} is not supported".format(sys.platform))
    sys.exit(1)

flext_url = "https://github.com/SopiMlab/flext/archive/master.zip"
py_url = "https://github.com/SopiMlab/py/archive/python3.zip"

root_dir = os.path.dirname(os.path.realpath(__file__))

flext_dir = os.path.join(root_dir, "flext")
py_dir = os.path.join(root_dir, "py")

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
    
def download_and_unzip(name, url, path, ctx):
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

def find_pd_app():
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

def find_purr_data_app():
    apps_dir = "/Applications"

    if not os.path.exists(apps_dir):
        return None

    app_names = ("PurrData.app", "Pd-l2ork.app")
    for app_name in app_names:
        app_path = os.path.join(apps_dir, app_name)
        if os.path.exists(app_path):
            return app_path

    return None

def check_purr_data(app_path):
    return os.path.exists(os.path.join(app_path, "Contents", "MacOS", "nwjs"))

def call_with_env(args, env, ok_codes=(0,)):
    env1 = os.environ.copy()
    for k in env:
        env1[k] = env[k]

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

print("Python version:", sys.version)
print("Python executable:", sys.executable)

pd = args.pd or find_pd_app()
if pd == None:
    print("Pd not found, please specify --pd /path/to/Pd.app")
    sys.exit(1)

pd = os.path.realpath(pd)
is_purr_data = check_purr_data(pd)
conda_root = os.path.dirname(os.path.dirname(sys.executable))

if not os.path.isdir(os.path.join(conda_root, "conda-meta")):
    print("A Conda environment does not seem to be active. Did you forget to run `conda activate`?")
    sys.exit(1)

print("Pd path:", pd)
variant = "Purr Data" if is_purr_data else "vanilla"
print("Pd variant:", variant)
print("Conda root:", conda_root)
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

os.chdir(root_dir)

download_and_unzip("flext", flext_url, flext_dir, ssl_ctx)
download_and_unzip("py", py_url, py_dir, ssl_ctx)

print()

build_dir = os.path.join(root_dir, "build")
flext_prefix = os.path.join(build_dir, "flext")
package_dir = os.path.join(build_dir, "py")

if os.path.exists(build_dir):
    print("cleaning build directory")
    shutil.rmtree(build_dir)

os.mkdir(build_dir)

os.chdir(flext_dir)

flext_build_cmd = ("bash", os.path.join(flext_dir, "build.sh"), "pd", "gcc")
flext_build_env = {
    #"BUILDMODE": "debug",
    #"TARGETMODE": "debug",
    "FLEXT_PD_APP": pd,
    "FLEXT_INSTALL_PATH": package_dir,
    "FLEXTPREFIX": flext_prefix,
    "FLEXT_NOATTREDIT": str(int(is_purr_data))
}
flext_build = lambda ok_codes=(0,), args=(): call_with_env(flext_build_cmd + args, flext_build_env, ok_codes)

if os.path.exists(flext_prefix):
    print("directory", flext_prefix, "exists, so assuming flext was already installed")
else:
    flext_platform_config_path = os.path.join(flext_dir, "buildsys", "config-mac-pd-gcc.txt")
    flext_config_path = os.path.join(flext_dir, "config.txt")
    flext_pd_darwin_dir = os.path.join(flext_dir, "pd-darwin")

    if not os.path.exists(flext_platform_config_path):
        print("creating flext system config")
        flext_build((0, 2))

    if not os.path.exists(flext_config_path):
        print("creating flext package config")
        flext_build((0, 2))

    if not os.path.exists(flext_pd_darwin_dir):
        print("building flext")
        flext_build()

    print("installing flext")
    flext_build(args=("install",))

os.chdir(py_dir)

py_build_env = dict(flext_build_env)
py_build_env["PY_CONDA_ROOT"] = conda_root
py_build_cmd = ("bash", os.path.join(flext_dir, "build.sh"), "pd", "gcc")
py_build = lambda ok_codes=(0,), args=(): call_with_env(py_build_cmd + args, py_build_env, ok_codes)

py_pd_darwin_dir = os.path.join(py_dir, "pd-darwin")
if os.path.exists(py_pd_darwin_dir):
    print("directory", py_pd_darwin_dir, "exists, so assuming py was already built")
else:    
    py_config_path = os.path.join(py_dir, "config.txt")
    
    if not os.path.exists(py_config_path):
        print("creating py config")
        py_build((0, 2))

    print("building py")
    py_build()

print("packaging files")
os.mkdir(package_dir)
py_build(args=("install",))

#py_extra_dirs = (os.path.join(py_dir, "pd"), os.path.join(py_dir, "scripts"))
#for py_extra_dir in py_extra_dirs:
#    for fn in os.listdir(py_extra_dir):
#        shutil.copyfile(
#            os.path.join(py_extra_dir, fn),
#            os.path.join(package_dir, fn)
#        )
    
print()
print("done:", package_dir)
