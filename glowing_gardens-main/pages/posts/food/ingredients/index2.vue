<template>
  <Navbar />

  <div id="container">
    <svg>
      <defs>
        <pattern
          id="pancakes"
          height="100%"
          width="100%"
          patternContentUnits="objectBoundingBox"
        >
          <image
            xlink:href="https://glowinggardensstorage.blob.core.windows.net/glyfs/images/food/pancakes.png"
            preserveAspectRatio="none"
            width="1"
            height="1"
          ></image>
        </pattern>

        <pattern
          id="egg"
          height="100%"
          width="100%"
          patternContentUnits="objectBoundingBox"
        >
          <image
            xlink:href="https://glowinggardensstorage.blob.core.windows.net/glyfs/images/food/egg.png"
            preserveAspectRatio="none"
            width="1"
            height="1"
          ></image>
        </pattern>

        <pattern
          id="flour"
          height="100%"
          width="100%"
          patternContentUnits="objectBoundingBox"
        >
          <image
            xlink:href="https://glowinggardensstorage.blob.core.windows.net/glyfs/images/food/flour.png"
            preserveAspectRatio="none"
            width="1"
            height="1"
          ></image>
        </pattern>

        <pattern
          id="milk"
          height="100%"
          width="100%"
          patternContentUnits="objectBoundingBox"
        >
          <image
            xlink:href="https://glowinggardensstorage.blob.core.windows.net/glyfs/images/food/milk.png"
            preserveAspectRatio="none"
            width="1"
            height="1"
          ></image>
        </pattern>

        <pattern
          id="sugar"
          height="50%"
          width="50%"
          patternContentUnits="objectBoundingBox"
        >
          <image
            xlink:href="https://glowinggardensstorage.blob.core.windows.net/glyfs/images/food/sugar.png"
            preserveAspectRatio="none"
            width="15"
            height="15"
          ></image>
        </pattern>

        <pattern
          id="baking-soda"
          height="100%"
          width="100%"
          patternContentUnits="objectBoundingBox"
        >
          <image
            xlink:href="https://glowinggardensstorage.blob.core.windows.net/glyfs/images/food/baking-soda.png"
            preserveAspectRatio="none"
            width="1"
            height="1"
          ></image>
        </pattern>
        <pattern
          id="salt"
          height="100%"
          width="100%"
          patternContentUnits="objectBoundingBox"
        >
          <image
            xlink:href="https://glowinggardensstorage.blob.core.windows.net/glyfs/images/food/salt.png"
            preserveAspectRatio="none"
            width="1"
            height="1"
          ></image>
        </pattern>

        <pattern
          id="olive-oil"
          height="100%"
          width="100%"
          patternContentUnits="objectBoundingBox"
        >
          <image
            xlink:href="https://glowinggardensstorage.blob.core.windows.net/glyfs/images/food/olive-oil.png"
            preserveAspectRatio="none"
            width="1"
            height="1"
          ></image>
        </pattern>
      </defs>

      <g class="links"></g>
      <g class="nodes"></g>
    </svg>
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
      <v-list-item v-for="ing in ingredients" @click="load_ingredients(ing)">
        <v-list-item-title>{{ ing.name }}</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-navigation-drawer>
</template>

<script setup>
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

let lefter = ref(true);

const load_ingredients = (ing) => {
  console.log(ing);
};

onMounted(() => {
  first();
});

let ingredients = ref([
  {
    name: "pancakes",
    ingredients: ["milk", "flour", "egg", "sugar", "butter", "baking powder"],
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

let nodes = [
  {
    name: "pancakes",
    radius: 100,
  },
  {
    name: "flour",
    radius: 25,
  },
  {
    name: "milk",
    radius: 25,
  },
  {
    name: "egg",
    radius: 25,
  },
  {
    name: "baking-soda",
    radius: 25,
  },
  {
    name: "salt",
    radius: 25,
  },
  {
    name: "olive-oil",
    radius: 25,
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
  {
    source: 4,
    target: 0,
  },
  {
    source: 5,
    target: 0,
  },
  {
    source: 6,
    target: 0,
  },
];

const first = () => {
  let width = 600;
  let height = 600;

  var simulation = d3
    .forceSimulation(nodes)
    .force("charge", d3.forceManyBody().strength(-6000))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("link", d3.forceLink().links(links))
    .on("tick", ticked);
};
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
  u = d3
    .select(".nodes")
    .selectAll("circle")
    .data(nodes)
    .join("circle")
    .attr("cx", function (d) {
      return d.x;
    })
    .attr("cy", function (d) {
      return d.y;
    })
    .attr("r", function (d) {
      return d.radius;
    })
    .attr("fill", function (d) {
      return `url(#${d.name})`;
    })
    .attr("stroke", "#FC0FC0")
    .attr("stroke-width", 2);
};

const ticked = () => {
  updateLinks();
  updateNodes();
};
</script>

<style scoped>
#container {
  width: 600px;
  margin: 0 auto;
  margin-top: 84px;
  height: calc(100vh - 164px);
  box-shadow: 0 0 10px 5px rgba(0, 0, 0, 0.1);
}
#bottomer {
  width: 100vw;
}

svg {
  height: 600px;
  width: 600px;
  border: 1px solid grey;
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
