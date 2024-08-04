from .setupparser import parse_file as parse_setup
from .scriptparser import parse_file as parse_script
from .projectbuilder import ProjectBuilder
from .logger import log_prefixes, logger, debug, info, warn, error
import os
import glob
import sys

def get_arguments():
    provided_arguments = sys.argv[1:]

    # Get project directory (always the first argument)
    provided_path = provided_arguments[0]
    if not os.path.exists(provided_path):
        error(f'The provided path ("{provided_path}") does not exist', exit=True)
    provided_arguments = provided_arguments[1:]

    # Set defaults
    output_filename = None
    log_level       = "info"
    color           = True

    # While-based loop so we can skip argument values
    i = 0
    while i < len(provided_arguments):
        string = provided_arguments[i]
        if string[0] == '"' and string[-1] == '"':
            string = string[1:-1]

        if string.endswith(".sb3"):
            output_filename = string

        elif string == "-log":
            if i == len(provided_arguments) - 1:
                error("Missing log level", exit=True)
            if provided_arguments[i + 1] not in log_prefixes:
                valid_arguments = ", ".join(log_prefixes.keys())
                error(f"Invalid log level, must be one of {valid_arguments}", exit=True)

            i += 1
            log_level = provided_arguments[i]

        elif string == "-color":
            if i == len(provided_arguments) - 1:
                error("Missing color option", exit=True)
            if provided_arguments[i + 1].lower() not in ("on", "off"):
                error("Invalid color option, must be one of on, off", exit=True)

            i += 1
            color = provided_arguments[i].lower() == "on"

        else:
            error(f'Unknown argument - "{string}"', exit=True)

        i += 1

    return {
        "project path":    provided_path,
        "output filename": output_filename,
        "log level":       log_level,
        "color":           color
    }

def main():
    arguments = get_arguments()
    project_path    = arguments["project path"]
    output_filename = arguments["output filename"]
    log_level       = arguments["log level"]
    color           = arguments["color"]

    logger.log_level = log_level
    logger.color     = color

    # Makes accessing file paths easier
    debug(f'Changing running directory to {project_path}')
    running_directory = os.getcwd()
    os.chdir(project_path)

    directory_name = os.path.basename(os.getcwd())
    projectbuilder = ProjectBuilder(directory_name)

    debug("Applying setup")
    if os.path.exists("setup.sbc"):
        projectbuilder.apply_setup(parse_setup("setup.sbc"))
        info("Setup applied")
    else:
        warn("Setup file not found")

    debug("Adding stage")
    if os.path.exists("stage.sbs"):
        projectbuilder.add_stage(parse_script("stage.sbs"))
    else:
        warn("Stage not found")

    debug("Searching for sprite folder")
    if not os.path.exists("sprites"):
        warn("Sprites folder not found")

    debug("Gathering sprites")
    sprite_paths = glob.glob("sprites/*.sbs")
    if not sprite_paths:
        warn("Sprites folder exists but contains no sprites")

    debug("Adding sprites")
    for filepath in sprite_paths:
        debug(f'Adding sprite from "{filepath}"')
        sprite_name = projectbuilder.add_sprite(
            parse_script(filepath),
            os.path.basename(filepath)
        )
        info(f'Added sprite "{sprite_name}"')

    debug("Building project")
    projectbuilder.build()
    info("Project built")

    debug("Saving project")
    os.chdir(running_directory)
    filename = projectbuilder.save(output_filename)
    info(f'Project saved as "{filename}"')

if __name__ == "__main__":
    main()
