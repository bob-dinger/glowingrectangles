<template>
  <svg width="800" height="800" style="margin: 0 auto; border: 1px solid pink">
    <g transform="translate(400,400)">
      <!-- Center the pie in the SVG -->
      <path
        v-for="index in 32"
        :key="index"
        :d="getPathData(index)"
        fill="currentColor"
        stroke="white"
        stroke-width="2"
      ></path>
    </g>
  </svg>
</template>

<script setup>
import { computed } from "vue";

const radius = 200; // Radius of the pie

// Function to calculate path data for each slice
const getPathData = (index) => {
  const sliceAngle = (2 * Math.PI) / 32; // Total angle divided by 32 slices
  const startAngle = sliceAngle * (index - 1);
  const endAngle = sliceAngle * index;

  // Function to calculate x and y coordinates on the circle for a given angle
  const getCoordinatesForAngle = (angle) => ({
    x: Math.cos(angle - Math.PI / 2) * radius,
    y: Math.sin(angle - Math.PI / 2) * radius,
  });

  const start = getCoordinatesForAngle(startAngle);
  const end = getCoordinatesForAngle(endAngle);

  // Path data using the SVG path syntax
  return `M 0,0 
          L ${start.x},${start.y} 
          A ${radius},${radius} 0 0,1 ${end.x},${end.y} 
          Z`;
};
</script>

<style scoped>
path {
  transition: fill 0.3s ease;
}

path:hover {
  fill: #42b983; /* Change color on hover */
}
</style>
