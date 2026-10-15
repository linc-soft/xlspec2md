<template>
  <el-container style="min-height:100vh">
    <el-header style="display:flex;align-items:center;background:#2c3e50;color:#fff">
      <h2 style="margin:0;cursor:pointer" @click="view = { name: 'list' }">xlspec2md</h2>
      <span style="margin-left:16px;opacity:.7;font-size:13px">基本設計書 → Markdown 変換プラットフォーム</span>
    </el-header>
    <el-main>
      <ProjectList v-if="view.name === 'list'"
                   @open="openProject" @deleted="refresh" ref="list" />
      <ProjectDetail v-else-if="view.name === 'project'"
                     :project-id="view.id" :key="view.id"
                     @open-build="openBuild" @back="view = { name: 'list' }" />
      <BuildView v-else-if="view.name === 'build'"
                 :build-id="view.id" :key="view.id"
                 @back="openProject(view.pid)" />
    </el-main>
  </el-container>
</template>

<script setup>
import { ref } from 'vue'
import ProjectList from './views/ProjectList.vue'
import ProjectDetail from './views/ProjectDetail.vue'
import BuildView from './views/BuildView.vue'

const view = ref({ name: 'list' })
const list = ref(null)

function openProject(id) { view.value = { name: 'project', id } }
function openBuild(payload) { view.value = { name: 'build', id: payload.id, pid: payload.pid } }
function refresh() { if (list.value) list.value.load() }
</script>
