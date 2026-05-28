import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const iflowAPI = {
  generate: (data: object) => api.post('/iflow/generate', data),
  explain: (xml: string) => api.post('/iflow/explain', { xml }),
  downloadZip: (data: object) =>
    api.post('/iflow/download-zip', data, { responseType: 'blob' }),
  fdToIflow: (fd: File, attachments: File[], name: string, version: string) => {
    const form = new FormData()
    form.append('file', fd)
    attachments.forEach(f => form.append('attachments', f))
    form.append('name', name)
    form.append('version', version)
    return api.post('/iflow/fd-to-iflow', form)
  },
}

export const mappingAPI = {
  generate: (data: object) => api.post('/mapping/generate', data),
  automap: (data: object) => api.post('/mapping/automap', data),
  generateMmap: (data: object) =>
    api.post('/mapping/generate-mmap', data, { responseType: 'blob' }),
  generateMmapAuto: (data: object) =>
    api.post('/mapping/generate-mmap-auto', data, { responseType: 'blob' }),
  catalog: () => api.get('/mapping/catalog'),
  schema: (filename: string) => api.get(`/mapping/schema/${encodeURIComponent(filename)}`),
  prebuiltStatus: () => api.get('/mapping/prebuilt/status'),
  prebuiltGenerate: (pairId: string) => api.post(`/mapping/prebuilt/generate/${encodeURIComponent(pairId)}`),
  prebuiltGenerateAll: () => api.post('/mapping/prebuilt/generate-all'),
  prebuiltDownload: (pairId: string) =>
    api.get(`/mapping/prebuilt/download/${encodeURIComponent(pairId)}`, { responseType: 'blob' }),
  prebuiltPreview: (pairId: string) => api.get(`/mapping/prebuilt/preview/${encodeURIComponent(pairId)}`),
  fromSheet: (sourceXsd: File, targetXsd: File, mappingSheet: File, mappingName: string) => {
    const form = new FormData()
    form.append('source_xsd', sourceXsd)
    form.append('target_xsd', targetXsd)
    form.append('mapping_sheet', mappingSheet)
    form.append('mapping_name', mappingName)
    return api.post('/mapping/from-sheet', form, { responseType: 'blob' })
  },
}

export const groovyAPI = {
  generate: (data: object) => api.post('/groovy/generate', data),
  explain: (script: string) => api.post('/groovy/explain', { script }),
  debug: (data: object) => api.post('/groovy/debug', data),
}

export const xsltAPI = {
  generate: (data: object) => api.post('/xslt/generate', data),
  explain: (xslt: string) => api.post('/xslt/explain', { xslt }),
  fromSamples: (data: object) => api.post('/xslt/from-samples', data),
}

export const chatAPI = {
  ask: (question: string, context?: string) => api.post('/chat/ask', { question, context }),
  review: (data: object) => api.post('/chat/review', data),
}

export const cpiAPI = {
  ping:        ()                            => api.get('/cpi/ping'),
  packages:    ()                            => api.get('/cpi/packages'),
  iflows:      (packageId: string)           => api.get(`/cpi/packages/${encodeURIComponent(packageId)}/iflows`),
  deploy:      (packageId: string, iflowId: string) =>
    api.post(`/cpi/packages/${encodeURIComponent(packageId)}/iflows/${encodeURIComponent(iflowId)}/deploy`),
  messages:    (top = 20, status?: string)   => api.get('/cpi/messages', { params: { top, ...(status ? { status } : {}) } }),
  credentials: ()                            => api.get('/cpi/security/credentials'),
  keystores:   ()                            => api.get('/cpi/security/keystores'),
  importIflow: (data: object)                => api.post('/cpi/import-iflow', data),
}
