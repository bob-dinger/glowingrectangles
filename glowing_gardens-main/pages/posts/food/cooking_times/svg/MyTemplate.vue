<template>
  <svg viewBox="0 0 800 800">
    <image :href="equipment_image" width="400" height="400" x="200" y="200" />
    <image :href="food_image" width="200" height="200" x="300" y="25" />
    <text y="700" x="260" font-size="24">20 minutes in the oven</text>
    <text y="740" x="300" font-size="24">At 375 deg F</text>
  </svg>
</template>

<script setup>
import { gsap } from "gsap";
//define props
const props = defineProps(["equipment_image", "food_image", "text"]);

onMounted(() => {
  let tl = gsap.timeline();
});
</script>

<style scoped>
svg {
}
</style>
