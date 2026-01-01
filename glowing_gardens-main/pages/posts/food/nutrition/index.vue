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

  <div
    class="card mt-4"
    :style="`margin-top:78px;height:${container_height}px;width:${carousel_width}px`"
  >
    <svg
      viewBox="0 0 600 600"
      :height="svg_width"
      :style="`width:${svg_width}px;margin:0 auto;`"
    ></svg>
    <div
      id="scroll_container"
      :style="`height:${bottom_container_height}px; overflow-y: scroll;`"
    >
      <v-card v-for="c in foods" :key="c" class="mt-1">
        <div class="d-flex justify-start">
          <img class="pa-1 ma-1" :src="c.img" aspect-ratio="1.5" style="height: 40px" />
          <div class="text-h6 mt-2">{{ c.name }}</div>
        </div>
      </v-card>
    </div>
  </div>
</template>

<script setup>
import { useDisplay } from "vuetify";
const { mdAndDown } = useDisplay();
import { nextTick } from "vue";
let cards = ref([1, 2, 3, 4, 5, 6, 7, 8, 9]);

let foods = ref([
  {
    name: "Beef",
    img: "https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/beef.png",
  },
  {
    name: "Potato",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/potato.png",
  },
  {
    name: "Apple",
    img: "https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/apple.png",
  },
  {
    name: "Avocado",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/avocado.png",
  },
  {
    name: "Salmon",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/salmon.png",
  },
  {
    name: "Egg",
    img: "https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/egg.png",
  },
  {
    name: "Butter",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/butter.png",
  },
  {
    name: "Milk",
    img: "https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/milk.png",
  },
  {
    name: "Orange",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/orange.png",
  },
  {
    name: "Rice",
    img: "https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/rice.png",
  },
  {
    name: "Flour",
    img: "https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/flour.png",
  },
  {
    name: "Pinto Beans",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/red-beans.png",
  },
  {
    name: "Pork",
    img: "https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/pork.png",
  },
  {
    name: "Sugar",
    img: "https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/sugar.png",
  },
  {
    name: "Broccoli",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/broccoli.png",
  },
]);

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
    let navbar_height = 68;

    nextTick().then(() => {
      carousel_width.value = window.innerWidth;
      svg_width.value = window.innerWidth;
      container_height.value = window.innerHeight - navbar_height - 16;
      bottom_container_height.value =
        window.innerHeight - svg_width.value - navbar_height - 16;
    });
  } else {
    nextTick().then(() => {
      carousel_width.value = 600;
      svg_width.value = 600;
      svg_margin_left.value = 0;
      container_height.value = window.innerHeight - 84; //72 = bigger than 68 navbar

      bottom_container_height.value = window.innerHeight - svg_width.value - 84;
    });
  }

  let svg2 = document.querySelector("svg");
  svg2.addEventListener("click", () => {
    console.log("svg clicked");
    create_force();
  });
});

let circles = reactive(null);

const create_force = () => {
  const svg = d3.select("svg");
  const width = 600;
  const height = 600;

  // Data for circles: one large and three small
  const nodes = [
    { id: 1, radius: 30 },
    { id: 2, radius: 10 },
    { id: 3, radius: 10 },
    { id: 4, radius: 10 },
    { id: 1, radius: 10 },
    { id: 2, radius: 10 },
    { id: 3, radius: 10 },
    { id: 4, radius: 10 },
    { id: 1, radius: 10 },
    { id: 2, radius: 10 },
    { id: 3, radius: 10 },
    { id: 4, radius: 10 },
    { id: 1, radius: 10 },
    { id: 2, radius: 10 },
    { id: 3, radius: 10 },
    { id: 4, radius: 10 },
    { id: 1, radius: 10 },
    { id: 2, radius: 10 },
    { id: 3, radius: 10 },
    { id: 4, radius: 10 },
    { id: 1, radius: 10 },
    { id: 2, radius: 10 },
    { id: 3, radius: 10 },
    { id: 4, radius: 10 },
    { id: 4, radius: 6 },
    { id: 1, radius: 6 },
    { id: 2, radius: 5 },
    { id: 3, radius: 5 },
    { id: 4, radius: 5 },
  ];

  const simulation = d3
    .forceSimulation(nodes)
    // .force("x", d3.forceX(300).strength(1))
    // .force("y", d3.forceY(300).strength(1))
    .force("center", d3.forceCenter(300, 300))
    .force("charge", d3.forceManyBody().strength(10))
    .force(
      "collision",
      d3.forceCollide().radius((d) => d.radius + 1)
    )
    .on("tick", ticked);

  // Append circles to the svg for each node in the simulation
  circles = svg
    .selectAll("circle")
    .data(nodes)
    .join("circle")
    .attr("r", (d) => d.radius)
    .style("fill", (d, i) => (i === 0 ? "#ff8c00" : "#6b486b")); // Color the largest circle differently

  // Function to set circle positions on each tick of the simulation
};

const ticked = () => {
  circles.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
};

let nutrition = ref([
  {
    name: "Banana",
    amount: "1",
    unit: "Banana",
    calories: 105,
    fat: 0.4,
    carbs: 27,
    protein: 1.3,
    sugar: 14.4,
  },
  {
    name: "Apple",
    amount: "1",
    unit: "",
    calories: 105,
    fat: 0.4,
    carbs: 27,
    protein: 1.3,
    sugar: 14.4,
  },
  {
    name: "Beef",
    amount: "1",
    unit: "",
    calories: 105,
    fat: 0.4,
    carbs: 27,
    protein: 1.3,
    sugar: 14.4,
  },
  {
    name: "Chicken",
    amount: 200,
    unit: "grams",
    calories: 105,
    fat: 0.4,
    carbs: 27,
    protein: 1.3,
    sugar: 14.4,
  },
  {
    name: "Pork",
    amount: 200,
    unit: "grams",
    calories: 105,
    fat: 0.4,
    carbs: 27,
    protein: 1.3,
    sugar: 14.4,
  },
  {
    name: "Beans",
    amount: 200,
    unit: "grams",
    calories: 105,
    fat: 0.4,
    carbs: 27,
    protein: 1.3,
    sugar: 14.4,
  },
  {
    name: "Potatoes",
    amount: 1.5,
    unit: "pounds",
    calories: 105,
    fat: 0.4,
    carbs: 27,
    protein: 1.3,
    sugar: 14.4,
  },
]);
</script>

<style scoped>
body {
  overscroll-behavior: none;
}
svg {
  border: 1px solid navy;
  margin: 0 auto;
}
#my_carousel {
  margin: 0 auto;
}
.card {
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.2), 0 0 10px rgba(0, 0, 0, 0.15),
    0 0 10px rgba(0, 0, 0, 0.1), 0 0 10px rgba(255, 255, 255, 0.1);
  margin: 8px;
  margin: 0 auto;
  margin-top: 68px !important;
}
</style>
