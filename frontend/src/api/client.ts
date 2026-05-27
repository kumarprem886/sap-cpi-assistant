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
