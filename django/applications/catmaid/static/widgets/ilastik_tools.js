/* -*- mode: espresso; espresso-indent-level: 2; indent-tabs-mode: nil -*- */
/* vim: set softtabstop=2 shiftwidth=2 tabstop=2 expandtab: */

"use strict";

function IlastikTools() {
  this.widgetID = this.registerInstance();
};

IlastikTools.prototype = {};
$.extend(IlastikTools.prototype, new InstanceRegistry());

IlastikTools.prototype.init = function(container) {
  
}
