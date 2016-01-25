import io
import codecs
import csv
import cStringIO

from collections import Counter

try:
    import web
    store = web.storage
except:
    # borrowed from web.py storage class
    class store(dict):
        def __getattr__(self, key):
            try:
                return self[key]
            except KeyError as k:
                raise AttributeError(k)

        def __setattr__(self, key, value):
            self[key] = value

        def __delattr__(self, key):
            try:
                del self[key]
            except KeyError as k:
                raise AttributeError(k)

        def __repr__(self):
            return '<store ' + dict.__repr__(self) + '>'


class CSVField(object):
    def __init__(self, csv_name, name=None, value_fun=None, **kwargs):
        self.csv_name = csv_name
        self.name = name or csv_name.lower().replace(" ", "_")
        self.value_fun = value_fun if value_fun else lambda v: v
        self.kwargs = kwargs

    def values_for(self, v):
        value = self.value_fun(v)
        if isinstance(value, (basestring, unicode)):
            value = value.strip()
        return [(self.name, value)]


class BooleanCSVField(CSVField):
    def __init__(self, csv_name, name=None):
        value_fun = lambda v: False if not v else v.strip().lower() == 'yes'
        super(BooleanCSVField, self).__init__(csv_name, name, value_fun)


class ChoiceCSVField(CSVField):
    def __init__(self, csv_name, name=None, choices=None, default=None):
        self.choices = choices
        self.default = default
        super(ChoiceCSVField, self).__init__(csv_name, name)

    def values_for(self, v):
        v = v.strip().title() if v else v
        if not v and self.default:
            v = self.default
        if self.choices and v not in self.choices:
            raise ValueError("{0} is not a valid choice: {1}".format(
                v, self.choices))
        return [(self.name, v)]


def num_parse(fun, *to_strip):
    def parse(v):
        v = v or ""
        for char in to_strip:
            v = v.replace(char, "")
        return fun(v) if v else None
    return parse


class IntCSVField(CSVField):
    def __init__(self, csv_name, name=None):
        parser = num_parse(int, ",", "$")
        super(IntCSVField, self).__init__(csv_name, name, parser)


class FloatCSVField(CSVField):
    def __init__(self, csv_name, name=None):
        parser = num_parse(float, ",", "%", "$")
        super(FloatCSVField, self).__init__(csv_name, name, parser)


class PercentCSVField(FloatCSVField):
    pass


class GeoCSVField(CSVField):
    def __init__(self, csv_name):
        self.csv_name = csv_name

    def values_for(self, v):
        values = [None, None]
        if v:
            parts = v.split(",")
            if len(parts) > 1:
                values = [float(f) for f in parts]
        return zip(['latitude', 'longitude'], values)


def unicode_csv_reader(file, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    data = utf_8_encoder(file)
    csv_reader = csv.reader(data, dialect=dialect, **kwargs)

    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, 'utf-8') for cell in row]


def utf_8_encoder(file):
    lines = file.read().splitlines()
    return [line.encode('utf-8') for line in lines]


def _load_csv(file):
    rows = unicode_csv_reader(file)
    rows = [[v.strip() for v in row] for row in rows]
    if not rows:
        raise CSVError("CSV appears to be empty")
    header = rows.pop(0)
    return header, [zip(header, row) for row in rows]


class CSVError(StandardError):
    pass


def _validate_header(expected_header, included_header):
    def format_message(detail, header_names):
        joined = ", ".join(header_names)
        if joined:
            return "The following columns are %s: %s. " % (detail, joined)
        else:
            return ""

    expected_header = set(expected_header)
    included_header = set(included_header)

    msg = format_message("missing", expected_header - included_header)
    msg += format_message("unknown", included_header - expected_header)
    if msg:
        raise CSVError("Invalid CSV File: " + msg)


def _parse_csv(file, csv_mappings=None, validate=False, **kwargs):
    header, rows = _load_csv(file)
    if validate:
        _validate_header([c.csv_name for c in csv_mappings], header)

    if not csv_mappings:
        results = rows
    else:
        results = []
        for row in rows:
            row = dict(row)
            attributes = []
            for csv_mapping in csv_mappings:
                raw_value = row.get(csv_mapping.csv_name)
                attributes += csv_mapping.values_for(raw_value)
            record = store(dict(attributes))
            results.append(record)

    skip_if = kwargs.get("skip_if", None)
    if skip_if:
        results = [r for r in results if not skip_if(r)]

    unique_field = kwargs.get("unique_on", None)
    if unique_field:
        values = [getattr(r, unique_field) for r in results]
        dups = [key for key, value in Counter(values).items() if value > 1]
        if dups:
            message = u"Invalid CSV File: duplicate rows with {0}: {1}".format(
                unique_field, ", ".join(dups))
            raise CSVError(message)

    return results


def parse_csv_data(data, csv_mappings=None, validate=False, **kwargs):
    try:
        encoded = data if isinstance(data, unicode) else unicode(data)
    except UnicodeDecodeError:
        encoded = unicode(data, "iso8859")

    f = io.StringIO(encoded)
    return _parse_csv(f, csv_mappings, validate, **kwargs)


def parse_csv(filepath, csv_mappings=None, validate=False, **kwargs):
    def parse_and_encode(encoding):
        with codecs.open(filepath, 'r', encoding) as f:
            return _parse_csv(f, csv_mappings, validate, **kwargs)
    try:
        return parse_and_encode('utf-8')
    except UnicodeDecodeError:
        return parse_and_encode("iso8859")


def snake_to_title(w):
    return u" ".join(p.title() for p in w.split("_"))


def build_csv(recs, fields=None):
    def enc(d):
        try:
            return unicode(d).encode('utf-8')
        except UnicodeDecodeError:
            return unicode(d, 'iso8859').encode('utf-8')

    import cStringIO
    import csv
    if fields:
        header = [snake_to_title(field) for field in fields]
        recs = [[getattr(rec, field) for field in fields] for rec in recs]
        recs = [header] + recs

    f = cStringIO.StringIO()
    writer = csv.writer(f)
    for row in recs:
        row = [enc(v) for v in row]
        writer.writerow(row)
    f.seek(0)
    return f.read()
