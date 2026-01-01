<template>
  <Navbar />
  <div id="container">
    <v-carousel :show-arrows="false" :hide-delimiters="true" id="car">
      <v-carousel-item style="height: 800px">
        <PostOne />
      </v-carousel-item>
      <v-carousel-item>
        <PostTwo />
      </v-carousel-item>
      <v-carousel-item>
        <PostThree />
      </v-carousel-item>
    </v-carousel>
  </div>
  <v-bottom-navigation>
    <v-chip-group id="chip_container">
      <v-chip>Chip 1</v-chip>

      <v-chip>Chip 2</v-chip>

      <v-chip>Chip 3</v-chip>
      <v-chip>Chip 1</v-chip>

      <v-chip>Chip 2</v-chip>

      <v-chip>Chip 3</v-chip>
      <v-chip>Chip 1</v-chip>

      <v-chip>Chip 2</v-chip>

      <v-chip>Chip 3</v-chip>
      <v-chip>Chip 1</v-chip>

      <v-chip>Chip 2</v-chip>

      <v-chip>Chip 3</v-chip>
    </v-chip-group>
  </v-bottom-navigation>
</template>

<script setup>
import PostOne from "./post/one.vue";
import PostTwo from "./post/two.vue";
import PostThree from "./post/three.vue";
</script>

<style scoped>
#container {
  width: 600px;
  margin: 0 auto;
  margin-top: 72px;
  height: calc(100vh - 84px);
  overflow-x: hidden;
  padding: 16px;
}
#chip_container {
  width: 600px;
}
#car {
  height: 800px !important;
  overflow-x: hidden;
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
  #chip_container {
    width: 100vw;
  }
}
</style>
