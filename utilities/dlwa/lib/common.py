import os
import shlex
import subprocess
from types import SimpleNamespace

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
repos_dir = os.path.join(root_dir, "repos")
conda_env_specs_dir = os.path.join(root_dir, "conda-env-specs")

repos = {
    "magenta": "https://github.com/SopiMlab/magenta.git",
    "ddsp": "https://github.com/SopiMlab/ddsp.git",
    "prism-samplernn": "https://github.com/SopiMlab/prism-samplernn.git"
}

def repo_dir(key):
    return os.path.join(repos_dir, key)

class DlwaAbort(Exception):
    pass

def is_seq(x):
    return isinstance(x, tuple) or isinstance(x, list)

def run_script(desc, script, validate=None, capture_output=True):
    if validate is None:
        validate = lambda r, o: (r == 0, None, None)
    print()
    print(f"run script: {desc}")
    print("----------------")
    if is_seq(script):
        script_lines = []
        for line in script:
            if is_seq(line):
                script_lines.append(" ".join(map(shlex.quote, line)))
            else:
                script_lines.append(line)
        script_str = "\n".join(script_lines)
    else:
        script_str = script    
    for line in script_str.split("\n"):
        print(f"  {line}")        
    print("----------------")
    cmd = ["bash", "-ec", script_str]
    if capture_output:
        try:
            output = subprocess.check_output(cmd)
            returncode = 0
        except subprocess.CalledProcessError as e:
            output = e.output
            returncode = e.returncode
    else:
        output = b""
        try:
            subprocess.check_call(cmd)
            returncode = 0
        except subprocess.CalledProcessError as e:
            output = e.output
            returncode = e.returncode            
    ok, result, info = validate(returncode, output)
    ok_str = "ok" if ok else "fail"
    info_str = f" ({info})" if info else ""
    print(f"-> {ok_str}{info_str}")
    if not ok:
        raise DlwaAbort(f"script failed: {desc}")
    return result

class Runner:
    def __init__(self):
        print("INIT!!!!")
        self.cache = {}
        self.platform = "linux-64"

    @staticmethod
    def validate_which(returncode, output):
        path = output.rstrip(b"\n").decode("utf-8")
        return returncode == 0, path, path

    @staticmethod
    def validate_lmod(returncode, output):
        have = output.rstrip(b"\n") == b"function"
        return True, have, "have lmod" if have else "no lmod"

    def env_name(self, key):
        return f"dlwa-{key}"
    
    def check_cached(self, key, check):
        print(f"check_cached({key})")
        print(self.cache)
        
        if key not in self.cache:
            self.cache[key] = check()
        
        return self.cache[key]

    def conda_prep_script(self):
        def _check_lmod():
            check_lmod_script = ["type -t module"]
            return run_script("check for lmod", check_lmod_script, self.validate_lmod)
            
        have_lmod = self.check_cached("lmod", _check_lmod)
        script = []
        if have_lmod:
            script.append("module load miniconda")

        script.append('eval "$(conda shell.bash hook)"')
        return script

    def conda_activate_script(self, env_name):
        return [
            *self.conda_prep_script(),
            ["conda", "activate", env_name]
        ]
    
    def ensure_conda(self):
        def _check_conda():
            check_conda_script = [*self.conda_prep_script(), "which conda"]
            conda_path = run_script("check for conda", check_conda_script, self.validate_which)

        return self.check_cached("conda", _check_conda)
    
    def ensure_git(self):
        def _check_git():
            check_git_script = "which git"
            return run_script("check for git", check_git_script, self.validate_which)    

        return self.check_cached("git", _check_git)

    def ensure_repo(self, key):
        def _ensure_repo():
            url = repos[key]
            url_q = shlex.quote(url)
            dstdir = repo_dir(key)
            dstdir_q = shlex.quote(dstdir)
            git_clone_script = [
                f"if [ ! -d {dstdir_q} ]; then",
                f"  git clone {url_q} {dstdir_q}",
                f"fi"
            ]
            return run_script(f"check for {key} git repository, download if needed", git_clone_script)

        return self.check_cached(f"repo.{key}", _ensure_repo)

    def ensure_conda_env(self, key):
        def _ensure_conda_env():
            env_name = self.env_name(key)
            env_name_q = shlex.quote(env_name)
            yml_path = os.path.join(conda_env_specs_dir, f"{key}_{self.platform}.yml")
            yml_path_q = shlex.quote(yml_path)
            
            conda_create_script = [
                *self.conda_prep_script(),
                f"""if [ "$(conda env list | grep -E '^'{env_name_q} | wc -l)" -eq 0 ]; then""",
                f"  conda env create -n {env_name_q} -f {yml_path_q}",
                f"fi"
            ]
            return run_script(f"check for {key} conda environment, create if needed", conda_create_script, capture_output=False)

        return self.check_cached(f"conda_env.{key}", _ensure_conda_env)

    def ensure_pip_install(self, key, regular_pkgs, editable_pkgs):
        def _ensure_pip_install():
            regular_script = [["pip", "install", *regular_pkgs]] if regular_pkgs else []
            editable_script = [["pip", "install", "-e", *editable_pkgs]] if editable_pkgs else []
            pip_install_script = [
                *self.conda_activate_script(self.env_name(key)),
                *regular_script,
                *editable_script
            ]
            return run_script(f"install {key} packages if needed", pip_install_script, capture_output=False)

        _ensure_pip_install()
    
    def basic_setup(self):
        self.ensure_git()
        self.ensure_conda()
            
        if not os.path.isdir(repos_dir):
            os.mkdir(repos_dir)
        
