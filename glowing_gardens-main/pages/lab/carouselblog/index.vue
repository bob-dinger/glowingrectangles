<template>
  <Navbar />
  <div id="container">
    <v-carousel :show-arrows="false" :hide-delimiters="true" id="car">
      <v-carousel-item>
        <PostOne />
      </v-carousel-item>
      <v-carousel-item>
        <PostTwo />
      </v-carousel-item>
      <v-carousel-item>
        <!-- <svg style="height: 600px; width: 600px"></svg> -->
        <PostThree />
      </v-carousel-item>
      <v-carousel-item>
        <MarkdownContent
          :file_url="'https://glowinggardensstorage.blob.core.windows.net/images/mds/four.md'"
        />
      </v-carousel-item>
      <v-carousel-item>
        <MarkdownContent
          :file_url="'https://raw.githubusercontent.com/bob-dinger/gg_markdown/main/moral_foundations_theory/sanctity.md'"
        />
      </v-carousel-item>
    </v-carousel>
  </div>
  <v-bottom-navigation>
    <v-btn color="purple">Next</v-btn>
  </v-bottom-navigation>
</template>

<script setup>
import PostOne from "./post/one.vue";
import PostTwo from "./post/two.vue";
import PostThree from "./post/three.vue";

let file_url2 = ref("");
</script>

<style scoped>
#container {
  width: 600px;
  margin: 0 auto;
  margin-top: 68px;
  height: calc(100vh - 132px) !important;
  overflow-x: hidden;
  padding: 16px;
  overflow-y: hidden;
}
#car {
  height: calc(100vh - 132px) !important;
  overflow-x: hidden;
  width: 600px;
}

svg {
  box-shadow: 0 0 10px 5px rgba(0, 0, 0, 0.2);
}

@media (max-width: 600px) {
  #container {
    width: 100vw;
  }
  svg {
    width: 100vw;
  }
  #car {
    height: calc(100vh - 132px) !important;
    overflow-x: hidden;
    width: 100vw;
  }
  #car img {
    width: 100vw;
  }
}
</style>
