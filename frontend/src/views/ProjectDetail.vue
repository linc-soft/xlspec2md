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
          <el-button type="success" :disabled="!pendingCount"
                     :loading="building" @click="build">変換実行（未変換 {{ pendingCount }} 件）</el-button>
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
          <el-table-column label="状態" width="90">
            <template #default="{ row }">
              <el-tag :type="row.current_converted ? 'success' : 'danger'">
                {{ row.current_converted ? '変換済' : '未変換' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="最新版" width="80" prop="current_version" />
          <el-table-column label="版数" width="70" prop="version_count" />
          <el-table-column label="" width="110">
            <template #default="{ row }">
              <el-button size="small" type="primary" plain
                         :disabled="!row.current_version_id || !!row.current_converted"
                         :loading="buildingDoc === row.id"
                         @click="buildDoc(row)">変換実行</el-button>
            </template>
          </el-table-column>
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

const props = defineProps({ projectId: { type: Number, required: true } })
defineEmits(['back', 'open-build'])

const tab = ref('docs')
const uploadKind = ref('design_book')
const detail = ref(null)
const loading = ref(false)
const building = ref(false)
const buildingDoc = ref(null)

const pendingCount = computed(() =>
  (detail.value?.documents || [])
    .filter(d => d.current_version_id && !d.current_converted).length)

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
    ElMessage.success('アップロードしました（未変換状態で登録されました）')
    await load()
  } catch (e) { ElMessage.error(String(e)) }
}

async function build() {
  const ids = (detail.value?.documents || [])
    .filter(d => d.current_version_id && !d.current_converted)
    .map(d => d.current_version_id)
  if (!ids.length) {
    ElMessage.info('未変換のファイルはありません')
    return
  }
  building.value = true
  try {
    const b = await api.createBuild(props.projectId, ids)
    ElMessage.info(`ビルド #${b.id} を開始しました（未変換 ${ids.length} 件）`)
    await poll(b.id)
  } catch (e) { ElMessage.error(String(e)) } finally { building.value = false }
}

async function buildDoc(row) {
  buildingDoc.value = row.id
  try {
    const b = await api.createBuild(props.projectId, [row.current_version_id])
    ElMessage.info(`ビルド #${b.id} を開始しました: ${row.name}`)
    await poll(b.id)
  } catch (e) { ElMessage.error(String(e)) } finally { buildingDoc.value = null }
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
