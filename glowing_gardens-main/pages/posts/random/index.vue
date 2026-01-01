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
    <v-container fluid>
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
            <div class="d-flex box-shadow-glow pa-2" style="border-radius: 4px">
              <img :src="post.img" style="height: 100px" />
              <div
                class="d-flex justify-center align-center items-center flex-column"
                style="margin-left: 5%"
              >
                <div class="ml-2 post-title">{{ post.title }}</div>
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
    title: "Waves",
    img:
      "https://glowinggardensstorage.blob.core.windows.net/images/title_images/waves2.png",
    route: "random/waves",
  },
]);
</script>

<style scoped>
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

.post-title {
  font-size: 18px;
  font-weight: bold;
  color: teal;
}
/* body {
  overflow: scroll;
} */

a:visited {
  text-decoration: none;
}
a {
  text-decoration: none !important;
}
</style>
