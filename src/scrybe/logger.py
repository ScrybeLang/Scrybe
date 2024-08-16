from colorama import Fore, Style
import sys

all_colors = {**Fore.__dict__, **Style.__dict__}.values()
log_prefixes = {
    "debug":   Fore.GREEN  + "Debug:  ",
    "info":    Fore.BLUE   + "Info:   ",
    "warning": Fore.YELLOW + "Warning:",
    "error":   Fore.RED    + "Error:  "
}

MAX_PREVIOUS_ERROR_LINES = 3

class Logger:
    def __init__(self):
        self.log_level = "info"
        self.color     = True
        self.lexpos    = None

    def set_lexpos(self, lexpos):
        self.lexpos = lexpos

    def _remove_colors(self, text):
        for color in all_colors:
            text = text.replace(color, "")

        return text

    def _print(self, *args, exit):
        text = " ".join(args)

        if not self.color:
            text = self._remove_colors(text)

        if exit: sys.exit(text)
        print(text)

    def _log(self, type, text, exit=False):
        log_levels = list(log_prefixes.keys())
        log_level  = log_levels.index(self.log_level)
        log_type   = log_levels.index(type)

        if log_type >= log_level:
            self._print(log_prefixes[type] + Fore.RESET, text, exit=exit)

    def debug(self, text):             self._log("debug",   text)
    def info(self, text):              self._log("info",    text)
    def warn(self, text):              self._log("warning", text)
    def error(self, text, exit=False): self._log("error",   text, exit=exit)

    def code_error(self, text):
        from . import filestate # Lazy import

        file_name = filestate.current_entry
        source_code = filestate.read_file()

        split_lines = source_code.split("\n")
        lexpos = self.lexpos
        text_index = lexpos if lexpos is not None else len(source_code.strip()) - 1

        # Show the faulty line of code as well as the previous few
        line_number       = source_code.count("\n", 0, lexpos)
        lower_line_index  = source_code[:text_index].count("\n") + 1
        upper_line_index  = max(lower_line_index - MAX_PREVIOUS_ERROR_LINES, 0)
        lines_to_show     = split_lines[upper_line_index:lower_line_index]
        lines_to_show[-1] = f"{Fore.YELLOW}{lines_to_show[-1]}{Fore.RESET}"
        lines_to_show     = "\n".join(lines_to_show)

        # Get the column number of the token index in the source code
        column_number  = text_index - source_code.rfind("\n", 0, text_index)
        indented_arrow = f"{' ' * (column_number - 1)}^"

        text_info_line1  = f"There was a problem parsing {Style.BRIGHT}{file_name}"
        text_info_line2  = f"Error on line {line_number + 1}, column {column_number}: "
        text_info_line2 += f"{Fore.RED}{text}{Fore.RESET + Style.RESET_ALL}"
        text_info_line3  = "-" * (len(text_info_line2) - 14) # Separator with the right size
        text_info = f"{text_info_line1}\n\n{text_info_line2}\n{text_info_line3}"

        self._print(f"{text_info}\n{lines_to_show}\n{indented_arrow}", exit=True)


logger = Logger()

debug      = logger.debug
info       = logger.info
warn       = logger.warn
error      = logger.error
code_error = logger.code_error

set_lexpos = logger.set_lexpos
