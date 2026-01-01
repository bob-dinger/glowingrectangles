<template>
  <v-app-bar id="app_bar">
    <!-- <v-app-bar-nav-icon @click="lefter = !lefter" /> -->
    <v-spacer></v-spacer>
    <v-avatar class="mr-2">
      <v-img
        alt="John"
        src="https://www.glowinggardens.io/assets/garden_clear.png"
        @click="lefter = !lefter"
      ></v-img>
    </v-avatar>

    <v-btn color="white" style="background: #111827">Glowing Gardens</v-btn>
    <v-spacer></v-spacer>
  </v-app-bar>

  <v-navigation-drawer width="300" v-model="lefter"> </v-navigation-drawer>

  <v-main>
    <v-container fluid id="main_container">
      <v-row>
        <v-col
          cols="12"
          xs="12"
          sm="12"
          md="3"
          lg="3"
          v-for="post in posts"
          :key="post.title"
        >
          <!-- <v-card>
            <v-img :src="post.img" aspect-ratio="1.5"></v-img>
            <v-card-title>{{ post.title }}</v-card-title>
          </v-card> -->
          <NuxtLink :to="`/posts/${post.route}`">
            <div class="postcard d-flex box-shadow-glow pa-2" style="border-radius: 4px">
              <img :src="post.img" style="height: 100px" />
              <div class="d-flex flex-column justify-center" style="margin-left: 5%">
                <div class="ml-2 post-title">{{ post.title }}</div>
                <div class="ml-2 post-subtitle">
                  {{ post.subtitle }}
                </div>
              </div>
            </div>
          </NuxtLink>
        </v-col>
      </v-row>
    </v-container>
  </v-main>
  <!-- <v-bottom-navigation>
    <v-btn icon>
      <v-icon>mdi-home</v-icon>
    </v-btn>
  </v-bottom-navigation> -->
</template>

<script setup>
let lefter = ref(false);

definePageMeta({
  head: {
    link: [
      {
        rel: "stylesheet",
        href:
          "https://fonts.googleapis.com/css2?family=Advent+Pro:ital,wght@0,100..900;1,100..900&display=swap",
      },
    ],
  },
});

let posts = ref([
  {
    title: "Join the Email List",
    subtitle: "Do it!",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/angel_and_dragon_square.png",
    route: "email_list",
  },
  {
    title: "Moral Tribes",
    subtitle: "why do our values differ?",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/moral_square.png",
    route: "moral_tribes",
  },
  {
    title: "Moral Foundations Theory",
    subtitle: "why Americans don't get along...",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/values_square.png",
    route: "moral_foundations_theory",
  },
  // {
  //   title: "Food",
  //   img:
  //     "https://glowinggardensstorage.blob.core.windows.net/images/title_images/diet.png",
  //   route: "food",
  // },
  {
    title: "Perception Gap",
    subtitle: "Americans Don't Understand Each Other",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/perceptiongap_square.png",
    route: "moral_tribes",
  },
  // {
  //   title: "The Angel & The Dragon",
  //   img:
  //     "https://glowinggardensstorage.blob.core.windows.net/images/title_images/angel_and_dragon_square.png",
  //   route: "angel_and_dragon",
  // },
  {
    title: "Voroni",
    subtitle: "A visual algorithm",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/voroni.png",
    route: "voroni",
  },
  {
    title: "Nonlinearity",
    subtitle: "The goldilocks principle",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/linearity3.png",
    route: "nonlinearity",
  },
  {
    title: "Binary",
    subtitle: "How computers store information",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/binary3.png",
    route: "binary",
  },
  {
    title: "Mosquitoes & Malaria",
    subtitle: "probability and geometry",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/mosquitos.png",
    route: "mosquitoes",
  },
  {
    title: "Box Breathing",
    subtitle: "calm your mind",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/box_breathing.png",
    route: "box_breathing",
  },
  {
    title: "524 Years",
    subtitle: "history in 500 years",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/524_years.png",
    route: "500years",
  },
  {
    title: "Taxonomy",
    subtitle: "know your life forms",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/taxonomy2.png",
    route: "taxonomy",
  },
  {
    title: "Random Visuals",
    subtitle: "just for fun",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/waves2.png",
    route: "random",
  },
  {
    title: "Bliss Symbolics",
    subtitle: "A visual language",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/bliss4.png",
    route: "bliss_symbolics",
  },
  {
    title: "The Elephant & The Rider",
    subtitle: "The divided mind",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/elephant6.png",
    route: "elephant_and_rider",
  },
  {
    title: "Nutrition",
    subtitle: "what's in food?",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/nutrition1.png",
    route: "food/nutrition/index2",
  },
  {
    title: "Cooking Times",
    subtitle: "how long to cook things",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/cooking-time1.png",
    route: "food/cooking_times",
  },
  {
    title: "Meditation Wheel",
    subtitle: "a metaphor for the scattered mind",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/meditation_wheel.png",
    route: "meditation_wheel",
  },
  {
    title: "Books",
    subtitle: "Some of my favorite books",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/books2.png",
    route: "books",
  },
  {
    title: "Cognitive Reflection Test",
    subtitle: "test your elephant & rider",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/cognitive2.png",
    route: "cognitive_reflection_test",
  },
  {
    title: "Emotions",
    subtitle: "our core drives",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/emotion_wave1.png",
    route: "books",
  },
  {
    title: "Antifragility",
    subtitle: "building strength",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/cracked2.png",
    route: "books",
  },
  {
    title: "Hormones",
    subtitle: "what do they do?",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/hormones_400.png",
    route: "body/hormones",
  },
  {
    title: "Enzymes",
    subtitle: "what do they do?",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/enzyme_400.png",
    route: "body/enzymes",
  },
]);
</script>

<style scoped>
/* #main_container {
  width: 800px;
  margin: 0 auto;
} */
body {
  font-family: "Carlito", sans-serif;
}
#app_bar {
  border-bottom: 1px solid green;
  box-shadow: none !important;
}
/* .box-shadow-glow {
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.2), 0 0 10px rgba(0, 0, 0, 0.15),
    0 0 10px rgba(0, 0, 0, 0.1), 0 0 10px rgba(255, 255, 255, 0.1);

  color: teal;
  font-family: "Carlito", sans-serif;
} */

.box-shadow-glow {
  border: 1px solid lightgrey;
}

.postcard:hover {
  background: #f0f0f0;
}

.post-title {
  font-size: 16px;
  font-weight: bold;
  color: teal;
}
.post-subtitle {
  font-size: 14px;
  color: grey;
}
/* body {
  overflow: scroll;
} */

a:visited {
  text-decoration: none !important;
}
a {
  text-decoration: none !important;
}
@media (max-width: 600px) {
  #main_container {
    width: 100vw;
  }
  img {
    width: 100px;
  }
}
</style>
