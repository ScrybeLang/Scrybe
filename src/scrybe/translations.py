from ScratchGen.blocks import *
from ScratchGen import constants
from ScratchGen.datacontainer import List
import operator

# Unfortunately, Scratch has no first-party implementation of exponentiation,
# so we do some tricky math workarounds
def _exponent_function(base, exponent):
    # For literal numbers (same as `operator.pow` but we still need support for other expressions)
    if isinstance(base, (int, float)) and isinstance(exponent, (int, float)):
        return base ** exponent

    # The first tricky math part; this only works with positive bases but any exponent works
    exponent_part = Operation(TEN_TO_THE, Multiply(exponent, Operation(LOGARITHM, Operation(ABSOLUTE, base))))

    if isinstance(base, (int, float)) and base >= 0: # If the base is a positive literal number
        return exponent_part

    # The second tricky math part (I engineered this myself!); this calculates the correct sign multiplier (-1 or 1)
    # of the power. For positive bases, the sign is always positive. For negative bases, the sign is negative
    # if the exponent is odd. It's complicated, but just trust me bro:
    # https://www.reddit.com/r/scratch/comments/1e90p0f/how_to_calculate_exponents/ (read my correction comment)
    sign_part = Add(Multiply(Multiply(LessThan(Modulo(Add(exponent, 1), 2), 1), Multiply(-1, LessThan(base, 0))), 2), 1)
    return Multiply(exponent_part, sign_part)

operations = {
    "+":   operator.add,
    "-":   operator.sub,
    "*":   operator.mul,
    "/":   operator.truediv,
    "%":   operator.mod,
    "**":  _exponent_function,
    "<":   operator.lt,
    ">":   operator.gt,
    "<=":  operator.le,
    ">=":  operator.ge,
    "==":  operator.eq
}

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
    "==":  Equals
}

reporters = {
    "scratch": {
        "backdrop": {
            "name":             lambda: Backdrop(NAME),
            "number":           lambda: Backdrop(NUMBER)
        },
        "answer":               Answer,
        "mouse_down":           MouseDown,
        "mouse_x":              MouseX,
        "mouse_y":              MouseY,
        "loudness":             Loudness,
        "username":             Username
    },

    "C": {},

    "time": {
        "year":                 lambda: Current(YEAR),
        "month":                lambda: Current(MONTH),
        "date":                 lambda: Current(DATE),
        "day_of_week":          lambda: Current(DAY_OF_WEEK),
        "hour":                 lambda: Current(HOUR),
        "minute":               lambda: Current(MINUTE),
        "second":               lambda: Current(SECOND),
        "timer":                Timer,
        "days_since_2000":      DaysSince2000
    },

    "math": {
        "pi":                   lambda: 3.141592653589793
    },

    "this": {
        "x":                    XPosition,
        "y":                    YPosition,
        "direction":            Direction,
        "size":                 Size,
        "costume": {
            "name":             lambda: Costume(NAME),
            "number":           lambda: Costume(NUMBER)
        },
        "volume":               Volume
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
    reporters["C"][constant] = _make_lambda(constant)

def _random_choice(item):
    if isinstance(item, List):
        return ItemOfList(PickRandom(1, ListLength(item)), item)
    return LetterOf(PickRandom(1, LengthOf(item)), item)

function_reporters = {
    "scratch": {
        "key_pressed":          KeyPressed,
        "get_attribute":        GetAttribute
    },

    "math": {
        "round":                Round,
        "abs":                  lambda x: Operation(ABSOLUTE, x),
        "floor":                lambda x: Operation(FLOOR, x),
        "ceil":                 lambda x: Operation(CEILING, x),
        "sqrt":                 lambda x: Operation(SQUARE_ROOT, x),
        "sin":                  lambda x: Operation(SINE, x),
        "cos":                  lambda x: Operation(COSINE, x),
        "tan":                  lambda x: Operation(TANGENT, x),
        "asin":                 lambda x: Operation(ARCSINE, x),
        "acos":                 lambda x: Operation(ARCCOSINE, x),
        "atan":                 lambda x: Operation(ARCTANGENT, x),
        "log":                  lambda x: Operation(NATURAL_LOGARITHM, x),
        "log10":                lambda x: Operation(LOGARITHM, x),
        "exp":                  lambda x: Operation(E_TO_THE, x),
        "exp10":                lambda x: Operation(TEN_TO_THE, x)
    },

    "random": {
        "range":                PickRandom,
        "choice":               _random_choice
    },

    "this": {
        "touching":             TouchingObject,
        "touching_color":       TouchingColor,
        "color_touching_color": ColorTouchingColor,
        "distance_to":          DistanceTo
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
        "stop":                 Stop,
        "ask":                  AskAndWait,
        "broadcast":            Broadcast,
        "broadcast_and_wait":   BroadcastAndWait,
        "clone":                lambda x = MYSELF: CreateCloneOf(x),
        "delete_clone":         DeleteThisClone
    },

    "time": {
        "sleep":                Wait,
        "reset_timer":          ResetTimer,
        "wait_until":           WaitUntil
    },

    "move_steps":               MoveSteps,
    "go_to":                    GoTo,
    "set_pos":                  GoToPosition,
    "glide_to":                 lambda x, y: GlideTo(y, x),
    "glide_to_pos":             lambda x, y, z: GlideToPosition(z, x, y),
    "point_towards":            PointTowards,
    "bounce_off_edge":          BounceOffEdge,
    "set_rotation_style":       SetRotationStyle,
    "say_for_seconds":          SayForSeconds,
    "say":                      Say,
    "think_for_seconds":        ThinkForSeconds,
    "think":                    Think,
    "set_costume":              SwitchCostume,
    "next_costume":             NextCostume,
    "switch_backdrop":          SwitchBackdrop,
    "next_backdrop":            NextBackdrop,
    "change_effect":            _change_effect,
    "set_effect":               _set_effect,
    "clear_graphic_effects":    ClearGraphicEffects,
    "show":                     Show,
    "hide":                     Hide,
    "set_layer":                SetLayer,
    "change_layer":             _change_layer,
    "play_until_done":          PlayUntilDone,
    "play_sound":               Play,
    "stop_all_sounds":          StopSounds,
    "clear_sound_effects":      ClearSoundEffects,
    "set_drag_mode":            SetDragMode
}

# Attributes that can be set, like `this.x += 10` or `this.size = 50`
setters = {
    "this": {
        "x":         SetX,
        "y":         SetY,
        "direction": PointInDirection,
        "size":      SetSize,
        "volume":    SetVolume
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
}

list_reporters = {
    "length": ListLength,
    "index":  lambda item, _list: ListIndexOf(item, _list) - 1
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
