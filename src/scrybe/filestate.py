from .logger import debug, info, warn, error

file_handle = None
file_name = ""
source_code = ""

def open_file(file_path):
    global file_handle, file_name, source_code

    file_handle = open(file_path)
    file_name = file_handle.name
    source_code = file_handle.read()
    file_handle.seek(0)

    debug(f'  Opened file "{file_path}"')

def close_file():
    file_handle.close()
