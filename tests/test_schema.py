'''tests for the schema module'''
from collections import OrderedDict

import pytest

from lima import abc, fields, schema
from lima.registry import global_registry


@pytest.fixture
def str_field():
    return fields.String()


@pytest.fixture
def int_field():
    return fields.Integer()


@pytest.fixture
def date_field():
    return fields.Date()


@pytest.fixture
def person_schema_cls(str_field, int_field, date_field):
    class PersonSchema(schema.Schema):
        name = str_field
        number = int_field
        born = date_field
    return PersonSchema


# To test if this schema gets registered.
class NonLocalSchema(schema.Schema):
    foo = fields.String()


class TestHelperFunctions:
    '''Class collecting tests of helper functions.'''

    def test_into_list_if_str(self):
        assert schema._into_list_if_str([]) == []
        assert schema._into_list_if_str(42) == 42
        assert schema._into_list_if_str(['foo']) == ['foo']
        assert schema._into_list_if_str('bar') == ['bar']

    def test_ensure_iterable(self):
        # none of these should raise anything
        schema._ensure_iterable([1, 2, 3])
        schema._ensure_iterable(range(10))
        schema._ensure_iterable(i for i in range(10))

        with pytest.raises(TypeError):
            schema._ensure_iterable(3)

    def test_ensure_mapping(self):
        from collections import defaultdict

        # none of these should raise anything
        schema._ensure_mapping({})
        schema._ensure_mapping({'a': 1})
        schema._ensure_mapping(defaultdict(lambda: 1))

        with pytest.raises(TypeError):
            schema._ensure_mapping(set([1, 2, 3]))

        with pytest.raises(TypeError):
            schema._ensure_mapping(None)

    def test_ensure_disjoint(self):
        # this should not raise anything
        schema._ensure_disjoint([1, 2], [3, 4])

        with pytest.raises(ValueError):
            schema._ensure_disjoint([1, 2], (2, 3))

    def test_ensure_subset(self):
        # this should not raise anything
        schema._ensure_subset([1, 2], [0, 1, 2, 3, 4])

        with pytest.raises(ValueError):
            schema._ensure_subset([1, 'foo'], [1, 2, 3])

        with pytest.raises(TypeError):
            schema._ensure_subset(1, [1, 2, 3])


class TestSchemaDefinition:
    '''Class collecting tests of Schema class definition.'''

    def test_schema_definition1(self, str_field, int_field, date_field):
        '''Test if class vars are processed correctly.'''

        class TestSchema(schema.Schema):
            foo = str_field
            bar = int_field
            baz = date_field
            unrelated = 42

        assert hasattr(TestSchema, '__fields__')
        assert hasattr(TestSchema, 'unrelated')
        assert not hasattr(TestSchema, 'foo')
        assert not hasattr(TestSchema, 'bar')
        assert not hasattr(TestSchema, 'baz')
        assert TestSchema.__fields__['foo'] == str_field
        assert TestSchema.__fields__['bar'] == int_field
        assert TestSchema.__fields__['baz'] == date_field

    def test_schema_definition2(self, str_field, int_field, date_field):
        '''Test if __lima_args__ class var is processed correctly.'''
        class TestSchema(schema.Schema):
            __lima_args__ = {
                'include': {
                    'foo': str_field,
                    'bar': int_field,
                    'baz': date_field,
                }
            }
            unrelated = 42

        assert hasattr(TestSchema, '__fields__')
        assert hasattr(TestSchema, 'unrelated')

        # those should get removed on class Creation
        assert not hasattr(TestSchema, '__lima_args__')
        assert not hasattr(TestSchema, 'foo')
        assert not hasattr(TestSchema, 'bar')
        assert not hasattr(TestSchema, 'baz')

        assert TestSchema.__fields__['foo'] == str_field
        assert TestSchema.__fields__['bar'] == int_field
        assert TestSchema.__fields__['baz'] == date_field

    def test_fail_on_wrong_args(self, str_field, int_field, date_field):
        '''test if incorrect __lima_args__ are caught'''
        with pytest.raises(TypeError):
            class WrongSchema1(schema.Schema):
                foo = str_field
                __lima_args__ = {
                    'include': 'this_is_not_a_mapping'
                }

        with pytest.raises(TypeError):
            class WrongSchema2(schema.Schema):
                foo = str_field
                __lima_args__ = {
                    'exclude': 42  # 42 is not a list
                }

        with pytest.raises(ValueError):
            class WrongSchema3(schema.Schema):
                foo = str_field
                __lima_args__ = {
                    'include': {},
                    'exclude': [],
                    'this_is_not_a_lima_arg': 42,
                }

        with pytest.raises(ValueError):
            class WrongSchema4(schema.Schema):
                foo = str_field
                bar = int_field
                baz = date_field
                # exclude AND only are forbidden
                __lima_args__ = {
                    'exclude': ['foo', 'bar'],
                    'only': 'baz',
                }

    def test_schema_inheritance(self, str_field, int_field, date_field):
        '''Test if inheritance of fields works correctly.'''
        class BaseSchema(schema.Schema):
            foo = str_field
            bar = int_field

        class DerivedSchema1(BaseSchema):
            bar = date_field  # this should override BaseSchema's foo

        class DerivedSchema2(BaseSchema):
            __lima_args__ = {
                'include': {
                    'bar': date_field  # this should override BaseSchema's foo
                }
            }

        assert DerivedSchema1.__fields__['foo'] is str_field
        assert DerivedSchema1.__fields__['bar'] is date_field

        assert DerivedSchema2.__fields__['foo'] is str_field
        assert DerivedSchema2.__fields__['bar'] is date_field

    def test_schema_multi_inheritance1(self, str_field, int_field, date_field):
        '''Test if inheritance of fields works correctly.'''
        class PrimarySchema(schema.Schema):
            __lima_args__ = {
                'include': {
                    'foo': str_field,
                    'bar': int_field,
                }
            }
            unrelated = 42

        class SecondarySchema(schema.Schema):
            bar = str_field   # this shoud get overridden in TestSchema
            baz = date_field

        class TestSchema(PrimarySchema, SecondarySchema):
            pass

        assert hasattr(TestSchema, 'unrelated')

        # attrs get moved out of class dict by metaclass
        assert not hasattr(TestSchema, 'bar')
        assert not hasattr(TestSchema, 'baz')

        assert TestSchema.__fields__['foo'] == str_field
        assert TestSchema.__fields__['bar'] == int_field
        assert TestSchema.__fields__['baz'] == date_field

    def test_schema_multi_inheritance2(self, str_field, int_field, date_field):
        '''Test if inheritance of fields works correctly.'''
        class PrimarySchema(schema.Schema):
            __lima_args__ = {
                'include': {
                    'foo': str_field,
                    'bar': int_field,
                }
            }
            unrelated = 42

        class SecondarySchema(schema.Schema):
            __lima_args__ = {
                'include': {
                    'bar': str_field  # this shoud get overridden in TestSchema
                }
            }
            baz = date_field

        class TestSchema(PrimarySchema, SecondarySchema):
            pass

        assert hasattr(TestSchema, 'unrelated')

        # attrs get moved out of class dict by metaclass
        assert not hasattr(TestSchema, 'bar')
        assert not hasattr(TestSchema, 'baz')

        assert TestSchema.__fields__['foo'] == str_field
        assert TestSchema.__fields__['bar'] == int_field
        assert TestSchema.__fields__['baz'] == date_field

    def test_schema_exclude1(self, str_field, int_field, date_field):
        '''Test if excluding fields works ok.'''
        class TestSchema(schema.Schema):
            __lima_args__ = {'exclude': ['foo', 'bar']}
            foo = str_field
            bar = int_field
            baz = date_field

        # attrs get moved out of class dict by metaclass
        assert not hasattr(TestSchema, 'foo')
        assert not hasattr(TestSchema, 'bar')
        assert not hasattr(TestSchema, 'baz')

        assert 'foo' not in TestSchema.__fields__
        assert 'bar' not in TestSchema.__fields__
        assert TestSchema.__fields__['baz'] is date_field

    def test_schema_exclude2(self, str_field, int_field, date_field):
        '''Test if excluding a single fields specified as string works.'''
        class TestSchema(schema.Schema):
            __lima_args__ = {'exclude': 'foo'}
            foo = str_field
            bar = int_field

        # attrs get moved out of class dict by metaclass
        assert not hasattr(TestSchema, 'foo')
        assert not hasattr(TestSchema, 'bar')

        assert 'foo' not in TestSchema.__fields__
        assert TestSchema.__fields__['bar'] is int_field

    def test_schema_only1(self, str_field, int_field, date_field):
        '''Test if excluding fields via only works ok.'''
        class TestSchema(schema.Schema):
            __lima_args__ = {'only': ['foo', 'bar']}
            foo = str_field
            bar = int_field
            baz = date_field

        # attrs get moved out of class dict by metaclass
        assert not hasattr(TestSchema, 'foo')
        assert not hasattr(TestSchema, 'bar')
        assert not hasattr(TestSchema, 'baz')

        assert TestSchema.__fields__['foo'] is str_field
        assert TestSchema.__fields__['bar'] is int_field
        assert 'baz' not in TestSchema.__fields__

    def test_schema_only2(self, str_field, int_field, date_field):
        '''Test if excluding fields via only spec. as string works ok.'''
        class TestSchema(schema.Schema):
            __lima_args__ = {'only': 'foo'}
            foo = str_field
            bar = int_field
            baz = date_field

        # attrs get moved out of class dict by metaclass
        assert not hasattr(TestSchema, 'foo')
        assert not hasattr(TestSchema, 'bar')
        assert not hasattr(TestSchema, 'baz')

        assert TestSchema.__fields__['foo'] is str_field
        assert 'bar' not in TestSchema.__fields__
        assert 'baz' not in TestSchema.__fields__

    def test_fail_on_duplicate_fields(self, str_field, int_field):
        '''Test if duplicate field definition raises an error.'''
        with pytest.raises(ValueError):
            class TestSchema(schema.Schema):
                __lima_args__ = {
                    'include': {
                        'foo': str_field,
                    }
                }
                foo = int_field

    def test_fail_on_nonexistent_fields(self, str_field, int_field):
        '''Test if mentining nonexistent field in exlcude raises an error.'''
        with pytest.raises(ValueError):
            class TestSchema(schema.Schema):
                __lima_args__ = {
                    'include': {
                        'foo': str_field,
                        'bar': int_field,
                    },
                    'exclude': ['nonexistent'],
                }

    def test_schema_registered(self, str_field):
        '''Test if nonlocal Schemas land in the registry.'''
        retrieved_schema = global_registry.get(__name__ + '.NonLocalSchema')
        assert retrieved_schema == NonLocalSchema

    def test_schema_field_order_1(self):
        '''Test if fields are in the expected order.'''
        # this test is rather long. surely there is a better way to do this
        field1 = fields.String()
        field2 = fields.String()
        field3 = fields.String()
        field4 = fields.String()
        field5 = fields.String()
        field6 = fields.String()
        field7 = fields.String()
        field8 = fields.String()
        field9 = fields.String()

        # to test overrides
        new_field4 = fields.String()
        new_field5 = fields.String()

        class TestSchema1(schema.Schema):
            one = field1
            two = field2
            three = field3
            four = field4
            five = field5
        test_instance1 = TestSchema1()
        expected = OrderedDict(
            [
                ('one', field1),
                ('two', field2),
                ('three', field3),
                ('four', field4),
                ('five', field5),
            ]
        )
        assert TestSchema1.__fields__ == expected
        assert test_instance1._fields == expected

        class TestMixin(schema.Schema):
            five = new_field5
            six = field6

        # should NOT override TestSchema1's field5
        class TestSchema2(TestSchema1, TestMixin):
            pass
        test_instance2 = TestSchema2()
        expected = OrderedDict(
            [
                ('one', field1),
                ('two', field2),
                ('three', field3),
                ('four', field4),
                ('five', field5),
                ('six', field6),
            ]
        )
        assert TestSchema2.__fields__ == expected
        assert test_instance2._fields == expected

        # SHOULD override TestSchema1's field5. Also, different order.
        class TestSchema3(TestMixin, TestSchema1):
            pass
        test_instance3 = TestSchema3()
        expected = OrderedDict(
            [
                ('five', new_field5),
                ('six', field6),
                ('one', field1),
                ('two', field2),
                ('three', field3),
                ('four', field4),
            ]
        )
        assert TestSchema3.__fields__ == expected
        assert test_instance3._fields == expected

        class TestSchema4(TestSchema1):
            four = new_field4   # this should replace inherited
            six = field6  # this should land afterwards
            seven = field7  # this should land afterwards
            __lima_args__ = {
                'include': OrderedDict(
                    [
                        ('five', new_field5),  # this should replace inherited
                        ('eight', field8),  # this sould land afterwards
                        ('nine', field9),  # this sould land afterwards
                    ]
                )
            }
        test_instance4 = TestSchema4()
        expected = OrderedDict(
            [
                ('one', field1),
                ('two', field2),
                ('three', field3),
                ('four', new_field4),
                ('five', new_field5),
                ('six', field6),
                ('seven', field7),
                ('eight', field8),
                ('nine', field9),
            ]
        )
        assert TestSchema4.__fields__ == expected
        assert test_instance4._fields == expected

        # see if only/exclude don't mess up order
        class TestSchema5(TestSchema1):
            __lima_args__ = {'only': ['three', 'five', 'one']}
        class TestSchema6(TestSchema1):
            __lima_args__ = {'exclude': ['four', 'two']}
        test_instance5 = TestSchema5()
        test_instance6 = TestSchema6()
        test_instance1a = TestSchema1(only=['three', 'five', 'one'])
        test_instance1b = TestSchema1(exclude=['four', 'two'])
        expected = OrderedDict(
            [
                ('one', field1),
                ('three', field3),
                ('five', field5),
            ]
        )
        assert TestSchema5.__fields__ == expected
        assert test_instance5._fields == expected
        assert TestSchema6.__fields__ == expected
        assert test_instance6._fields == expected
        assert test_instance1a._fields == expected
        assert test_instance1b._fields == expected

class TestSchemaInstantiation:
    '''Class collecting tests of Schema object creation.'''

    def test_instance_gets_class_fields(self, str_field,
                                        int_field, date_field):
        '''Test if class fields land in instance.

        This might fail in the future if field instances are copied instead of
        taken from the class (there is no final decision on the ideal behaviour
        at the moment.)

        '''
        class TestSchema(schema.Schema):
            foo = str_field
            bar = int_field
            baz = date_field

        test_schema = TestSchema()

        assert isinstance(test_schema, abc.SchemaABC)
        assert hasattr(test_schema, '_fields')
        assert test_schema._fields['foo'] is TestSchema.__fields__['foo']
        assert test_schema._fields['bar'] is TestSchema.__fields__['bar']
        assert test_schema._fields['baz'] is TestSchema.__fields__['baz']

    def test_instance_gets_fields_like_class_fields(self, person_schema_cls):
        '''Test if instance gets fields like those of the class.

        This time, only check field names. This should always work, regardles
        of the decision on copying vs. referencing class fields.

        '''
        person_schema = person_schema_cls()

        assert 'name' in person_schema._fields
        assert 'number' in person_schema._fields
        assert 'born' in person_schema._fields

    def test_fields_exclude1(self, person_schema_cls):
        '''Test if excluding fields works.'''
        person_schema = person_schema_cls(exclude=['name', 'number'])

        assert 'name' not in person_schema._fields
        assert 'number' not in person_schema._fields
        assert 'born' in person_schema._fields

    def test_fields_exclude2(self, person_schema_cls):
        '''Test if excluding fields specified as string works.'''
        person_schema = person_schema_cls(exclude='name')

        assert 'name' not in person_schema._fields
        assert 'number' in person_schema._fields
        assert 'born' in person_schema._fields

    def test_fields_only1(self, person_schema_cls):
        '''Test if having only specified fields works.'''
        person_schema = person_schema_cls(only=['name', 'number'])

        assert 'name' in person_schema._fields
        assert 'number' in person_schema._fields
        assert 'born' not in person_schema._fields

    def test_fields_only2(self, person_schema_cls):
        '''Test if having only specified fields works.'''
        person_schema = person_schema_cls(only='name')

        assert 'name' in person_schema._fields
        assert 'number' not in person_schema._fields
        assert 'born' not in person_schema._fields

    def test_fields_include(self, person_schema_cls):
        '''Test if including fields works.'''
        fld = fields.DateTime()
        person_schema = person_schema_cls(include={'timestamp': fld})

        assert 'name' in person_schema._fields
        assert 'number' in person_schema._fields
        assert 'born' in person_schema._fields
        assert person_schema._fields['timestamp'] is fld

    def test_fail_on_exclude_nonexistent(self, person_schema_cls):
        '''Test if excluding nonexistent fields raises an error.'''
        with pytest.raises(ValueError):
            person_schema = person_schema_cls(exclude=['nonexistent'])

    def test_fail_on_only_nonexistent(self, person_schema_cls):
        '''Test if spec. only for nonexistent fields raises an error.'''
        with pytest.raises(ValueError):
            person_schema = person_schema_cls(only=['nonexistent'])

    def test_fail_on_exclude_wrong_type(self, person_schema_cls):
        '''Test if specifying the wrong type for exclude raises an error.'''
        with pytest.raises(TypeError):
            person_schema = person_schema_cls(exclude=42)

    def test_fail_on_only_wrong_type(self, person_schema_cls):
        '''Test if specifying the wrong type for exclude raises an error.'''
        with pytest.raises(TypeError):
            person_schema = person_schema_cls(only=42)

    def test_fail_on_exclude_and_only(self, person_schema_cls):
        '''Test if providing exclude AND only raises an error.'''
        with pytest.raises(ValueError):
            person_schema = person_schema_cls(exclude=['number'],
                                              only=['name'])

    def test_fail_on_non_identifier_attr_name(self):
        '''Test if providing a non-identifier attr name raises an error'''
        class TestSchema(schema.Schema):
            foo = fields.String()
            foo.attr = 'this-is@not;an+identifier'

        with pytest.raises(ValueError):
            test_schema = TestSchema()

    def test_fail_on_non_identifier_field_name_without_attr(self):
        '''Test if providing a non-identifier field name raises an error ...

        ... for the case where the field name would be used as attr name
        (because field has neither getter nor attr name)

        '''
        class TestSchema(schema.Schema):
            __lima_args__ = {
                'include': {
                    'not@an-identifier': fields.String()
                }
            }

        with pytest.raises(ValueError):
            test_schema = TestSchema()

    def test_succes_on_non_identifier_field_name_with_attr(self):
        '''Test if providing a non-identifier field name raises no error ...

        ... because field has an attr name specified

        '''
        class TestSchema(schema.Schema):
            __lima_args__ = {
                'include': {
                    'not;an-identifier': fields.String(attr='but_with_attr')
                }
            }

        test_schema = TestSchema()
        assert 'not;an-identifier' in test_schema._fields

    def test_fail_on_field_name_with_quotes(self):
        '''Test if providing a field name with quotes raises an error ...'''
        class TestSchema(schema.Schema):
            __lima_args__ = {
                'include': {
                    'field_with_"quotes"': fields.String(attr='foo')
                }
            }

        with pytest.raises(ValueError):
            test_schema = TestSchema()

    def test_get_dump_function_code(self):
        '''Test if _get_dump_function_code gets a simple function right.'''
        from textwrap import dedent

        class TestSchema(schema.Schema):
            foo = fields.String()

        test_schema = TestSchema()
        expected = dedent(
            '''def _dump_function(ser, obj):
                return {
                    "foo": obj.foo
                }
            '''
        )

        assert test_schema._get_dump_function_code() == expected
