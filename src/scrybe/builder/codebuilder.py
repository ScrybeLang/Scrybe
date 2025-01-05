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
    def add_variable(self, variable_name, variable_type, variable_value):
        ...

    @abstractmethod
    def resolve_data_name(self, data_name, allow_nonexistent=False):
        ...

    def translate_index(self, expression):
        target = self.translate_expression(expression["target"])
        index = self.translate_expression(expression["index"])

        Types.check_types([[Types.LIST], [Types.STRING]], [target],
            "Index target must be a string/list, not a {}")
        Types.check_types([[Types.NUMBER]], [index],
            "Index must be a number, not a {}")

        index += 1  # Scratch indices are 1-based

        if Types.get_type(target) == Types.LIST:
            return set_type(ItemOfList(index, target), Types.GENERAL)
        return LetterOf(index, target)

    def translate_concatenation(self, expression):
        operand_1, operand_2 = map(self.translate_expression, expression["operands"])

        Types.check_types(
            [[Types.STRING, Types.STRING]],
            [operand_1, operand_2],
            "Cannot concatenate a {} to a {}"
        )

        if isinstance(operand_1, str) and isinstance(operand_2, str):
            return operand_1 + operand_2
        return Join(operand_1, operand_2)

    def translate_numerical_operation(self, expression):
        operation = expression["operation"]
        operands = list(map(self.translate_expression, expression["operands"]))

        if len(operands) == 1:
            Types.check_types([[Types.NUMBER]], [operands[0]],
                "Cannot perform numerical operation on a {}")
        else:
            Types.check_types(
                [[Types.NUMBER, Types.NUMBER]],
                operands,
                "Cannot perform numerical operation on a {} and a {}"
            )

        return translations.numerical_operations[operation](*operands)

    def translate_comparison_operation(self, expression):
        condition = expression["condition"]
        comparand_1, comparand_2 = map(self.translate_expression, expression["operands"])

        possible_types = [[Types.NUMBER, Types.NUMBER]]
        if condition in ("==", "!="):
            # (In)equality comparisons can also work with two strings
            possible_types += [[Types.STRING, Types.STRING]]

        Types.check_types(possible_types, [comparand_1, comparand_2],
            "Cannot perform comparison operation on a {} and a {}")

        return translations.comparison_operations[condition](comparand_1, comparand_2)

    def translate_logical_operation(self, expression):
        condition = expression["condition"]
        # Don't translate boolean literals yet because they are handled
        # in a special way during translation to avoid unnecessary operations
        comparands = [i if isinstance(i, bool) else self.translate_expression(i) for i in expression["comparands"]]

        if condition == "in":
            Types.check_types([[Types.LIST], [Types.STRING]], [comparands[1]],
                "{} is not a container")
        else:
            Types.check_types([[Types.BOOLEAN, Types.BOOLEAN]], comparands,
                "Cannot perform logical operation on a {} and a {}")

        return translations.logical_operations[condition](*comparands)

    def _check_assignment_types(self, variable_type, value_type):
        Types.check_types(
            [[variable_type, variable_type]],
            [variable_type, value_type],
            "Cannot assign a {1} value to a {0}"
        )
