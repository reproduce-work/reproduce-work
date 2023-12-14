# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/01_core.ipynb.

# %% auto 0
__all__ = ['reproduce_dir', 'project_path', 'VAR_REGISTRY', 'printrw', 'set_default_dir', 'find_project_path', 'read_base_config',
           'toml_dump', 'ReproduceWorkEncoder', 'validate_base_config', 'requires_config', 'update_watched_files',
           'PublishedObj', 'check_for_embedded_objects', 'replace_with_embedded_links', 'publish_data',
           'generate_filepath_key', 'get_cell_index', 'publish_file', 'register_notebook', 'find_pubdata_links',
           'modify_links', 'process_pubdata_links']

# %% ../nbs/01_core.ipynb 4
import os
from dotenv import load_dotenv
from pathlib import Path
import functools
import hashlib
import inspect
import re
import toml
import pandas as pd
import numpy as np
import datetime
import os
import sys
import platform
load_dotenv()


def printrw(*args, **kwargs):
    '''fancy reproduce.work print function'''
    # if the first arg is a string, prepend it with ╔ω
    if len(args) > 0 and isinstance(args[0], str):
        args = ("╔ω: "+args[0], *args[1:])

    # for each arg, replace newlines with ╚
    if len(args) > 0:
        new_args = []
        for a in args[:-1]:
            if isinstance(a, str):  
                a = a.replace("\n", "\n║ ")

            new_args.append(a)
        if isinstance(args[:-1], str): 
            new_args.append(args[:-1].replace("\n", "\n╚ "))
        else:
            new_args.append(args[-1])
        args = tuple(new_args)

    print(*args, **kwargs, flush=True)


  

def set_default_dir():
    if not os.getenv("REPROWORKDIR", False):
        dir_ = Path("./reproduce")
    else:
        dir_ = os.getenv("REPROWORKDIR")
    return dir_
                
reproduce_dir = set_default_dir()
printrw(f'Setting reproduce.work config dir to {reproduce_dir}')

def find_project_path():
    current_dir = Path().resolve()

    project_path = None
    for parent_dir in current_dir.parents:
        config_file = parent_dir / reproduce_dir / 'config.toml'
        if config_file.is_file():
            project_path = parent_dir
            break

    if not project_path:
        raise Exception(f"Could not find config.toml in any parent directory of {current_dir}; ensure you have run `rw init` in the root of your project and that you are running this command from within your project directory.")
    
    return project_path


project_path = find_project_path()



def read_base_config(return_project_path=False):

    project_path = find_project_path()
    config_loc = project_path / reproduce_dir / 'config.toml'

    with open(config_loc, 'r') as f:
        base_config = toml.load(f)
    return base_config

    
def toml_dump(val):
    # Convert special types to serializable formats
    def serialize_special_types(obj):
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient='records')
        elif obj is None:
            return 'None'
        elif isinstance(obj, dict):
            return {k: serialize_special_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [serialize_special_types(i) for i in obj]
        else:
            return obj

    serialized_val = serialize_special_types(val)
    
    return toml.loads(toml.dumps({'val': serialized_val}))['val']

class ReproduceWorkEncoder(toml.TomlEncoder):
    def dump_str(self, v):
        """Encode a string."""
        if "\n" in v:
            return '"""\n' + v.strip() + '\n' + '"""'
        return super().dump_str(v)
    
    def dump_value(self, v):
        """Determine the type of a Python object and serialize it accordingly."""
        if isinstance(v, str) and "\n" in v:
            return '"""\n' + v.strip() + '\n' + '"""'
        return super().dump_value(v)


def validate_base_config(base_config, quiet=False):
    required_keys = ['authors', 'repro']
    for key in required_keys:
        if key not in base_config:
            #printrw(toml.dumps(base_config))
            if not quiet:
                raise Exception(f"Error with ╔ω config: Missing required field '{key}' in config.toml")
            return False
        if key=='repro':
            stages = ['build', 'develop', 'run'] #base_config['repro']['stages']
            for stage in stages:
                if (f'repro.stage.{stage}' not in base_config) and (stage not in base_config['repro']['stage']):
                    if not quiet:
                        (toml.dumps(base_config, encoder=ReproduceWorkEncoder()))
                    raise Exception(f"Error with ╔ω config:: Missing required field repro.stage.{stage} in reproduce.work configuration at {reproduce_dir}/config.toml")
    return True


def requires_config(func):
    def wrapper(*args, **kwargs):
        try:
            config = read_base_config()
        except:
            print(os.getcwd())
            print(os.listdir())
            raise Exception("Your reproduce.work config is either missing or invalid. Run generate_config() to generate a config file.")
        if not validate_base_config(config):
            raise Exception("Your reproduce.work configuration is not valid.")
        if func.__name__ in ["publish_data","publish_file"] and VAR_REGISTRY['REPROWORK_REMOTE_URL'] is None:
            msg = (
                "When using publish_data or publish_file, you must first run register_notebook('code/<path to this notebook>.ipynb')" +
                "to register this session with reproduce.work. If you have multiple notebooks open simultaneously, keep in mind that" +
                "only the most recently registered notebook will be used as the generating script for any data published with publish_data or publish_file."
            )
            raise Exception(msg)
        return func(*args, **kwargs)
    return wrapper


VAR_REGISTRY = {
    'REPROWORK_REMOTE_URL': None,
    'REPROWORK_ACTIVE_NOTEBOOK': None
}

# %% ../nbs/01_core.ipynb 8
def update_watched_files(add=[], remove=[], quiet=False):
    base_config = read_base_config()
    existing_files = base_config['repro']['files']['watch']
    new_files = existing_files + [a for a in add if a not in existing_files]
    new_files = [f for f in new_files if f not in remove]
    base_config['repro']['files']['watch'] = new_files

    current_develop_script = base_config['repro']['stage']['develop']['script']
    
    # regex to replace content in string matching 'watcher \"{to_replace}\"'
    # with 'watcher \"{new_files}\"'
    # and replace 'build_cmd' with 'python reproduce_work.build()'
    import re
    new_develop_script = re.sub(
        r'watcher \"(.*?)\"', 
        f'watcher \"{",".join([f.strip() for f in new_files])}\"'.strip().rstrip(","), 
        current_develop_script
    )
    base_config['repro']['stage']['develop']['script'] = new_develop_script

    if current_develop_script!=new_develop_script:
        with open(Path(reproduce_dir, 'config.toml'), 'w') as f:
            toml.dump(base_config, f, encoder=ReproduceWorkEncoder())
            
        if base_config['repro'].get('verbose', False) and not quiet:
            printrw(f"Updated watched files to {new_files}")

    return new_files


# %% ../nbs/01_core.ipynb 10
class PublishedObj:
    def __init__(self, key, metadata=None, filepath=None, value=None):
        self.key = key
        self._metadata = metadata or {}
        self._type = self._metadata.get('type', None)
        self.value = value or self._metadata.get('value', None)
        self.embedded_link = self._metadata.get('published_url', None)
        
        self._content = None
        self._str_content = None

        # Check if this is a file type and then load content if possible
        if self._type == 'file':
            self.filepath = filepath
            self.load_file_content()
            if self._str_content:
                self.value = self._str_content
        
        elif self._type == 'data':
            self.value = self._metadata.get('value', None)
        
        else:
            self.value = self._metadata.get('value', None)
            
    def __call__(self):
        return self.value

    def load_file_content(self):
        # Check if file exists
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'rb') as f:
                    self._content = f.read()
            except Exception as e:
                raise Exception(f"Error reading file: {e}")

            # If the file extension indicates it's a text type, load as string
            if self.filepath.endswith(('.txt', '.csv', '.json')):  # add more text file extensions as needed
                self._str_content = self._content.decode('utf-8', errors='replace')

    def get_embedded_link(self):
        #printrw('loading embedded link: ' + self._metadata['published_url'] + '#' + self.key)
        self.embedded_link = self._metadata['published_url'] + '#' + self.key
        return self.embedded_link

    @property
    def content(self):
        return self._content

    @property
    def str_content(self):
        return self._str_content

    @property
    def metadata(self):
        return self._metadata



def check_for_embedded_objects(metadata, current_path=None, existing_results=None):
    if existing_results is None:
        result = {}
    else:
        result = existing_results.copy()
    
    # Initialize current_path as an empty list if it's None
    if current_path is None:
        current_path = []

    # Check if metadata is a list
    if isinstance(metadata, list):
        for idx, item in enumerate(metadata):
            new_path = current_path + [str(idx)]
            # If item is a dictionary or another list, check recursively
            if isinstance(item, (dict, list)):
                new_result = check_for_embedded_objects(item, current_path=new_path, existing_results=result)
                result.update(new_result)
            # If item is an instance of PublishedObj, process it
            elif isinstance(item, PublishedObj):
                key = ".".join(new_path)
                # Process as per your original logic
                keys = key.split('.')
                current_result = result
                for k in keys[:-1]:
                    if k not in current_result:
                        current_result[k] = {}
                    current_result = current_result[k]
                current_result[keys[-1]] = item#.metadata['published_url']
    elif isinstance(metadata, dict):
        for k, v in metadata.items():
            new_path = current_path + [k]
            
            if isinstance(v, PublishedObj):
                # Generate a key based on the current path
                key = ".".join(new_path)
                # Store the metadata
                keys = key.split('.')
                current_result = result
                for k in keys[:-1]:
                    if k not in current_result:
                        current_result[k] = {}
                    current_result = current_result[k]
                current_result[keys[-1]] = v#.metadata['published_url']

            elif isinstance(v, (dict, list)):
                # check recursively
                new_result = check_for_embedded_objects(v, current_path=new_path, existing_results=result)
                # Merge new results into the existing result dictionary
                result.update(new_result)

    else:
        raise Exception(f'Unknown metadata type: {type(metadata)}')

    return result

def replace_with_embedded_links(obj):
    """
    Recursively replace PublishedObj instances with the result of their get_embedded_link method.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, PublishedObj):
                obj[key] = value.get_embedded_link()
            else:
                replace_with_embedded_links(value)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            if isinstance(item, PublishedObj):
                obj[idx] = item.get_embedded_link()
            else:
                replace_with_embedded_links(item)


@requires_config
def publish_data(content, name, metadata={}, watch=True, force=False):
    """
    Save data to default pubdata.toml file and register metadata.
    # publishing the exact same data twice will NOT update the pubdata.toml file
    """
    base_config = read_base_config()
    pubdata_relpath = Path(base_config['repro']['files']['dynamic'])
    pubdata_fullpath = find_project_path() / pubdata_relpath

    # handle any embedded objects:
    # recurse through metadata and find any objects that are of type PublishedObj
    # and print out their names
    embedded_objects = check_for_embedded_objects(metadata)
    if embedded_objects:
        metadata_copy = metadata.copy()
        replace_with_embedded_links(metadata_copy)
        metadata = metadata_copy.copy()
    
    # Capture dynamic metadata
    timestamp = datetime.datetime.now().isoformat()
    inspect_filename = inspect.currentframe().f_back.f_code.co_filename
    #python_version = sys.version.strip().replace('\n', ' ')
    #platform_info = platform.platform()

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
    else:
        metadata['published_url'] = f"{Path(reproduce_dir, 'pubdata.toml').resolve().as_posix()}".replace('/home/jovyan/', '')

    if VAR_REGISTRY['REPROWORK_ACTIVE_NOTEBOOK']:
        metadata['generating_script'] = VAR_REGISTRY['REPROWORK_ACTIVE_NOTEBOOK']
    else:
        metadata['generating_script'] = inspect_filename.replace('/home/jovyan/', '')

    metadata.update(new_metadata)

    for k,v in metadata.items():
        if isinstance(v, dict):
            #printrw('Dumping dict w/ toml')
            metadata[k] = rf'{toml_dump(v)}'
    
    metadata['value'] = f'{toml_dump(content)}'

    """
    if metadata.get('type', '') == 'text/latex':
        # escape special characters
        #metadata['value'] = content.replace('\\', '\\\\').replace('&', '\\&').replace('$', '\$')
        pass
    elif isinstance(content, dict):
        metadata['value'] = f'''{toml_dump(content)}'''
    else:
        metadata['value'] = content
    """

    if watch:
        update_watched_files(add=[Path(reproduce_dir, 'pubdata.toml').resolve().as_posix().replace('/home/jovyan/', '')])

    # check if dynamic file exists
    if not os.path.exists(pubdata_fullpath):
        with open(pubdata_fullpath, 'w') as file:
            file.write(toml.dumps({}))
        existing_dynamic_data = {}
    else:
        with open(pubdata_fullpath, 'r') as file:
            existing_dynamic_data = toml.load(file)
        
    dynamic_data = existing_dynamic_data.copy()
    dynamic_data[name] = metadata

    existing_vals = []
    for k,v in existing_dynamic_data.items():
        if isinstance(v, dict):
            if 'value' in v:
                existing_vals.append({k:v['value']})
    
    new_vals = []
    for k,v in dynamic_data.items():
        if isinstance(v, dict):
            if 'value' in v:
                new_vals.append({k:v['value']})


    def is_equal(a, b):
        try:
            a = toml_dump(a)
            b = toml_dump(b)
            # Handle NumPy arrays
            if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
                return np.array_equal(a, b)
            
            # Handle lists and tuples
            elif isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
                return len(a) == len(b) and all([is_equal(x, y) for x, y in zip(a, b)])
            
            # For other types, attempt a direct comparison
            else:
                return a == b
            
        except ValueError:
            # If direct comparison raises a ValueError, assume they're not equal
            printrw('ValueError: could not compare values: {} and {}'.format(a, b))
            return False

    #value_changed = any([not is_equal(v, new_vals[i]) for i, v in enumerate(existing_vals)])
    #iterate through existing_vals and new_vals and check if any have changed
    changed_vals = []
    for i, v in enumerate(existing_vals):
        if i<len(new_vals):
            #if objects are identical, return False; otherwise return name(s) of variable(s) that changed
            if not is_equal(v, new_vals[i]):
                changed_vals.append(name)

    # do same for reverse
    for i, v in enumerate(new_vals):
        if i<len(existing_vals):
            if not is_equal(v, existing_vals[i]):
                changed_vals.append(name)
    
    changed_vals = list(set(changed_vals))

    if changed_vals:
        value_changed = changed_vals
    else:
        value_changed = False
    

    existing_nontimefields = {name: {k:v for k,v in var.items() if (isinstance(k, str) and k[:4] not in ['time','valu'])} if isinstance(var, dict) else var for name,var in existing_dynamic_data.items()}
    new_nontimefields = {name: {k:v for k,v in var.items() if (isinstance(k, str) and k[:4] not in ['time','valu'])} if isinstance(var, dict) else var for name,var in dynamic_data.items()}
    which_changed = []
    
    if existing_nontimefields == new_nontimefields:
        non_timefield_changed = False
    else:
        for name in existing_nontimefields:
            if name in new_nontimefields:
                if existing_nontimefields[name] != new_nontimefields[name]:
                    which_changed.append(name)
            else:
                which_changed.append(name)
        
        for name in new_nontimefields:
            if name not in existing_nontimefields:
                which_changed.append(name)
        
        non_timefield_changed = which_changed

    if value_changed:
        which_changed = value_changed + which_changed


    data_obj = PublishedObj(name, metadata)
    data_obj.get_embedded_link()
        
    if value_changed or non_timefield_changed or force:
        with open(pubdata_fullpath, 'w') as file:
            toml.dump(dynamic_data, file, encoder=ReproduceWorkEncoder())

        print(f'Published data in {pubdata_relpath}')
        print('    generating_script: ' + data_obj.metadata['generating_script'])
        print('    timed_hash: ' + data_obj.metadata['timed_hash'])
        if len(which_changed)>0:
            print('    Fields changed: ' + ', '.join([f'"{f}"' for f in which_changed]))
        

        #if base_config['repro'].get('verbose', False):
        #    if len(which_changed)>1:
        #        printrw(f"Updated {which_changed} in {pubdata_relpath}")
        #    else:
        #        printrw(f"Updated {which_changed[0]} in {pubdata_relpath}")

    else:
        print(f'Data already published in {pubdata_relpath} and value unchanged; use force=True to overwrite.')
        print('    generating_script: ' + data_obj.metadata['generating_script'])
        print('    timed_hash: ' + data_obj.metadata['timed_hash'])

    return data_obj

def generate_filepath_key(path):
    # Extract the filename from the path
    filename = path.split("/")[-1]
    
    # Replace slashes, dots, and underscores with TOML-compatible delimiters
    transformed_filename = filename.replace("_", "_us_").replace("/", "__").replace(".", "_dot_")
    
    # Compute the hash of the entire path
    hash_value = hashlib.sha256(path.encode()).hexdigest()

    # Chop off everything after and including "_dot_"
    keyname = transformed_filename.split("_dot_")[0]
    
    # Replace "_us_" with "_"
    keyname = keyname.replace("_us_", "_")
    
    # Combine the transformed filename with the first 8 characters of the hash
    key = f"{keyname}_{hash_value[:8]}"
    
    return key


def get_cell_index():
    """
    Get the current cell index in a Jupyter notebook environment.
    If not in Jupyter, return None.
    """
    try:
        # Execute JavaScript to get the current cell index
        from IPython import get_ipython
        get_ipython().run_cell_magic('javascript', '', 'IPython.notebook.kernel.execute(\'current_cell_index = \' + IPython.notebook.get_selected_index())')
        return current_cell_index
    except:
        return None
    

@requires_config
def publish_file(filepath, key=None, metadata={}, watch=True):
    """
    Save content to a file and register metadata.
    """
    if metadata is None:
        metadata = {}
    
    project_path = find_project_path()
    base_config = read_base_config()
    pubdata_relpath = Path(base_config['repro']['files']['dynamic'])
    pubdata_fullpath = project_path / pubdata_relpath

    if key is None:
        key = generate_filepath_key(filepath)


    embedded_objects = check_for_embedded_objects(metadata)
    if embedded_objects:
        #print(metadata)
        metadata_copy = metadata.copy()
        replace_with_embedded_links(metadata_copy)
        metadata = metadata_copy.copy()
        #print(metadata)

    for k,v in metadata.items():
        if isinstance(v, dict):
            #printrw('Dumping dict w/ toml')
            metadata[k] = rf'{toml_dump(v)}'

    # Capture metadata
    timestamp = datetime.datetime.now().isoformat()
    
    if 'co_filepath' in inspect.currentframe().f_back.f_code.__dir__():
        # check if in Jupyter environment has co_filepath
        inspect_filepath = inspect.currentframe().f_back.f_code.co_filepath
    else:
        inspect_filepath = ''

    #python_version = sys.version.strip().replace('\n', ' ')
    #platform_info = platform.platform()

    # generate cryptographic hash of file contents
    file_fullpath = project_path / filepath
    if not file_fullpath.exists():
        raise Exception(f'Could not find file {filepath}; ensure the file you are trying to publish is in the {project_path} directory and you are using the exact path from this location to the saved file.')
    
    with open(file_fullpath, 'rb') as file:
        content = file.read()

    content_hash = hashlib.md5(content).hexdigest()
    timed_hash = hashlib.md5((content_hash + timestamp).encode('utf-8')).hexdigest()
         
    #save_context, definition_context = check_for_defintion_in_context(function_name='save')

    # Store metadata
    new_metadata = {
        "type": "file",
        "filepath": filepath,
        "timestamp": timestamp,
        #"python_version": python_version,
        #"platform_info": platform_info,
        "content_hash": content_hash,
        "timed_hash": timed_hash
        #"save_context": save_context,
        #"definition_context": definition_context
    }
    cell_index = get_cell_index()
    if cell_index:
        new_metadata["cell_index"] = cell_index
        
    metadata.update(new_metadata)

    if watch:
        update_watched_files(add=[filepath])

    # check if dynamic file exists
    if not os.path.exists(pubdata_fullpath):
        with open(Path(pubdata_fullpath), 'w') as file:
            dynamic_data = {}
            file.write(toml.dumps(dynamic_data))
    else:
        with open(pubdata_fullpath, 'r') as file:
            dynamic_data = toml.load(file)

    if VAR_REGISTRY['REPROWORK_REMOTE_URL']:
        metadata['published_url'] = f"{VAR_REGISTRY['REPROWORK_REMOTE_URL']}/{pubdata_relpath}"
        metadata['content_url'] = f"{VAR_REGISTRY['REPROWORK_REMOTE_URL']}/{filepath}"
    else:
        metadata['published_url'] = base_config['repro']['files']['dynamic']
        metadata['content_url'] = filepath

    if VAR_REGISTRY['REPROWORK_ACTIVE_NOTEBOOK']:
        metadata['generating_script'] = VAR_REGISTRY['REPROWORK_ACTIVE_NOTEBOOK']
    else:
        metadata['generating_script'] = inspect_filename.replace('/home/jovyan/', '')

    dynamic_data[key] = metadata

    #printrw(dynamic_data)

    with open(pubdata_fullpath, 'w') as file:
        toml.dump(dynamic_data, file, encoder=ReproduceWorkEncoder())

    #if 'verbosity' in base_config['repro'] and base_config['repro']['verbose']:
    #    printrw(f"Added metadata for file {filepath} to dynamic file {pubdata_relpath}")

    data_obj = PublishedObj(key, metadata=metadata, filepath=filepath)
    data_obj.get_embedded_link()

    print(f'Published metadata for file in {pubdata_relpath}')
    print('    generating_script: ' + data_obj.metadata['generating_script'])
    print('    timed_hash: ' + data_obj.metadata['timed_hash'])

    return data_obj



@requires_config
def register_notebook(notebook_path, notebook_dir=None, quiet=False):
    """
    Register a notebook to the config.toml file.
    """
    
    base_config = read_base_config()
    project_path = find_project_path()

    if not (project_path / notebook_path).exists():
        raise Exception(f"Error: Notebook '{notebook_path}' does not exist. Ensure the notebook you are trying to register is in the '{project_path}' directory and you are using the exact path to the current notebook.")
    
    if 'repository' in base_config['project']:
        remote_url_val = f"{base_config['project']['repository']}/blob/main"
        notebook_new_val = f"{remote_url_val}/{notebook_path}"
    else:
        remote_url_val = ''
        notebook_new_val = Path(notebook_path).resolve().as_posix().replace('/home/jovyan/', '')
    
    if VAR_REGISTRY['REPROWORK_REMOTE_URL'] is None:
        printrw(f"Registered notebook {notebook_new_val} in {reproduce_dir}/config.toml")

    elif remote_url_val!=VAR_REGISTRY['REPROWORK_REMOTE_URL']:
        printrw(f"Warning: {VAR_REGISTRY['REPROWORK_REMOTE_URL']} is already registered. Overwriting with {remote_url_val}")
    VAR_REGISTRY['REPROWORK_REMOTE_URL'] = remote_url_val

    if VAR_REGISTRY['REPROWORK_ACTIVE_NOTEBOOK']:
        printrw(f"Warning: Notebook {VAR_REGISTRY['REPROWORK_ACTIVE_NOTEBOOK']} is already registered. Overwriting with {notebook_new_val}")
    VAR_REGISTRY['REPROWORK_ACTIVE_NOTEBOOK'] = notebook_new_val
    
    #update_watched_files(add=[notebook_path], quiet=True)
    if 'registered' not in base_config['repro']['files']:
        base_config['repro']['files']['registered'] = [notebook_path]
    elif notebook_path not in base_config['repro']['files']['registered']:
        base_config['repro']['files']['registered'].append(notebook_path)
    



# %% ../nbs/01_core.ipynb 12
def find_pubdata_links():
    base_config = read_base_config()
    dynamic_file = base_config['repro']['files']['dynamic']
    with open(dynamic_file, 'r') as f:
        content = f.read()
    
    # Adjusted pattern to capture optional #hash
    pattern = r"['\"]?(\w+)['\"]?\s*[:=]\s*(?:\[\s*)?['\"]?([^'\"]*pubdata\.toml(?:#([\w\d_\-]+))?)[\"']?"

    results = []
    lines = content.splitlines()
    for match in re.finditer(pattern, content):
        # Extract matched data
        var_name = match.group(1)
        path = match.group(2)
        hash_name = match.group(3)
        
        # Extract matched path details
        start_pos = match.start(2)
        end_pos = match.end(2)
        line_number = content.count('\n', 0, start_pos) + 1  # +1 because line numbers are 1-indexed

        # Identify contiguous lines before the matched line
        start_line = line_number
        for i in range(line_number - 1, 0, -1):  # Start from the line before the match
            line = lines[i - 1].strip()  # -1 because list indices are 0-indexed
            if not line and "'''" not in line and '"""' not in line:
                break
            start_line = i
        
        # Identify contiguous lines after the matched line
        end_line = line_number
        for i in range(line_number, len(lines)):
            line = lines[i].strip()
            if not line and "'''" not in line and '"""' not in line:
                break
            end_line = i + 1  # +1 because line numbers are 1-indexed

        # Extract the first line of the chunk
        toml_header = lines[start_line - 1].strip()  # -1 because list indices are 0-indexed
        
        result_data = {
            "variable": var_name,
            "path": path,
            "start_pos": start_pos,
            "end_pos": end_pos,
            "line_range": (start_line, end_line),
            "toml_header": toml_header,
            "on_line": line_number,
            'at_char': start_pos - content.rfind('\n', 0, start_pos),
        }
        
        if hash_name:
            result_data["hash"] = hash_name
        else:
            result_data["hash"] = None
        
        
        results.append(result_data)
    
    final_results = []
    for r in results:
        if 'variable' in r.keys() and 'path' in r.keys():
            if r['variable'] + r['path'][:2] in ['https//','http//']:
                continue
        
        # if r['hash'] resembles 'L{DIGITS}(\-L{DIGITS})?', then continue
        #if 'hash' in r.keys() and r['hash']:
        #    if re.match(r'L\d+(\-L\d+)?', r['hash']):
        #        continue
            
        final_results.append(r)              
    
    return final_results


# %% ../nbs/01_core.ipynb 14
def modify_links(linenum, link_str, newlink):

    base_config = read_base_config()
    pubdata_filename = Path(base_config['repro']['files']['dynamic'])
    pubdata_loc = find_project_path() / pubdata_filename

    with open(pubdata_loc, 'r') as f:
        content = f.read()

    lines = content.splitlines()
    content_line = lines[linenum-1]

    # Define a replacement function that retains the original hash (if present) and appends the linehash
    def replacement(match):
        # Determine the type of quote used based on the first character of the matched link
        quote_type = match.group(1)[0]
        
        return f'{quote_type}{newlink}{quote_type}'  # Construct the replacement string

    # Patterns to match the link (double or single quoted) and capture the hash if present
    double_quoted_pattern = rf'("{link_str})(#.*?)?"'
    single_quoted_pattern = rf'(\'{link_str})(#.*?)?\''

    # Apply the replacement for both double and single quoted links
    new_content_line = re.sub(double_quoted_pattern, replacement, content_line)
    new_content_line = re.sub(single_quoted_pattern, replacement, new_content_line)

    lines[linenum-1] = new_content_line
    new_content = '\n'.join(lines)

    with open(pubdata_loc, 'w') as f:
        f.write(new_content)

    return content_line



def process_pubdata_links(verbose=False):
    #base_config = read_base_config()
    #verbose = base_config['repro']['verbose']
    publinks = find_pubdata_links()
    pldf = pd.DataFrame(publinks)

    pldf_og = pldf.copy

    # iterate through find the self-referenential links first,
    # i.e., those for which the "variable" of the link is "published_url"
    vars = (pldf.variable=='published_url')
    top_level_vars = pldf.loc[vars,'toml_header'].str.slice(1,-1).tolist()
    for var in top_level_vars:
        # find the linkdata for this variable
        linkdata = pldf.query(f"toml_header=='[{var}]' and variable=='published_url'")
        linkdata = linkdata.iloc[0]

        #if end of linkpath already ends with pattern like `#L[numbers]` or `#L[numbers]-L[numbers]`, continue
        if re.match(r'.*#L\d+(\-L\d+)?', linkdata.path):
            continue

        llo, lhi = (linkdata.line_range)
        newlink = linkdata.path + f'#L{llo}-L{lhi}'
        if verbose:
            printrw(f'modify_links({linkdata.on_line}, {linkdata.path}, {newlink})')
        modify_links(linkdata.on_line, linkdata.path, newlink)
        
    publinks = find_pubdata_links()
    pldf = pd.DataFrame(publinks)
    top_var_links = dict(zip(
        pldf.loc[vars,'toml_header'].str.slice(1,-1).tolist(), 
        pldf.loc[vars,'path'].tolist()
    ))

    nontop_vars = pldf.loc[~vars,].index.tolist()

    for linktext_idx in nontop_vars:
        linkdata = pldf.loc[linktext_idx]

        #print(linktext_idx, linkdata)

        if re.match(r'.*#L\d+(\-L\d+)?', linkdata.path):
            continue
        
        if (
            ('hash' in linkdata and linkdata['hash'] in top_var_links.keys()) or \
            ('variable' in linkdata and linkdata['variable'] in top_var_links.keys())
        ):
            
            target_var = linkdata['hash'] if ('hash' in linkdata and linkdata['hash']) else linkdata['variable']
            newlink = top_var_links[target_var]

            if verbose:
                printrw(f'modify_links({linkdata.on_line}, {linkdata.path}, {newlink})')
                modify_links(linkdata.on_line, linkdata.path, newlink)

        else:
            raise Exception(f"Could not find link target for {linkdata['path']}")

    return pldf_og
