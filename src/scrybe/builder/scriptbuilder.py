from ScratchGen.block import Boolean
from ScratchGen.blocks import *
from ..codebuilder import CodeBuilder
from .. import translations
from .. import utils
from ..logger import debug, code_error, set_lexpos
from inspect import signature

class ScriptBuilder(CodeBuilder):
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
        #         "type":       <return type>,
        #         "output":     <output variable object>
        #     },
        #     ...
        # }
        self.functions = {}
        self.current_function_building = "" # Name of the function currently being built
        self.script_stack = [] # 2D array of scripts being built
        self.current_script = None # Reference to the current script stack
        self.scripts = [] # 2D list of block objects

        self.is_clone_variable = None

    # Non-boolean expression translation

    def translate_expression(self, expression):
        if isinstance(expression, bool):
            return self.translate_boolean(expression)

        if isinstance(expression, list):
            return list(map(self.translate_expression, expression))

        if not isinstance(expression, dict):
            return expression

        set_lexpos(expression["lexpos"])

        match expression["type"]:
            case "binary operation": translation_function = self.translate_numerical_binary_operation
            case "unary minus":      translation_function = self.translate_unary_minus
            case "condition":        translation_function = self.translate_boolean
            case "concatenation":    translation_function = self.translate_concatenation
            case "index":            translation_function = self.translate_index
            case "get attribute":    translation_function = self.translate_attribute
            case "function call":    translation_function = self.translate_method
            case "variable":         return self.resolve_data_name(expression["variable"])

        return translation_function(expression)

    def translate_variable_attribute(self, expression, type, arguments=[]):
        variable_object = self.resolve_data_name(expression["object"])
        variable_type = variable_object.type
        attribute = expression["attribute"]

        dictionary = getattr(translations, f"{variable_type}_{type}s")

        callable_object = dictionary.get(attribute)
        if not callable_object:
            # Set lex position of attribute (+ 1 for the period)
            set_lexpos(expression["lexpos"] + len(expression["object"]) + 1)
            code_error(f"{variable_type.title()} {type} not found")

        return callable_object(*arguments, variable_object)

    def translate_attribute(self, expression):
        # Check if attribute is of a list/variable
        if self.resolve_data_name(expression["object"], allow_nonexistent=True):
            return self.translate_variable_attribute(expression, "field")

        if expression["object"] == "this" and expression["attribute"] == "is_clone":
            if not self.is_sprite: code_error("This attribute can only be used in a sprite")
            if not self.is_clone_variable: self.add_is_sprite_check()
            return self.is_clone_variable

        return self.get_builtin(
            expression,
            translations.resolve_reporter,
            "attribute"
        )()

    def translate_method(self, expression):
        function = expression["function"]
        arguments = list(map(self.translate_expression, expression["arguments"]))

        # Check if is a custom function
        if function["type"] == "variable" and function["variable"] in self.functions:
            function_name = function["variable"]
            dict_entry = self.functions[function_name]

            if dict_entry["output"] is None:
                code_error("This function has no return type")

            self.argument_error_message(0, dict_entry["parameters"], len(arguments))
            callable_object = dict_entry["callable"]
            output_object = dict_entry["output"]

            self.current_script.append(callable_object(*arguments))
            return output_object

        # Check if method is of a list/variable
        if "object" in function and self.resolve_data_name(function["object"], allow_nonexistent=True):
            return self.translate_variable_attribute(function, "method", arguments)

        callable_object = self.get_builtin(
            function,
            translations.resolve_function_reporter,
            "function"
        )
        self.check_argument_count(callable_object, len(arguments))

        if callable_object.__name__ == "TouchingObject":
            target = arguments[0]
            if target in self.projectbuilder.sprites:
                return callable_object(self.projectbuilder.sprites[target]["object"])

        return callable_object(*arguments)

    # Boolean expression translation

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
            variable_object = self.translate_expression(expression)

            if isinstance(variable_object, Boolean):
                return variable_object
            if getattr(variable_object, "name", None) == "sg_is_clone":
                return Equals(variable_object, 1)

            utils.check_types(("boolean", "variable"),
                              "Cannot compare a {}", variable_object)
            return Equals(variable_object, 1)

        condition = expression["condition"]

        if condition == "not":
            return Not(self.translate_boolean(expression["comparand"]))

        translated = self.translate_logical_operation(
            condition,
            expression["comparand 1"],
            expression["comparand 2"]
        )
        if isinstance(translated, bool): # translate_logical_expression can return a Boolean (for building setup)
            return self.translate_boolean(translated)
        return translated

    # Defined variables

    def get_builtin(self, obj, resolution_function, type_name, allow_nonexistent=False):
        resolution_attempt = resolution_function(obj)
        if not resolution_attempt:
            if allow_nonexistent: return None
            if "lexpos" in obj: set_lexpos(obj["lexpos"])
            code_error(f"{type_name.title()} not found")

        callable_object, sprite_specific = resolution_attempt
        if sprite_specific and not self.is_sprite:
            code_error(f"This {type_name} can only be used in a sprite")

        return callable_object

    def add_variable(self, variable_name, variable_type, variable_value):
        prefix = self.variable_prefix
        current_scope = self.current_scope_ID
        if current_scope > 0:
            prefix += str(current_scope)

        variable_name = f"{prefix}_{variable_name}"

        return self.projectbuilder.add_variable(
            variable_name, variable_type, variable_value,
            self.target
        )

    def resolve_data_name(self, data_name, allow_nonexistent=False):
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
        for encoded_name, variable_object in local_variables.items():
            if any(encoded_name.startswith(i) for i in ("g_", "s_", "b_", "fo_", "bfo_")):
                continue

            encoded_scope, name = encoded_name.split("_", maxsplit=1)
            scope_ID = int(encoded_scope[1:])

            if name == data_name and scope_ID in [self.current_scope_ID, *self._scope_stack]:
                # `scope_ID` can either be the current scope ID or in the stack
                return variable_object

        # Variable wasn't found, either error or implicitly return None
        if not allow_nonexistent:
            code_error("Variable not found")

    def add_is_sprite_check(self):
        self.is_clone_variable = self.target.createVariable("sg_is_clone", 0)

        self.scripts.extend([[
            WhenFlagClicked(),
            SetVariable(self.is_clone_variable, 0)
        ], [
            WhenStartAsClone(),
            SetVariable(self.is_clone_variable, 1)
        ]])

    # Inner statement translation

    def build_inner_statements(self, statements, modify_scope=True):
        self.add_to_stack(modify_scope)

        for statement in statements:
            set_lexpos(statement["lexpos"])

            match statement["type"]:
                case "assignment":          application_function = self.apply_variable_setter
                case "in-place assignment": application_function = self.apply_in_place_assignment
                case "index assign":        application_function = self.apply_index_assignment
                case "function call":       application_function = self.apply_function_call
                case "if":                  application_function = self.apply_if
                case "if-else":             application_function = self.apply_if_else
                case "while":               application_function = self.apply_while
                case "for":                 application_function = self.apply_for
                case "return":              application_function = self.apply_return

            application_function(statement)

        return self.remove_from_stack(modify_scope)

    def apply_variable_setter(self, statement):
        to_assign = statement["variable"]
        variable_value = self.translate_expression(statement["value"])

        set_lexpos(to_assign["lexpos"])

        # For things like `this.size = 50`
        if to_assign["type"] == "get attribute":
            self.current_script.append(self.get_builtin(
                to_assign,
                translations.resolve_setter,
                "attribute"
            )(variable_value))
            return

        # User-defined variables
        variable_name = to_assign["variable"]
        variable_object = self.resolve_data_name(variable_name, allow_nonexistent=True)

        # Check variable type against value type
        statement_variable_type = statement["variable type"]
        if variable_object:
            # Check that the variable isn't being redeclared as something different
            variable_type = variable_object.type
            if statement_variable_type != variable_type and statement_variable_type != "variable":
                code_error(f"Cannot redeclare a {variable_type} as a {statement_variable_type}")
        else:
            variable_type = statement_variable_type
        self._check_assignment_types(variable_type, utils.get_type(variable_value))

        if not variable_object:
            # Variable doesn't exist yet, create and set it
            match variable_type:
                case "number":   initial_value = 0
                case "string":   initial_value = ""
                case "boolean":  initial_value = False
                case "variable": initial_value = ""
                case "list":     initial_value = []

            variable_object = self.add_variable(variable_name, variable_type, initial_value)

        if variable_object.type == "list":
            self.current_script.append(ClearList(variable_object))
            self.current_script.extend(AddToList(item, variable_object) for item in variable_value)
        else:
            self.current_script.append(SetVariable(variable_object, variable_value))

    def apply_in_place_assignment(self, statement):
        operation_type = statement["operation"][:-1] # Cut off the trailing equals sign
        operation = Join if operation_type == ".." else translations.operations[operation_type]

        to_assign = statement["variable"]
        operand = self.translate_expression(statement["operand"])

        if to_assign["type"] == "variable":
            variable_object = self.resolve_data_name(to_assign["variable"])
            self.current_script.append(SetVariable(variable_object, operation(variable_object, operand)))

        if to_assign["type"] == "get attribute":
            # For things like `this.x += 10`
            setter_function = self.get_builtin(
                to_assign,
                translations.resolve_setter,
                "attribute"
            )

            new_value = operation(translations.resolve_reporter(to_assign)[0](), operand)
            self.current_script.append(setter_function(new_value))

    def apply_index_assignment(self, statement):
        target = self.translate_expression(statement["target"])
        index = self.translate_expression(statement["index"])
        value = self.translate_expression(statement["value"])

        target_type = utils.get_type(target)
        self.check_index_types(target, index)
        if target_type != "list":
            code_error(f"Can only assign to indices in a list, not a {target_type}")

        self.current_script.append(ReplaceInList(index + 1, target, value))

    def apply_function_call(self, statement):
        function = statement["function"]
        arguments = list(map(self.translate_expression, statement["arguments"]))
        callable_object = None

        # Check builtin functions
        callable_object = self.get_builtin(
            function,
            translations.resolve_function,
            "function",
            allow_nonexistent = True
        )
        if callable_object:
            self.check_argument_count(callable_object, len(arguments))

        else:
            # Check custom functions
            if self.functions.get(function.get("variable")):
                dict_entry = self.functions[function["variable"]]

                # You may invoke a function with a return type as a statement
                # because I don't really see any downsides to it

                callable_object = dict_entry["callable"]
                parameter_count = dict_entry["parameters"]

                self.argument_error_message(0, parameter_count, len(arguments))

        # Check variable/list functions
        if not callable_object and self.resolve_data_name(function.get("object", None), allow_nonexistent=True):
            self.current_script.append(
                self.translate_variable_attribute(function, "function", arguments))
            return

        if (
            function["type"] == "get attribute" and
            function["object"] == "scratch" and
            function["attribute"].startswith("broadcast")
        ):
            # Set broadcast message variable to the second argument,
            # or an empty string to reset it. Then add the rest
            broadcast_name = arguments[0]
            broadcast_message = arguments[1] if len(arguments) > 1 else ""

            dict_entry = self.projectbuilder.get_broadcast(broadcast_name)
            broadcast_object = dict_entry["broadcast"]
            variable_object = dict_entry["variable"]

            self.current_script.append(SetVariable(variable_object, broadcast_message))
            arguments = [broadcast_object]

        if not callable_object:
            code_error("Function not found")
        self.current_script.append(callable_object(*arguments))

    def get_control_flow_condition(self, expression):
        condition = self.translate_expression(expression)
        utils.check_types(("boolean",),
            "Condition must be a boolean, not a {}", condition)

        return condition

    def check_argument_count(self, function_object, given_argument_count):
        parameters = [i for i in signature(function_object).parameters.values()]
        required_parameters = len([i for i in parameters if i.default == i.empty])
        optional_parameters = len(parameters) - required_parameters

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
                expected + f"{"" if total_parameters == 1 else "s"}, "
                f"got {given_argument_count}"
            ))

    def apply_if(self, statement):
        condition = self.get_control_flow_condition(statement["expression"])
        body = self.build_inner_statements(statement["body"])

        self.current_script.append(If(condition, *body))

    def apply_if_else(self, statement):
        condition = self.get_control_flow_condition(statement["expression"])
        body_1 = self.build_inner_statements(statement["body 1"])
        body_2 = self.build_inner_statements(statement["body 2"])

        self.current_script.append(If(condition, *body_1).Else(*body_2))

    def apply_while(self, statement):
        expression = statement["expression"]
        body = self.build_inner_statements(statement["body"])

        if expression == True:
            # Optimize to a "forever" loop if expression is just `true`
            self.current_script.append(Forever(*body))
        else:
            condition = self.get_control_flow_condition(expression)
            self.current_script.append(RepeatUntil(Not(condition), *body))

    def apply_for(self, statement):
        initializer_statement = statement["initializer"]
        expression = statement["expression"]
        post_iteration_statement = statement["post-iteration"]
        body = statement["body"]

        # The iteration variable must be set in the next scope
        self.enter_scope()

        self.apply_variable_setter(initializer_statement)
        statements = self.build_inner_statements(
            [*body, post_iteration_statement],
            modify_scope = False # Avoid changing the current scope
        )
        expression = self.get_control_flow_condition(expression)
        self.current_script.append(RepeatUntil(Not(expression), *statements))

        self.exit_scope()

    def apply_return(self, statement):
        if self.current_function_building:
            # Returning from a function
            return_expression = statement["expression"]
            if return_expression:
                function_output_variable = self.functions[self.current_function_building]["output"]
                return_expression = self.translate_expression(return_expression)

                if return_expression and not function_output_variable:
                    code_error("This function has no return type")

                function_return_type = utils.get_type(function_output_variable)
                return_expression_type = utils.get_type(return_expression)
                utils.check_types((
                    f"{function_return_type} {function_return_type}"
                    f"variable               any"
                ), "Return type must be a {}, not a {}", function_return_type, return_expression_type,
                is_types = True)

                self.current_script.append(SetVariable(function_output_variable, return_expression))

        # Returning from a hat
        self.current_script.append(Stop(THIS_SCRIPT))

    def apply_local_variable(self, statement):
        value = statement["value"]
        if not isinstance(value, bool): value = self.translate_expression(value)

        if isinstance(value, Block) or isinstance(value, list) and any(isinstance(i, Block) for i in value):
            set_lexpos(statement["value"]["lexpos"])
            code_error("Top-level assignment values must be literals")
        else:
            self.add_variable(
                statement["variable"]["variable"],
                statement["variable type"],
                value
            )

    def build_function(self, function):
        function_type = function["return type"]
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
            variable_object = self.add_variable(parameter_name, "variable", "")
            this_script.append(SetVariable(variable_object, parameter_object))

        if function_type is not None:
            output_variable_name = f"fo_{function_name}" if self.is_sprite else f"bfo_{function_name}"
            output_variable = self.projectbuilder.add_variable(output_variable_name, function_type, "", self.target)
        else:
            output_variable = None
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

    def build_hat(self, hat):
        set_lexpos(hat["lexpos"])

        hat_event = hat["event"]
        hat_arguments = hat["arguments"]
        hat_body = hat["body"]

        if hat_event["attribute"] == "on_keyrelease":
            key = self.translate_expression(hat_arguments[0])
            self.scripts.append([
                WhenKeyPressed(key),
                WaitUntil(Not(KeyPressed(key))),
                *self.build_inner_statements(hat_body)
            ])

            return

        hat_class = translations.resolve_hat(hat_event)
        if not hat_class: code_error("Hat not found")

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
                message_object = self.add_variable(message_argument, "variable", "")
                message_setter = SetVariable(message_object, variable_object)
                this_script.append(message_setter)

            # Then the rest of the statements
            body = self.build_inner_statements(hat_body, modify_scope=False)
            this_script.extend(body)

            self.scripts.append(this_script)
            self.exit_scope()

        else:
            # Just an average hat
            hat_object = hat_class(*map(self.translate_expression, hat_arguments))
            body = self.build_inner_statements(hat_body)
            self.scripts.append([hat_object, *body])

    # Main building methods

    def build(self):
        statements = self.statements

        local_variables = [i for i in statements if i["type"] == "assignment"]
        function_decs   = [i for i in statements if i["type"] == "function declaration"]
        hat_decs        = [i for i in statements if i["type"] == "hat"]

        for i in local_variables: self.apply_local_variable(i)
        debug(f"  Added {len(local_variables)} targetwide variable{"" if len(local_variables) == 1 else "s"}")
        for i in function_decs: self.build_function(i)
        debug(f"  Built {len(function_decs)} function{"" if len(function_decs) == 1 else "s"}")
        for i in hat_decs: self.build_hat(i)
        debug(f"  Built {len(hat_decs)} hat{"" if len(hat_decs) == 1 else "s"}")

        for script in self.scripts:
            self.target.createScript(*script)

    def add_to_stack(self, modify_scope):
        if modify_scope: self.enter_scope()

        new_script = []
        self.script_stack.append(new_script)
        self.current_script = new_script

    def remove_from_stack(self, modify_scope):
        if modify_scope: self.exit_scope()

        result = self.script_stack.pop()
        self.current_script = self.script_stack[-1] if self.script_stack else None

        return result

    def enter_scope(self):
        self._scope_ID += 1
        self._scope_stack.append(self._scope_ID)
        self.current_scope_ID = self._scope_stack[-1]

    def exit_scope(self):
        del self._scope_stack[-1]
        self.current_scope_ID = self._scope_stack[-1]