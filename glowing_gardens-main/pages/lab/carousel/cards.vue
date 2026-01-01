<template>
  <Navbar />
  <div id="middle_container">
    <v-carousel
      id="carouseler"
      height="calc(100vh - 84px)"
      :width="600"
      :show-arrows="false"
      :hide-delimiters="false"
      transition="fade-transition"
      class="mx-auto"
      v-model="indexer"
    >
      <v-carousel-item>
        <div class="card">
          <div class="d-flex justify-center">
            <div id="textElement"></div>
          </div>
        </div>
      </v-carousel-item>
      <v-carousel-item>
        <div class="card"></div>
      </v-carousel-item>
    </v-carousel>
  </div>
</template>

<script setup>
let indexer = ref(0);
import { gsap } from "gsap";
import { TextPlugin } from "gsap/TextPlugin";
gsap.registerPlugin(TextPlugin);

const textElement = ref(null);

onMounted(() => {
  //let card = document.querySelector(".card");
  gsap.to("#textElement", {
    duration: 2,
    text:
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla necpurus nec libero ultricies ultricies. Nulla facilisi. Nulla facilisi. Nulla",
  });
});
</script>

<style scoped>
#middle_container {
  width: 600px;
  height: calc(100vh - 128px);
  margin: 0 auto;
  margin-top: 72px;
}
.card {
  width: 98%;
  height: 90%;
  border: 1px solid pink;
  margin: 0 auto;
}
#textElement {
  width: 360px;
  margin-top: 100px;
}
</style>
