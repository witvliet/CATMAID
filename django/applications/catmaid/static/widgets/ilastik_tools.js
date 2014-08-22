/* -*- mode: espresso; espresso-indent-level: 2; indent-tabs-mode: nil -*- */
/* vim: set softtabstop=2 shiftwidth=2 tabstop=2 expandtab: */

"use strict";

function IlastikTools() {
  this.widgetID = this.registerInstance();
  this.positions = [];
  this.$data_container = null;
};

IlastikTools.prototype = {};
$.extend(IlastikTools.prototype, new InstanceRegistry());

IlastikTools.prototype.init = function(container) {
  var $container = $(container);

  // Check for the various File API support.
  if (!(window.File && window.FileReader && window.FileList && window.Blob)) {
    $container.text('The File APIs are not fully supported in this browser.');
    return;
  }

  // Add form elements for user input
  var fileInput = $('<input />').attr('type', 'file');
  $container.append(fileInput);

  fileInput.on('change', (function(evt) {
    var files = evt.target.files;
    for (var i=0, f; f=files[i]; ++i) {
      this.addFile(f);
    }
  }).bind(this));

  this.$data_container = $('<div />');
  $container.append(this.$data_container);
};

/**
 * Reads a file from a file object and tries to parse it as CSV file generated
 * by Ilastik.
 */
IlastikTools.prototype.addFile = function(file) {
  if (!file) {
    return;
  }

  // Only process text files
  if (!file.type.match('text.*')) {
    alert('Please provide a valid text file!');
    return;
  }

  // Helper to check if an array (CSV line) has five elements
  function not_five_elements(line) {
    return 5 !== line.length;
  }

  var reader = new FileReader();

  reader.onload = (function(e) {
    // Try to parse content as CSV
    var csv = $.csv.toArrays(e.target.result, {separator: '\t'});
    if (csv && csv.length > 0) {
      this.positions = [];
      if (csv.some(not_five_elements)) {
        alert('Not all lines of the CSV file have five elements!');
      } else {
        this.positions = csv;
      }
    } else {
      alert('No data to import!');
    }
    this.update_ui();
  }).bind(this);

  reader.readAsText(file);
};

/**
 * Recreates the user interface.
 */
IlastikTools.prototype.update_ui = function() {
  this.$data_container.empty();

  // Add resolution input fields
  var xRes = $('<input />').attr('type', 'text').val('4.0');
  var yRes = $('<input />').attr('type', 'text').val('4.0');
  var zRes = $('<input />').attr('type', 'text').val('45.0');
  this.$data_container
      .append($('<label />').text('X resolution:').append(xRes))
      .append($('<label />').text('Y resolution:').append(yRes))
      .append($('<label />').text('Z resolution:').append(zRes));

  // Add result table
  this.$data_container.append('<table cellpadding="0" cellspacing="0" ' +
      'border="0" class="display" id="ilastik_result' + this.widgetID +
      '"></table>' );

  var table = $('#ilastik_result' + this.widgetID).dataTable({
    "aaData": this.positions,
    "aoColumns": [
      { "sTitle": "Index" },
      { "sTitle": "X" },
      { "sTitle": "Y" },
      { "sTitle": "Z" },
      { "sTitle": "Value" }
    ]
  });

  // Double-clicking on a row jumps to position
  $('#ilastik_result' + this.widgetID).on('dblclick', 'td', function() {
    var tr = this.parentNode;
    var data = [];
    $(this).parent().find('td').each(function() {
      data.push($(this).html());
    });
    // Expect coordinates in 2., 3. and 4. column. These coordinates are in
    // stack coordinats (of the stack where synapses where searched for in) and
    // have to be converted to project space.
    var x = parseFloat(data[1]) * parseFloat(xRes.val());
    var y = parseFloat(data[2]) * parseFloat(yRes.val());
    var z = parseFloat(data[3]) * parseFloat(zRes.val());
    project.moveTo(z, y, x);
  });
};
