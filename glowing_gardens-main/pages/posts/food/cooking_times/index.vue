<template>
  <Navbar />
  <v-navigation-drawer v-model="lefter" clipped="true">
    <v-list>
      <v-list-item v-for="item in items" :key="item" @click="changeComponent(item.index)">
        {{ item.name }}
      </v-list-item>
    </v-list>
  </v-navigation-drawer>
  <div id="card">
    <ChickenOven v-if="selected_index == 0" />
    <ChickenSkillet v-if="selected_index == 1" />
    <HaidtQuote v-if="selected_index == 2" />
    <SalmonOven v-if="selected_index == 4" />
    <MyTemplate
      v-if="selected_index == 5"
      :equipment_image="'https://glowinggardensstorage.blob.core.windows.net/images/food_equipment_pngs/oven.png'"
      :food_image="'https://glowinggardensstorage.blob.core.windows.net/images/food_pngs/chicken-breast.png'"
      :text="'hello'"
    />
  </div>
  <v-bottom-navigation style="width: 100vw; position: absoulte; left: 0">
    <v-btn icon @click="lefter = !lefter">
      <v-icon>mdi-arrow-right-bold-circle-outline</v-icon>
    </v-btn>
  </v-bottom-navigation>
</template>

<script setup>
import ChickenOven from "./svg/ChickenOven.vue";
import ChickenSkillet from "./svg/ChickenSkillet.vue";
import HaidtQuote from "./svg/HaidtQuote.vue";
import SalmonOven from "./svg/SalmonOven.vue";
import MyTemplate from "./svg/MyTemplate.vue";

let lefter = ref(true);
let selected_index = ref(0);
const changeComponent = (index) => {
  console.log(index);
  selected_index.value = index;
};

let items = ref([
  {
    name: "chicken breast in the oven",
    time: "",
    heat: "350 degrees F",
    index: 0,
  },
  {
    name: "chicken breast on cast iron skillet",
    time: "",
    index: 1,
    notes: "7 minutes per side over medium heat",
  },
  {
    name: "chicken breast poaching",
    time: "",
    index: 2,
  },
  {
    name: "filet on cast iron skillet",
    time: "",
    heat: "",
    index: 3,
    notes:
      "sear for 2 minutes on each side, transfer to oven at 400 degrees F for 10 minutes",
  },
  {
    name: "salmon in the oven",
    time: "",
    heat: "425 deg F",
    notes: "10 min per inch of thickness",
    index: 4,
  },
  {
    name: "ground beef in non-stick pan",
    time: "",
    heat: "420 deg F",
    notes: "6 minutes",
    index: 5,
  },
  {
    name: "burger in cast iron skillet",
    time: "3 min per side",
    heat: "420 deg F",
    notes: "3 min per side",
    index: 6,
  },
  {
    name: "boneless pork shoulder in the crock pot",
    time: "8 hours",
    heat: "low",
    notes: "",
    index: 7,
  },
  {
    name: "egg in boiling water (hard boiled)",
    time: "8 minutes",
    heat: "boiling",
    notes: "",
    index: 7,
  },
]);
</script>

<style scoped>
#card {
  width: 600px;
  height: 800px;
  margin: 0 auto;
  margin-top: 72px;
}
svg {
  box-shadow: 0 0 10px 5px rgba(0, 0, 0, 0.2);
}

@media only screen and (max-width: 599px) {
  #card {
    width: 100vw;
    height: calc(100vh - 172px);
    margin: 0 auto;
    margin-top: 72px;
  }
}
</style>
