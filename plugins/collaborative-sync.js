// ==UserScript==
// @id             iitc-plugin-collaborate@nocarryr
// @name           IITC plugin: Collaborative Sync
// @category       Misc
// @version        0.0.1.@@DATETIMEVERSION@@
// @namespace      https://github.com/jonatkins/ingress-intel-total-conversion
// @updateURL      @@UPDATEURL@@
// @downloadURL    @@DOWNLOADURL@@
// @description    [@@BUILDNAME@@-@@BUILDDATE@@] Sync data between clients via Google Realtime API. Allow sharing certain items with other users.
// @include        https://www.ingress.com/intel*
// @include        http://www.ingress.com/intel*
// @match          https://www.ingress.com/intel*
// @match          http://www.ingress.com/intel*
// @grant          none
// ==/UserScript==

@@PLUGINSTART@@

// PLUGIN START ////////////////////////////////////////////////////////

////////////////////////////////////////////////////////////////////////
// Notice for developers:
//
// You should treat the data stored on Google Realtime API as volatile.
// Because if there are change in Google API client ID, Google will
// treat it as another application and could not access the data created
// by old client ID. Store any important data locally and only use this
// plugin as syncing function.
//
// Google Realtime API reference
// https://developers.google.com/drive/realtime/application
////////////////////////////////////////////////////////////////////////

// use own namespace for plugin
window.plugin.collaborate = function() {};

// add all the things here ;)

var setup = function(){

};
// PLUGIN END //////////////////////////////////////////////////////////

@@PLUGINEND@@
