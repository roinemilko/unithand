from sympy import (
    pretty,
    erf,
    erfc
)
import re
from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from sympy.physics.units import convert_to
from sympy.physics.units.util import quantity_simplify
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application
)
from sympy import physics
from sympy.physics import units as sympy_units

transformations = (standard_transformations + (implicit_multiplication_application,))

buffer = Buffer()
result_history = []
SI_BASE = [
    sympy_units.meter,
    sympy_units.kilogram,
    sympy_units.second,
    sympy_units.ampere,
    sympy_units.kelvin,
    sympy_units.mole,
    sympy_units.candela
]
current_expr = None
state = 0

class IncompatibleDims(Exception):
    def __init__(self):
        super().__init__()
    def __str__(self):
        return f"Check dimentions!"

def get_units():
    unit_dict = {}

    for name in dir(sympy_units):
        if name.startswith("_"):
            continue
        obj = getattr(sympy_units, name)

        if not callable(obj):
            unit_dict[name] = obj

    aliases = {
        'R': sympy_units.molar_gas_constant,
        'kB': sympy_units.boltzmann_constant,
        'k_B': sympy_units.boltzmann_constant,
        'NA': sympy_units.avogadro_constant,
        'N_A': sympy_units.avogadro_constant,
        'c': sympy_units.speed_of_light,
        'J': sympy_units.joule,
        'hbar': sympy_units.hbar,
        'h': sympy_units.planck,
        'G': sympy_units.gravitational_constant,
        'q':sympy_units.elementary_charge,
        'me':sympy_units.electron_rest_mass,
        'g': sympy_units.gram,
        'erf': erf,
        'erfc': erfc
    }
    unit_dict.update(aliases)

    return unit_dict

ALL_UNITS = get_units()

def parse(input_text, evaluate = False):
    if not input_text.strip():
        return ''
    try:
        input_text = re.sub(r'(\d)J\b', r'\1*J', input_text)
        return parse_expr(
            input_text,
            transformations=transformations,
            local_dict=ALL_UNITS,
            evaluate=evaluate
        )
    except Exception:
        return None

def get_preview():
        text = buffer.text
        expr = parse(text)

        if expr:
            return pretty(expr, use_unicode = True)
        else:
            return ""


def dim_sanity_check(expr1, expr2):
    try:
        si_sys = UnitSystem.get_unit_system("SI")
        dim1 = convert_to(expr1, SI_BASE)
        dim2 = convert_to(expr2, SI_BASE)
        dim1 = si_sys.get_dimensional_expr(dim1)
        dim2 = si_sys.get_dimensional_expr(dim2)
        return dim1 == dim2
    except AttributeError:
        return False

preview_control = FormattedTextControl(text=get_preview)

preview = HSplit([
	Window(content = preview_control, height = 15),
	Window(height = 1, char = '-'),
	Window(content = BufferControl(buffer = buffer),
           height = 2)
])

kb = KeyBindings()

@kb.add('c-c')
def exit_app(event):
    event.app.exit()

@kb.add('enter')
def calculate(event):
    global current_expr
    global state

    if state == -1:
        buffer.reset()
        state = 0

    if state == 0:
        text = buffer.text
        if not text:
            return

        parsed = parse(text, evaluate=True)
        if parsed:
            current_expr = parsed
            buffer.reset()
            buffer.text = "In: "
            buffer.cursor_position = len(buffer.text)
            state = 1
            return


    if state == 1:
        text = buffer.text
        target_unit = None

        if "In: " in text:
            parts = text.split("In: ")
            if len(parts) > 1:
                right = parts[1]
                if right:
                    target_unit = parse(right, evaluate=True)

        try:
            base_expr = convert_to(current_expr, SI_BASE)

            if target_unit:
                if not dim_sanity_check(base_expr, target_unit):
                    raise IncompatibleDims
                final_result = convert_to(current_expr, target_unit)
            else:
                numeric = base_expr.evalf()
                final_result = quantity_simplify(numeric)

            state = 0
            display_str = (str(final_result).replace('**', '^')
                                            .replace('*', ' ')
                                            .replace('^', '**')
                           )
            buffer.text = display_str
            buffer.cursor_position = len(buffer.text)

        except Exception as e:
            state = -1
            buffer.text = f"Error: {e}\nPress ENTER to continue... "



app = Application(
    layout=Layout(preview),
    key_bindings=kb,
    full_screen=True,
    mouse_support=True
)

if __name__ == "__main__":
    app.run()
