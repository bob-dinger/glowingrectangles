<template>
  <div :style="`width:${container_width}px; margin: 0 auto`">
    <v-row class="ma-1">
      <v-col cols="12" sm="12" class="my-2">
        <NuxtLink :to="`/posts/food/nutrition`">
          <v-card class="mx-auto" max-width="100%" height="100">
            <v-card-title>Nutrition</v-card-title>
          </v-card>
        </NuxtLink>
        <NuxtLink :to="`/posts/food/nutrition`">
          <v-card class="mx-auto mt-4" max-width="100%" height="100">
            <v-card-title>Foods</v-card-title>
          </v-card>
        </NuxtLink>
        <NuxtLink :to="`/posts/food/nutrition`">
          <v-card class="mx-auto mt-4" max-width="100%" height="100">
            <v-card-title>Recipes</v-card-title>
          </v-card>
        </NuxtLink>

        <NuxtLink :to="`/posts/food/nutrition`">
          <v-card class="mx-auto mt-4" max-width="100%" height="100">
            <v-card-title>How It's Made</v-card-title>
          </v-card>
        </NuxtLink>

        <NuxtLink :to="`/posts/food/nutrition`">
          <v-card class="mx-auto mt-4" max-width="100%" height="100">
            <v-card-title>Spoilage</v-card-title>
          </v-card>
        </NuxtLink>

        <NuxtLink :to="`/posts/food/nutrition`">
          <v-card class="mx-auto mt-4" max-width="100%" height="100">
            <v-card-title>Equipment</v-card-title>
          </v-card>
        </NuxtLink>
        <NuxtLink :to="`/posts/food/nutrition`">
          <v-card class="mx-auto mt-4" max-width="100%" height="100">
            <v-card-title>Cooking</v-card-title>
          </v-card>
        </NuxtLink>
        <NuxtLink :to="`/posts/food/cooking_times`">
          <v-card class="mx-auto mt-4" max-width="100%" height="100">
            <v-card-title>Cooking Times</v-card-title>
          </v-card>
        </NuxtLink>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { useDisplay } from "vuetify";
const { mdAndDown } = useDisplay();
let container_width = ref(600);

onMounted(() => {
  if (mdAndDown.value) {
    container_width.value = window.innerWidth - 16;
  }
});

// let foods = ref([
//   "banana",
//   "apple",
//   "orange",
//   "grape",
//   "strawberry",
//   "blueberry",
//   "kiwi",
//   "mango",
//   "pineapple",
//   "watermelon",
//   "ground beef",
//   "chicken breast",
//   "filet",
//   "bacon",
//   "sausage",
//   "turkey",
//   "salmon",
// ]);
</script>

<style scoped></style>
