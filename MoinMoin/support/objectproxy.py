"""
Dynamic Object Proxy building

Usage:
    x = something
    px = Proxy(x) # px should behave the same as x now (not very useful).

    class MyProxy(Proxy):
        def some_method(self):
            super(self.__class__, self).some_method() # do what x would do
            # Note: you must use self.__class__ not MyProxy for super()
            ... # additionally, do something more than x would do

    x = something
    px = MyProxy(x) # behaves same as x, except when calling some_method

Features:
    * px.__class__ inherits from x.__class__, thus:
      * px is-a x and can be used instead of it
      * super(self.__class__, self).target_method() works
      * if a method defined in target (x) calls some other target method,
        the call will go through the proxy (so you could overwrite it using
        a proxy method of same name)
    * px does NOT inherit from Proxy - this avoids stuff from Proxy (or from
      its base class 'object') getting in the way.
    * If you use MyProxy(target, *args, **kwargs), the arguments will be given
      to MyProxy.__init__(self, *args, **kwargs).
    * If you don't need MyProxy.__init__, we put a dummy __init__ there to
      avoid a call getting forwarded to target's __init__.

Known issues and workarounds:
    * attribute resolution order:
      The proxy_class inherits from target_class and Python will use the
      standard attribute lookup order.
      For example:
      1. instance attributes of proxy
      2. class attributes of proxy
      3. class attributes of target (proxy's base class)
      4. if it still hasn't found the attribute, it will call our __getattr__
         and lookup instance attributes of target.
      
      Workaround: to avoid embarrassment with 3. and 4., avoid having target
                  class attributes with same name as target instance
                  attributes.

@copyright: Thomas Waldmann <tw AT waldmann-edv DOT de>
@license: MIT license
"""

class Proxy(object):
    """
    Dynamically build an object proxy
    """
    def __new__(cls, target, *args, **kwargs):
        target_class = target.__class__
        class_name = "%s(%s)" % (cls.__name__, target_class.__name__)
        # The dynamically created proxy_class (see below) inherits from
        # target_class.
        # Note: We do NOT inherit from (cls, target_class) because cls
        #       inherits from object and thus, object's class attributes
        #       and methods would override target_class' attributes/methods.
        bases = (target_class, )
        # But we want the methods/attributes of cls (this is Proxy or rather
        # some class the user derived from Proxy) nevertheless, thus we
        # patch them into the namespace of the class we build:
        # First, put a dummy __init__ into namespace (we do not want to call
        # target's __init__ if there is not __init__ in cls):
        namespace = dict(__init__= lambda self: None)
        # now add stuff from cls:
        namespace.update(cls.__dict__)
        # and add what we need for proxying:
        namespace.update(dict(
            _pRoXy_TaRgEt=target,
            __getattr__=lambda self, name: getattr(self._pRoXy_TaRgEt, name),
        ))
        # dynamically create the proxy class:
        proxy_class = type(class_name, bases, namespace)
        # Use superclass' __new__, not object.__new__:
        proxy_instance = target_class.__new__(proxy_class)
        # Python does NOT call __init__ for us, because we do NOT return
        # an instance of Proxy (but of proxy_class - it does not even inherit
        # from Proxy [as far as Python knows]):
        proxy_instance.__init__(*args, **kwargs)
        return proxy_instance


if __name__ == '__main__':
    """
    code to demonstrate usage
    """
    class TestBase(object):
        def test_super(self):
            return "TestBase.test_super called"

    class Test(TestBase):
        y = 42
        def __init__(self, x):
            self.x = x
            self.y = 23
        
        def foo(self):
            return "Test.foo %d %d" % (self.x, self.y)

        def bar(self):
            # if this is called via the proxy,
            # it shall call .foo() of the proxy!
            return self.foo() + " Test.bar"

        def test_super(self):
            return super(Test, self).test_super()
        
        def baz(self):
            return "Test.baz called"


    class MyProxy(Proxy):
        def __init__(self, x):
            print "MyProxy.init called with x=%r" % x
            self.x = x

        def foo(self):
            return "MyProxy.foo %d %d" % (self.x, self.y)
        
        def baz(self):
            # can we use super here?
            return "MyProxy.baz + " + super(self.__class__, self).baz()

    t = Test(5)
    p = MyProxy(t, 555)
    
    print t.foo()
    print t.bar()
    print t.test_super()
    print
    print p.foo()
    print p.bar()
    print p.test_super()
    print p.baz()

    print p.x
    p.x += 1
    print p.x

    l = []
    p = MyProxy(l, 123)
    assert not p
    p.append(1)
    assert p == [1]

