<template>
  <div class="post_container" v-html="htmlContent"></div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { marked } from "marked";
const { file_url } = defineProps(["file_url"]);

const htmlContent = ref("");

onMounted(async () => {
  try {
    const response = await fetch(file_url);
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
  height: calc(100vh - 124px);
  overflow-x: hidden;
  width: 600px;
}
img {
  max-width: 600px !important;
}

@media (max-width: 600px) {
  .post_container {
    width: 100vw;
    padding-right: 16px;
    padding-left: 8px;
  }
  img {
    max-width: 90vw !important;
  }
  .post_container img {
    width: 90vw;
  }
  /* .v-img {
    width: 100vw;
  }

  .v-responsive__content img {
    width: 100vw;
  } */
}
</style>
