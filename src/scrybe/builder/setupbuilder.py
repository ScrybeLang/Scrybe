from .codebuilder import CodeBuilder
from ..logger import set_lexpos, code_error
from .. import utils

class SetupBuilder(CodeBuilder):
    def __init__(self, projectbuilder, statements):
        self.projectbuilder = projectbuilder
        self.statements = statements

        self.variables = {}

    # Non-boolean expression translation

    def translate_expression(self, expression):
        if isinstance(expression, (int, float, str, bool)):
            return expression

        if isinstance(expression, list):
            return list(map(self.translate_expression, expression))

        set_lexpos(expression["lexpos"])

        match expression["type"]:
            case "binary operation": translation_function = self.translate_numerical_binary_operation
            case "unary minus":      translation_function = self.translate_unary_minus
            case "condition":        translation_function = self.translate_boolean
            case "concatenation":    translation_function = self.translate_concatenation
            case "index":            translation_function = self.translate_index
            case "variable":         return self.resolve_data_name(expression["variable"])

        return translation_function(expression)

    # Boolean expression translation

    def translate_boolean(self, expression):
        if isinstance(expression, (int, float)):
            return expression != 0

        if isinstance(expression, str):
            return expression != ""

        if isinstance(expression, bool):
            return expression

        condition = expression["condition"]

        if condition == "not":
            return not self.translate_boolean(expression)

        return self.translate_logical_operation(
            condition,
            expression["comparand 1"],
            expression["comparand 2"]
        )

    # Defined (global) variables

    def add_variable(self, variable_name, variable_type, variable_value):
        self.variables[variable_name] = self.projectbuilder.add_variable(
            f"g_{variable_name}", variable_type, variable_value,
            self.projectbuilder.project.stage
        )

        return self.variables[variable_name]

    def resolve_data_name(self, data_name, allow_nonexistent=False):
        if data_name in self.variables:
            return self.variables[data_name].value

        if not allow_nonexistent:
            code_error("Variable not found")

    # Inner variable declaration translation

    def build_inner_statements(self):
        for declaration in self.statements:
            set_lexpos(declaration["lexpos"])

            variable_name = declaration["name"]
            variable_type = declaration["type"]
            variable_value = self.translate_expression(declaration["value"])

            if self.resolve_data_name(variable_name, allow_nonexistent=True):
                code_error("Cannot redeclare globals")

            self._check_assignment_types(variable_type, variable_value)
            self.add_variable(
                variable_name, variable_type, variable_value
            )

    def build(self):
        self.build_inner_statements()
