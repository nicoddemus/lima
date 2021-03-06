'''tests for schema.Schema.dump module'''

from datetime import date, datetime

import pytest

from lima import fields, schema, registry


class Person:
    def __init__(self, title, name, number, born):
        self.title = title
        self.name = name
        self.number = number
        self.born = born


class PersonSchema(schema.Schema):
    title = fields.String()
    name = fields.String()
    number = fields.Integer()
    born = fields.Date()


class DifferentAttrSchema(schema.Schema):
    date_of_birth = fields.Date(attr='born')


class GetterSchema(schema.Schema):
    some_getter = lambda obj: '{} {}'.format(obj.title, obj.name)

    full_name = fields.String(get=some_getter)


class KnightSchema(schema.Schema):
    name = fields.String()


class KingSchemaNestedStr(KnightSchema):
    title = fields.String()
    subjects = fields.Nested(schema=__name__ + '.KnightSchema', many=True)


class KingSchemaNestedClass(KnightSchema):
    title = fields.String()
    subjects = fields.Nested(schema=KnightSchema, many=True)


class KingSchemaNestedObject(KnightSchema):
    some_schema_object = KnightSchema(many=True)

    title = fields.String()
    subjects = fields.Nested(schema=some_schema_object)


class SelfReferentialKingSchema(schema.Schema):
    name = fields.String()
    boss = fields.Nested(schema=__name__ + '.SelfReferentialKingSchema',
                         exclude='boss')


@pytest.fixture
def king():
    return Person('King', 'Arthur', 1, date(501, 1, 1))


@pytest.fixture
def knights():
    return [
        Person('Sir', 'Bedevere', 2, date(502, 2, 2)),
        Person('Sir', 'Lancelot', 3, date(503, 3, 3)),
        Person('Sir', 'Galahad', 4, date(504, 4, 4)),
    ]


def test_simple_dump(king):
    person_schema = PersonSchema()
    expected = {
        'title': 'King',
        'name': 'Arthur',
        'number': 1,
        'born': '0501-01-01'
    }

    assert person_schema.dump(king) == expected


def test_simple_dump_exclude(king):
    person_schema = PersonSchema(exclude=['born'])
    expected = {
        'title': 'King',
        'name': 'Arthur',
        'number': 1,
    }

    assert person_schema.dump(king) == expected


def test_simple_dump_only(king):
    person_schema = PersonSchema(only=['name'])
    expected = {
        'name': 'Arthur',
    }

    assert person_schema.dump(king) == expected


def test_attr_field_dump(king):
    attr_schema = DifferentAttrSchema()
    expected = {
        'date_of_birth': '0501-01-01'
    }
    assert attr_schema.dump(king) == expected


def test_getter_field_dump(king):
    getter_schema = GetterSchema()
    expected = {
        'full_name': 'King Arthur'
    }
    assert getter_schema.dump(king) == expected


def test_many_dump1(knights):
    multi_person_schema = PersonSchema(only=['name'], many=True)
    expected = [
        {'name': 'Bedevere'},
        {'name': 'Lancelot'},
        {'name': 'Galahad'},
    ]
    assert multi_person_schema.dump(knights) == expected


def test_many_dump2(knights):
    multi_person_schema = PersonSchema(only=['name'], many=False)
    expected = [
        {'name': 'Bedevere'},
        {'name': 'Lancelot'},
        {'name': 'Galahad'},
    ]
    assert multi_person_schema.dump(knights, many=True) == expected


@pytest.mark.parametrize('schema_cls',
                         [KingSchemaNestedStr,
                          KingSchemaNestedClass,
                          KingSchemaNestedObject])
def test_dump_nested_schema(schema_cls, king, knights):
    '''Test with nested Schema specified as a String'''
    king_schema = schema_cls()
    king.subjects = knights
    expected = {
        'title': 'King',
        'name': 'Arthur',
        'subjects': [
            {'name': 'Bedevere'},
            {'name': 'Lancelot'},
            {'name': 'Galahad'},
        ]
    }
    assert king_schema.dump(king) == expected


def test_dump_nested_schema_instance_double_kwargs_error(king, knights):
    '''Test for ValueError when providing unnecssary kwargs.'''

    class KnightSchema(schema.Schema):
        name = fields.String()

    nested_schema = KnightSchema(many=True)

    with pytest.raises(ValueError):
        class KingSchema(KnightSchema):
            title = fields.String()
            subjects = fields.Nested(schema=nested_schema, many=True)


def test_dump_nested_schema_self(king):
    '''Test with nested Schema specified as a String'''
    king_schema = SelfReferentialKingSchema()
    king.boss = king
    expected = {
        'name': 'Arthur',
        'boss': {'name': 'Arthur'},
    }
    assert king_schema.dump(king) == expected
