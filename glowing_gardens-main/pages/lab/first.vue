<template>
  <v-app-bar>
    <!-- <v-app-bar-nav-icon>
      <v-img
        src="https://www.glowinggardens.io/assets/garden_clear.png"
        height="40"
        class="ma-2 pa-2"
      ></v-img>
    </v-app-bar-nav-icon> -->
    <v-spacer></v-spacer>
    <v-avatar class="mr-2">
      <v-img
        alt="John"
        src="https://www.glowinggardens.io/assets/garden_clear.png"
      ></v-img>
    </v-avatar>

    <v-btn color="white" style="background: #111827">Glowing Gardens</v-btn>
    <v-spacer></v-spacer>
  </v-app-bar>

  <v-carousel
    :continuous="false"
    :show-arrows="false"
    delimiter-icon="mdi-square"
    :height="carousel_height"
    hide-delimiter-background
    style="margin-top: 64px"
    v-model="slide_number"
  >
    <v-carousel-item v-for="(slide, i) in slides" :key="i">
      <v-sheet :color="colors[i]" height="100%" tile>
        <div class="d-flex fill-height justify-center align-center">
          <div class="text-h2">{{ slide }} Slide</div>
        </div>
      </v-sheet>
    </v-carousel-item>
  </v-carousel>

  <v-bottom-navigation>
    <v-btn icon>
      <v-icon>mdi-arrow-left-bold-circle-outline</v-icon>
    </v-btn>
    <v-btn icon>
      <v-icon>mdi-home</v-icon>
    </v-btn>
    <v-btn icon @click="next_button">
      <v-icon>mdi-arrow-right-bold-circle-outline</v-icon>
    </v-btn>
  </v-bottom-navigation>
</template>

<script setup>
let colors = ref([
  "green",
  "secondary",
  "yellow darken-4",
  "red lighten-2",
  "orange darken-1",
  "blue darken-1",
  "purple darken-1",
]);
let slides = ref(["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh"]);
let slide_number = ref(0);

let carousel_height = ref(300);

const next_button = () => {
  slide_number.value = slide_number.value + 1;
  console.log("slide_number.value");
};

onMounted(() => {
  carousel_height.value = window.innerHeight - 124;
});
</script>

<style scoped>
html {
  font-size: 100%;
  overflow: hidden;
  overscroll-behavior: none;
}
</style>
