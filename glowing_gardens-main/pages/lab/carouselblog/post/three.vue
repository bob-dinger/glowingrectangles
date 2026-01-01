<template>
  <div class="post_container" v-html="htmlContent"></div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { marked } from "marked";

const htmlContent = ref("");

onMounted(async () => {
  try {
    const response = await fetch(
      "https://glowinggardensstorage.blob.core.windows.net/images/mds/three.md"
    );
    const mdText = await response.text();
    htmlContent.value = marked(mdText);
  } catch (error) {
    console.error("Failed to load markdown file:", error);
  }
});
</script>

<style scoped>
.post_container {
  overflow-y: scroll;
  height: 800px;
  overflow-x: hidden;
}
</style>
