from .setupparser import parse_file as parse_setup
from .scriptparser import parse_file as parse_script
from .builder import ProjectBuilder
from .logger import log_prefixes, logger, debug, info, warn, error
from . import filestate
from argparse import ArgumentParser
import os
import glob

def get_arguments():
    parser = ArgumentParser()
    parser.add_argument("path", help="Relative path to the project directory")
    parser.add_argument("filename", nargs="?", help="Name of the output file with .sb3 extension")
    parser.add_argument("-log", choices=log_prefixes.keys(), default="info", help="Logging level")
    parser.add_argument("-nocolor", action="store_false", dest="color", help="Disable colored output")
    parser.add_argument("-open", action="store_true", help="Open the output file after building")

    args = parser.parse_args()

    if not os.path.exists(args.path):
        error(f'The provided path ("{args.path}") does not exist', exit=True)

    return args

def main():
    arguments = get_arguments()
    project_path    = arguments.path
    output_filename = arguments.filename
    log_level       = arguments.log
    color           = arguments.color
    open_after      = arguments.open

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
        filestate.open_file("setup.sbc")
        projectbuilder.apply_setup(parse_setup())
        filestate.close_file()

        info("Setup applied")
    else:
        warn("Setup file not found")

    debug("Adding stage")
    if os.path.exists("stage.sbs"):
        filestate.open_file("stage.sbs")
        projectbuilder.add_stage(parse_script())
        filestate.close_file()

    else:
        warn("Stage not found")

    debug("Searching for sprite folder")
    if not os.path.exists("sprites"):
        warn("Sprites folder not found")

    else:
        debug("Gathering sprites")
        sprite_paths = glob.glob("sprites/*.sbs")
        if not sprite_paths:
            warn("Sprites folder exists but contains no sprites")

        debug("Adding sprites")
        for filepath in sprite_paths:
            debug(f'Adding sprite from "{filepath}"')

            filestate.open_file(filepath)
            sprite_name = projectbuilder.add_sprite(parse_script(), os.path.basename(filepath))
            filestate.close_file()

            info(f'Added sprite "{sprite_name}"')

    debug("Building project")
    projectbuilder.build()
    info("Project built")

    debug("Saving project")
    os.chdir(running_directory)
    filename = projectbuilder.save(output_filename)
    info(f'Project saved as "{filename}"')

    if open_after:
        os.startfile(filename)

if __name__ == "__main__":
    main()
