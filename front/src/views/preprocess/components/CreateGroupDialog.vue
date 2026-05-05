<template>
  <el-dialog :model-value="modelValue" title="创建预处理组" width="420px" @close="$emit('update:modelValue', false)">
    <el-form @submit.prevent>
      <el-form-item label="组名" required>
        <el-input v-model="name" maxlength="255" placeholder="输入一个便于识别的组名" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="loading" :disabled="!name.trim()" @click="submit">创建</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'submit'])

const name = ref('')

watch(() => props.modelValue, (value) => {
  if (value) name.value = ''
})

const submit = () => {
  emit('submit', name.value.trim())
}
</script>
