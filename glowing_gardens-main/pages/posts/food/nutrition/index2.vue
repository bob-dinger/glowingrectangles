<template>
  <Navbar />
  <v-navigation-drawer width="350" location="right" v-model="lefter">
    <v-list>
      <v-list-item v-for="food in foods" :key="food" @click="load_nutrition(food)">
        <v-list-item-title>{{ food.name }}</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-navigation-drawer>

  <div id="container">
    <svg viewBox="0 0 600 600">
      <g class="links"></g>
      <g class="nodes"></g>
    </svg>
    <div class="iframely-embed" :key="my_key">
      <div class="iframely-responsive">
        <a data-iframely-url :href="current_url"></a>
      </div>
    </div>
  </div>

  <v-bottom-navigation style="width: 100vw">
    <v-btn @click="lefter = !lefter">List of Foods</v-btn>
  </v-bottom-navigation>
</template>

<script setup>
//nav drawer with foods
import { nextTick } from "vue";

let lefter = ref(true);
let current_url = ref(
  "https://www.amazon.com/Just-BARE-Chicken-Hand-Trimmed-Boneless/dp/B00AR0ZZ62"
);
let my_key = ref(0);
import { useHead } from "#app";

useHead({
  script: [
    {
      src: "https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js",
      type: "text/javascript",
      async: true,
      defer: true,
    },
  ],
});

let nodes = [
  {
    name: "pancakes",
    radius: 40,
    color: "green",
  },
  {
    name: "flour",
    radius: 15,
    color: "green",
  },
  {
    name: "milk",
    radius: 15,
    color: "green",
  },
  {
    name: "egg",
    radius: 15,
    color: "green",
  },
];

let links = [
  {
    source: 1,
    target: 0,
  },
  {
    source: 2,
    target: 0,
  },
  {
    source: 3,
    target: 0,
  },
];
let u = null;

const updateLinks = () => {
  u = d3
    .select(".links")
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("x1", function (d) {
      return d.source.x;
    })
    .attr("y1", function (d) {
      return d.source.y;
    })
    .attr("x2", function (d) {
      return d.target.x;
    })
    .attr("y2", function (d) {
      return d.target.y;
    });
};

const updateNodes = () => {
  // First, select all groups for nodes, which will contain both the circle and text
  let nodeGroups = d3
    .select(".nodes")
    .selectAll("g.node")
    .data(nodes, (d) => d.name) // Use name as the key for data binding
    .join("g")
    .attr("class", "node")
    .attr("transform", (d) => `translate(${d.x}, ${d.y})`); // Position the group according to node position

  // Append a circle to each group
  nodeGroups
    .append("circle")
    .attr("r", (d) => d.radius)
    .attr("fill", (d) => d.color)
    .attr("opacity", 0.4)
    .attr("stroke", "navy")
    .attr("stroke-width", 3);

  // Append a text element to each group
  nodeGroups
    .append("text")
    .attr("dy", ".35em") // Center the text vertically
    .style("text-anchor", "middle") // Center the text horizontally
    .text((d) => d.name + " - " + d.value); // Use the 'name' property for the text
};

const create_force = (nodes, links) => {
  let width = 600;
  let height = 600;

  //   d3.selectAll(".nodes circle").remove();
  //   d3.selectAll(".links line").remove();

  var simulation = d3
    .forceSimulation(nodes)
    .force("charge", d3.forceManyBody().strength(-6000))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("link", d3.forceLink().links(links))
    .on("tick", ticked);

  //   function updateLinks() {
  //     u = d3
  //       .select(".links")
  //       .selectAll("line")
  //       .data(links)
  //       .join("line")
  //       .attr("x1", function (d) {
  //         return d.source.x;
  //       })
  //       .attr("y1", function (d) {
  //         return d.source.y;
  //       })
  //       .attr("x2", function (d) {
  //         return d.target.x;
  //       })
  //       .attr("y2", function (d) {
  //         return d.target.y;
  //       });
  //   }

  //   function updateNodes() {
  //     u = d3
  //       .select(".nodes")
  //       .selectAll("circle")
  //       .data(nodes)
  //       .join("circle")
  //       .attr("cx", function (d) {
  //         return d.x;
  //       })
  //       .attr("cy", function (d) {
  //         return d.y;
  //       })
  //       .attr("r", function (d) {
  //         return d.radius;
  //       })
  //       .attr("fill", function (d) {
  //         return d.color;
  //       })
  //       .attr("opacity", function (d) {
  //         return 0.4;
  //       })
  //       .attr("stroke", "navy")
  //       .attr("stroke-width", 3);
  //   }

  //   function updateNodes() {
  //     // First, select all groups for nodes, which will contain both the circle and text
  //     let nodeGroups = d3
  //       .select(".nodes")
  //       .selectAll("g.node")
  //       .data(nodes, (d) => d.name) // Use name as the key for data binding
  //       .join("g")
  //       .attr("class", "node")
  //       .attr("transform", (d) => `translate(${d.x}, ${d.y})`); // Position the group according to node position

  //     // Append a circle to each group
  //     nodeGroups
  //       .append("circle")
  //       .attr("r", (d) => d.radius)
  //       .attr("fill", (d) => d.color)
  //       .attr("opacity", 0.4)
  //       .attr("stroke", "navy")
  //       .attr("stroke-width", 3);

  //     // Append a text element to each group
  //     nodeGroups
  //       .append("text")
  //       .attr("dy", ".35em") // Center the text vertically
  //       .style("text-anchor", "middle") // Center the text horizontally
  //       .text((d) => d.name); // Use the 'name' property for the text
  //   }

  //   function ticked() {
  //     updateLinks();
  //     updateNodes();
  //   }
};

const ticked = () => {
  updateLinks();
  updateNodes();
};

onMounted(() => {
  nextTick().then(() => {
    iframely.load();
  });

  setTimeout(() => {
    create_force(nodes, links);
  }, 1000);
});

const load_nutrition = (food) => {
  current_url.value = food.link;
  my_key.value = my_key.value + 1;
  console.log(food.link);
  nextTick().then(() => {
    iframely.load();
  });

  let chosen_food = foods.value.find((f) => f.name === food.name);

  nodes = [
    {
      name: "calories",
      radius: chosen_food.calories / 2,
      color: "teal",
      value: chosen_food.calories,
    },
    {
      name: "protein",
      radius: chosen_food.protein / 2,
      color: "purple",
      value: chosen_food.protein,
    },
    {
      name: "fat",
      radius: chosen_food.fat / 2,
      color: "red",
      value: chosen_food.fat,
    },
    {
      name: "carbs",
      radius: chosen_food.carbs / 2,
      color: "goldenrod",
      value: chosen_food.carbs,
    },
  ];

  links = [
    {
      source: 1,
      target: 0,
    },
    {
      source: 2,
      target: 0,
    },
    {
      source: 3,
      target: 0,
    },
  ];

  //   d3.selectAll(".nodes circle").remove();
  //   d3.selectAll(".links line").remove();

  //   let svg = document.querySelector("svg");

  //   svg.innerHTML = "<g class='links'></g><g class='nodes'></g>";

  d3.selectAll(".nodes > *").remove(); // Removes all children of the 'nodes' group
  d3.selectAll(".links > *").remove(); // Removes all children of the 'links' group

  create_force(nodes, links);
};

const choose_food = (food_name) => {
  //food_chosen matches the name of the foods array. find the food with that name from food_chosen
  //look through foods array to find matching name
  //let chosen_food = food
};

let foods = ref([
  {
    name: "chicken breast",
    amount: "100",
    unit: "g",
    calories: 195,
    protein: 30,
    fat: 8,
    carbs: 0,
    link: "https://www.amazon.com/Just-BARE-Chicken-Hand-Trimmed-Boneless/dp/B00AR0ZZ62",
  },
  {
    name: "ground beef",
    amount: "1/2",
    unit: "lb",
    calories: 254,
    protein: 17,
    fat: 20,
    carbs: 0,
    link: "https://www.amazon.com/Just-BARE-Chicken-Hand-Trimmed-Boneless/dp/B00AR0ZZ62",
  },
  {
    name: "filet mignon",
    amount: "1",
    unit: "lb",
    calories: 165,
    protein: 31,
    fat: 3.6,
    carbs: 0,
    link: "https://www.amazon.com/Just-BARE-Chicken-Hand-Trimmed-Boneless/dp/B00AR0ZZ62",
  },
  {
    name: "ground pork",
    amount: "1",
    unit: "lb",
    calories: 165,
    protein: 31,
    fat: 3.6,
    carbs: 0,
    link: "https://www.amazon.com/Niman-Ranch-Ground-Pork/dp/B074Z5JWD2",
  },
  {
    name: "2 wheat bread slices",
    amount: "2",
    unit: "slices",
    calories: 120,
    protein: 8,
    fat: 1,
    carbs: 22,
    link:
      "https://www.walmart.com/ip/Nature-s-Own-100-Whole-Wheat-Bread-Loaf-20-oz/10450002",
  },
  {
    name: "Frozen Chicken Tacos",
    amount: "4",
    unit: "tacos",
    calories: 260,
    // protein: 11 * 4,
    // fat: 13 * 7,
    // carbs: 24 * 4,
    protein: 44,
    fat: 91,
    carbs: 96,

    link: "https://www.traderjoes.com/home/products/pdp/mini-chicken-tacos-070708",
  },
]);
</script>

<style scoped>
#container {
  width: 600px;
  margin: 0 auto;
  margin-top: 84px;
}
svg {
  box-shadow: 0 0 10px 5px rgba(0, 0, 0, 0.2);
}
svg line {
  stroke: #ccc;
  stroke-width: 2;
}
@media (max-width: 600px) {
  #container {
    width: 100vw;
  }
  svg {
    width: 100vw;
  }
  line {
    stroke: #ccc;
  }
}
</style>
