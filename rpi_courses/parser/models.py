"""models.py - The classes that store the data retrieved by features.py

Generally, all instances should be read only.
"""
from ..utils import safeInt

class ReadOnly(object):
    """All attributes that are prefixed with a single underscore will have
    a equivalent getter property without the underscore prefix.
    
    eg - setting self._foo, allows you to access it publicly using self.foo
    """
    def __getattr__(self, key):
        if not key.endswith('__') and not key.startswith('__'):
            return getattr(self, '_'+key)
        raise AttributeError, '%r has no attribute %r' % (
            self.__class__.__name__,
            key
        )

class CrossListing(ReadOnly):
    """Represents a crosslisted set of CRNs and Seats.
    This is immutable once created.
    """
    def __init__(self, crns, seats):
        self._crns, self._seats = set(crns), seats
    
    def __eq__(self, other):
        return self.crns == other.crns and self.seats == other.seats

MAPPER = {
    0: 'Monday',
    1: 'Tuesday',
    2: 'Wednesday',
    3: 'Thursday',
    4: 'Friday',
}
class Period(ReadOnly):
    def __init__(self, type, instructor, start, end, location, days):
        self._type, self._instructor, self._location = \
            type.strip(), instructor.strip(), location.strip()
        try:
            self._start, self._end = int(start), int(end)
        except ValueError:
            # == '** TBA **'
            self._start = self._end = None
        self._int_days = tuple(map(int, days))
    
    @staticmethod
    def from_soup_tag(tag):
        days = []
        for elem in tag.findAll(recursive=False):
            if elem.name != 'day':
                raise TypeError, "Unknown tag found: "+str(elem)
            days.append(elem.string)
        return Period(
            tag['type'], tag['instructor'], tag['start'], tag['end'],
            tag['location'], days
        )
    
    @property
    def tba(self):
        "The time period hasn't been announced yet."
        return self.start is None or self.end is None
    
    @property
    def is_lecture(self):
        return self.type == 'LEC'
    
    @property
    def is_studio(self):
        return self.type == 'STU'
    
    @property
    def is_lab(self):
        return self.type == 'LAB'
    
    @property
    def is_testing_period(self):
        return self.type == 'TES'
    
    @property
    def is_recitation(self):
        return self.type == 'REC'
    
    @property
    def days(self):
        return tuple(map(MAPPER.get, self.int_days))

class Section(ReadOnly):
    """A section is a particular timeslot to take the given course.
    It is uniquely represented in SIS via CRN. The CRN is used for
    registration.
    """
    def __init__(self, crn, num, taken, total, periods, notes):
        self._crn, self._seats_taken, self._seats_total = \
            safeInt(crn), int(taken), int(total)
        try:
            self._num = int(num)
        except ValueError:
            self._num = num
        self._periods = tuple(periods)
        self._notes = tuple(set(notes))
        
    @staticmethod
    def from_soup_tag(tag):
        "Returns an instance from a given soup tag."
        periods = []
        notes = []
        for elem in tag.findAll(recursive=False):
            if elem.name not in ('period', 'note'):
                raise TypeError, "Unknown tag found: "+str(elem)
            if elem.name == 'note':
                notes.append(elem.string.strip())
            elif elem.name == 'period':
                periods.append(Period.from_soup_tag(elem))
        return Section(
            tag['crn'], tag['num'], tag['students'], tag['seats'],
            periods, notes
        )
        
    @property
    def is_valid(self):
        """Invalid sections have only notes."""
        return type(self.num) in (int, long)

    @property
    def is_filled(self):
        "Returns True if the course is full and not accepting any more seats."
        return self.seats_taken >= self.seats_total

    @property
    def seats_left(self):
        """Returns the number of seats left.
        A negative number indicates more seats taken than are available.
        """
        return self.seats_total - self.seats_taken

    def __eq__(self, other):
        return (
            self.crn == other.crn and self.num == other.num and
            self.periods == other.periods
        )

class Course(ReadOnly):
    """Represents a particular kind of course and its sections.
    Also immutable once created.
    """
    def __init__(self, name, dept, num, credmin, credmax, grade_type, sections):
        self._name, self._dept, self._num, self._cred, self._grade_type = \
            name.strip(), dept.strip(), safeInt(num), \
            (int(credmin), int(credmax)), grade_type.strip()
        self._sections = tuple(sections)

    def __eq__(self, other):
        return (
            self.name == other.name and self.dept == other.dept and
            self.num == other.num and self.cred == other.cred and
            self.grade_type == other.grade_type and
            self.sections == other.sections
        )
    
    def __hash__(self):
        return hash(repr(self))

    def __str__(self):
        return "%(name)s %(dept)s %(num)s" % {
            'name': self.name,
            'dept': self.dept,
            'num': self.num,
        }

    def __repr__(self):
        return "<Course: %(name)r, %(dept)r, %(num)r, %(mincred)r, %(maxcred)r, %(grade_type)r, section_count=%(section_count)s>" % {
            'name': self.name,
            'dept': self.dept,
            'num': self.num,
            'mincred': self.cred[0],
            'maxcred': self.cred[1],
            'grade_type': self.grade_type,
            'section_count': len(self.sections)
        }
        
    @property
    def credits(self):
        """Returns either a tuple representing the credit range or a 
        single integer if the range is set to one value.
        
        Use self.cred to always get the tuple.
        """
        if self.cred[0] == self.cred[1]:
            return self.cred[0]
        return self.cred

    @property
    def is_pass_or_fail(self):
        "Returns True if this course is graded as pass/fail."
        return self.grade_type.lower() == 'satisfactory/unsatisfactory'

    @property
    def code(self):
        "Returns the 'dept num'."
        return u"%s %s" % (self.dept, self.num)

    @staticmethod
    def from_soup_tag(tag):
        "Creates an instance from a given soup tag."
        sections = [Section.from_soup_tag(s) for s in tag.findAll('section')]
        return Course(
            tag['name'], tag['dept'], int(tag['num']), tag['credmin'],
            tag['credmax'], tag['gradetype'], sections
        )