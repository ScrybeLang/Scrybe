from .codebuilder import CodeBuilder
from ..logger import set_lexpos, code_error

class SetupBuilder(CodeBuilder):
    def __init__(self, projectbuilder, statements):
        self.projectbuilder = projectbuilder
        self.statements = statements

        self.variables = {}

    # Expression translation

    def translate_expression(self, expression):
        if isinstance(expression, list):
            return list(map(self.translate_expression, expression))

        if not isinstance(expression, dict):
            # Handle all other literals
            return expression

        set_lexpos(expression["lexpos"])

        match expression["type"]:
            case "index":                translation_function = self.translate_index
            case "concatenation":        translation_function = self.translate_concatenation
            case "numerical operation":  translation_function = self.translate_numerical_operation
            case "comparison operation": translation_function = self.translate_comparison_operation
            case "logical operation":    translation_function = self.translate_logical_operation

            case "variable":             return self.resolve_data_name(expression["variable"])

        return translation_function(expression)

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
