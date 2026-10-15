<template>
  <div>
    <div style="margin-bottom:16px;display:flex;gap:8px">
      <el-input v-model="newName" placeholder="新規プロジェクト名" style="width:280px"
                @keyup.enter="create" />
      <el-button type="primary" @click="create">作成</el-button>
    </div>
    <el-table :data="projects" v-loading="loading" style="width:100%">
      <el-table-column prop="name" label="プロジェクト名" min-width="200">
        <template #default="{ row }">
          <el-link type="primary" @click="$emit('open', row.id)">{{ row.name }}</el-link>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="作成日" width="220" />
      <el-table-column label="" width="120">
        <template #default="{ row }">
          <el-popconfirm title="削除しますか？（ファイルも全て削除）" @confirm="remove(row)">
            <template #reference><el-button type="danger" size="small">削除</el-button></template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

defineEmits(['open', 'deleted'])
const projects = ref([])
const newName = ref('')
const loading = ref(false)

async function load() {
  loading.value = true
  try { projects.value = await api.listProjects() } finally { loading.value = false }
}
async function create() {
  if (!newName.value.trim()) return
  try {
    await api.createProject(newName.value.trim())
    newName.value = ''
    await load()
  } catch (e) { ElMessage.error(String(e)) }
}
async function remove(row) {
  try {
    await api.deleteProject(row.id)
    await load()
    ElMessage.success('削除しました')
  } catch (e) { ElMessage.error(String(e)) }
}
onMounted(load)
defineExpose({ load })
</script>
