QUnit.test('Utilities test', function( assert ) {
  // Test Z plane intersection function
  var i1 = CATMAID.tools.intersectLineWithZPlane(-1, 1, 1, 1, 2, 3, 0);
  assert.deepEqual(i1, [-2, 0.5]);

  var i2 = CATMAID.tools.intersectLineWithZPlane(0, 0, 0, 0, 0, 0, 0);
  assert.deepEqual(i2, [NaN, NaN]);
});
