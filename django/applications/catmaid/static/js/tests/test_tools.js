/* -*- mode: espresso; espresso-indent-level: 2; indent-tabs-mode: nil -*- */
/* vim: set softtabstop=2 shiftwidth=2 tabstop=2 expandtab: */

QUnit.test('Utilities test', function( assert ) {

  /**
   * Fake user agent. From:
   * http://stackoverflow.com/questions/1307013
   */
  function setUserAgent(window, userAgent) {
    if (window.navigator.userAgent != userAgent) {
      var userAgentProp = { get: function () { return userAgent; } };
      try {
        Object.defineProperty(window.navigator, 'userAgent', userAgentProp);
      } catch (e) {
        window.navigator = Object.create(navigator, {
          userAgent: userAgentProp
        });
      }
    }
  }


  // Test CATMAID.tools.getOS for Linux
  var originalUserAgent = navigator.userAgent;
  setUserAgent(window, "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36");
  assert.strictEqual(CATMAID.tools.getOS(), "LINUX",
      "CATMAID.tools.getOS recognizes a Linux Chrome user agent");
  setUserAgent(window, "Mozilla/5.0 (X11; Linux i586; rv:31.0) Gecko/20100101 Firefox/31.0");
  assert.strictEqual(CATMAID.tools.getOS(), "LINUX",
      "CATMAID.tools.getOS recognizes a Linux Firefox user agent");
  setUserAgent(window, "Mozilla/5.0 (X11; U; Linux x86_64; en-us) AppleWebKit/531.2+ (KHTML, like Gecko) Version/5.0 Safari/531.2+");
  assert.strictEqual(CATMAID.tools.getOS(), "LINUX",
      "CATMAID.tools.getOS recognizes a Linux Safari user agent");

  // Test CATMAID.tools.getOS for Mac
  setUserAgent(window, "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36");
  assert.strictEqual(CATMAID.tools.getOS(), "MAC",
      "CATMAID.tools.getOS recognizes a MacOS Chrome user agent");
  setUserAgent(window, "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; rv:33.0) Gecko/20100101 Firefox/33.0");
  assert.strictEqual(CATMAID.tools.getOS(), "MAC",
      "CATMAID.tools.getOS recognizes a MacOS Firefox user agent");
  setUserAgent(window, "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A");
  assert.strictEqual(CATMAID.tools.getOS(), "MAC",
      "CATMAID.tools.getOS recognizes a MacOS Safari user agent");

  // Test CATMAID.tools.getOS for Windows
  setUserAgent(window, "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36");
  assert.strictEqual(CATMAID.tools.getOS(), "WIN",
      "CATMAID.tools.getOS recognizes a Windows Chrome user agent");
  setUserAgent(window, "Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0");
  assert.strictEqual(CATMAID.tools.getOS(), "WIN",
      "CATMAID.tools.getOS recognizes a Windows Firefox user agent");
  setUserAgent(window, "Mozilla/5.0 (Windows; U; Windows NT 6.1; tr-TR) AppleWebKit/533.20.25 (KHTML, like Gecko) Version/5.0.4 Safari/533.20.27");
  assert.strictEqual(CATMAID.tools.getOS(), "WIN",
      "CATMAID.tools.getOS recognizes a Windows Safari user agent");

  setUserAgent(window, "No real user agent");
  assert.strictEqual(CATMAID.tools.getOS(), "UNKNOWN",
      "CATMAID.tools.getOS handles unknown user agent");

  // Reset user agent
  setUserAgent(window, originalUserAgent);


  // Test CATMAID.tools.compareStrings
  var stringList = ['Test', 'Value', '4', 'test-90', 'test-87', '5010'];
  stringList.sort(CATMAID.tools.compareStrings);
  // Unfortunately, localeCompare() is implemented differently in PhantomJS <
  // 2.0 from  how all major browsers do it.
  if (-1 === navigator.userAgent.toUpperCase().indexOf('PHANTOMJS')) {
    assert.deepEqual(stringList,
        ['4', '5010', 'Test', 'test-87', 'test-90', 'Value'],
        "CATMAID.tools.compareStrings sorts a list as expected");
  } else {
    assert.deepEqual(stringList,
        ['4', '5010', 'Test', 'Value', 'test-87', 'test-90'],
        "CATMAID.tools.compareStrings sorts a list as expected");
  }


  // Test CATMAID.tools.getIndex
  assert.strictEqual(CATMAID.tools.parseIndex("123"), 123,
      "CATMAID.tools.parseIndex parses \"123\" to 123");
  assert.strictEqual(CATMAID.tools.parseIndex("-123"), 123,
      "CATMAID.tools.parseIndex parses \"-123\" as 123");
  assert.strictEqual(CATMAID.tools.parseIndex(null), false,
      "CATMAID.tools.parseIndex can't parse \"null\"");
  assert.strictEqual(CATMAID.tools.parseIndex("abc"), false,
      "CATMAID.tools.parseIndex can't parse \"abc\"");


  // Test CATMAID.tools.parseQuery
  var url = "?pid=2&zp=5115&yp=3835&xp=0&tool=tracingtool&sid0=5&s0=1";
  var o = {
    pid: "2",
    xp: "0",
    zp: "5115",
    yp: "3835",
    tool: "tracingtool",
    sid0: "5",
    s0: "1"
  };
  var urlObject = CATMAID.tools.parseQuery(url);
  assert.deepEqual(urlObject, o,
      "CATMAID.tools.parseQuery() correctly extracts parameters from URL");


  // Test CATMAID.tools.uniqueId
  var uniqueId1 = CATMAID.tools.uniqueId();
  var uniqueId2 = CATMAID.tools.uniqueId();
  assert.ok(uniqueId1 != uniqueId2,
      "CATMAID.tools.uniqueId retuens different IDs with two calls");


  // Test CATMAID.tools.deepCopy
  var o1 = {
    o2: {
      f3: null,
    },
    f1: 1,
    f2: "test",
  };
  assert.deepEqual(CATMAID.tools.deepCopy(o1), o1,
      "CATMAID.tools.deepEqual can copy nested objects");


  // Test CATMAID.tools.setXYZ
  var o_setXYZ = {x: 2, y: 2, z: 2};
  assert.deepEqual(CATMAID.tools.setXYZ({x: 1, y: 1, z: 1}, 2), o_setXYZ,
      "CATMAID.tools.setXYZ sets all fields as expexted");
  assert.deepEqual(CATMAID.tools.setXYZ({}, 2), o_setXYZ,
      "CATMAID.tools.setXYZ sets all fields of an empty object as expexted");


  // Test CATMAID.tools.isFn
  (function() {
    assert.ok(!CATMAID.tools.isFn(null),
        "CATMAID.tools.isFn says 'null' is no function.");
    assert.ok(!CATMAID.tools.isFn(undefined),
        "CATMAID.tools.isFn says 'undefined' is no function.");
    assert.ok(!CATMAID.tools.isFn({}),
        "CATMAID.tools.isFn says an empty object is no function.");
    assert.ok(CATMAID.tools.isFn(function() {}),
        "CATMAID.tools.isFn says a function is a function.");
  })();


  // Test CATMAID.tools.callIfFn
  (function() {
    var called = false;
    CATMAID.tools.callIfFn(function() { called = true; });
    assert.ok(called, "CATMAID.tools.callIfFn properly calls a function.");
    var o = { called: false };
    CATMAID.tools.callIfFn(function(obj) { obj.called = true; }, o);
    assert.ok(o.called, "CATMAID.tools.callIfFn properly passes arguments to called function.");
  })();
});
