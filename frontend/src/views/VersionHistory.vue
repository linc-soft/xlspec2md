<template>
  <div>
    <el-popover placement="bottom-start" width="660" trigger="click">
      <template #reference>
        <el-button size="small">履歴 ({{ versions.length }})</el-button>
      </template>
      <el-table :data="versions" size="small" max-height="300">
        <el-table-column prop="version_no" label="版" width="60" />
        <el-table-column prop="filename" label="ファイル名" min-width="170" />
        <el-table-column label="状態" width="76">
          <template #default="{ row }">
            <el-tag size="small" :type="row.converted ? 'success' : 'danger'">
              {{ row.converted ? '変換済' : '未変換' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="uploaded_at" label="アップロード日時" width="190" />
      </el-table>
      <DiffDialog :doc="doc" :versions="versions" />
    </el-popover>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'
import DiffDialog from './DiffDialog.vue'

const props = defineProps({ doc: { type: Object, required: true } })
const versions = ref([])

onMounted(async () => {
  versions.value = await api.docVersions(props.doc.id)
})
</script>
