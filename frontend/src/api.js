async function request(url, options = {}) {
  const r = await fetch(url, options)
  if (!r.ok) {
    let detail = r.statusText
    try { detail = (await r.json()).detail || detail } catch (e) { /* noop */ }
    throw new Error(detail)
  }
  const ct = r.headers.get('content-type') || ''
  return ct.includes('json') ? r.json() : r.text()
}

export const api = {
  listProjects: () => request('/api/projects'),
  createProject: (name) => {
    const f = new FormData(); f.append('name', name)
    return request('/api/projects', { method: 'POST', body: f })
  },
  deleteProject: (pid) => request(`/api/projects/${pid}`, { method: 'DELETE' }),
  projectDetail: (pid) => request(`/api/projects/${pid}`),
  uploadDocument: (pid, kind, file) => {
    const f = new FormData(); f.append('kind', kind); f.append('file', file)
    return request(`/api/projects/${pid}/documents`, { method: 'POST', body: f })
  },
  docVersions: (docId) => request(`/api/documents/${docId}/versions`),
  docDiff: (docId, va, vb) => request(`/api/documents/${docId}/diff?va=${va}&vb=${vb}`),
  createBuild: (pid, versionIds = []) => {
    const f = new FormData(); f.append('version_ids', versionIds.join(','))
    return request(`/api/projects/${pid}/builds`, { method: 'POST', body: f })
  },
  buildStatus: (bid) => request(`/api/builds/${bid}`),
  buildTree: (bid) => request(`/api/builds/${bid}/tree`),
  buildFile: (bid, path) => request(`/api/builds/${bid}/file?path=${encodeURIComponent(path)}`),
  buildFileUrl: (bid, path, download = false) =>
    `/api/builds/${bid}/file?path=${encodeURIComponent(path)}${download ? '&download=1' : ''}`,
  buildZipUrl: (bid) => `/api/builds/${bid}/zip`
}
