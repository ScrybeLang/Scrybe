from .logger import debug

# File entries: {
#     <relative filepath>: {
#         "handle":  <file handle>,
#         "content": <file content>
#     },
#     ...
# }
file_entries = {}
current_entry = None

def open_file(file_path):
    global file_entries, current_entry

    file_path = file_path.replace("\\", "/")
    file_handle = open(file_path)
    file_content = file_handle.read()

    file_entries[file_path] = {
        "handle":  file_handle,
        "content": file_content
    }

    current_entry = file_path
    debug(f'  Opened file "{file_path}"')

def read_file():
    global file_entries, current_entry

    return file_entries[current_entry]["content"]

def close_file():
    global file_entries, current_entry

    file_entries[current_entry]["handle"].close()
    current_entry = None
