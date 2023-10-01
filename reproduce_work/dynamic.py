# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/02_dynamic.ipynb.

# %% auto 0
__all__ = ['reproduce_dir', 'dev_image_tag', 'x', 'y', 'z', 'save']

# %% ../nbs/02_dynamic.ipynb 4
import toml
import os
from pathlib import Path
from dotenv import load_dotenv
import sys

load_dotenv()
reproduce_dir = os.getenv("REPROWORKDIR", Path("./reproduce"))
dev_image_tag = os.getenv("REPRODEVIMAGE")

import toml

def save():
    # Get all global variables
    all_globals = globals()
    
    # Filter out built-in and system-related entries (e.g., functions, modules)
    # You might need to add more filtering depending on your environment
    filtered_globals = {k: v for k, v in all_globals.items() if not k.startswith("_") and not callable(v) and type(v).__name__ != 'module'}
    
    # Check if the code is being executed in an interactive notebook environment or in a script environment
    if 'ipykernel' in sys.modules:
        # If executed in an interactive notebook environment, print the output
        print(toml.dumps(filtered_globals))
    else:
        # If executed in a script environment, save the output to a file
        with open('globals.toml', 'w') as f:
            f.write(toml.dumps(filtered_globals))

# Test
x = 10
y = "Hello"
z = [1, 2, 3]

save()

