import 'leaflet-draw/dist/leaflet.draw.js';
import 'leaflet-draw/dist/leaflet.draw.css';

import {get} from 'svelte/store';
import {areaSelectionLayerStore} from '../stores.js';


L.DrawingLayer = L.FeatureGroup.extend({
  onRemove: function(map) {
    this.panel.removeSelectionControls();
    this.drawControl.remove();
    this.clearLayers();
  },

  onAdd: function(map) {
    const drawPluginOptions = {
      // position: 'topleft',
      draw: {
        polygon: {
          allowIntersection: true,
          shapeOptions: {
            color: '#4d88c7',
          },
        },
        polyline: false,
        circlemarker: false,
        marker: false,
        rectangle: false,
        circle: false,
      },
      edit: {
        featureGroup: this, // REQUIRED!!
        remove: true,
      },
    };

    // Initialise the draw control and send it to the panel that must contain it
    this.drawControl = new L.Control.Draw(drawPluginOptions);

    const container = this.drawControl.onAdd(map);
    this.panel.addSelectionControls(container);

    map.on(L.Draw.Event.CREATED, L.Util.bind(this.drawCreated, this));
    map.on(L.Draw.Event.DELETED, L.Util.bind(this.drawDeleted, this));
  },

  getSelection: function() {
    return this.toGeoJSON();
  },

  drawCreated: function(e) {
    const layer = e.layer;
    this.addLayer(layer);

    const areaSelectionLayer = get(areaSelectionLayerStore);
    areaSelectionLayerStore.set(areaSelectionLayer);
  },

  drawDeleted: function(e) {
    const areaSelectionLayer = get(areaSelectionLayerStore);
    areaSelectionLayerStore.set(areaSelectionLayer);
  },
});
