import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const authAPI = {
  login:          (email: string, password: string)  => api.post('/auth/login', { email, password }),
  register:       (data: object)                      => api.post('/auth/register', data),
  me:             ()                                  => api.get('/auth/me'),
  updateMe:       (data: object)                      => api.put('/auth/me', data),
  changePassword: (data: object)                      => api.post('/auth/change-password', data),
}

export const usersAPI = {
  list:          ()                                   => api.get('/users'),
  create:        (data: object)                       => api.post('/users', data),
  update:        (id: string, data: object)           => api.put(`/users/${id}`, data),
  resetPassword: (id: string, newPassword: string)   => api.post(`/users/${id}/reset-password`, { new_password: newPassword }),
  delete:        (id: string)                         => api.delete(`/users/${id}`),
}

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
  extractXml: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/iflow/extract-xml', form)
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
  template: () =>
    api.get('/mapping/template', { responseType: 'blob' }),
  previewSheet: (sourceXsd: File, targetXsd: File, mappingSheet: File) => {
    const form = new FormData()
    form.append('source_xsd', sourceXsd)
    form.append('target_xsd', targetXsd)
    form.append('mapping_sheet', mappingSheet)
    return api.post('/mapping/preview-sheet', form)
  },
  deriveRules: (rows: object[]) => api.post('/mapping/derive-rules', { rows }),
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

export const settingsAPI = {
  getAI:  ()             => api.get('/settings/ai'),
  saveAI: (data: object) => api.put('/settings/ai', data),
}

export const cpiAPI = {
  ping:              ()                            => api.get('/cpi/ping'),
  getSettings:       ()                            => api.get('/cpi/settings'),
  saveSettings:      (data: object)                => api.put('/cpi/settings', data),

  // ── Packages ────────────────────────────────────────────────────────────────
  packages:          ()                            => api.get('/cpi/packages'),
  createPackage:     (name: string, desc: string)  => api.post('/cpi/packages', { name, description: desc }),
  updatePackage:     (id: string, name: string, desc: string) => api.put(`/cpi/packages/${encodeURIComponent(id)}`, { name, description: desc }),
  deletePackage:     (id: string)                  => api.delete(`/cpi/packages/${encodeURIComponent(id)}`),

  // ── Artifacts ───────────────────────────────────────────────────────────────
  iflows:            (pkgId: string)               => api.get(`/cpi/packages/${encodeURIComponent(pkgId)}/iflows`),
  allArtifacts:      (pkgId: string)               => api.get(`/cpi/packages/${encodeURIComponent(pkgId)}/all-artifacts`),
  exportIflow:       (pkgId: string, id: string)   =>
    api.get(`/cpi/packages/${encodeURIComponent(pkgId)}/iflows/${encodeURIComponent(id)}/export`, { responseType: 'blob' }),
  deleteIflow:       (pkgId: string, id: string)   =>
    api.delete(`/cpi/packages/${encodeURIComponent(pkgId)}/iflows/${encodeURIComponent(id)}`),
  copyIflow:         (sourceId: string, targetPkgId: string, newName?: string) =>
    api.post('/cpi/copy-iflow', { source_id: sourceId, target_package_id: targetPkgId, new_name: newName }),
  deployAll:         (pkgId: string)               => api.post(`/cpi/packages/${encodeURIComponent(pkgId)}/deploy-all`),

  // ── Externalized Parameters ─────────────────────────────────────────────────
  configurations:    (iflowId: string)             => api.get(`/cpi/iflows/${encodeURIComponent(iflowId)}/configurations`),
  updateConfig:      (iflowId: string, key: string, value: string) =>
    api.put(`/cpi/iflows/${encodeURIComponent(iflowId)}/configurations/${encodeURIComponent(key)}`, { value }),

  // ── Deploy / Undeploy ───────────────────────────────────────────────────────
  deploy:            (pkgId: string, id: string)   =>
    api.post(`/cpi/packages/${encodeURIComponent(pkgId)}/iflows/${encodeURIComponent(id)}/deploy`),
  runtimeStatus:     ()                            => api.get('/cpi/runtime'),
  runtimeIflowStatus:(id: string)                  => api.get(`/cpi/runtime/${encodeURIComponent(id)}/status`),
  undeploy:          (id: string)                  => api.delete(`/cpi/runtime/${encodeURIComponent(id)}`),

  // ── Messages ────────────────────────────────────────────────────────────────
  messages:          (top = 50, status?: string)   =>
    api.get('/cpi/messages', { params: { top, ...(status ? { status } : {}) } }),
  messageError:      (guid: string)                => api.get(`/cpi/messages/${encodeURIComponent(guid)}/error`),
  messageRuns:       (guid: string)                => api.get(`/cpi/messages/${encodeURIComponent(guid)}/runs`),
  messageAttachments:(guid: string)                => api.get(`/cpi/messages/${encodeURIComponent(guid)}/attachments`),
  messageStoreEntries:(top = 20)                   => api.get('/cpi/message-store-entries', { params: { top } }),

  // ── Security ────────────────────────────────────────────────────────────────
  credentials:       ()                            => api.get('/cpi/security/credentials'),
  keystores:         ()                            => api.get('/cpi/security/keystores'),
  secureParameters:  ()                            => api.get('/cpi/security/secure-parameters'),
  oauthCredentials:  ()                            => api.get('/cpi/security/oauth-credentials'),
  certMappings:      ()                            => api.get('/cpi/security/certificate-mappings'),
  numberRanges:      ()                            => api.get('/cpi/number-ranges'),
  logFiles:          ()                            => api.get('/cpi/log-files'),

  // ── Data Stores ─────────────────────────────────────────────────────────────
  datastores:        ()                            => api.get('/cpi/datastores'),
  datastoreEntries:  (name: string, top = 50)      =>
    api.get(`/cpi/datastores/${encodeURIComponent(name)}/entries`, { params: { top } }),
  deleteDatastoreEntry:(name: string, entryId: string) =>
    api.delete(`/cpi/datastores/${encodeURIComponent(name)}/entries/${encodeURIComponent(entryId)}`),

  // ── Import ──────────────────────────────────────────────────────────────────
  importIflow: (data: object) => api.post('/cpi/import-iflow', data),
  importZip: (file: File, packageId: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('package_id', packageId)
    return api.post('/cpi/import-zip', form)
  },

  // ── Variables (runtime iFlow string parameters) ──────────────────────────────
  variables:                ()                                    => api.get('/cpi/variables'),
  deleteVariable:           (iflowId: string, name: string)       => api.delete(`/cpi/variables/${encodeURIComponent(iflowId)}/${encodeURIComponent(name)}`),

  // ── Tenant Configurations (global string parameters) ─────────────────────────
  tenantConfigurations:     ()                                    => api.get('/cpi/tenant-configurations'),
  updateTenantConfig:       (key: string, value: string)          => api.put(`/cpi/tenant-configurations/${encodeURIComponent(key)}`, { value }),

  // ── Build & Deploy Status ─────────────────────────────────────────────────────
  deployStatus:             (taskId: string)                      => api.get(`/cpi/deploy-status/${encodeURIComponent(taskId)}`),

  // ── Message Adapter Attributes ───────────────────────────────────────────────
  messageAdapterAttributes: (guid: string)                        => api.get(`/cpi/messages/${encodeURIComponent(guid)}/adapter-attributes`),

  // ── Log file download ─────────────────────────────────────────────────────────
  downloadLogFile:          (application: string)                 => api.get(`/cpi/log-files/${encodeURIComponent(application)}/download`, { responseType: 'blob' }),

  // ── Payload downloads ─────────────────────────────────────────────────────────
  datastoreEntryPayload:    (store: string, entryId: string)      => api.get(`/cpi/datastores/${encodeURIComponent(store)}/entries/${encodeURIComponent(entryId)}/payload`, { responseType: 'blob' }),
  messageStoreEntryPayload: (entryId: string)                     => api.get(`/cpi/message-store-entries/${encodeURIComponent(entryId)}/payload`, { responseType: 'blob' }),
  messageStoreEntryAttachments: (entryId: string)                 => api.get(`/cpi/message-store-entries/${encodeURIComponent(entryId)}/attachments`),
  messageStoreAttachmentPayload:(entryId: string, attachId: string) => api.get(`/cpi/message-store-entries/${encodeURIComponent(entryId)}/attachments/${encodeURIComponent(attachId)}/payload`, { responseType: 'blob' }),

  // ── Security CRUD ─────────────────────────────────────────────────────────────
  createCredential:         (data: object)                        => api.post('/cpi/security/credentials', data),
  updateCredential:         (name: string, data: object)          => api.put(`/cpi/security/credentials/${encodeURIComponent(name)}`, data),
  deleteCredential:         (name: string)                        => api.delete(`/cpi/security/credentials/${encodeURIComponent(name)}`),

  createSecureParameter:    (data: object)                        => api.post('/cpi/security/secure-parameters', data),
  updateSecureParameter:    (name: string, data: object)          => api.put(`/cpi/security/secure-parameters/${encodeURIComponent(name)}`, data),
  deleteSecureParameter:    (name: string)                        => api.delete(`/cpi/security/secure-parameters/${encodeURIComponent(name)}`),

  createOAuthCredential:    (data: object)                        => api.post('/cpi/security/oauth-credentials', data),
  deleteOAuthCredential:    (name: string)                        => api.delete(`/cpi/security/oauth-credentials/${encodeURIComponent(name)}`),

  createNumberRange:        (data: object)                        => api.post('/cpi/security/number-ranges', data),
  updateNumberRange:        (name: string, data: object)          => api.put(`/cpi/security/number-ranges/${encodeURIComponent(name)}`, data),
  deleteNumberRange:        (name: string)                        => api.delete(`/cpi/security/number-ranges/${encodeURIComponent(name)}`),

  // ── Access Policies ───────────────────────────────────────────────────────────
  accessPolicies:           ()                                    => api.get('/cpi/access-policies'),
  createAccessPolicy:       (data: object)                        => api.post('/cpi/access-policies', data),
  deleteAccessPolicy:       (id: string)                          => api.delete(`/cpi/access-policies/${encodeURIComponent(id)}`),
  accessPolicyReferences:   (id: string)                          => api.get(`/cpi/access-policies/${encodeURIComponent(id)}/references`),

  // ── JMS Brokers ───────────────────────────────────────────────────────────────
  jmsBrokers:               ()                                    => api.get('/cpi/jms-brokers'),

  // ── ID Mapper ─────────────────────────────────────────────────────────────────
  idMaps:                   (agency?: string, scheme?: string)    => api.get('/cpi/id-maps', { params: { ...(agency ? { agency } : {}), ...(scheme ? { scheme } : {}) } }),
  deleteIdMap:              (id: string)                          => api.delete(`/cpi/id-maps/${encodeURIComponent(id)}`),
}
