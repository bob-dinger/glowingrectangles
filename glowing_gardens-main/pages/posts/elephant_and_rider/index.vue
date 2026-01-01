<template>
  <Navbar />
  <div id="container">
    <v-carousel
      id="carousel"
      :show-arrows="false"
      height="calc(100vh - 144px)"
      :hide-delimiters="true"
      transition="fade-transition"
    >
      <v-carousel-item>
        <IntroCard />
      </v-carousel-item>
      <v-carousel-item>
        <CardOne />
      </v-carousel-item>
      <v-carousel-item>
        <CardTwo />
      </v-carousel-item>
      <v-carousel-item>
        <CardThree />
      </v-carousel-item>
      <v-carousel-item>
        <CardFour />
      </v-carousel-item>
    </v-carousel>
  </div>
  <v-bottom-navigation></v-bottom-navigation>
</template>

<script setup>
import IntroCard from "./cards/intro.vue";
import CardOne from "./cards/one.vue";
import CardTwo from "./cards/two.vue";
import CardThree from "./cards/three.vue";
import CardFour from "./cards/four.vue";

onMounted(() => {
  console.log("mounted");
});
</script>

<style scoped>
#container {
  width: 600px;
  margin: 0 auto;
  margin-top: 84px;
  height: calc(100vh - 154px);
  box-shadow: 0 0 10px 5px rgba(0, 0, 0, 0.2);
}
#carousel {
  height: calc(100vh - 124px);
}

@media (max-width: 600px) {
  #container {
    width: 100vw;
  }
  #carousel {
    width: 100vw;
    height: calc(100vh - 124px);
  }
}
</style>
