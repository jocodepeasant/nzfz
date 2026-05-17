import type { TowerDefenseScript } from './types'

const ROI_ID_RE = /^[a-z][a-z0-9_]*$/

export function listRoiKeys(script: TowerDefenseScript): string[] {
  return Object.keys(script.recognition.rois).sort()
}

export function isValidRoiId(id: string): boolean {
  return validateRoiId(id) === null
}

export function validateRoiId(id: string): string | null {
  const t = id.trim()
  if (!t) return 'ID 不能为空'
  if (!ROI_ID_RE.test(t)) return 'ID 须为小写字母开头，仅含 a-z、0-9、_'
  return null
}

const ROI_NUM_RE = /^roi_(\d+)$/

/** Next unused id in roi_1, roi_2, … sequence. */
export function nextRoiId(script: TowerDefenseScript): string {
  let max = 0
  for (const key of listRoiKeys(script)) {
    const m = ROI_NUM_RE.exec(key)
    if (m) max = Math.max(max, Number.parseInt(m[1], 10))
  }
  return `roi_${max + 1}`
}

export function resolvePendingRoiId(script: TowerDefenseScript, pending: string): string {
  const t = pending.trim()
  if (!t || validateRoiId(t)) return nextRoiId(script)
  return t
}

export function addRoi(script: TowerDefenseScript, id: string): TowerDefenseScript {
  const key = id.trim()
  if (script.recognition.rois[key]) return script
  return {
    ...script,
    recognition: {
      ...script.recognition,
      rois: {
        ...script.recognition.rois,
        [key]: { x_ratio: 0.1, y_ratio: 0.1, w_ratio: 0.12, h_ratio: 0.05 }
      },
      multi_frame: {
        ...script.recognition.multi_frame,
        [`${key}_frames`]: 3
      }
    }
  }
}

export function removeRoi(script: TowerDefenseScript, key: string): TowerDefenseScript {
  const { [key]: _r, ...rois } = script.recognition.rois
  const mf = { ...script.recognition.multi_frame }
  delete mf[`${key}_frames`]
  delete mf[key]
  const labels = script.recognition.roi_labels
    ? (() => {
        const { [key]: _l, ...rest } = script.recognition.roi_labels!
        return rest
      })()
    : undefined
  return {
    ...script,
    recognition: {
      ...script.recognition,
      rois,
      multi_frame: mf,
      ...(labels && Object.keys(labels).length > 0 ? { roi_labels: labels } : {})
    }
  }
}

export function renameRoi(
  script: TowerDefenseScript,
  oldKey: string,
  newKey: string
): TowerDefenseScript {
  if (oldKey === newKey || !script.recognition.rois[oldKey]) return script
  const rect = script.recognition.rois[oldKey]
  let next = removeRoi(script, oldKey)
  next = addRoi(next, newKey)
  next = {
    ...next,
    recognition: {
      ...next.recognition,
      rois: { ...next.recognition.rois, [newKey]: rect }
    }
  }
  const oldFrames = script.recognition.multi_frame[`${oldKey}_frames`]
  if (oldFrames != null) {
    next.recognition.multi_frame[`${newKey}_frames`] = oldFrames
    delete next.recognition.multi_frame[`${oldKey}_frames`]
  }
  if (script.recognition.roi_labels?.[oldKey]) {
    next.recognition.roi_labels = {
      ...next.recognition.roi_labels,
      [newKey]: script.recognition.roi_labels[oldKey]
    }
    delete next.recognition.roi_labels![oldKey]
  }
  return next
}
