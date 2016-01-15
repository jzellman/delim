import codecs

from nose.tools import assert_equals, assert_raises, assert_true

from delim import delim


class Row:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def test_build_csv():
    recs = [Row(full_name="foo", id=1, blah=False),
            Row(full_name="bar", id=2, blah=False),
            Row(full_name="baz", id=3, blah=True)]
    result = delim.build_csv(recs, ['id', 'full_name'])
    assert_equals("Id,Full Name\r\n1,foo\r\n2,bar\r\n3,baz\r\n", result)


def test_validate_csv_unknown_columns():
    data = "Foo,Bar,Baz"
    with assert_raises(delim.CSVError) as cm:
        delim.parse_csv_data(data, [], True)
    assert_true("unkown: Foo, Bar, Baz", cm.exception.message)


def test_validate_csv_empty():
    with assert_raises(delim.CSVError) as cm:
        delim.parse_csv_data("", [])
    assert_equals("CSV appears to be empty", cm.exception.message)


def test_validate_csv_missing_columns():
    with assert_raises(delim.CSVError) as cm:
        fields = [delim.CSVField('Foo'),
                  delim.CSVField('Bar'),
                  delim.CSVField('Baz')]
        delim.parse_csv_data("Foo", fields, True)
    assert_true("missing: Bar, Baz", cm.exception.message)


def test_validate_on_duplicates():
    data = "Name,Bar\n1,2\n1,2"
    fields = [delim.CSVField('Name'), delim.CSVField('Bar')]
    with assert_raises(delim.CSVError) as cm:
        delim.parse_csv_data(data, fields, unique_on="name")
    assert_true("duplicate rows with name: 1", cm.exception.message)


def test_parse_csv_data_no_mappings():
    data = "Name,Bar\n1,2\n3,4"
    results = delim.parse_csv_data(data)
    assert_equals(2, len(results))
    assert_equals("1", results[0]['Name'])
    assert_equals("2", results[0]['Bar'])


def test_parse_csv_data_mappings():
    data = "Name,Bar\n1,2\n3,4"
    fields = [delim.CSVField('Name'), delim.CSVField('Bar')]
    results = delim.parse_csv_data(data, fields)
    assert_equals(2, len(results))
    assert_equals("1", results[0].name)
    assert_equals("2", results[0].bar)


def test_skip_blank_ones():
    data = "Name,Bar\n,,\n\n1,2\n,,\n\n"
    fields = [delim.CSVField('Name'), delim.CSVField('Bar')]
    results = delim.parse_csv_data(data, fields,
                                   skip_if=lambda row: not row.name)
    assert_equals(1, len(results), results)
    assert_equals("1", results[0].name)
    assert_equals("2", results[0].bar)


def test_parse_csv():
    # utf-8
    delim.parse_csv('tests/utf8.csv')
    # iso8859
    delim.parse_csv('tests/win_encoded.csv')


def test_parse_csv_data():
    # utf-8
    with codecs.open('tests/utf8.csv', 'r', 'utf-8') as f:
        delim.parse_csv_data(f.read())
    # iso8859
    with codecs.open('tests/win_encoded.csv', 'r', 'iso8859') as f:
        delim.parse_csv_data(f.read())

    # Open the files naively, much like it was coming from a web server.
    with open('tests/win_encoded.csv', 'r') as f:
        delim.parse_csv_data(f.read())

    with open('tests/utf8.csv', 'r') as f:
        delim.parse_csv_data(f.read())


def test_boolean_csv():
    f = delim.BooleanCSVField('foo', 'foo_type')
    assert_single_csv(f.values_for(' yes '), True)
    assert_single_csv(f.values_for(' YeS '), True)
    assert_single_csv(f.values_for('no'), False)
    assert_single_csv(f.values_for(''), False)
    assert_single_csv(f.values_for(None), False)


def test_percent_csv_field():
    f = delim.PercentCSVField('foo', 'foo_type')
    assert_single_csv(f.values_for('12.8'), 12.8)
    assert_single_csv(f.values_for('12.8%'), 12.8)
    assert_single_csv(f.values_for(''), None)
    assert_single_csv(f.values_for(None), None)


def assert_single_csv(values, expected_value, expected_field_name='foo_type'):
    assert_equals(1, len(values), values)
    computed_field_name, computed_value = values[0]
    assert_csv_field(expected_value, expected_field_name,
                     computed_value, computed_field_name)


def assert_csv_field(expected_value, expected_field_name,
                     computed_value, computed_field_name):
    assert_equals(expected_field_name, computed_field_name)
    assert expected_value == computed_value, "Expected {0} but was {1}".format(
        expected_value, computed_value)


def test_choice_csv():
    f = delim.ChoiceCSVField('Foo Type', 'foo_type',
                             ['Biz', 'Baz'], default='Baz')
    assert_single_csv(f.values_for('  biz '), 'Biz')
    assert_single_csv(f.values_for('BIZ'), 'Biz')
    try:
        f.values_for("blah")
    except ValueError as e:
        assert_equals("Blah is not a valid choice: ['Biz', 'Baz']", e.message)
    assert_single_csv(f.values_for(None), 'Baz')
    assert_single_csv(f.values_for(' '), 'Baz')


def test_int_csv():
    f = delim.IntCSVField('Foo', 'foo_type')
    assert_single_csv(f.values_for(None), None)
    assert_single_csv(f.values_for(""), None)
    assert_single_csv(f.values_for("1"), 1)


def test_float_csv():
    f = delim.FloatCSVField('Foo', 'foo_type')
    assert_single_csv(f.values_for(None), None)
    assert_single_csv(f.values_for(""), None)
    assert_single_csv(f.values_for("1"), 1.0)
    assert_single_csv(f.values_for("1.2"), 1.2)
    assert_single_csv(f.values_for("1,000.2"), 1000.2)
    assert_single_csv(f.values_for("$1,000.20"), 1000.2)


def test_geo_csv():
    def assert_geo(str, exp_lat, exp_lon):
        f = delim.GeoCSVField("location")
        lat, lon = f.values_for(str)
        assert_csv_field("latitude", exp_lat, *lat)
        assert_csv_field("longitude", exp_lon, *lon)

    assert_geo("1,2", 1.0, 2.0)
    assert_geo("", None, None)
    assert_geo(None, None, None)
    assert_geo("1", None, None)


def test_snake_to_title():
    assert_equals("Foo", delim.snake_to_title("foo"))
    assert_equals("Foo Bar", delim.snake_to_title("foo_bar"))
