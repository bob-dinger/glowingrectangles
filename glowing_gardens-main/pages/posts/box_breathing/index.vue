<template>
  <Navbar />
  <div id="container" :style="`width:${container_width};margin-top:84px;`">
    <svg :height="container_width" :width="container_width">
      <rect
        id="recter"
        :x="box_offset"
        :y="box_offset"
        :width="box_width"
        :height="box_width"
        fill="white"
        stroke="navy"
      />
    </svg>
  </div>
</template>

<script setup>
import { gsap } from "gsap";
let container_width = ref(600);
let svg_width = ref(600);
let box_width = ref(200);
let box_offset = ref(200);
import { useDisplay } from "vuetify";
const { mdAndDown } = useDisplay();

onMounted(() => {
  if (mdAndDown.value) {
    container_width.value = window.innerWidth - 24;
    svg_width.value = window.innerWidth - 24;
    box_width.value = window.innerWidth / 3;
    box_offset.value = svg_width.value / 2 - box_width.value / 2;
  } else {
    container_width.value = 600;
  }
  let intro = gsap.timeline({
    repeat: -1, // Repeat the timeline indefinitely
    repeatRefresh: true, // Uncomment if you need to refresh starting values on each repeat
  });
  intro.to("#recter", {
    duration: 4,
    scale: 2,
    transformOrigin: "center",
    fill: "blue",
    ease: "none",
  });
  intro.to("#recter", { duration: 0.5, fill: "red", ease: "none" });
  intro.to("#recter", { duration: 3.5, fill: "red", ease: "none" });
  //intro.to("#recter", { duration: 0.01, fill: "green" });
  intro.to("#recter", {
    duration: 4,
    scale: 1,
    transformOrigin: "center",
    fill: "white",
    ease: "none",
  });
  intro.to("#recter", { duration: 4, fill: "white", ease: "none" });
  //intro.to("#recter", { duration: 4, fill: "white" });
});
</script>

<style scoped>
svg {
  border: 1px solid navy;
}
#container {
  margin: 0 auto;
}
</style>
