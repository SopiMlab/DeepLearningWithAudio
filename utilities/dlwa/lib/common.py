import os
import shlex
import subprocess
from types import SimpleNamespace

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
repos_dir = os.path.join(root_dir, "repos")
conda_env_specs_dir = os.path.join(root_dir, "conda-env-specs")
inputs_dir = os.path.join(root_dir, "inputs")
datasets_dir = os.path.join(root_dir, "datasets")
models_dir = os.path.join(root_dir, "models")
misc_dir = os.path.join(root_dir, "misc")

repos = {
    "magenta": "https://github.com/SopiMlab/magenta.git",
    "ddsp": "https://github.com/SopiMlab/ddsp.git",
    "prism-samplernn": "https://github.com/SopiMlab/prism-samplernn.git"
}

def repo_dir(key):
    return os.path.join(repos_dir, key)

def input_dir(name):
    return os.path.join(inputs_dir, name)

def dataset_dir(key, name):
    return os.path.join(datasets_dir, key, name)

def model_dir(key, name):
    return os.path.join(models_dir, key, name)

class DlwaAbort(Exception):
    pass

def is_seq(x):
    return isinstance(x, tuple) or isinstance(x, list)

def join_args(args):
    return " ".join(map(shlex.quote, args))

def process_remainder(args):
    return args[1:] if args and args[0] == "--" else args

def gin_quote_str(text):
    return "'" + text.replace("\\", r"\\\\").replace("'", "\\'") + "'"

class Runner:
    def __init__(self):
        self.cache = {}
        self.platform = "linux-64"
        self.screen_name = "dlwa"

    @staticmethod
    def validate_which(returncode, output):
        path = output.rstrip(b"\n").decode("utf-8")
        return returncode == 0, path, path

    @staticmethod
    def validate_lmod(returncode, output):
        have = output.rstrip(b"\n") == b"function"
        return True, have, "have lmod" if have else "no lmod"

    @staticmethod
    def flatten_script(script):
        if is_seq(script):
            script_lines = []
            for line in script:
                if is_seq(line):
                    script_lines.append(join_args(line))
                else:
                    script_lines.append(line)
            script_str = "\n".join(script_lines)
        else:
            script_str = script
        return script_str

    @staticmethod
    def make_script_command(script_str):
        return ["bash", "-ec", script_str]
    
    @staticmethod
    def run_script(desc, script, validate=None, capture_output=True):
        if validate is None:
            validate = lambda r, o: (r == 0, None, None if r == 0 else f"exited with code {r}")
        print()
        print(f"run script: {desc}")
        print("----------------")
        script_str = Runner.flatten_script(script)
        for line in script_str.split("\n"):
            print(f"  {line}")
        print("----------------")
        cmd = Runner.make_script_command(script_str)
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
    
    def env_name(self, key):
        return f"dlwa-{key}"
    
    def check_cached(self, key, check):
        # print(f"check_cached({key})")
        # print(self.cache)
        
        if key not in self.cache:
            self.cache[key] = check()
        
        return self.cache[key]

    def conda_prep_script(self):
        def _check_lmod():
            check_lmod_script = ["type -t module"]
            return self.run_script("check for lmod", check_lmod_script, self.validate_lmod)
            
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
    
    def require_conda(self):
        def _check_conda():
            check_conda_script = [*self.conda_prep_script(), "which conda"]
            conda_path = self.run_script("check for conda", check_conda_script, self.validate_which)

        return self.check_cached("conda", _check_conda)
    
    def require_git(self):
        def _check_git():
            check_git_script = "which git"
            return self.run_script("check for git", check_git_script, self.validate_which)    

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
            return self.run_script(f"check for {key} git repository, download if needed", git_clone_script)

        self.require_git()
        if not os.path.isdir(repos_dir):
            os.mkdir(repos_dir)
            
        return self.check_cached(f"repo.{key}", _ensure_repo)

    def check_conda_env_cmd(self, env_name):
        env_name_q = shlex.quote(env_name)
        return f"""[ "$(conda env list | grep -E '^'{env_name_q} | wc -l)" -gt 0 ]"""
    
    def ensure_conda_env(self, key):
        def _ensure_conda_env():
            env_name = self.env_name(key)
            env_name_q = shlex.quote(env_name)
            yml_path = os.path.join(conda_env_specs_dir, f"{key}_{self.platform}.yml")
            yml_path_q = shlex.quote(yml_path)
            check_cmd = self.check_conda_env_cmd(env_name)

            conda_create_script = [
                *self.conda_prep_script(),
                f"""if ! {check_cmd}; then""",
                f"  CONDA_PKGS_DIRS=~/.conda/pkgs conda env create -n {env_name_q} -f {yml_path_q}",
                f"fi"
            ]
            return self.run_script(f"check for {key} conda environment, create if needed", conda_create_script, capture_output=False)

        self.require_conda()
        return self.check_cached(f"conda_env.{key}", _ensure_conda_env)

    def require_conda_env(self, key):
        def _require_conda_env():
            env_name = self.env_name(key)
            check_script = [
                *self.conda_prep_script(),
                self.check_conda_env_cmd(env_name)
            ]
            return self.run_script(f"check for {key} conda environment", check_script, capture_output=False)

        self.require_conda()
        return self.check_cached(f"conda_env.{key}", _require_conda_env)
    
    def run_with_conda(self, cmd):
        self.require_conda()
        cmd_str = join_args(cmd)
        cmd_script = [
            *self.conda_prep_script(),
            cmd
        ]
        return self.run_script(f"run command with conda enabled: {cmd_str}", cmd_script, capture_output=False)
    
    def ensure_pip_install(self, key, regular_pkgs, editable_pkgs):
        def _ensure_pip_install():
            regular_script = [["pip", "install", *regular_pkgs]] if regular_pkgs else []
            editable_script = [["pip", "install", "-e", *editable_pkgs]] if editable_pkgs else []
            pip_install_script = [
                *self.conda_activate_script(self.env_name(key)),
                *regular_script,
                *editable_script
            ]
            return self.run_script(f"install {key} packages if needed", pip_install_script, capture_output=False)

        return _ensure_pip_install()

    def check_screen(self, name):
        def _check_screen():
            name_q = shlex.quote(name)
            check_script = [
                f"""[ "$(screen -ls | grep -E '^[[:space:]]*[[:digit:]]+\.{name_q}[[:space:]]' | wc -l)" -gt 0 ]"""
            ]
            def _validate_screen(returncode, output):
                exists = returncode == 0
                return True, exists, "yes" if exists else "no"
            
            return self.run_script(f"check for existing {name} screen", check_script, _validate_screen, capture_output=False)

        return _check_screen()

    def require_no_screen(self):
        name = self.screen_name
        name_q = shlex.quote(name)
        screen_exists = self.check_screen(name)
        if screen_exists:
            msg = "\n".join([
                f"you already have a {name} screen session running on this system. you can:",
                f"  a) attach to it: screen -Dr {name_q}",
                f"  b) kill it: screen -S {name_q} -X kill"
            ])
            raise DlwaAbort(msg)

    def make_screen_script(self, script, log_path=None):
        name = self.screen_name
        log_args = [
            "-L", "-Logfile", log_path
        ] if log_path else []
        return [[
            "screen",
            "-S", name,
            "-c", os.path.join(misc_dir, "dlwa.screenrc"),
            *log_args,
            "-d",
            "-m",
            *self.make_script_command(self.flatten_script(script))
        ]]
