<template>
  <div id="phenotype_div">
    acgtacgtagtcgtcccgtagctagtcgtgctagctagatcgatcgatgtgtcacacaacagtgtgtgtcagctagctagctagtagctagcatgtgtgttttgatgctagtca
  </div>
</template>

<script setup>
onMounted(() => {
  console.log("mounted");
});
</script>

<style scoped>
#phenotype_div {
  width: 600px;
  border: 1px solid navy;
  overflow-wrap: break-word;
}
</style>
