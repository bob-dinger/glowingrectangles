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

  <v-main>
    <v-carousel
      :continuous="false"
      :show-arrows="false"
      delimiter-icon="mdi-square"
      :width="carousel_width"
      :height="container_height"
      hide-delimiter-background
      v-model="slide_number"
      id="my_carousel"
    >
      <v-carousel-item>
        <div
          class="container mt-2"
          :style="`height:${container_height}px;border:1px solid pink`"
        >
          <svg
            class="my_svg"
            :height="svg_width"
            :width="svg_width"
            :style="`margin-left:${svg_margin_left}`"
          ></svg>
          <div
            class="bottom_container"
            :style="`height:${bottom_container_height}px; overflow-y: scroll;`"
          >
            <div
              id="bottom_content"
              style="height: 1600px; background: blue; width: 100%"
            >
              why the fuck is there no scroll here. wtf.
            </div>
          </div>
        </div>
      </v-carousel-item>
    </v-carousel>
  </v-main>
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
      carousel_width.value = window.innerWidth;
      svg_width.value = window.innerWidth - 24;
      container_height.value = window.innerHeight - 132;
      bottom_container_height.value = window.innerHeight - svg_width.value - 132;
    });
  } else {
    nextTick().then(() => {
      svg_margin_left.value = 0;
      container_height.value = window.innerHeight - 132;
      svg_width.value = 600;

      bottom_container_height.value = window.innerHeight - svg_width.value - 132;
    });
  }

  //   nextTick().then(() => {
  //   let svg1 = document.querySelector("#svg1");
  //   let svg1_width = svg1.getBoundingClientRect().width;
  //   svg1.style.height = svg1_width + "px";
  // });
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
  width: 600px;
  margin: 0 auto;
}
</style>
