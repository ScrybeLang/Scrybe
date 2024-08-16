from ScratchGen.block import Boolean
from ScratchGen.blocks import *
from ScratchGen.datacontainer import List
from . import translations
from . import utils
from .logger import debug, code_error, set_lexpos
from inspect import signature

class ScriptBuilder:
    def __init__(self, projectbuilder, statements, target):
        self.projectbuilder = projectbuilder
        self.statements = statements
        self.target = target
        self.is_sprite = not self.target._is_stage
        self.variable_prefix = "s" if self.is_sprite else "b"

        self._scope_ID = 0
        self._scope_stack = [0]
        self.current_scope_ID = 0

        # Functions: {
        #     <function name>: {
        #         "callable":   <callable object>,
        #         "parameters": <parameter count>,
        #         "output":     <output variable>
        #     },
        #     ...
        # }
        self.functions = {}
        self.current_function_building = "" # Name of the function currently being built
        self.current_script_reference = [] # Python list references son epicas
        self.scripts = [] # 2D list of block objects

        if self.is_sprite:
            self.is_clone_variable = self.target.createVariable("sg_is_clone", "false")

            self.scripts.extend([[
                WhenFlagClicked(),
                SetVariable(self.is_clone_variable, "false")
            ], [
                WhenStartAsClone(),
                SetVariable(self.is_clone_variable, "true")
            ]])

    def translate_expression(self, expression):
        if isinstance(expression, bool):
            return self.translate_boolean(expression)

        if isinstance(expression, list):
            return list(map(self.translate_expression, expression))

        if not isinstance(expression, dict):
            return expression

        set_lexpos(expression["lexpos"])

        if expression["type"] == "binary operation":
            operation = translations.operations[expression["operation"]]
            operand_1 = self.translate_expression(expression["operand 1"])
            operand_2 = self.translate_expression(expression["operand 2"])

            return operation(operand_1, operand_2)

        if expression["type"] == "condition":
            return self.translate_boolean(expression)

        if expression["type"] == "unary minus":
            return self.translate_expression(expression["expression"]) * -1

        if expression["type"] == "variable":
            dict_entry = self.resolve_data_name(expression["variable"])
            if not dict_entry:
                code_error("Variable not found")

            return dict_entry["object"]

        if expression["type"] == "index":
            expression_target = expression["target"]
            expression_index = expression["index"]

            try:
                # Add one to the index because Scratch has one-based indexing
                index = self.translate_expression(expression["index"]) + 1
            except:
                if isinstance(expression_index, dict):
                    set_lexpos(expression_index["lexpos"])
                code_error("Index must be numerical")

            # For literals
            if not isinstance(expression_target, dict):
                return LetterOf(index, expression_target)

            if expression_target["type"] == "variable":
                dict_entry = self.resolve_data_name(expression_target["variable"])
                variable_object = dict_entry["object"]

                if dict_entry["type"] == "list":
                    return ItemOfList(index, variable_object)
                return LetterOf(index, variable_object)

            # Any other expression
            target_object = self.translate_expression(expression_target)
            return LetterOf(index, target_object)

        if expression["type"] == "get attribute":
            # Check if attribute is of a list/variable first
            variable_attribute = self.translate_variable_attribute(expression, [], "reporter")
            if variable_attribute:
                return variable_attribute

            if expression["object"] == "this" and expression["attribute"] == "is_clone":
                if not self.is_sprite:
                    code_error("This attribute can only be used in a sprite")
                return self.is_clone_variable

            return self.get_builtin(
                expression,
                translations.resolve_reporter,
                "attribute"
            )()

        if expression["type"] == "function call":
            function = expression["function"]
            arguments = list(map(self.translate_expression, expression["arguments"]))

            # Check if is a custom function first
            if function["type"] == "variable" and function["variable"] in self.functions:
                function_name = function["variable"]
                dict_entry = self.functions[function_name]

                self.argument_error_message(0, dict_entry["parameters"], len(arguments))
                callable_object = dict_entry["callable"]
                output_object = dict_entry["output"]

                self.current_script_reference.append(callable_object(*arguments))
                return output_object

            # Check if function is of a list/variable
            variable_attribute = self.translate_variable_attribute(function, arguments, "reporter")
            if variable_attribute:
                return variable_attribute

            callable_object = self.get_builtin(
                function,
                translations.resolve_function_reporter,
                "function"
            )
            self.check_argument_count(callable_object, arguments)

            if callable_object.__name__ == "TouchingObject":
                target = arguments[0]
                if target in self.projectbuilder.sprites:
                    return callable_object(self.projectbuilder.sprites[target]["object"])

            return callable_object(*arguments)

        if expression["type"] == "concatenation":
            one = self.translate_expression(expression["one"])
            two = self.translate_expression(expression["two"])

            if isinstance(one, str) and isinstance(two, str):
                return one + two

            return Join(one, two)

    def translate_boolean(self, expression):
        if isinstance(expression, bool):
            # True = 1, False = 0
            return Equals(int(expression), 1)

        if isinstance(expression, str):
            # Check if string is not empty
            return Not(Equals(expression, ""))

        if isinstance(expression, (int, float)):
            # Zero is the only numerically falsy value
            return Not(Equals(expression, 0))

        if "condition" not in expression:
            reporter = self.translate_expression(expression)

            if isinstance(reporter, Boolean):
                return reporter
            if getattr(reporter, "name", None) == "sg_is_clone":
                return Equals(reporter, "true")

            return Not(Or(Equals(reporter, 0), Equals(reporter, "")))

        condition = expression["condition"]

        if condition == "not":
            return Not(self.translate_boolean(expression["comparand"]))

        if condition in translations.number_conditions:
            return translations.number_conditions[condition](
                self.translate_expression(expression["comparand 1"]),
                self.translate_expression(expression["comparand 2"])
            )

        if condition in translations.boolean_conditions:
            # Only the inputs for "in" aren't boolean inputs
            function = self.translate_expression if condition == "in" else self.translate_boolean

            return translations.boolean_conditions[condition](
                function(expression["comparand 1"]),
                function(expression["comparand 2"])
            )

    def resolve_data_name(self, data_name):
        variables = self.projectbuilder.variables

        # Check global variables first
        global_variables = variables["global"]
        if f"g_{data_name}" in global_variables:
            return global_variables[f"g_{data_name}"]

        # Then, check target-wise local variables
        if self.is_sprite:
            local_variables = variables["local"]["sprites"][self.target.name]
        else:
            local_variables = variables["local"]["stage"]

        if f"{self.variable_prefix}_{data_name}" in local_variables:
            return local_variables[f"{self.variable_prefix}_{data_name}"]

        # Lastly, check scoped variables
        for encoded_name, dict_entry in local_variables.items():
            if encoded_name[:2] in ("g_", "s_", "b_", "fo"):
                continue

            encoded_scope, name = encoded_name.split("_", maxsplit=1)
            scope_ID = int(encoded_scope[1:])

            if name == data_name and scope_ID in [self.current_scope_ID, *self._scope_stack]:
                # `scope_ID` can either be the current scope ID or in the stack
                return dict_entry

    def add_variable(self, variable_name, variable_value):
        prefix = self.variable_prefix
        current_scope = self.current_scope_ID
        if current_scope > 0:
            prefix += str(current_scope)

        variable_name = f"{prefix}_{variable_name}"

        dict_entry = self.projectbuilder.add_variable(variable_name, variable_value, self.target)
        return dict_entry["object"]

    # Returns a list of blocks necessary to set any value
    def get_variable_setter(self, statement):
        to_assign = statement["variable"]
        variable_value = self.translate_expression(statement["value"])

        set_lexpos(to_assign["lexpos"])

        if to_assign["type"] == "variable":
            variable_name = to_assign["variable"]
            is_literal_list = isinstance(variable_value, list)
            is_variable_list = isinstance(variable_value, List)

            dict_entry = self.resolve_data_name(variable_name)
            if dict_entry:
                # Variable already exists
                variable_type = dict_entry["type"]
                variable_object = dict_entry["object"]

                if variable_type != "list" and (is_literal_list or is_variable_list):
                    code_error("Cannot assign a list value to a non-list")

                if variable_type == "list" and not (is_literal_list or is_variable_list):
                    code_error("Cannot assign variable value to a list")

            else:
                # Variable does not yet exist, create and set it
                initial_value = variable_value
                if not utils.is_literal(initial_value):
                    initial_value = [] if is_literal_list else ""

                # This is just the initial value, which doesnt't matter much;
                # the setter block is added next
                variable_object = self.add_variable(variable_name, initial_value)

            if is_literal_list:
                # Add each item to the list separately
                return [
                    ClearList(variable_object),
                    *(AddToList(self.translate_expression(item), variable_object) for item in variable_value)
                ]

            else:
                return [SetVariable(variable_object, variable_value)]

        # For things like `this.size = 50`
        if to_assign["type"] == "get attribute":
            return [
                self.get_builtin(
                    to_assign,
                    translations.resolve_setter,
                    "attribute"
                )(variable_value)
            ]

    # Get either a block or reporter from a variable function or attribute
    # For example, `my_list.length` translates to about `ListLength(my_list)`
    def translate_variable_attribute(self, expression, arguments, function_type):
        list_dictionary = translations.list_reporters if function_type == "reporter" else translations.list_functions
        variable_dictionary = translations.variable_reporters if function_type == "reporter" else translations.variable_functions
        attribute = expression["attribute"]

        dict_entry = self.resolve_data_name(expression["object"])
        if dict_entry:
            # Set lex position of attribute (+ 1 for the period)
            set_lexpos(expression["lexpos"] + len(expression["object"]) + 1)

            if dict_entry["type"] == "list":
                if attribute not in list_dictionary:
                    code_error("List function not found")

                function = list_dictionary[expression["attribute"]]
            else:
                if attribute not in variable_dictionary:
                    code_error("Variable function not found")

                function = variable_dictionary[expression["attribute"]]

            variable_object = dict_entry["object"]
            return function(*arguments, variable_object)

    def check_argument_count(self, function_object, given_arguments):
        parameters = [i for i in signature(function_object).parameters.values()]
        required_parameters = len([i for i in parameters if i.default == i.empty])
        optional_parameters = len(parameters) - required_parameters
        given_argument_count = len(given_arguments)

        self.argument_error_message(optional_parameters, required_parameters, given_argument_count)

    def argument_error_message(self, optional_parameters, required_parameters, given_argument_count):
        should_error = False
        if not optional_parameters and given_argument_count != required_parameters:
            should_error = True
            expected = f"Expected {required_parameters} argument"

        total_parameters = required_parameters + optional_parameters
        if optional_parameters and not (required_parameters <= given_argument_count <= total_parameters):
            should_error = True
            expected = f"Expected {required_parameters} to {total_parameters} argument"

        if should_error:
            code_error((
                expected +
                f"{"" if total_parameters == 1 else "s"}, "
                f"got {given_argument_count}"
            ))

    def get_builtin(self, obj, resolution_function, type_name):
        resolution_attempt = resolution_function(obj)
        if not resolution_attempt:
            if "lexpos" in obj: set_lexpos(obj)
            code_error(f"{type_name.title()} not found")

        callable_object, sprite_specific = resolution_attempt
        if sprite_specific and not self.is_sprite:
            code_error(f"This {type_name} can only be used in a sprite")

        return callable_object

    # Inner statements: what are under a hat block/function prototype
    def build_inner_statements(self, statements, modify_scope=True):
        if modify_scope:
            self.enter_scope()

        current_script = []
        self.current_script_reference = current_script

        for statement in statements:
            set_lexpos(statement["lexpos"])

            if statement["type"] == "assignment":
                current_script.extend(self.get_variable_setter(statement))

            if statement["type"] == "in-place assignment":
                operation_type = statement["operation"][:-1] # Cut off the trailing equals sign
                operation = Join if operation_type == ".." else translations.operations[operation_type]

                to_assign = statement["variable"]
                operand = self.translate_expression(statement["operand"])

                if to_assign["type"] == "variable":
                    variable_object = self.resolve_data_name(to_assign["variable"])["object"]
                    current_script.append(SetVariable(variable_object, operation(variable_object, operand)))

                if to_assign["type"] == "get attribute":
                    # For things like `this.x += 10`
                    setter_function = self.get_builtin(
                        to_assign,
                        translations.resolve_setter,
                        "attribute"
                    )

                    new_value = operation(translations.resolve_reporter(to_assign)(), operand)
                    current_script.append(setter_function(new_value))

            if statement["type"] == "function call":
                function = statement["function"]
                arguments = list(map(self.translate_expression, statement["arguments"]))

                # For things like `my_list.length`
                if function["type"] == "get attribute":
                    variable_attribute = self.translate_variable_attribute(function, arguments, "function")
                    if variable_attribute:
                        current_script.append(variable_attribute)
                        continue

                # Check custom functions
                dict_entry = self.functions.get(function.get("variable", None))
                if dict_entry:
                    self.argument_error_message(0, dict_entry["parameters"], len(arguments))
                    callable_object = dict_entry["callable"]

                else:
                    # Check builtin functions
                    callable_object = self.get_builtin(
                        function,
                        translations.resolve_function,
                        "function"
                    )
                    self.check_argument_count(callable_object, arguments)

                class_name = callable_object.__name__

                if class_name.startswith("Broadcast"):
                    # Set broadcast message variable to the second argument,
                    # or an empty string to reset it. Then add the rest
                    broadcast_name = arguments[0]
                    broadcast_message = arguments[1] if len(arguments) > 1 else ""

                    dict_entry = self.projectbuilder.get_broadcast(broadcast_name)
                    broadcast_object = dict_entry["broadcast"]
                    variable_object = dict_entry["variable"]

                    current_script.append(SetVariable(variable_object, broadcast_message))
                    broadcast_function = BroadcastAndWait if "Wait" in class_name else Broadcast
                    current_script.append(broadcast_function(broadcast_object))
                else:
                    current_script.append(callable_object(*arguments))

            if statement["type"] == "if":
                condition = self.translate_boolean(statement["expression"])
                body = self.build_inner_statements(statement["body"])

                current_script.append(If(condition, *body))

            if statement["type"] == "if-else":
                condition = self.translate_boolean(statement["expression"])
                body_1 = self.build_inner_statements(statement["body 1"])
                body_2 = self.build_inner_statements(statement["body 2"])

                current_script.append(If(condition, *body_1).Else(*body_2))

            if statement["type"] == "while":
                expression = statement["expression"]
                body = self.build_inner_statements(statement["body"])

                if not isinstance(expression, dict) and expression:
                    # If expression is literal and truthy
                    # (`while (true)` and `while(1 + 2 * 3)` will just run forever)
                    current_script.append(Forever(*body))
                else:
                    condition = self.translate_boolean(expression)
                    current_script.append(RepeatUntil(Not(condition), *body))

            if statement["type"] == "for":
                initializer_statement = statement["initializer"]
                expression = statement["expression"]
                post_iteration_statement = statement["post-iteration"]
                body = statement["body"]

                # The iteration variable must be set in the next scope
                self.enter_scope()

                current_script.extend(self.get_variable_setter(initializer_statement))
                statements = self.build_inner_statements(
                    [*body, post_iteration_statement],
                    modify_scope = False # Avoid changing the current scope
                )
                current_script.append(RepeatUntil(
                    Not(self.translate_boolean(expression)),
                    *statements
                ))

                self.exit_scope()

            if statement["type"] == "return":
                if self.current_function_building:
                    # Returning from a function
                    return_expression = statement["expression"]
                    if return_expression:
                        function_output_variable = self.functions[self.current_function_building]["output"]
                        return_expression = self.translate_expression(return_expression)

                        current_script.append(SetVariable(function_output_variable, return_expression))

                # Returning from a hat
                current_script.append(Stop(THIS_SCRIPT))

        if modify_scope:
            self.exit_scope()

        return current_script

    def add_local_variables(self, statements):
        for statement in statements:
            translated_value = self.translate_expression(statement["value"])

            if isinstance(translated_value, Block):
                set_lexpos(statement["value"]["lexpos"])
                code_error("Top-level assignment values must be literals")
            else:
                self.add_variable(
                    statement["variable"]["variable"],
                    self.translate_expression(statement["value"])
                )

    def build_functions(self, functions):
        for function in functions:
            function_name = function["name"]
            function_parameters = function["parameters"]
            function_warp = function["warp"]
            function_body = function["body"]

            # A function name of `reverse_text` with two parameters
            # is named "reverse_text %s %s"
            function_prototype = self.target.createCustomBlock(
                f"{function_name} {"%s " * len(function_parameters)}".strip(),
                run_without_screen_refresh = function_warp
            )
            parameter_objects = function_prototype.getParameters()
            parameter_objects = parameter_objects if isinstance(parameter_objects, list) else [parameter_objects]

            this_script = []
            self.enter_scope()

            # Redefine arguments in case the function modifies them
            for parameter_name, parameter_object in zip(function_parameters, parameter_objects):
                variable_object = self.add_variable(parameter_name, "")
                this_script.append(SetVariable(variable_object, parameter_object))

            output_variable = self.projectbuilder.add_variable(f"fo_{function_name}", "", self.target)["object"]
            self.functions[function_name] = {"output": output_variable} # Add to functions dictionary first
                                                                        # so it can be used when returning
            self.current_function_building = function_name
            this_script.extend(self.build_inner_statements(
                function_body,
                modify_scope = False
            ))
            self.current_function_building = ""

            callable_object = function_prototype.setScript(*this_script)
            self.functions[function_name].update({
                "callable":   callable_object,
                "parameters": len(function_parameters)
            })

            self.exit_scope()

    def build_hats(self, hats):
        for hat in hats:
            set_lexpos(hat["lexpos"])

            hat_event = hat["event"]
            hat_arguments = hat["arguments"]
            hat_body = hat["body"]

            if hat_event["attribute"] == "on_keyrelease":
                key = hat_arguments[0]

                hat_object = WhenKeyPressed(key)
                body = self.build_inner_statements(hat_body)
                self.scripts.append([
                    hat_object,
                    WaitUntil(Not(KeyPressed(key))),
                    *body
                ])

                continue

            hat_class = translations.resolve_hat(hat_event)

            if not hat_class:
                code_error("Hat not found")

            if hat_class.__name__ == "WhenBroadcastReceived": # Is this Pythonic?
                broadcast_name = hat_arguments[0]
                message_argument = hat_arguments[1]["variable"] if len(hat_arguments) > 1 else None

                dict_entry = self.projectbuilder.get_broadcast(broadcast_name)
                broadcast_object = dict_entry["broadcast"]
                variable_object = dict_entry["variable"]

                # Build the script piece-by-piece
                this_script = []
                # The broadcast message must be scoped, similarly to the
                # iteration variable in the `for` loop
                self.enter_scope()

                # Add the hat block first
                this_script.append(WhenBroadcastReceived(broadcast_object))
                # Then the scoped message setter (if present)
                if message_argument:
                    message_object = self.add_variable(message_argument, "")
                    message_setter = SetVariable(message_object, variable_object)
                    this_script.append(message_setter)
                # Then the rest of the statements
                body = self.build_inner_statements(hat_body, modify_scope=False)
                this_script.extend(body)

                self.scripts.append(this_script)

                self.exit_scope()
            else:
                hat_object = hat_class(*hat_arguments)
                body = self.build_inner_statements(hat_body)
                self.scripts.append([hat_object, *body])

    def build(self):
        statements = self.statements

        local_variables = [i for i in statements if i["type"] == "assignment"]
        function_decs   = [i for i in statements if i["type"] == "function declaration"]
        hat_decs        = [i for i in statements if i["type"] == "hat"]

        self.add_local_variables(local_variables)
        debug(f"  Added {len(local_variables)} targetwide variable{"" if len(local_variables) == 1 else "s"}")
        self.build_functions(function_decs)
        debug(f"  Built {len(function_decs)} function{"" if len(function_decs) == 1 else "s"}")
        self.build_hats(hat_decs)
        debug(f"  Built {len(hat_decs)} hat{"" if len(hat_decs) == 1 else "s"}")

        for script in self.scripts:
            self.target.createScript(*script)

    def enter_scope(self):
        self._scope_ID += 1
        self._scope_stack.append(self._scope_ID)
        self.current_scope_ID = self._scope_stack[-1]

    def exit_scope(self):
        del self._scope_stack[-1]
        self.current_scope_ID = self._scope_stack[-1]
