from abc import ABC, abstractmethod
from ScratchGen.blocks import *
from . import translations
from . import utils

class CodeBuilder(ABC):
    @abstractmethod
    def __init__(self, projectbuilder, statements, *args, **kwargs):
        ...

    @abstractmethod
    def build(self):
        ...

    @abstractmethod
    def build_inner_statements(self, statements, modify_scope=True):
        ...

    @abstractmethod
    def translate_expression(self, expression):
        ...

    @abstractmethod
    def translate_boolean(self, expression):
        ...

    @abstractmethod
    def add_variable(self, variable_name, variable_type, variable_value):
        ...

    @abstractmethod
    def resolve_data_name(self, data_name, allow_nonexistent=False):
        ...

    def translate_numerical_binary_operation(self, expression):
        operation = translations.operations[expression["operation"]]
        operand_1 = self.translate_expression(expression["operand 1"])
        operand_2 = self.translate_expression(expression["operand 2"])

        utils.check_types((
            "number|variable number|variable",),
            "Cannot perform numerical operation on a {} and a {}",
            operand_1, operand_2
        )

        return operation(operand_1, operand_2)

    def translate_unary_minus(self, expression):
        expression = self.translate_expression(expression["expression"]) # Expression

        utils.check_types((
            "number", "variable"),
            "Cannot negate a {}", expression)

        return expression * -1

    def translate_numerical_logic_operation(self, condition, comparand_1, comparand_2):
        comparand_1 = self.translate_expression(comparand_1)
        comparand_2 = self.translate_expression(comparand_2)

        possibilities = ["number|variable number|variable"]
        if condition in ("==", "!="):
            possibilities += ["string|variable string|variable"]

        utils.check_types(possibilities, "Cannot compare a {} to a {}",
                            comparand_1, comparand_2)

        return translations.operations[condition](comparand_1, comparand_2)

    def translate_logical_binary_operation(self, condition, comparand_1, comparand_2):
        is_in = condition == "in"

        # Only the inputs for "in" aren't boolean inputs
        function = self.translate_expression if is_in else self.translate_boolean
        operand_1 = function(comparand_1)
        operand_2 = function(comparand_2)

        if is_in:
            utils.check_types(("string", "variable", "list"),
                "{} is not a container", operand_2)

        return translations.boolean_conditions[condition](operand_1, operand_2)

    def translate_logical_operation(self, condition, comparand_1, comparand_2):
        if condition in translations.number_conditions:
            function = self.translate_numerical_logic_operation
        else:
            function = self.translate_logical_binary_operation

        return function(condition, comparand_1, comparand_2)

    def translate_concatenation(self, expression):
        string_1 = self.translate_expression(expression["operand 1"])
        string_2 = self.translate_expression(expression["operand 2"])

        utils.check_types((
            "string|variable string|variable"),
            "Cannot concatenate a {} to a {}", string_1, string_2)

        if isinstance(string_1, str) and isinstance(string_2, str):
            return string_1 + string_2

        return Join(string_1, string_2)

    def translate_index(self, expression):
        target = self.translate_expression(expression["target"])
        index = self.translate_expression(expression["index"])

        self._check_index_types(target, index)
        index += 1

        if utils.get_type(target) == "list":
            return utils.copy_and_apply_type(ItemOfList(index, target), "variable")
        return LetterOf(index, target)

    def _check_index_types(self, target, index):
        utils.check_types(("list", "string", "variable"),
            "Index target must be a string or a list, not a {}", target)

        utils.check_types(("number", "variable"),
            "Index must be a number, not a {}", index)

    def _check_assignment_types(self, variable_type, value_type):
        utils.check_types((
            f"{variable_type} {variable_type}",
            "variable         any",
            "any              variable"
        ),
        "Cannot assign a {1} value to a {0}",
        variable_type, value_type, is_types=True)
