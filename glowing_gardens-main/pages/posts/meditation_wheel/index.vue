<template>
  <Navbar />
  <div id="container">
    <svg id="circleSvg" viewBox="0 0 600 600">
      <g id="slices"></g>
    </svg>

    <div class="d-flex justify-center ma-4">
      <v-btn @click="animate">Play</v-btn>
    </div>
    <div class="d-flex justify-center">
      Our minds try to focus on breathing, the center two slices, but our thoughts are
      always justting back and forth between work, kids, and other things. In meditation
      you try to always go back to the center, breathing whenever this happens.
    </div>
  </div>
</template>

<script setup>
import { gsap } from "gsap";
//wheel with 16 slices going around and jutting back and forth'
//2 slices in front are blue and focus on breathing
//always trying to get back there

const addSlicesToCircle = (svgId, slices, radius) => {
  const svg = document.getElementById(svgId);
  const centerX = 300; // SVG width / 2
  const centerY = 300; // SVG height / 2
  const angleStep = 360 / slices;

  for (let i = 0; i < slices; i++) {
    const startAngle = (angleStep * i * Math.PI) / 180;
    const endAngle = (angleStep * (i + 1) * Math.PI) / 180;

    const x1 = centerX + radius * Math.cos(startAngle);
    const y1 = centerY + radius * Math.sin(startAngle);
    const x2 = centerX + radius * Math.cos(endAngle);
    const y2 = centerY + radius * Math.sin(endAngle);

    // Create a path for the slice
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    const d = [
      "M",
      centerX,
      centerY,
      "L",
      x1,
      y1,
      "A",
      radius,
      radius,
      0,
      0,
      1,
      x2,
      y2,
      "Z",
    ].join(" ");

    path.setAttribute("d", d);
    path.setAttribute("fill", `hsl(${(i / slices) * 360}, 70%, 70%)`); // Color the slices
    path.setAttribute("stroke", "black");
    let grouper = document.querySelector("#slices");
    grouper.appendChild(path);
  }
};
onMounted(() => {
  addSlicesToCircle("circleSvg", 16, 200);
});

const animate = () => {
  let tl = gsap.timeline();

  tl.to("#slices", {
    duration: 1,
    rotation: 30,
    ease: "none",
    transformOrigin: "center center",
  });

  tl.to("#slices", {
    duration: 1,
    rotation: -60,
    ease: "none",
    transformOrigin: "center center",
  });
};
</script>

<style scoped>
#container {
  width: 600px;
  margin: 0 auto;
  margin-top: 84px;
}
svg {
  box-shadow: 0 0 10px 5px rgba(0, 0, 0, 0.2);
}
@media (max-width: 600px) {
  #container {
    width: 100vw;
  }
  svg {
    width: 100vw;
  }
}
</style>
