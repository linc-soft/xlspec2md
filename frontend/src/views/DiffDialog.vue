<template>
  <div style="display:inline-flex;gap:8px;align-items:center;margin-top:10px">
    <span style="font-size:12px;opacity:.7">版比較:</span>
    <el-select v-model="va" size="small" placeholder="比較元" style="width:90px">
      <el-option v-for="v in versions" :key="v.id" :label="`v${v.version_no}`" :value="v.id" />
    </el-select>
    <span>→</span>
    <el-select v-model="vb" size="small" placeholder="比較先" style="width:90px">
      <el-option v-for="v in versions" :key="v.id" :label="`v${v.version_no}`" :value="v.id" />
    </el-select>
    <el-button size="small" :disabled="!va || !vb || va === vb" :loading="loading" @click="run">
      diff
    </el-button>
    <el-dialog v-model="show" title="版差分（Markdown 産物）" width="80%" top="5vh">
      <el-tabs v-model="cur">
        <el-tab-pane v-for="f in files" :key="f" :label="f" :name="f">
          <div v-if="!diffs[f]" class="diff-empty">差分なし（内容は同一です）</div>
          <div v-else class="diff-view">
            <div v-for="(line, i) in diffs[f].split('\n')" :key="i"
                 class="diff-line" :class="lineClass(line)">{{ line || ' ' }}</div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const props = defineProps({
  doc: { type: Object, required: true },
  versions: { type: Array, default: () => [] }
})

const va = ref(null)
const vb = ref(null)
const show = ref(false)
const cur = ref('')
const files = ref([])
const diffs = ref({})
const loading = ref(false)

// 既定値: 直前版 → 最新版
watch(() => props.versions, (vs) => {
  if (va.value || !vs.length) return
  if (vs.length >= 2) { va.value = vs[1].id; vb.value = vs[0].id }
  else { vb.value = vs[0].id }
})

function lineClass(line) {
  if (line.startsWith('+')) return 'add'
  if (line.startsWith('-')) return 'del'
  if (line.startsWith('@')) return 'hunk'
  return ''
}

async function run() {
  loading.value = true
  try {
    const r = await api.docDiff(props.doc.id, va.value, vb.value)
    files.value = r.files
    diffs.value = r.diffs
    cur.value = r.files[0] || ''
    show.value = true
  } catch (e) { ElMessage.error(String(e)) } finally { loading.value = false }
}
</script>

<style scoped>
.diff-view {
  max-height: 65vh;
  overflow: auto;
  background: #fff;
  border: 1px solid #dcdfe6;
  font-family: Consolas, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
}
.diff-line { white-space: pre-wrap; word-break: break-all; padding: 0 8px; }
.diff-line.add { background: #e6ffed; color: #1a7f37; }
.diff-line.del { background: #ffebe9; color: #cf222e; }
.diff-line.hunk { background: #ddf4ff; color: #0969da; }
.diff-empty { color: #67c23a; padding: 12px 4px; }
</style>
