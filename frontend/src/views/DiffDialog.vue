<template>
  <div style="display:inline-flex;gap:8px;align-items:center">
    <span style="font-size:12px;opacity:.7">比較:</span>
    <el-select v-model="other" size="small" placeholder="対象ビルド" style="width:110px">
      <el-option v-for="b in builds.filter(x => x.id !== build.id)" :key="b.id"
                 :label="`#${b.id}`" :value="b.id" />
    </el-select>
    <el-button size="small" :disabled="!other" @click="run">diff</el-button>
    <el-dialog v-model="show" title="Markdown diff" width="80%" top="5vh">
      <el-tabs v-model="cur">
        <el-tab-pane v-for="f in files" :key="f" :label="f" :name="f">
          <pre style="max-height:65vh;overflow:auto;background:#111;color:#eee;padding:12px;
                      font-size:12px;line-height:1.5">{{ diffs[f] }}</pre>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const props = defineProps({
  build: { type: Object, required: true },
  builds: { type: Array, default: () => [] }
})
const emit = defineEmits(['done'])

const other = ref(null)
const show = ref(false)
const cur = ref('')
const files = ref([])
const diffs = ref({})

async function run() {
  try {
    const r = await api.buildDiff(props.build.id, other.value)
    files.value = r.files
    diffs.value = r.diffs
    cur.value = r.files[0] || ''
    show.value = true
    emit('done')
  } catch (e) { ElMessage.error(String(e)) }
}
</script>
