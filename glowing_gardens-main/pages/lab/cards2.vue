<template>
  <v-app-bar>
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
    :width="carousel_width"
    :height="container_height + 24"
    hide-delimiter-background
    v-model="slide_number"
    id="my_carousel"
    :style="`margin-top:72px;width:${carousel_width}px;`"
  >
    <v-carousel-item>
      <div
        class="card mt-2"
        :style="`height:${container_height}px;border:1px solid pink`"
      ></div>
    </v-carousel-item>
    <v-carousel-item>
      <div
        class="card mt-2"
        :style="`height:${container_height}px;border:1px solid pink`"
      ></div>
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
import { useDisplay } from "vuetify";
const { mdAndDown } = useDisplay();
import { nextTick } from "vue";

let container_height = ref(600);
let svg_width = ref(600);
let carousel_width = ref(600);
let svg_margin_left = ref(12);
let bottom_container_height = ref(300);
let slide_number = ref(0);

const next_button = () => {
  slide_number.value = slide_number.value + 1;
  console.log("slide_number.value");
};

onMounted(() => {
  if (mdAndDown.value) {
    console.log("md and down");

    nextTick().then(() => {
      carousel_width.value = window.innerWidth - 48;
      //svg_width.value = window.innerWidth - 56;
      container_height.value = window.innerHeight - 156;
      //bottom_container_height.value = window.innerHeight - svg_width.value - 132;
    });
  } else {
    nextTick().then(() => {
      carousel_width.value = 720;
      //svg_margin_left.value = 0;
      container_height.value = window.innerHeight - 156;
      //svg_width.value = 600;

      //bottom_container_height.value = window.innerHeight - svg_width.value - 132;
    });
  }
});
</script>

<style scoped>
/* html {
  font-size: 100%;
  overflow: hidden;
  overscroll-behavior: none;
} */
svg {
  border: 1px solid navy;
}
#my_carousel {
  width: 720px;
  margin: 0 auto;
}
.card {
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.2), 0 0 10px rgba(0, 0, 0, 0.15),
    0 0 10px rgba(0, 0, 0, 0.1), 0 0 10px rgba(255, 255, 255, 0.1);
  margin-left: 4px;
  width: 98%;
  height: 98%;
}

@media (max-width: 600px) {
  .card {
    /* Adjustments for screens smaller than 600px */
  }
}
</style>
