# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_core.ipynb.

# %% auto 0
__all__ = ['reproduce_dir', 'dev_image_tag', 'base_config', 'VAR_REGISTRY', 'set_default_dir', 'read_base_config',
           'validate_base_config', 'requires_config', 'ReproduceWorkEncoder', 'generate_config',
           'test_validate_base_config', 'update_watched_files', 'get_cell_index', 'check_for_defintion_in_context',
           'serialize_to_toml', 'publish_data', 'publish_file', 'reproducible', 'publish_variable', 'register_notebook']

# %% ../nbs/00_core.ipynb 3
import toml
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

def set_default_dir():
    print('Setting reproduce.work config dir to ./reproduce')
    return Path("./reproduce")

reproduce_dir = os.getenv("REPROWORKDIR", set_default_dir())
dev_image_tag = os.getenv("REPRODEVIMAGE")

def read_base_config():
    with open(Path(reproduce_dir, 'config.toml'), 'r') as f:
        base_config = toml.load(f)
    return base_config



def validate_base_config(base_config):
    required_keys = ['authors', 'repro']
    for key in required_keys:
        if key not in base_config:
            print(toml.dumps(base_config))
            print(f"Error: Missing required field '{key}' in config.toml")
            return False
        if key=='repro':
            if 'stages' not in base_config['repro']:
                print(f"Error: Missing required field 'repro.stages' in reproduce.work configuration at {reproduce_dir}/config.toml")
                return False
            for stage in base_config['repro']['stages']:
                if (f'repro.stage.{stage}' not in base_config) and (stage not in base_config['repro']['stage']):
                    print(toml.dumps(base_config))
                    print(f"Error: Missing required field repro.stage.{stage} in reproduce.work configuration at {reproduce_dir}/config.toml")
                    return False
    return True

def requires_config(func):
    def wrapper(*args, **kwargs):
        config = read_base_config()
        if not validate_base_config(config):
            raise Exception("Your reproduce.work configuration is not valid.")
        return func(*args, **kwargs)
    return wrapper


class ReproduceWorkEncoder(toml.TomlEncoder):
    def dump_str(self, v):
        """Encode a string."""
        if "\n" in v:
            return v  # If it's a multi-line string, return it as-is
        return super().dump_str(v)
    
    def dump_value(self, v):
        """Determine the type of a Python object and serialize it accordingly."""
        if isinstance(v, str) and "\n" in v:
            return '"""\n' + v.strip() + '\n' + '"""'
        return super().dump_value(v)


def generate_config(inputs={}, version="reproduce.work/v1/default"):
    if inputs=={}:
        # Authors section
        author1_email = input("Enter author's email (required): ")
        author1_name = input("Enter author's name: ")
        author1_affiliation = input("Enter author's affiliation: ")
        repro_version = input(f"Enter reproduce_work API version (Default: {version}): ") or version

        # Repro stage init section
        dev_image_tag = input("Enter dev image tag (required; the docker image of your local development workflow): ")
        
        # default should be no
        nbdev_project = input("Is this a nbdev project? (y/n) ") == 'y'
        github_repo = input("Enter github repo (required): ")

        project_full_title = input("Enter project full title (options): ") or "Title goes here"
        project_abstract = input("Enter project abstract (optional): ") or "Abstract goes here."

        full_url = False
    else:
        author1_email = inputs['authors']['author1']['email']
        if 'name' in inputs['authors']['author1']:
            author1_name = inputs['authors']['author1']['name']
        else:
            author1_name = None

        if 'affiliation' in inputs['authors']['author1']:
            author1_affiliation = inputs['authors']['author1']['affiliation']
        else:
            author1_affiliation = None
            
        dev_image_tag = inputs['dev_image_tag']
        repro_version = version

        nbdev_project = False
        if 'nbdev_project' in inputs:
            nbdev_project = inputs['nbdev_project']


        project_full_title = 'Title goes here'
        project_abstract = 'Abstract goes here.'
        github_repo = False
        if 'project' in inputs:
            if 'github_repo' in inputs['project']:
                github_repo = inputs['project']['github_repo']
            if 'full_title' in inputs['project']:
                project_full_title = inputs['project']['full_title']
            if 'abstract' in inputs['project']:
                project_abstract = inputs['project']['abstract']

        if 'full_url' in inputs:
            full_url = inputs['full_url']
        else:  
            full_url = False
        
        verbose = False
        if 'verbose' in inputs:
            verbose = inputs['verbose']

    verbose_str = "true" if verbose else "false"

    if repro_version in ["reproduce.work/v1/default"]:
        document_dir = reproduce_dir
        input_file = f"{document_dir}/main.md"
        dynamic_file = f"{document_dir}/pubdata.toml"
        latex_template = f"{document_dir}/latex/template.tex"
        output_file =f"{document_dir}/latex/compiled.tex"
        watch_files = [input_file, dynamic_file, latex_template]
    
    # Check for critical fields
    if not dev_image_tag:
        print("Error: Missing critical field 'dev_image_tag'.")
        return
    
    nbdev_project_cmd = ""
    if nbdev_project:
        nbdev_project_cmd = '\nnbdev_install_hooks && nbdev_export'

    github_repo_str = ''
    if github_repo:
        github_repo_str = f'\ngithub_repo = "{github_repo}"'

    if not full_url and github_repo:
        full_url = f"https://github.com{github_repo}"
    if full_url:
        full_url_str = f'\nfull = "{full_url}"'
    else:
        full_url_str = ''

    #reproduce_dir_default = f"{reproduce_dir}"  # this can be changed if needed
    #reproduce_dir = input(f"Enter reproduce directory (Default: {reproduce_dir_default}): ") or reproduce_dir_default
    
    repro_init_script = f'''docker build -t {dev_image_tag} .
    docker build -t tex-prepare https://github.com/reproduce-work/tex-prepare.git
    docker build -t tex-compile https://github.com/reproduce-work/tex-compile.git
    docker build -t watcher https://github.com/reproduce-work/rwatch.git
    '''

    # ensure reproduce_dir exists
    Path(reproduce_dir).mkdir(parents=True, exist_ok=True)

    newline = "\n"
    with open(Path(reproduce_dir, 'config.toml'), 'w') as f:
        f.write(f'''
[authors]
author1.email = "{author1_email}"{newline + 'author1.name = "' + author1_name + '"' if author1_name else ""}{newline + 'author1.affiliation = "' + author1_affiliation + '"' if author1_affiliation else ""}

[project]
full_title = "{project_full_title}"
abstract = """
{project_abstract}
"""{github_repo_str}{full_url_str}

# reproduce.work configuration
[repro]
version = "{repro_version}"
stages = ["init", "develop", "build"]
verbose = {verbose_str}
terminal_linefile = "report.tex" # must be plaintext file
terminal_file = "report.pdf" # can be any filetype

[repro.files]
input = "{input_file}"
dynamic = "{dynamic_file}"
latex_template = "{latex_template}"
output = "{output_file}"
watch = {watch_files}

[repro.stage.init]
script = """
{repro_init_script}
"""

[repro.stage.develop]
script = """
docker run -v $(pwd):/home/jovyan -p 8888:8888 {dev_image_tag}
\INSERT{{watch_cmd_here}}
"""

[repro.stage.build]
script = """
docker run --rm -i -v $(pwd):/home/jovyan -p 8888:8888 {dev_image_tag} python reproduce_work.build() # this replaces instances of INSERTvar in input file
docker run --rm -i -v $(pwd):/home -e REPROWORKDIR="{reproduce_dir}" -e REPROWORKOUTFILE="{output_file}" tex-prepare python build.py # this converts the markdown to latex
docker run --rm -i --net=none -v $(pwd):/home tex-compile sh -c "cd /home/{document_dir}/latex && xelatex compiled.tex" # this compiles the latex{nbdev_project_cmd}
"""
        ''')


    # By default, TOML files cannot reference variables defined earlier in the file
    # This is a hack to get around that which allows me to read in the TOML data,
    # and then backfill the watch command with the files listed in the TOML file itself.
    if '\INSERT{watch_cmd_here}' in open(Path(reproduce_dir, 'config.toml'), 'r').read():
        with open(Path(reproduce_dir, 'config.toml'), 'r') as f:
            base_config_str = f.read()
        replaced_config = base_config_str.replace(
            '\INSERT{watch_cmd_here}', 
            f"""docker run watcher "{','.join(watch_files)}" "echo \"File has changed!\" && build_cmd" """
        )
        with open(Path(reproduce_dir, 'config.toml'), 'w') as f:
            f.write(replaced_config)
    else:
        print('did not replace watch command')


    with open(Path(reproduce_dir, 'config.toml'), 'r') as f:
        config_data = toml.load(f)

    with open(Path(reproduce_dir, 'config.toml'), 'w') as f:
        toml.dump(config_data, f, encoder=ReproduceWorkEncoder())

    print(f"Successfully generated reproduce.work configuration at {reproduce_dir}/config.toml")

    # check if input file exists
    if not os.path.exists(input_file):
        with open(input_file, 'w') as f:
            f.write('')
        print(f"Successfully generated input file at {input_file}")

    # check if latex template exists
    if not os.path.exists(latex_template):
        # Fill in with package default
        Path(latex_template).parent.mkdir(parents=True, exist_ok=True)
        latex_template_default_str = r'\documentclass[12pt]{article}\usepackage[english]{babel}\usepackage{xcolor}\usepackage[hmargin=1in,vmargin=1in]{geometry}\usepackage{amsmath}\usepackage{unicode-math}\usepackage[round,sort,comma]{natbib}\bibliographystyle{apa}\usepackage{setspace}\usepackage{graphicx}\usepackage{caption}\usepackage{subcaption}\usepackage[colorlinks=true, allcolors=blue]{hyperref}\usepackage{float}\usepackage{booktabs}\usepackage{titlesec}\newcommand{\addperiod}[1]{#1.$\;$}\titlespacing{\section}{0pt}{\parskip}{-\parskip}\titleformat{\subsection}[runin]{\normalsize\bfseries}{\thesubsection}{1em}{\addperiod}\titleformat{\subsubsection}[runin]{\normalfont\normalsize\itshape}{\thesubsubsection}{1em}{\addperiod}\titlespacing{\subsubsection}{14pt plus 4pt minus 2pt}{0pt}{0pt plus 2pt minus 2pt}\setlength{\parindent}{1em}\makeatletter\g@addto@macro \normalsize {\setlength\abovedisplayskip{3pt plus 5pt minus 2pt}\setlength\belowdisplayskip{3pt plus 5pt minus 2pt}}\makeatother\newcommand{\comment}[1]{}\begin{document}\pagenumbering{gobble}\begin{center}{\fontsize{16}{16}\selectfont\bfseries \INSERT{config.project.full_title}}\vspace{5mm}\begin{table}[!ht]\begin{center}\begin{tabular}{c c }\shortstack{ \INSERT{config.authors.author1.name} \\\INSERT{config.authors.author1.affiliation} \\\INSERT{config.authors.author1.email} }\end{tabular}\end{center}\end{table}\vspace{5mm}\emph{Last updated: \today}\vspace{4mm}\abstract{\INSERT{config.project.abstract}}\vspace{2cm}{\scriptsize \noindent Notes: }\vspace{10mm}\end{center}\newpage\doublespacing\pagenumbering{arabic}\setcounter{page}{1}%%@@LOWDOWN_CONTENT@@%%\bibliography{latex/bibliography}\end{document}'
        with open(latex_template, 'w') as f:
            f.write(latex_template_default_str)
        print(f"Successfully generated latex template at {latex_template}")


# Write some basic tests
def test_validate_base_config():
    # Test a valid base_config
    base_config = {
        'authors': {
            'author1.name': 'Alex P. Miller',
            'author1.affiliation': 'USC Marshall School of Business',
            'author1.email': 'alex.miller@marshall.usc.edu'
        },
        'repro': {
            'version': 'reproduce.work/v1/default',
            'stages': ['init', 'develop', 'build']
        },
        'repro.files': {
            'input': 'document/main.md',
            'dynamic': 'document/pubdata.toml',
            'latex_template': 'document/latex/template.tex',
            'output': 'document/latex/compiled.tex',
            'watch': ['document/main.md', 'document/pubdata.toml', 'document/latex/template.tex']
        },
        'repro.stage.init': {
            'script': 'docker build -t {dev_image_tag} .\ndocker build -t tinytex {reproduce_dir}/Dockerfile.tinytex\ndocker build -t watcher {reproduce_dir}/Dockerfile.watch\n'
        },
        'repro.stage.develop': {
            'script': 'docker run -v $(pwd):/home/jovyan -p 8888:8888 {dev_image_tag} start.sh jupyter lab --LabApp.token=\'\'\n\\INSERT{watch_cmd_here}\n'
        },
        'repro.stage.build': {
            'script': 'docker run --rm -i -v $(pwd):/home/jovyan -p 8888:8888 {dev_image_tag} python reproduce_work.build() # this replaces instances of \\INSERT{var} in `input` file\ndocker run --rm -i -v $(pwd):/home lowdown # this converts the markdown to latex\ndocker run --rm -i --net=none -v $(pwd):/home tinytex sh -c "cd /home/document/latex && xelatex compiled.tex" # this compiles the latex\n'
        }
    }
    assert validate_base_config(base_config) == True

# Test an invalid base_config
base_config = {
    'au': {
        'author1.name': 'Alex P. Miller',
        'author1.affiliation': 'USC Marshall School of Business',
        'author1.email': 'alex.miller@marshall.usc.edu'
    },
    'repro': {
        'version': 'reproduce.work/v1/default',
        'stages': ['init', 'develop', 'build']
    },
    'repro.files': {
        'input': 'document/main.md',
        'dynamic': 'document/pubdata.toml',
        'latex_template': 'document/latex/template.tex',
        'output': 'document/latex/compiled.tex'
    },
    'repro.stage.init': {
        'script': 'docker build -t {dev_image_tag} .\ndocker build -t tinytex {reproduce_dir}/Dockerfile.tinytex\ndocker build -t watcher {reproduce_dir}/Dockerfile.watch\n'
    },
    'repro.stage.develop': {
        'script': 'docker run -v $(pwd):/home/jovyan -p 8888:8888 {dev_image_tag} start.sh jupyter lab --LabApp.token=\'\'\n\\INSERT{watch_cmd_here}\n'
    },
    'repro.stage.build': {
        'script': 'docker run --rm -i -v $(pwd):/home/jovyan -p 8888:8888 {dev_image_tag} python reproduce_work.build() # this replaces instances of \\INSERT{var} in `input` file\ndocker run --rm -i -v $(pwd):/home lowdown # this converts the markdown to latex\ndocker run --rm -i --net=none -v $(pwd):/home tinytex sh -c "cd /home/document/latex && xelatex compiled.tex" # this compiles the latex\n'
    }
}
assert validate_base_config(base_config) == False

print("All tests passed!")



# %% ../nbs/00_core.ipynb 7
import datetime
import os
import sys
import platform
from dotenv import load_dotenv
from pathlib import Path
import functools

load_dotenv()
def set_default_dir():
    print('Setting reproduce.work config dir to ./reproduce')
    return Path("./reproduce")

reproduce_dir = os.getenv("REPROWORKDIR", set_default_dir())
dev_image_tag = os.getenv("REPRODEVIMAGE")


def read_base_config():
    #print(os.getcwd())
    with open(Path(reproduce_dir, 'config.toml'), 'r') as f:
        base_config = toml.load(f)
    return base_config

def update_watched_files(add=[], remove=[]):
    base_config = read_base_config()
    existing_files = base_config['repro']['files']['watch']
    new_files = existing_files + [a for a in add if a not in existing_files]
    new_files = [f for f in new_files if f not in remove]
    base_config['repro']['files']['watch'] = new_files

    current_develop_script = base_config['repro']['stage']['develop']['script']
    current_develop_script
    # regex to replace content in string matching 'watcher \"{to_replace}\"'
    # with 'watcher \"{new_files}\"'
    # and replace 'build_cmd' with 'python reproduce_work.build()'
    import re
    new_develop_script = re.sub(
        r'watcher \"(.*?)\"', 
        f'watcher \"{",".join(new_files)}\"', 
        current_develop_script
    )
    base_config['repro']['stage']['develop']['script'] = new_develop_script

    with open(Path(reproduce_dir, 'config.toml'), 'w') as f:
        toml.dump(base_config, f)
        
    if base_config['repro']['verbose']:
        print(f"Updated watched files to {new_files}")
    return new_files

def validate_base_config(base_config):
    required_keys = ['authors', 'repro']
    for key in required_keys:
        if key not in base_config:
            print(toml.dumps(base_config))
            print(f"Error: Missing required field '{key}' in config.toml")
            return False
        if key=='repro':
            if 'stages' not in base_config['repro']:
                print(f"Error: Missing required field 'repro.stages' in reproduce.work configuration at {reproduce_dir}/config.toml")
                return False
            for stage in base_config['repro']['stages']:
                if (f'repro.stage.{stage}' not in base_config) and (stage not in base_config['repro']['stage']):
                    print(toml.dumps(base_config))
                    print(f"Error: Missing required field repro.stage.{stage} in reproduce.work configuration at {reproduce_dir}/config.toml")
                    return False
    return True

def requires_config(func):
    def wrapper(*args, **kwargs):
        config = read_base_config()
        if not validate_base_config(config):
            raise Exception("Your reproduce.work configuration is not valid.")
        return func(*args, **kwargs)
    return wrapper


VAR_REGISTRY = {
    'REPROWORK_REMOTE_URL': None,
    'REPROWORK_ACTIVE_NOTEBOOK': None
}

# %% ../nbs/00_core.ipynb 11
from pathlib import Path
import hashlib
import inspect
import re
import toml
import io
import pandas as pd
import numpy as np

#def update_registry(var_name, value):
    

def get_cell_index():
    """
    Get the current cell index in a Jupyter notebook environment.
    If not in Jupyter, return None.
    """
    try:
        # Execute JavaScript to get the current cell index
        get_ipython().run_cell_magic('javascript', '', 'IPython.notebook.kernel.execute(\'current_cell_index = \' + IPython.notebook.get_selected_index())')
        return current_cell_index
    except:
        return None
    
def check_for_defintion_in_context(function_name='save'):
    assert function_name in ['save', 'assign'], "function_name must be either 'save' or 'assign'"
    
    from IPython import get_ipython
    ip = get_ipython()

    # Check if in Jupyter environment
    if ip is None:
        
        #fill this in 
        pass

    else:
        # Get the input history
        #lineno = inspect.stack()[0].lineno
        raw_hist = ip.history_manager.input_hist_raw
        current_cell = raw_hist[-1]


        matches = re.findall(rf"{function_name}\((.+?),", current_cell)
                
        if matches:
            # save call
            defined_var = matches[0].strip()
            definition_cell_content = ''
            
            for prior_cell in raw_hist[-2::-1]:
                #print(prior_cell)
                if f'{defined_var} =' in prior_cell or f'{defined_var}=' in prior_cell:
                    definition_cell_content = prior_cell
                    break
            
            # find the line number of the where the variable was defined
            # Give a window of 5 lines around the definition call
            def_cell_lines = definition_cell_content.split('\n')
            if len(def_cell_lines)>0:
                lineno = None
                for line_num, line in enumerate(def_cell_lines):
                    if defined_var in line:
                        lineno = line_num
                        break
                if lineno:
                    definition_context = (
                        '\n'.join(def_cell_lines[max(0, lineno-5):lineno]) + 
                        '\nFLAG' + def_cell_lines[lineno] + '\n' +
                        '\n'.join(def_cell_lines[lineno+1:min(len(def_cell_lines), lineno+5)])
                    )
                else:
                    definition_context = None

            else:
                definition_context = None

            
            save_cell_lines = current_cell.split('\n')
            if len(save_cell_lines)>0:
                save_lineno = None
                for line_num, line in enumerate(save_cell_lines):
                    if 'save(' in line:
                        save_lineno = line_num
                        break
                
                if save_lineno:
                    save_context = (
                        '\n'.join(save_cell_lines[max(0, save_lineno-5):save_lineno]) + 
                        '\nFLAG' + save_cell_lines[save_lineno] + '\n' +
                        '\n'.join(save_cell_lines[save_lineno+1:min(len(save_cell_lines), save_lineno+5)])
                    )
                else:
                    save_context = None
                
            else:
                save_context = None
            

        else:
            # not a save call
            save_context = None
            definition_context = None

        return(save_context, definition_context)


class ReproduceWorkEncoder(toml.TomlEncoder):
    def dump_str(self, v):
        """Encode a string."""
        if "\n" in v:
            return v  # If it's a multi-line string, return it as-is
        return super().dump_str(v)
    
    def dump_value(self, v):
        """Determine the type of a Python object and serialize it accordingly."""
        if isinstance(v, str) and "\n" in v:
            return '"""\n' + v.strip() + '\n' + '"""'
        return super().dump_value(v)


def serialize_to_toml(data, root=True):
    """Unified function to serialize various Python data types to TOML format."""
    toml_string = ""
    
    # Handle numpy array
    if isinstance(data, np.ndarray):
        toml_string += f"array = {data.tolist()}"
    
    # Handle pandas DataFrame
    if isinstance(data, pd.DataFrame):
        toml_string += "[dataframe]\n"
        for col in data.columns:
            values = data[col].tolist()
            if all(isinstance(val, (int, float)) for val in values):
                toml_string += f"{col} = {values}\n"
            else:
                values_str = ['"' + str(val) + '"' for val in values]
                toml_string += f"{col} = [{', '.join(values_str)}]\n"
        return toml_string
    
    # Handle dictionary
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                toml_string += f"{key} = \"{value}\"\n"
            elif isinstance(value, (int, float)):
                toml_string += f"{key} = {value}\n"
            elif isinstance(value, bool):
                toml_string += f"{key} = {str(value).lower()}\n"
            elif isinstance(value, (list, set, tuple)):
                values = ", ".join([str(v) for v in value])
                toml_string += f"{key} = [{values}]\n"
            elif value is None:
                toml_string += f"{key} = null\n"
            elif isinstance(value, (np.datetime64, pd.Timestamp)):
                toml_string += f"{key} = \"{str(value)}\"\n"
            elif isinstance(value, dict) or isinstance(value, pd.DataFrame):
                # Recursive call for nested dictionaries or DataFrames
                nested_str = serialize_to_toml(value, root=False)
                toml_string += f"[{key}]\n{nested_str}\n"
    
    # If it's the root call, remove any trailing newline
    if root:
        toml_string = toml_string.rstrip()
    return toml_string


class ReproduceWorkEncoder(toml.TomlEncoder):
    def dump_str(self, v):
        """Encode a string."""
        if "\n" in v:
            return v  # If it's a multi-line string, return it as-is
        return super().dump_str(v)
    
    def dump_value(self, v):
        """Determine the type of a Python object and serialize it accordingly."""
        if isinstance(v, str) and "\n" in v:
            return '"""\n' + v.strip() + '\n' + '"""'
        return super().dump_value(v)

@requires_config
def publish_data(content, name, metadata={}, watch=True):
    """
    Save data to default pubdata.toml file and register metadata.
    """
    # Capture metadata
    timestamp = datetime.datetime.now().isoformat()
    inspect_filename = inspect.currentframe().f_back.f_code.co_filename
    python_version = sys.version.strip().replace('\n', ' ')
    platform_info = platform.platform()

    # generate cryptographic hash of file contents
    content_hash = hashlib.md5(str(content).encode('utf-8')).hexdigest()
    timed_hash = hashlib.md5((str(content) + timestamp).encode('utf-8')).hexdigest()
         
    # Store metadata
    new_metadata = {
        "type": "data",
        "timestamp": timestamp,
        "content_hash": content_hash,
        "timed_hash": timed_hash,
        #"python_version": python_version,
        #"platform_info": platform_info,
    }
    if VAR_REGISTRY['REPROWORK_REMOTE_URL']:
        metadata['published_url'] = f"{VAR_REGISTRY['REPROWORK_REMOTE_URL']}/{reproduce_dir}/pubdata.toml"

    if VAR_REGISTRY['REPROWORK_ACTIVE_NOTEBOOK']:
        metadata['generating_script'] = VAR_REGISTRY['REPROWORK_ACTIVE_NOTEBOOK']
    else:
        metadata['generating_script'] = inspect_filename

    '''
    # detect if content var is of matplotlib or seaborn object type
    if type(content).__name__ in ['Figure', 'AxesSubplot'] and 'savefig' in dir(content):
        print('Saving serialized plot to SVG as file and in local data registry.')
        # Serialize plot to SVG
        buffer = io.BytesIO()
        content.savefig(buffer, format='svg')
        svg_data = buffer.getvalue()
        buffer.close()

        # Save SVG to file
        svg_filename = filename.replace('.py', '.svg')
        with open(svg_filename, 'wb') as file:
            file.write(svg_data)

        # Save SVG to registry
        metadata['plot'] = svg_data.decode()
    '''

    base_config = read_base_config()
    metadata.update(new_metadata)

    if metadata.get('type', '') == 'text/latex':
        # escape special characters
        metadata['value'] = content.replace('\\', '\\\\').replace('&', '\\&').replace('$', '\$')
    else:
        metadata['value'] = content

    # Save content to the default pubdata.toml file
    #with open(Path(reproduce_dir, 'pubdata.toml'), 'a') as file:
    #    file.write(f'\n[{name}]\n')
    #    file.write(toml.dumps(content, encoder=ReproduceWorkEncoder()))


    # For this demo, let's return the metadata (in practice, you might want to log it, save it to another file, etc.)
    if watch:
        update_watched_files(add=[Path(reproduce_dir, 'pubdata.toml').resolve().as_posix()])

    # check if dynamic file exists
    if not os.path.exists(Path(base_config['repro']['files']['dynamic'])):
        with open(Path(base_config['repro']['files']['dynamic']), 'w') as file:
            file.write(toml.dumps({}))

    with open(Path(base_config['repro']['files']['dynamic']), 'r') as file:
        dynamic_data = toml.load(file)
        
    dynamic_data[name] = metadata

    with open(Path(base_config['repro']['files']['dynamic']), 'w') as file:
        toml.dump(dynamic_data, file, encoder=ReproduceWorkEncoder())

    #return metadata
    

@requires_config
def publish_file(filename, metadata={}, watch=True):
    """
    Save content to a file and register metadata.
    """

    # Capture metadata
    timestamp = datetime.datetime.now().isoformat()
    inspect_filename = inspect.currentframe().f_back.f_code.co_filename
    #python_version = sys.version.strip().replace('\n', ' ')
    #platform_info = platform.platform()

    # generate cryptographic hash of file contents

    with open(filename, 'rb') as file:
        content = file.read()

    content_hash = hashlib.md5(content).hexdigest()
    timed_hash = hashlib.md5((content_hash + timestamp).encode('utf-8')).hexdigest()
         
    #save_context, definition_context = check_for_defintion_in_context(function_name='save')

    # Store metadata
    new_metadata = {
        "type": "file",
        "timestamp": timestamp,
        #"python_version": python_version,
        #"platform_info": platform_info,
        "content_hash": content_hash,
        "timed_hash": timed_hash,
        #"save_context": save_context,
        #"definition_context": definition_context
    }
    cell_index = get_cell_index()
    if cell_index:
        new_metadata["cell_index"] = cell_index

    if VAR_REGISTRY['REPROWORK_REMOTE_URL']:
        new_metadata['published_url'] = f"{VAR_REGISTRY['REPROWORK_REMOTE_URL']}/{filename}"

    if VAR_REGISTRY['REPROWORK_ACTIVE_NOTEBOOK']:
        new_metadata['generating_script'] = VAR_REGISTRY['REPROWORK_ACTIVE_NOTEBOOK']
    else:
        new_metadata['generating_script'] = inspect_filename

    base_config = read_base_config()
    #reproduce_work_watched_files = base_config['repro.files.watch']

    metadata.update(new_metadata)

    if watch:
        update_watched_files(add=[filename])

    # check if dynamic file exists
    if not os.path.exists(Path(base_config['repro']['files']['dynamic'])):
        with open(Path(base_config['repro']['files']['dynamic']), 'w') as file:
            file.write(toml.dumps({}))

    with open(Path(base_config['repro']['files']['dynamic']), 'r') as file:
        dynamic_data = toml.load(file)

    dynamic_data[filename] = metadata

    with open(Path(base_config['repro']['files']['dynamic']), 'w') as file:
        toml.dump(dynamic_data, file, encoder=ReproduceWorkEncoder())

    if 'verbosity' in base_config['repro'] and base_config['repro']['verbose']:
        print(f"Added metadata for file {filename} to dynamic file {base_config['repro']['files']['dynamic']}")

    #return metadata



def reproducible(var_assignment_func):
    """
    A decorator to register the line number and timestamp when a variable is assigned.
    """
    @functools.wraps(var_assignment_func)
    def wrapper(*args, **kwargs):
        # Extract value and var_name from args
        # Assumes the decorated function always takes at least two arguments: value and var_name
        value, var_name = args[0], args[1]

        # Extract metadata from kwargs or default to an empty dictionary
        metadata = kwargs.get('metadata', {})

        # Get the current frame and line number
        frame = inspect.currentframe()
        line_number = frame.f_back.f_lineno

        # Get the current timestamp
        timestamp = datetime.datetime.now().isoformat()

        # Get the filename of the caller
        filename = frame.f_back.f_code.co_filename

        # Execute the variable assignment function
        result = var_assignment_func(*args, **kwargs)

        # Register the variable name, line number, timestamp, and filename
        VAR_REGISTRY[var_name] = {
            "type": "string",
            "timestamp": timestamp,
        }

        if type(value) is not str:
            value = str(value)
            print(f"WARNING: value of {var_name} was not a string. Converted to string: {value}.")

        VAR_REGISTRY[var_name]['value'] = value

        metadata.update(VAR_REGISTRY[var_name])
        
        if VAR_REGISTRY['REPROWORK_REMOTE_URL']:
            metadata['published_url'] = f"{VAR_REGISTRY['REPROWORK_REMOTE_URL']}/{reproduce_dir}/pubdata.toml"

        if VAR_REGISTRY['REPROWORK_ACTIVE_NOTEBOOK']:
            metadata['generating_script'] = VAR_REGISTRY['REPROWORK_ACTIVE_NOTEBOOK']

        config = read_base_config()

        # check if dynamic file exists
        if not os.path.exists(Path(config['repro']['files']['dynamic'])):
            with open(Path(config['repro']['files']['dynamic']), 'w') as file:
                file.write(toml.dumps({}))
        with open(Path(config['repro']['files']['dynamic']), 'r') as file:
            dynamic_data = toml.load(file)

        dynamic_data[var_name] = metadata

        with open(Path(config['repro']['files']['dynamic']), 'w') as file:
            toml.dump(dynamic_data, file, encoder=ReproduceWorkEncoder())

        return result
    return wrapper

@reproducible
def publish_variable(value, var_name, metadata={}):
    globals()[var_name] = value


@requires_config
def register_notebook(notebook_name, notebook_dir='nbs'):
    """
    Register a notebook to the config.toml file.
    """
    notebook_path = notebook_dir + '/' + notebook_name
    base_config = read_base_config()
    
    # ensure notebook key exists
    if 'notebooks' not in base_config['repro']:
        base_config['repro']['notebooks'] = []

    if notebook_path not in base_config['repro']['notebooks']:
        base_config['repro']['notebooks'].append(notebook_path)
        with open(Path(reproduce_dir, 'config.toml'), 'w') as f:
            toml.dump(base_config, f)
        if base_config['repro']['verbose']:
            print(f"Registered notebook {notebook_path} in {reproduce_dir}/config.toml")
    else:
        if base_config['repro']['verbose']:
            print(f"Notebook {notebook_path} already registered in {reproduce_dir}/config.toml")

    if 'github_repo' in base_config['project']:
        remote_url_val = f"https://github.com/{base_config['project']['github_repo']}"
        notebook_new_val = f"{remote_url_val}/{notebook_path}"
    else:
        notebook_new_val = Path(notebook_path).resolve().as_posix()
    
    if VAR_REGISTRY['REPROWORK_REMOTE_URL']:
        print(f"Warning: {VAR_REGISTRY['REPROWORK_REMOTE_URL']} is already registered. Overwriting with {remote_url_val}")
    VAR_REGISTRY['REPROWORK_REMOTE_URL'] = remote_url_val

    if VAR_REGISTRY['REPROWORK_ACTIVE_NOTEBOOK']:
        print(f"Warning: Notebook {VAR_REGISTRY['REPROWORK_ACTIVE_NOTEBOOK']} is already registered. Overwriting with {notebook_new_val}")
    VAR_REGISTRY['REPROWORK_ACTIVE_NOTEBOOK'] = notebook_new_val

    return True

# Test code

