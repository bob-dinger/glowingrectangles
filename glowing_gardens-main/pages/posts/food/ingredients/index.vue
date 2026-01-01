<template>
  <Navbar />

  <div id="container">
    <svg>
      <defs>
        <pattern
          :id="selected_food.name"
          height="100%"
          width="100%"
          patternContentUnits="objectBoundingBox"
        >
          <image
            :xlink:href="`https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/${selected_food.name}.png`"
            preserveAspectRatio="none"
            width="1"
            height="1"
          ></image>
        </pattern>

        <pattern
          v-for="ing in selected_food.ingredients"
          :key="ing"
          :id="ing"
          height="100%"
          width="100%"
          patternContentUnits="objectBoundingBox"
        >
          <image
            :xlink:href="`https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/${ing}.png`"
            preserveAspectRatio="none"
            width="1"
            height="1"
          ></image>
        </pattern>
      </defs>
      <circle
        cx="300"
        cy="300"
        r="100"
        :fill="`url(#${selected_food.name})`"
        stroke="navy"
        stroke-width="4"
      />

      <circle
        v-if="my_circle_points"
        class="circler"
        v-for="(ing, index) in selected_food.ingredients"
        :cx="my_circle_points[index].x"
        :cy="my_circle_points[index].y"
        r="50"
        :fill="`url(#${ing})`"
        stroke="navy"
        stroke-width="4"
      />
    </svg>

    <div class="pa-8">For building an intuition of what is in certain foods.</div>
  </div>

  <v-bottom-navigation
    @click="lefter = !lefter"
    id="bottomer"
    width="100vw"
    style="position: absolute"
  >
    <v-btn>List of Foods</v-btn>
  </v-bottom-navigation>
  <v-navigation-drawer width="350" v-model="lefter">
    <v-list>
      <v-list-item v-for="food in foods" @click="load_ingredients(food)">
        <v-list-item-title>{{ food.name }}</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-navigation-drawer>
</template>

<script setup>
const { circle_points } = useGlyfs();
import { gsap } from "gsap";

let lefter = ref(true);
let my_circle_points = ref(null);

const load_ingredients = (food) => {
  //console.log(ing);
  //selected_food.value = food;
  //find food in foods

  selected_food.value = foods.value.find((f) => f.name == food.name);
};

onMounted(() => {
  selected_food.value = foods.value.find((f) => f.name == "pancakes");
  my_circle_points.value = circle_points(300, 300, 200, 8);
  //console.log(points);
  //then do a gsap random thingy

  // gsap.to(".circler", {
  // duration: 2,
  // x: "+=random(-10,10)",
  //  y: "+=random(-10,10)",
  //  ease: "bounce",
  // repeat: -1,
  //  yoyo: true,
  //});

  //tl.to('.pinker', {duration:1, y:'+=random(-3,3)', x:'+=random(-3,3)', repeat:-1, yoyo:true});
});

let foods = ref([
  {
    name: "pancakes",
    ingredients: ["milk", "flour", "egg", "sugar", "butter", "baking-soda"],
  },
  {
    name: "biscuits",
    ingredients: ["milk", "flour", "butter"],
  },
  {
    name: "bread",
    ingredients: ["water", "flour", "salt", "yeast"],
  },
]);
//mayo
//ranch dressing

let selected_food = ref(foods.value[0]);
</script>

<style scoped>
#container {
  width: 600px;
  margin: 0 auto;
  margin-top: 84px;
  height: calc(100vh - 164px);
}
#bottomer {
  width: 100vw;
}

svg {
  height: 600px;
  width: 600px;

  box-shadow: 0 0 10px 5px rgba(0, 0, 0, 0.1);
}

line {
  stroke: #ccc !important;
  stroke-width: 2 !important;
}
text {
  text-anchor: middle;
  font-family: "Helvetica Neue", Helvetica, sans-serif;
  fill: #666;
  font-size: 16px;
}
</style>
