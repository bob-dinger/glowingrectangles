<template>
  <svg viewBox="0 0 800 800">
    <image
      href="https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/salmon.png"
      width="200"
      height="200"
      x="300"
      y="300"
    />
    <text y="700" x="300" font-size="24">15 minutes in the oven</text>
    <text y="740" x="340" font-size="24">At 425 deg F</text>
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
