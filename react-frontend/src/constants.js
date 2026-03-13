/** Pipeline constants. */

export const INITIAL_PIPELINE_STATE = {
  running: false, pipeSteps: {}, pipeStatus: '',
  sql: null, sqlDialect: null,
  detectedDb: null, detectedDialect: null,
  valDetail: null, valDecision: null,
  results: null, resultCols: [], execMetrics: {},
  layerDetails: [], shown: false,
}
