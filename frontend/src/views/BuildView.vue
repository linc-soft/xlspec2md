<template>
  <div v-loading="loading">
    <el-page-header @back="$emit('back')" style="margin-bottom:16px">
      <template #content>ビルド #{{ buildId }}</template>
      <template #extra>
        <el-tag :type="statusType(status)">{{ status }}</el-tag>
        <el-button style="margin-left:12px" :disabled="status !== 'done'"
                   @click="downloadZip">zip ダウンロード</el-button>
      </template>
    </el-page-header>

    <el-alert v-if="error" type="error" :title="error" style="margin-bottom:12px" :closable="false" />

    <el-row :gutter="16">
      <el-col :span="7">
        <el-tree :data="treeData" :props="{ label: 'label' }" highlight-current
                 style="border:1px solid #dcdfe6;border-radius:4px;min-height:400px"
                 @node-click="onNode" />
      </el-col>
      <el-col :span="17">
        <template v-if="current">
          <div style="margin-bottom:8px;display:flex;gap:8px;align-items:center">
            <b style="font-size:13px">{{ current }}</b>
            <el-button size="small" @click="downloadFile">ダウンロード</el-button>
          </div>
          <pre v-if="text !== null"
               style="background:#f8f9fa;border:1px solid #e4e7ed;padding:12px;max-height:70vh;
                      overflow:auto;font-size:12px;white-space:pre-wrap">{{ text }}</pre>
          <img v-else-if="isImage" :src="fileUrl" style="max-width:100%;border:1px solid #e4e7ed" />
          <iframe v-else-if="isHtml" :src="fileUrl" style="width:100%;height:70vh;border:1px solid #e4e7ed" />
          <div v-else>プレビュー非対応のファイルです（ダウンロードしてください）</div>
        </template>
        <el-empty v-else description="左のツリーからファイルを選択" />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const props = defineProps({ buildId: { type: Number, required: true } })
defineEmits(['back'])

const status = ref('queued')
const error = ref('')
const files = ref([])
const current = ref('')
const text = ref(null)
const loading = ref(false)

const fileUrl = computed(() => api.buildFileUrl(props.buildId, current.value))
const isImage = computed(() => /\.(png|jpe?g|gif|bmp)$/i.test(current.value))
const isHtml = computed(() => /\.html$/i.test(current.value))

const treeData = computed(() => {
  const root = []
  const dirs = {}
  for (const f of files.value) {
    const parts = f.split('/')
    let level = root
    let acc = ''
    for (let i = 0; i < parts.length - 1; i++) {
      acc = acc ? `${acc}/${parts[i]}` : parts[i]
      if (!dirs[acc]) {
        const node = { label: parts[i], children: [] }
        dirs[acc] = node
        level.push(node)
      }
      level = dirs[acc].children
    }
    level.push({ label: parts[parts.length - 1], path: f })
  }
  return root
})

function statusType(s) {
  return { done: 'success', failed: 'danger', running: 'warning', queued: 'info' }[s] || 'info'
}

async function load() {
  loading.value = true
  try {
    const b = await api.buildStatus(props.buildId)
    status.value = b.status
    error.value = b.error || ''
    if (b.status === 'done') {
      const t = await api.buildTree(props.buildId)
      files.value = t.files
    } else if (b.status === 'queued' || b.status === 'running') {
      setTimeout(load, 800)
    }
  } catch (e) { ElMessage.error(String(e)) } finally { loading.value = false }
}

async function onNode(node) {
  if (!node.path) return
  current.value = node.path
  text.value = null
  if (/\.(md|json|txt)$/i.test(node.path)) {
    try { text.value = await api.buildFile(props.buildId, node.path) } catch (e) { /* noop */ }
  }
}

function downloadZip() { window.open(api.buildZipUrl(props.buildId), '_blank') }
function downloadFile() { window.open(api.buildFileUrl(props.buildId, current.value, true), '_blank') }

onMounted(load)
</script>
