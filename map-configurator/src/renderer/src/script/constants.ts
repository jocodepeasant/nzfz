/** Default ROI ids for new scripts only; runtime list comes from `recognition.rois`. */
export const DEFAULT_ROI_KEYS = [
  'wave',
  'resource',
  'core_hp',
  'map_ui_indicator',
  'place_error_tip'
] as const

export type DefaultRoiKey = (typeof DEFAULT_ROI_KEYS)[number]

/** @deprecated use DEFAULT_ROI_KEYS or listRoiKeys() */
export const ROI_KEYS = DEFAULT_ROI_KEYS
