<template>
  <v-app-bar>
    <v-app-bar-title>Glowing Gardens</v-app-bar-title>
  </v-app-bar>
  <div id="container" :style="`width:${container_width}px;`">
    <svg
      id="svger"
      viewbox="0 0 600 600"
      class="mx-auto mt-4"
      :style="`width:${svg_width}px;height:auto;margin:0 auto;margin-top:108px;border:1px solid navy;`"
    ></svg>
    <div id="scroller">
      <v-row no-gutters>
        <v-col sm="6" md="6" v-for="food in foods" :key="food" class="my-2">
          <v-card class="mx-auto" max-width="100%" height="40">
            <v-card-title>{{ food }}</v-card-title>
          </v-card>
        </v-col>
      </v-row>
    </div>
  </div>
</template>

<script setup>
import { useDisplay } from "vuetify";
const { mdAndDown } = useDisplay();
let container_width = ref(600);
let svg_width = ref(600);

onMounted(() => {
  if (mdAndDown.value) {
    container_width.value = window.innerWidth - 24;
    svg_width.value = window.innerWidth - 24;
  }
  let svg = document.querySelector("svg");
  svg.style.height = svg_width.value + "px";
});

//nutrition | spoilage | cooking

let foods = ref([
  "banana",
  "apple",
  "orange",
  "grape",
  "strawberry",
  "blueberry",
  "kiwi",
  "mango",
  "pineapple",
  "watermelon",
  "ground beef",
  "chicken breast",
  "filet",
  "bacon",
  "sausage",
  "turkey",
  "salmon",
]);
</script>

<style scoped>
#container {
  margin: 0 auto;
  overflow: hidden;
}
#svger {
  margin-top: 72px !important;
}
svg {
  width: 600px;
  height: 600px;
  height: auto;
  border: 1px solid white;
  box-shadow: 0 0 10px 0 rgba(0, 0, 0, 0.2);
  margin-top: 78px !important;
}
#scroller {
  overflow-y: scroll;
  height: 400px;

  margin: 0 auto;
}
html {
  overflow: hidden;
}
</style>
