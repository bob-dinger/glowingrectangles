<template>
  <div id="container">
    <svg viewBox="0 0 800 800">
      <g id="grouper"></g>
    </svg>
  </div>
</template>

<script setup>
// import { useHead } from "#app";

// useHead({
//   script: [
//     {
//       src: "https://raw.githubusercontent.com/bob-dinger/gg_markdown/main/glyfs.js",
//       type: "text/javascript",
//       async: true,
//       defer: true,
//     },
//   ],
// });
import { gsap } from "gsap";
//const { circle, rect } = useGlyfs();
onMounted(() => {
  let points = glyfs.circle_points(400, 400, 100, 8);
  console.log(points);
  //circle:(svg, left, top, radius, fill, stroke, opacity, label, idx)

  let svg = document.querySelector("svg");
  let g = document.querySelector("#grouper");
  points.forEach((point, idx) => {
    glyfs.circle(g, point.x, point.y, 20, "red", "black", 1, "circler", idx);
  });

  //let triangle_path = glyfs.randomTriangle();
  glyfs.path("svg");

  gsap.to("#grouper", {
    duration: 2,
    rotation: 270,
    repeat: 1,
    ease: "none",
    transformOrigin: "center",
  });
});
</script>

<style scoped>
#container {
  width: 610px;
  margin: 0 auto;
  margin-top: 84px;
}
svg {
  height: 600px;
  width: 600px;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
}
</style>
