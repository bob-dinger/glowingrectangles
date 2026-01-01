<template>
  <svg viewBox="0 0 800 800">
    <circle cx="400" cy="400" r="200" fill="blue" stroke="navy" stroke-width="4" />
  </svg>
</template>

<script setup>
import { gsap } from "gsap";

onMounted(() => {
  let tl = gsap.timeline();
});
</script>

<style scoped>
svg {
}
</style>
