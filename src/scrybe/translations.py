from ScratchGen.blocks import *
from ScratchGen import constants
from ScratchGen.datacontainer import List
import operator

# Get the amount of objects this object represents
# For example: "Equals(Add(2, 2), 4)" => 2
#              "Divide(2, 3)"         => 1
#              "15"                   => 1
def get_depth(object):
    if isinstance(object, (int, float)) or not object.contained_blocks:
        return 1
    return sum(map(get_depth, object.contained_blocks)) + 1

def _chain_multiply(base, exponent):
    if exponent == 2:
        # x ** 2 == x * x
        return Multiply(base, base)
    return Multiply(_chain_multiply(base, exponent - 1), base)

# Unfortunately, Scratch has no first-party implementation of exponentiation,
# so we do some tricky math workarounds
def _exponent_function(base, exponent):
    base_numeric = isinstance(base, (int, float))
    exponent_numeric = isinstance(exponent, (int, float))

    # For literal numbers (same as `operator.pow` but we still need support for other expressions)
    if base_numeric and exponent_numeric:
        return base ** exponent

    # Simple cases
    if not base_numeric and exponent_numeric:
        if exponent == -1:  return Divide(1, base)              # x ** -1 == 1 / x
        if exponent == 0:   return 1                            # x ** 0 == 1
        if exponent == 0.5: return Operation(SQUARE_ROOT, base) # x ** 0.5 == sqrt(x)
        if exponent == 1:   return base                         # x ** 1 == x

    # For cases when it would take less blocks just to multiply it manually
    if isinstance(exponent, int):
        base_depth = get_depth(base)
        chained_object_depth = base_depth * (exponent - 1) # Depth of resulting chained object
        if 0 < chained_object_depth < 13: # Full exponentiation has a depth of 13 objects
            return _chain_multiply(base, exponent)

    # The first tricky math part; this only works with positive bases but any exponent works
    exponent_part = Operation(TEN_TO_THE, Multiply(exponent, Operation(LOGARITHM, Operation(ABSOLUTE, base))))

    if base_numeric and base >= 0: # If the base is a positive literal number
        return exponent_part

    # The second tricky math part (I engineered this myself!); this calculates the correct sign multiplier (-1 or 1)
    # of the power. For positive bases, the sign is always positive. For negative bases, the sign is negative
    # if the exponent is odd. It's complicated, but just trust me bro:
    # https://www.reddit.com/r/scratch/comments/1e90p0f/how_to_calculate_exponents/ (read my correction comment)
    sign_part = Add(Multiply(Multiply(LessThan(Modulo(Add(exponent, 1), 2), 1), Multiply(-1, LessThan(base, 0))), 2), 1)
    return Multiply(exponent_part, sign_part)

def _contains(sub_item, item):
    if isinstance(item, List):
        return ListContains(item, sub_item)
    return Contains(item, sub_item)

boolean_conditions = {
    "and": And,
    "or":  Or,
    "in":  _contains
}

number_conditions = {
    "<":   LessThan,
    ">":   GreaterThan,
    "<=":  lambda x, y: Not(GreaterThan(x, y)),
    ">=":  lambda x, y: Not(LessThan(x, y)),
    "==":  Equals,
    "!=":  lambda x, y: Not(Equals(x, y))
}

# For if the left operand is a number
# This is needed because only reporters have overridden math dunder methods
def _make_lambda(original_function, scratchgen_function):
    return lambda x, y: (
        scratchgen_function(x, y) if (isinstance(x, (int, float)) and not
                                      isinstance(y, (int, float)))
        else original_function(x, y)
    )

operations = {
    "+":   _make_lambda(operator.add,     Add),
    "-":   _make_lambda(operator.sub,     Subtract),
    "*":   _make_lambda(operator.mul,     Multiply),
    "/":   _make_lambda(operator.truediv, Divide),
    "%":   _make_lambda(operator.mod,     Modulo),
    "**":  _exponent_function,
    "<":   _make_lambda(operator.lt,      number_conditions["<"]),
    ">":   _make_lambda(operator.gt,      number_conditions[">"]),
    "<=":  _make_lambda(operator.le,      number_conditions["<="]),
    ">=":  _make_lambda(operator.ge,      number_conditions[">="]),
    "==":  _make_lambda(operator.eq,      number_conditions["=="])
}

reporters = {
    "scratch": {
        "backdrop": {
            "name":             (lambda: Backdrop(NAME),   False),
            "number":           (lambda: Backdrop(NUMBER), False),
        },
        "answer":               (Answer,                   False),
        "mouse_down":           (MouseDown,                False),
        "mouse_x":              (MouseX,                   False),
        "mouse_y":              (MouseY,                   False),
        "loudness":             (Loudness,                 False),
        "username":             (Username,                 False)
    },

    "C": {},

    "time": {
        "year":                 (lambda: Current(YEAR),        False),
        "month":                (lambda: Current(MONTH),       False),
        "date":                 (lambda: Current(DATE),        False),
        "day_of_week":          (lambda: Current(DAY_OF_WEEK), False),
        "hour":                 (lambda: Current(HOUR),        False),
        "minute":               (lambda: Current(MINUTE),      False),
        "second":               (lambda: Current(SECOND),      False),
        "timer":                (Timer,                        False),
        "days_since_2000":      (DaysSince2000,                False)
    },

    "math": {
        "pi":                   (lambda: 3.141592653589793, False)
    },

    "this": {
        "x":                    (XPosition,               True),
        "y":                    (YPosition,               True),
        "direction":            (Direction,               True),
        "size":                 (Size,                    True),
        "costume": {
            "name":             (lambda: Costume(NAME),   True),
            "number":           (lambda: Costume(NUMBER), True),
        },
        "volume":               (Volume,                  False)
    }
}

def _make_lambda(constant):
    return lambda: getattr(constants, constant)

for constant in (
    "MOUSE", "STAGE", "EDGE", "MYSELF", "RANDOM",
    "COLOR", "FISHEYE", "WHIRL", "PIXELATE", "MOSAIC", "BRIGHTNESS", "GHOST",
    "PITCH", "PAN",
    "FRONT", "BACK",
    "DRAGGABLE", "NOT_DRAGGABLE",
    "LEFT_RIGHT", "DONT_ROTATE", "ALL_AROUND",
    "ALL", "OTHER_SCRIPTS", "THIS_SCRIPT",
    "SPACE", "ENTER", "UP_ARROW", "DOWN_ARROW", "LEFT_ARROW", "RIGHT_ARROW",
    "BACKDROP_NUMBER", "BACKDROP_NAME", "X_POSITION", "Y_POSITION", "DIRECTION", "COSTUME_NUMBER", "COSTUME_NAME", "SIZE", "VOLUME",
    "LOUDNESS", "TIMER"
):
    reporters["C"][constant] = (_make_lambda(constant), False)

def _random_choice(item):
    if isinstance(item, List):
        return ItemOfList(PickRandom(1, ListLength(item)), item)
    return LetterOf(PickRandom(1, LengthOf(item)), item)

function_reporters = {
    "scratch": {
        "key_pressed":          (KeyPressed,   False),
        "get_attribute":        (GetAttribute, False)
    },

    "math": {
        "round":                (Round,                                     False),
        "abs":                  (lambda x: Operation(ABSOLUTE, x),          False),
        "floor":                (lambda x: Operation(FLOOR, x),             False),
        "ceil":                 (lambda x: Operation(CEILING, x),           False),
        "sqrt":                 (lambda x: Operation(SQUARE_ROOT, x),       False),
        "sin":                  (lambda x: Operation(SINE, x),              False),
        "cos":                  (lambda x: Operation(COSINE, x),            False),
        "tan":                  (lambda x: Operation(TANGENT, x),           False),
        "asin":                 (lambda x: Operation(ARCSINE, x),           False),
        "acos":                 (lambda x: Operation(ARCCOSINE, x),         False),
        "atan":                 (lambda x: Operation(ARCTANGENT, x),        False),
        "log":                  (lambda x: Operation(NATURAL_LOGARITHM, x), False),
        "log10":                (lambda x: Operation(LOGARITHM, x),         False),
        "exp":                  (lambda x: Operation(E_TO_THE, x),          False),
        "exp10":                (lambda x: Operation(TEN_TO_THE, x),        False)
    },

    "random": {
        "range":                (PickRandom,     False),
        "choice":               (_random_choice, False)
    },

    "this": {
        "touching":             (TouchingObject,     True),
        "touching_color":       (TouchingColor,      True),
        "color_touching_color": (ColorTouchingColor, True),
        "distance_to":          (DistanceTo,         True)
    }
}

# `set_effect`/`change_effect` is only one function but can translate to
# one of two blocks, so distinguish between sound and graphic effects based
# on what effect is being set/changed

def _change_effect(effect, change):
    if effect in ("pitch", "pan"):
        return ChangeSoundEffect(effect, change)
    return ChangeGraphicEffect(effect, change)

def _set_effect(effect, value):
    if effect in ("pitch", "pan"):
        return SetSoundEffect(effect, value)
    return SetGraphicEffect(effect, value)

def _change_layer(change):
    return ChangeLayer(FORWARD, change)

functions = {
    "scratch": {
        "stop":                 (Stop,                                    False),
        "ask":                  (AskAndWait,                              False),
        "broadcast":            (lambda x, y = None: Broadcast(x),        False),
        "broadcast_and_wait":   (lambda x, y = None: BroadcastAndWait(x), False),
        "clone":                (lambda x = MYSELF: CreateCloneOf(x),     False),
        "delete_clone":         (DeleteThisClone,                         False)
    },

    "time": {
        "sleep":                (Wait,       False),
        "reset_timer":          (ResetTimer, False),
        "wait_until":           (WaitUntil,  False)
    },

    "move_steps":               (MoveSteps,                                True),
    "go_to":                    (GoTo,                                     True),
    "set_pos":                  (GoToPosition,                             True),
    "glide_to":                 (lambda x, y: GlideTo(y, x),               True),
    "glide_to_pos":             (lambda x, y, z: GlideToPosition(z, x, y), True),
    "point_towards":            (PointTowards,                             True),
    "bounce_off_edge":          (BounceOffEdge,                            True),
    "set_rotation_style":       (SetRotationStyle,                         True),
    "say_for_seconds":          (SayForSeconds,                            True),
    "say":                      (Say,                                      True),
    "think_for_seconds":        (ThinkForSeconds,                          True),
    "think":                    (Think,                                    True),
    "set_costume":              (SwitchCostume,                            True),
    "next_costume":             (NextCostume,                              True),
    "switch_backdrop":          (SwitchBackdrop,                           False),
    "next_backdrop":            (NextBackdrop,                             False),
    "change_effect":            (_change_effect,                           False),
    "set_effect":               (_set_effect,                              False),
    "clear_graphic_effects":    (ClearGraphicEffects,                      False),
    "show":                     (Show,                                     True),
    "hide":                     (Hide,                                     True),
    "set_layer":                (SetLayer,                                 True),
    "change_layer":             (_change_layer,                            True),
    "play_until_done":          (PlayUntilDone,                            False),
    "play_sound":               (Play,                                     False),
    "stop_all_sounds":          (StopSounds,                               False),
    "clear_sound_effects":      (ClearSoundEffects,                        False),
    "set_drag_mode":            (SetDragMode,                              True)
}

# Attributes that can be set, like `this.x += 10` or `this.size = 50`
setters = {
    "this": {
        "x":         (SetX,             True),
        "y":         (SetY,             True),
        "direction": (PointInDirection, True),
        "size":      (SetSize,          True),
        "volume":    (SetVolume,        False)
    }
}

hats = {
    "scratch": {
        "on_flag":         WhenFlagClicked,
        "on_keypress":     WhenKeyPressed,
        "on_clicked":      WhenThisSpriteClicked,
        "on_backdrop":     WhenBackdropSwitchesTo,
        "on_greater_than": WhenGreaterThan,
        "on_broadcast":    WhenBroadcastReceived,
        "on_clone":        WhenStartAsClone
    }
}

list_functions = {
    "push":   AddToList,
    "remove": lambda index, _list: DeleteOfList(index + 1, _list),
    "clear":  ClearList,
    "insert": lambda index, item, _list: InsertIntoList(item, index + 1, _list),
    "index":  lambda item, _list: ListIndexOf(item, _list) - 1
}

list_reporters = {
    "length": ListLength
}

variable_functions = {}

variable_reporters = {
    "length": LengthOf
}

# Resolves attribute/variable accessor expressions into the appropriate entry
# from the dictionaries defined above.
# For example: `this.x` -> `{... AST exp. ...}` -> `XPosition`
def _resolve(attribute, nested_dict):
    try:
        if not isinstance(attribute, dict):
            return nested_dict[attribute]

        if attribute["type"] == "variable":
            return nested_dict[attribute["variable"]]

        obj = _resolve(attribute["object"], nested_dict)
        attr = attribute["attribute"]
        return obj[attr]

    except:
        return None

def resolve_reporter(attribute):          return _resolve(attribute, reporters)
def resolve_function_reporter(attribute): return _resolve(attribute, function_reporters)
def resolve_function(attribute):          return _resolve(attribute, functions)
def resolve_setter(attribute):            return _resolve(attribute, setters)
def resolve_hat(attribute):               return _resolve(attribute, hats)
