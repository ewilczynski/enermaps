import {BASE_URL} from './settings.js';

export const WMS_URL = BASE_URL + 'api/wms?';


async function fetchJSON(endpoint, defaultValue) {
  const response = await fetch(BASE_URL + endpoint);

  if (!response.ok) {
    return defaultValue;
  }

  return await response.json();
}


async function fetchText(endpoint, defaultValue) {
  const response = await fetch(BASE_URL + endpoint);

  if (!response.ok) {
    return defaultValue;
  }

  return response.text();
}


// Datasets-related endpoints --------------------------------------------------

export async function getAreas() {
  return fetchJSON('api/datasets/areas/', []);
}


export async function getDatasets() {
  return fetchJSON('api/datasets/', []);
}


export async function getDatasetsWithVariables() {
  return fetchJSON('api/datasets/full/', []);
}


export async function getDatasetParameters(datasetId) {
  return fetchJSON('api/datasets/' + datasetId + '/parameters/', {});
}


export async function getDatasetLayerName(datasetId, raster, variable, timePeriod) {
  const prefix = raster ? 'raster' : 'vector';

  if (variable != null) {
    variable = variable.replaceAll('/', '__SLASH__');
  }

  if ((variable != null) && (timePeriod != null)) {
    return fetchText(
        'api/datasets/layer_name/' + prefix + '/' + datasetId + '/' +
        encodeURIComponent(variable) + '/' + timePeriod + '/',
    );
  } else if (variable != null) {
    return fetchText(
        'api/datasets/layer_name/' + prefix + '/' + datasetId + '/' +
        encodeURIComponent(variable) + '/',
    );
  } else if (timePeriod != null) {
    return fetchText(
        'api/datasets/layer_name/' + prefix + '/' + datasetId + '/-/' +
        timePeriod + '/',
    );
  } else {
    return fetchText('api/datasets/layer_name/' + prefix + '/' + datasetId + '/');
  }
}


export async function getDatasetLayerLegend(layerName) {
  return fetchJSON('api/datasets/legend/' + layerName + '/', {});
}


// Calculation modules-related endpoints ---------------------------------------

export async function getCMs() {
  const response = await fetch(BASE_URL + 'api/cm/');
  if (!response.ok) {
    return [];
  }
  const cmsResponse = await response.json();
  return cmsResponse;
}


export async function postCMTask(cm, parameters) {
  const response = await fetch(BASE_URL + 'api/cm/' + cm.name + '/task/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(parameters),
  });
  const task = await response.json();
  return {'cm': cm, 'id': task.task_id, 'parameters': parameters};
}


export async function getTaskResult(task) {
  const taskResponse = await fetch(
      BASE_URL + 'api/cm/' + task.cm.name + '/task/' + task.id + '/',
  );
  return await taskResponse.json();
}


export async function deleteTaskResult(task) {
  const taskResponse = await fetch(
      BASE_URL + 'api/cm/' + task.cm.name + '/task/' + task.id + '/',
      {
        method: 'DELETE',
      });
  return await taskResponse.json();
}


export async function getTaskDownloadLink(task) {
  const url = BASE_URL + 'api/cm/' + task.cm.name + '/task/' + task.id + '/download/';

  const response = await fetch(
      url,
      {
        method: 'HEAD',
      });

  if (!response.ok) {
    return null;
  }

  return url;
}
