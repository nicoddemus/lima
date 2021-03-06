'''tests for the fields module'''

import datetime as dt

import pytest

from lima import abc, fields, schema


PASSTHROUGH_FIELDS = [
    fields.Boolean,
    fields.Float,
    fields.Integer,
    fields.String,
]

SIMPLE_FIELDS = PASSTHROUGH_FIELDS + [
    fields.Date,
    fields.DateTime
]


@pytest.mark.parametrize('cls', SIMPLE_FIELDS)
def test_simple_fields(cls):
    '''Test creation of simple fields.'''
    field = cls()
    assert isinstance(field, abc.FieldABC)


@pytest.mark.parametrize('cls', SIMPLE_FIELDS)
def test_simple_fields_attr(cls):
    '''Test creation of simple fields with attr.'''
    attr = 'foo'
    field = cls(attr=attr)
    assert isinstance(field, abc.FieldABC)
    assert field.attr == attr


@pytest.mark.parametrize('cls', SIMPLE_FIELDS)
def test_simple_fields(cls):
    '''Test creation of simple fields with get.'''
    getter = lambda obj: obj.foo
    field = cls(get=getter)
    assert isinstance(field, abc.FieldABC)
    assert field.get == getter


@pytest.mark.parametrize('cls', SIMPLE_FIELDS)
def test_illegal_attr_fails(cls):
    '''Test if supplying a non-identifier attr raises an error.'''
    with pytest.raises(ValueError):
        field = cls(attr='0not;an,identifier')


@pytest.mark.parametrize('cls', SIMPLE_FIELDS)
def test_illegal_getter_fails(cls):
    '''Test if supplying a non-callable getter raises an error.'''
    with pytest.raises(ValueError):
        field = cls(get='this is not callable')


@pytest.mark.parametrize('cls', SIMPLE_FIELDS)
def test_attr_and_getter_fails(cls):
    '''Test if supplying both getter and attr raises an error.'''
    with pytest.raises(ValueError):
        field = cls(attr='foo', get=lambda obj: 'bar')


@pytest.mark.parametrize('cls', PASSTHROUGH_FIELDS)
def test_passthrough_field_no_attrs(cls):
    '''Test simple fields having neither get nor pack attrs ...

    ... which would slow down serialization of trivial stuff

    '''
    field = cls()
    assert not hasattr(field, 'attr')
    assert not hasattr(field, 'get')
    assert not hasattr(field, 'pack')


def test_date_pack():
    '''Test date field pack static method'''
    date = dt.date(1952, 9, 1)
    assert fields.Date.pack(date) == '1952-09-01'


def test_datetime_pack():
    '''Test date field pack static method'''
    tz = dt.timezone(dt.timedelta(hours=2))
    datetime = dt.datetime(1952, 9, 1, 23, 11, 59, 123456, tz)
    expected = '1952-09-01T23:11:59.123456+02:00'
    assert fields.DateTime.pack(datetime) == expected


# tests of nested fields assume a lot of the other stuff also works

def test_nested_by_name():
    field = fields.Nested(schema='NonExistentSchema')
    assert field.schema_name == 'NonExistentSchema'


def test_nested_error_on_illegal_schema_spec():

    with pytest.raises(TypeError):
        field = fields.Nested(schema=123)
