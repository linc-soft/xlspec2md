<template>
  <div v-loading="loading">
    <el-page-header @back="$emit('back')" style="margin-bottom:16px">
      <template #content>{{ detail?.project?.name }}</template>
    </el-page-header>

    <el-tabs v-model="tab">
      <!-- ドキュメント -->
      <el-tab-pane label="ドキュメント" name="docs">
        <div style="margin-bottom:12px;display:flex;gap:8px;align-items:center">
          <el-radio-group v-model="uploadKind">
            <el-radio-button value="design_book">設計書</el-radio-button>
            <el-radio-button value="common_spec">共通仕様書</el-radio-button>
          </el-radio-group>
          <el-upload :show-file-list="false" :auto-upload="false" accept=".xlsx"
                     :on-change="onFileChosen">
            <el-button type="primary">アップロード（新規バージョン）</el-button>
          </el-upload>
          <el-button type="success" :disabled="!detail?.documents?.length"
                     :loading="building" @click="build">変換実行</el-button>
        </div>

        <el-table :data="detail?.documents || []" row-key="id">
          <el-table-column prop="kind" label="種別" width="130">
            <template #default="{ row }">
              <el-tag :type="row.kind === 'common_spec' ? 'warning' : 'info'">
                {{ row.kind === 'common_spec' ? '共通仕様書' : '設計書' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="ファイル" min-width="220" />
          <el-table-column label="最新版" width="80" prop="current_version" />
          <el-table-column label="版数" width="70" prop="version_count" />
          <el-table-column label="バージョン履歴" min-width="380">
            <template #default="{ row }">
              <VersionHistory :doc="row" />
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 変換履歴 -->
      <el-tab-pane label="変換履歴" name="builds">
        <el-table :data="detail?.builds || []">
          <el-table-column prop="id" label="Build" width="80">
            <template #default="{ row }">
              <el-link type="primary" @click="$emit('open-build', { id: row.id, pid: projectId })">
                #{{ row.id }}
              </el-link>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状態" width="110">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="triggered_at" label="実行日時" width="220" />
          <el-table-column prop="error" label="エラー" min-width="200" />
          <el-table-column label="" width="200">
            <template #default="{ row }">
              <DiffDialog v-if="row.status === 'done'" :build="row"
                          :builds="doneBuilds" @done="load" />
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import VersionHistory from './VersionHistory.vue'
import DiffDialog from './DiffDialog.vue'

const props = defineProps({ projectId: { type: Number, required: true } })
defineEmits(['back', 'open-build'])

const tab = ref('docs')
const uploadKind = ref('design_book')
const detail = ref(null)
const loading = ref(false)
const building = ref(false)

const doneBuilds = computed(() =>
  (detail.value?.builds || []).filter(b => b.status === 'done'))

function statusType(s) {
  return { done: 'success', failed: 'danger', running: 'warning', queued: 'info' }[s] || 'info'
}

async function load() {
  loading.value = true
  try { detail.value = await api.projectDetail(props.projectId) } finally { loading.value = false }
}

async function onFileChosen(file) {
  try {
    await api.uploadDocument(props.projectId, uploadKind.value, file.raw)
    ElMessage.success('アップロードしました')
    await load()
  } catch (e) { ElMessage.error(String(e)) }
}

async function build() {
  building.value = true
  try {
    const b = await api.createBuild(props.projectId)
    ElMessage.info(`ビルド #${b.id} を開始しました`)
    await poll(b.id)
  } catch (e) { ElMessage.error(String(e)) } finally { building.value = false }
}

async function poll(bid) {
  for (;;) {
    const b = await api.buildStatus(bid)
    if (b.status === 'done') { ElMessage.success(`ビルド #${bid} 完了`); break }
    if (b.status === 'failed') { ElMessage.error(`ビルド #${bid} 失敗: ${b.error}`); break }
    await new Promise(r => setTimeout(r, 800))
  }
  await load()
}

onMounted(load)
</script>
