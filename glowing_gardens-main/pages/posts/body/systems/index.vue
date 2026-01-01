<template>
  <Navbar />
  <div>
    <Nervous />
  </div>
</template>

<script setup>
import Nervous from "./svg/nervous";

let systems = ref([
  {
    name: "endocrine",
  },
  {
    name: "nervous",
  },
  {
    name: "digestive",
  },
  {
    name: "respiratory",
  },
  {
    name: "circulatory",
  },
  {
    name: "lymphatic/immune",
  },
  {
    name: "reproductive",
  },
  {
    name: "integumentary",
  },
  {
    name: "muscular",
  },
  {
    name: "skeletal",
  },
]);
</script>

<style scoped></style>
