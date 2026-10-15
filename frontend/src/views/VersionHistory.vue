<template>
  <div>
    <el-popover placement="bottom-start" width="520" trigger="click">
      <template #reference>
        <el-button size="small">履歴 ({{ versions.length }})</el-button>
      </template>
      <el-table :data="versions" size="small" max-height="320">
        <el-table-column prop="version_no" label="版" width="60" />
        <el-table-column prop="filename" label="ファイル名" min-width="180" />
        <el-table-column prop="uploaded_at" label="アップロード日時" width="200" />
      </el-table>
    </el-popover>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const props = defineProps({ doc: { type: Object, required: true } })
const versions = ref([])

onMounted(async () => {
  versions.value = await api.docVersions(props.doc.id)
})
</script>
