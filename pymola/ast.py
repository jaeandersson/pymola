#!/usr/bin/env python
"""
Modelica AST definitions
"""
from __future__ import print_function, absolute_import, division, print_function, unicode_literals

import copy
import json
from enum import Enum
from typing import List, Union, Dict
from collections import OrderedDict


class ClassNotFoundError(Exception):
    pass


class Visibility(Enum):
    PRIVATE = 0, 'private'
    PROTECTED = 1, 'protected'
    PUBLIC = 2, 'public'

    def __new__(cls, value, name):
        member = object.__new__(cls)
        member._value_ = value
        member.fullname = name
        return member

    def __int__(self):
        return self.value

    def __str__(self):
        return self.fullname

    def __lt__(self, other):
        return self.value < other.value


nan = float('nan')

"""
AST Node Type Hierarchy

Root Class
    Class
        Equation
            ComponentRef
            Expression
            Primary
        IfEquation
            Expression
            Equation
        ForEquation
            Expression
            Equation
        ConnectClause
            ComponentRef
        Symbol
"""


class Node(object):
    def __init__(self, **kwargs):
        self.set_args(**kwargs)

    def set_args(self, **kwargs):
        for key in kwargs.keys():
            if key not in self.__dict__.keys():
                raise KeyError('{:s} not valid arg'.format(key))
            self.__dict__[key] = kwargs[key]

    def __repr__(self):
        return json.dumps(self.to_json(self), indent=2, sort_keys=True)

    @classmethod
    def to_json(cls, var):
        if isinstance(var, list):
            res = [cls.to_json(item) for item in var]
        elif isinstance(var, dict):
            res = {key: cls.to_json(var[key]) for key in var.keys()}
        elif isinstance(var, Node):
            res = {key: cls.to_json(var.__dict__[key]) for key in var.__dict__.keys()}
        elif isinstance(var, Visibility):
            res = str(var)
        else:
            res = var
        return res

    __str__ = __repr__


class Primary(Node):
    def __init__(self, **kwargs):
        self.value = None  # type: Union[bool, float, int, str, type(None)]
        super().__init__(**kwargs)


class Array(Node):
    def __init__(self, **kwargs):
        self.values = []  # type: List[Union[Expression, Primary, ComponentRef, Array]]
        super().__init__(**kwargs)


class Slice(Node):
    def __init__(self, **kwargs):
        self.start = Primary(value=0)  # type: Union[Expression, Primary, ComponentRef]
        self.stop = Primary(value=-1)  # type: Union[Expression, Primary, ComponentRef]
        self.step = Primary(value=1)  # type: Union[Expression, Primary, ComponentRef]
        super().__init__(**kwargs)


class ComponentRef(Node):
    def __init__(self, **kwargs):
        self.name = ''  # type: str
        self.indices = []  # type: List[Union[Expression, Slice, Primary, ComponentRef]]
        self.child = []  # type: List[ComponentRef]
        super().__init__(**kwargs)

    def __str__(self) -> str:
        return ".".join(self.to_tuple())

    def to_tuple(self) -> tuple:
        """
        Convert the nested component reference to flat tuple of names, which is
        hashable and can therefore be used as dictionary key. Note that this
        function ignores any array indices in the component reference.
        :return: flattened tuple of c's names
        """

        if self.child:
            return (self.name, ) + self.child[0].to_tuple()
        else:
            return (self.name, )

    @classmethod
    def from_tuple(cls, components: tuple) -> 'ComponentRef':
        """
        Convert the tuple pointing to a component to
        a component reference.
        :param components: tuple of components name
        :return: ComponentRef
        """

        component_ref = ComponentRef(name=components[0], child=[])
        c = component_ref
        for component in components[1:]:
            c.child.append(ComponentRef(name=component, child=[]))
            c = c.child[0]
        return component_ref

    @classmethod
    def from_string(cls, s: str) -> 'ComponentRef':
        """
        Convert the string pointing to a component using dot notation to
        a component reference.
        :param s: string pointing to component using dot notation
        :return: ComponentRef
        """

        components = s.split('.')
        return cls.from_tuple(components)

    @classmethod
    def concatenate(cls, *args: List['ComponentRef']) -> 'ComponentRef':
        """
        Helper function to append two component references to eachother, e.g.
        a "within" component ref and an "object type" component ref.
        :param a:
        :param b:
        :return: New component reference, with other appended to self.
        """

        a = copy.deepcopy(args[0])
        n = a
        for b in args[1:]:
            while n.child:
                n = n.child[0]
            b = copy.deepcopy(b)  # Not strictly necessary
            n.child = [b]
        return a


class Expression(Node):
    def __init__(self, **kwargs):
        self.operator = None  # type: Union[str, ComponentRef]
        self.operands = []  # type: List[Union[Expression, Primary, ComponentRef, Array, IfExpression]]
        super().__init__(**kwargs)


class IfExpression(Node):
    def __init__(self, **kwargs):
        self.conditions = []  # type: List[Union[Expression, Primary, ComponentRef, Array, IfExpression]]
        self.expressions = []  # type: List[Union[Expression, Primary, ComponentRef, Array, IfExpression]]
        super().__init__(**kwargs)


class Equation(Node):
    def __init__(self, **kwargs):
        self.left = None  # type: Union[Expression, Primary, ComponentRef, List[Union[Expression, Primary, ComponentRef]]]
        self.right = None  # type: Union[Expression, Primary, ComponentRef, List[Union[Expression, Primary, ComponentRef]]]
        self.comment = ''  # type: str
        super().__init__(**kwargs)


class IfEquation(Node):
    def __init__(self, **kwargs):
        self.conditions = []  # type: List[Union[Expression, Primary, ComponentRef]]
        self.equations = []  # type: List[Union[Expression, ForEquation, ConnectClause, IfEquation]]
        self.comment = ''  # type: str
        super().__init__(**kwargs)


class ForIndex(Node):
    def __init__(self, **kwargs):
        self.name = ''  # type: str
        self.expression = None  # type: Union[Expression, Primary, Slice]
        super().__init__(**kwargs)


class ForEquation(Node):
    def __init__(self, **kwargs):
        self.indices = []  # type: List[ForIndex]
        self.equations = []  # type: List[Union[Equation, ForEquation, ConnectClause]]
        self.comment = None  # type: str
        super().__init__(**kwargs)


class ConnectClause(Node):
    def __init__(self, **kwargs):
        self.left = ComponentRef()  # type: ComponentRef
        self.right = ComponentRef()  # type: ComponentRef
        self.comment = ''  # type: str
        super().__init__(**kwargs)


class AssignmentStatement(Node):
    def __init__(self, **kwargs):
        self.left = []  # type: List[ComponentRef]
        self.right = None  # type: Union[Expression, IfExpression, Primary, ComponentRef]
        self.comment = ''  # type: str
        super().__init__(**kwargs)


class IfStatement(Node):
    def __init__(self, **kwargs):
        self.conditions = []  # type: List[Union[Expression, Primary, ComponentRef]]
        self.statements = []  # type: List[Union[AssignmentStatement, IfStatement, ForStatement]]
        self.comment = ''  # type: str
        super().__init__(**kwargs)


class ForStatement(Node):
    def __init__(self, **kwargs):
        self.indices = []  # type: List[ForIndex]
        self.statements = []  # type: List[Union[AssignmentStatement, IfStatement, ForStatement]]
        self.comment = ''  # type: str
        super().__init__(**kwargs)


class Symbol(Node):
    """
    A mathematical variable or state of the model
    """
    ATTRIBUTES = ['value', 'min', 'max', 'start', 'fixed', 'nominal']

    def __init__(self, **kwargs):
        self.name = ''  # type: str
        self.type = ComponentRef()  # type: ComponentRef
        self.prefixes = []  # type: List[str]
        self.redeclare = False  # type: bool
        self.final = False  # type: bool
        self.inner = False  # type: bool
        self.outer = False  # type: bool
        self.dimensions = [Primary(value=1)]  # type: List[Union[Expression, Primary, ComponentRef]]
        self.comment = ''  # type: str
        # params start value is 0 by default from Modelica spec
        self.start = Primary(value=0)  # type: Union[Expression, Primary, ComponentRef, Array]
        self.min = Primary(value=None)  # type: Union[Expression, Primary, ComponentRef, Array]
        self.max = Primary(value=None)  # type: Union[Expression, Primary, ComponentRef, Array]
        self.nominal = Primary(value=None)  # type: Union[Expression, Primary, ComponentRef, Array]
        self.value = Primary(value=None)  # type: Union[Expression, Primary, ComponentRef, Array]
        self.fixed = Primary(value=False)  # type: Primary
        self.id = 0  # type: int
        self.order = 0  # type: int
        self.visibility = Visibility.PRIVATE  # type: Visibility
        self.class_modification = None  # type: ClassModification
        super().__init__(**kwargs)


class ComponentClause(Node):
    def __init__(self, **kwargs):
        self.prefixes = []  # type: List[str]
        self.type = ComponentRef()  # type: ComponentRef
        self.dimensions = [Primary(value=1)]  # type: List[Union[Expression, Primary, ComponentRef]]
        self.comment = []  # type: List[str]
        self.symbol_list = []  # type: List[Symbol]
        super().__init__(**kwargs)


class EquationSection(Node):
    def __init__(self, **kwargs):
        self.initial = False  # type: bool
        self.equations = []  # type: List[Union[Equation, IfEquation, ForEquation, ConnectClause]]
        super().__init__(**kwargs)


class AlgorithmSection(Node):
    def __init__(self, **kwargs):
        self.initial = False  # type: bool
        self.statements = []  # type: List[Union[AssignmentStatement, IfStatement, ForStatement]]
        super().__init__(**kwargs)


class ImportAsClause(Node):
    def __init__(self, **kwargs):
        self.component = ComponentRef()  # type: ComponentRef
        self.name = ''  # type: str
        super().__init__(**kwargs)


class ImportFromClause(Node):
    def __init__(self, **kwargs):
        self.component = ComponentRef()  # type: ComponentRef
        self.symbols = []  # type: List[str]
        super().__init__(**kwargs)


class ElementModification(Node):
    # TODO: Check if ComponentRef modifiers are handled correctly. For example,
    # check HomotopicLinear which extends PartialHomotopic with the modifier
    # "H(min = H_b)".
    def __init__(self, **kwargs):
        self.component = ComponentRef()  # type: Union[ComponentRef]
        self.modifications = []  # type: List[Union[Primary, Expression, ClassModification, Array, ComponentRef]]
        super().__init__(**kwargs)


class ShortClassDefinition(Node):
    def __init__(self, **kwargs):
        self.name = ''  # type: str
        self.type = ''  # type: str
        self.component = ComponentRef()  # type: ComponentRef
        self.class_modification = ClassModification()  # type: ClassModification
        super().__init__(**kwargs)


class ElementReplaceable(Node):
    def __init__(self, **kwargs):
        # TODO, add fields ?
        super().__init__(**kwargs)


class ClassModification(Node):
    def __init__(self, **kwargs):
        self.arguments = []  # type: List[Union[ElementModification, ComponentClause, ShortClassDefinition]]
        super().__init__(**kwargs)


class ExtendsClause(Node):
    def __init__(self, **kwargs):
        self.component = None  # type: ComponentRef
        self.class_modification = None  # type: ClassModification
        self.visibility = Visibility.PRIVATE  # type: Visibility
        super().__init__(**kwargs)


class Class(Node):
    def __init__(self, **kwargs):
        self.name = None  # type: str
        self.imports = []  # type: List[Union[ImportAsClause, ImportFromClause]]
        self.extends = []  # type: List[ExtendsClause]
        self.encapsulated = False  # type: bool
        self.partial = False  # type: bool
        self.final = False  # type: bool
        self.type = ''  # type: str
        self.comment = ''  # type: str
        self.classes = OrderedDict()  # type: OrderedDict[str, Class]
        self.symbols = OrderedDict()  # type: OrderedDict[str, Symbol]
        self.functions = OrderedDict()  # type: OrderedDict[str, Class]
        self.initial_equations = []  # type: List[Union[Equation, ForEquation]]
        self.equations = []  # type: List[Union[Equation, ForEquation, ConnectClause]]
        self.initial_statements = []  # type: List[Union[AssignmentStatement, IfStatement, ForStatement]]
        self.statements = []  # type: List[Union[AssignmentStatement, IfStatement, ForStatement]]
        self.within = []  # type: List[ComponentRef]
        super().__init__(**kwargs)


class File(Node):
    """
    Represents a .mo file for use in pre-processing before flattening to a single class.
    """

    def __init__(self, **kwargs):
        self.within = []  # type: List[ComponentRef]
        self.classes = OrderedDict()  # type: OrderedDict[str, Class]
        super().__init__(**kwargs)


class Collection(Node):
    """
    A list of modelica files, used in pre-processing packages etc. before flattening
    to a single class.
    """

    def __init__(self, **kwargs):
        self.files = []  # type: List[File]
        super().__init__(**kwargs)

        # TODO: Should be directly build the class_lookup, or wait until the first call to find_class?
        self._class_lookup = None

    def _build_class_lookup_for_class(self, c, within):
        if within:
            full_name = ComponentRef.concatenate(within, ComponentRef(name=c.name))
        else:
            full_name = ComponentRef(name=c.name)

        # FIXME: Do we have to convert to string?
        self._class_lookup[full_name.to_tuple()] = c

        if within:
            within = ComponentRef.concatenate(within, ComponentRef(name=c.name))
        else:
            within = ComponentRef(name=c.name)
        for nested_c in c.classes.values():
            self._build_class_lookup_for_class(nested_c, within)

    def _build_class_lookup(self):
        self._class_lookup = {}

        for f in self.files:
            within = f.within[0] if f.within else None
            for c in f.classes.values():
                self._build_class_lookup_for_class(c, within)

    def extend(self, other):
        self.files.extend(other.files)

    def find_class(self, component_ref: ComponentRef, within: list = None, check_builtin_classes=False, return_ref=False):
        if check_builtin_classes:
            if component_ref.name in ["Real", "Integer", "String", "Boolean"]:
                c = Class(name=component_ref.name)
                c.type = "__builtin"

                cref = ComponentRef(name=component_ref.name)
                s = Symbol(name="__value", type=cref)
                c.symbols[s.name] = s

                if return_ref:
                    return c, cref
                else:
                    return c

        if self._class_lookup is None:
            self._build_class_lookup()

        # TODO: Support lookups starting with a dot. These are lookups in the root node (i.e. within not used).
        # Odds are that these types of lookups are not parsed yet. We would expet an empty first name, with a non-empty child.

        # Lookup the referenced class, walking up the tree from the current
        # node until the root node.
        c = None

        if within:
            within_tuple = within[0].to_tuple()
        else:
            within_tuple = tuple()

        cref_tuple = component_ref.to_tuple()

        prev_tuple = None

        while c is None:
            c = self._class_lookup.get(within_tuple + cref_tuple, None)

            prev_tuple = within_tuple + cref_tuple

            if within_tuple:
                within_tuple = within_tuple[:-1]
            else:
                # Finished traversing up the tree all the way to the root. No
                # more lookups possible.
                break

        if c is None:
            # Class not found
            if component_ref.name in ("Real", "Integer", "Boolean", "String", "Modelica", "SI"):
                # FIXME: To support an "ignore" in the flattener, we raise a
                # KeyError for what are likely to be elementary types
                raise KeyError
            else:
                raise ClassNotFoundError("Could not find class {}".format(component_ref))

        if return_ref:
            return c, ComponentRef.from_tuple(prev_tuple)
        else:
            return c

    def find_symbol(self, node, component_ref: ComponentRef) -> Symbol:
        sym = node.symbols[component_ref.name]
        if len(component_ref.child) > 0:
            node = self.find_class(sym.type)
            return self.find_symbol(node, component_ref.child[0])
        else:
            return sym
