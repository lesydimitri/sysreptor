<template>
  <btn-confirm
    button-text="Export"
    button-icon="mdi-download"
    button-variant="list-item"
    :action="performExport"
    :confirm="false"
  />
</template>

<script setup lang="ts">
import fileDownload from "js-file-download";

const props = withDefaults(defineProps<{
  exportUrl: string;
  name?: string|null;
  extension?: string;
}>(), {
  name: null,
  extension: '.tar.gz',
});

const filename = computed(() => (props.name || 'export').replaceAll(' ', '-') + props.extension);

async function performExport() {
  const res = await $fetch<ArrayBuffer>(props.exportUrl, {
    method: 'POST',
    body: {},
    responseType: "arrayBuffer"
  });
  fileDownload(res, filename.value);
}
</script>
