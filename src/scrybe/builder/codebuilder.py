from abc import ABC, abstractmethod
from ScratchGen.blocks import *
from ..types import Types
from .. import translations
from ..utils import set_type

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

        Types.check_types(
            [[Types.NUMBER, Types.NUMBER]],
            [operand_1, operand_2],
            "Cannot perform numerical operation on a {} and a {}"
        )

        return operation(operand_1, operand_2)

    def translate_unary_minus(self, expression):
        number = self.translate_expression(expression["expression"])

        Types.check_types([[Types.NUMBER]], [number], "Cannot negate a {}")
        return number * -1

    def translate_numerical_logic_operation(self, condition, comparand_1, comparand_2):
        comparand_1 = self.translate_expression(comparand_1)
        comparand_2 = self.translate_expression(comparand_2)

        possible_types = [[Types.NUMBER, Types.NUMBER]]
        if condition in ("==", "!="):  # (In)equality operators can also work with strings
            possible_types += [[Types.STRING, Types.STRING]]

        Types.check_types(
            possible_types,
            [comparand_1, comparand_2],
            "Cannot compare a {} to a {}"
        )

        return translations.operations[condition](comparand_1, comparand_2)

    def translate_logical_binary_operation(self, condition, comparand_1, comparand_2):
        is_in = condition == "in"

        # Only the inputs for "in" aren't boolean inputs
        function = self.translate_expression if is_in else self.translate_boolean
        operand_1 = function(comparand_1)
        operand_2 = function(comparand_2)

        if is_in:
            Types.check_types(
                [[Types.LIST], [Types.STRING]],
                [operand_2],
                "{} is not a container"
            )

        return translations.boolean_conditions[condition](operand_1, operand_2)

    def translate_logical_operation(self, condition, comparand_1, comparand_2):
        if condition in translations.number_conditions:
            function = self.translate_numerical_logic_operation
        else:
            function = self.translate_logical_binary_operation

        return function(condition, comparand_1, comparand_2)

    def translate_concatenation(self, expression):
        operand_1 = self.translate_expression(expression["operand 1"])
        operand_2 = self.translate_expression(expression["operand 2"])

        Types.check_types(
            [[Types.STRING, Types.STRING]],
            [operand_1, operand_2],
            "Cannot concatenate a {} to a {}"
        )

        if isinstance(operand_1, str) and isinstance(operand_2, str):
            return operand_1 + operand_2
        return Join(operand_1, operand_2)

    def translate_index(self, expression):
        target = self.translate_expression(expression["target"])
        index = self.translate_expression(expression["index"])

        self._check_index_types(target, index)
        index += 1

        if Types.get_type(target) == Types.LIST:
            return set_type(ItemOfList(index, target), Types.GENERAL)
        return LetterOf(index, target)

    def _check_index_types(self, target, index):
        Types.check_types([[Types.LIST], [Types.STRING]], [target],
            "Index target must be a string/list, not a {}")

        Types.check_types([[Types.NUMBER]], [index],
            "Index must be a number, not a {}")

    def _check_assignment_types(self, variable_type, value_type):
        Types.check_types(
            [[variable_type, variable_type]],
            [variable_type, value_type],
            "Cannot assign a {1} value to a {0}"
        )
