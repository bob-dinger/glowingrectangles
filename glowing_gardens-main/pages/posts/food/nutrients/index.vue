<template>
  <Navbar />
  <div id="container">
    <v-carousel :show-arrows="false" :hide-delimiters="true" id="car" v-model="indexer">
      <v-carousel-item>
        <MarkdownContent
          :file_url="'https://raw.githubusercontent.com/bob-dinger/gg_markdown/main/nutrients/intro.md'"
        />
      </v-carousel-item>
      <v-carousel-item>
        <MarkdownContent
          :file_url="'https://raw.githubusercontent.com/bob-dinger/gg_markdown/main/nutrients/carbs.md'"
        />
      </v-carousel-item>
      <v-carousel-item>
        <MarkdownContent
          :file_url="'https://raw.githubusercontent.com/bob-dinger/gg_markdown/main/nutrients/fats.md'"
        />
      </v-carousel-item>
      <v-carousel-item>
        <MarkdownContent
          :file_url="'https://raw.githubusercontent.com/bob-dinger/gg_markdown/main/nutrients/proteins.md'"
        />
      </v-carousel-item>
    </v-carousel>
  </div>
  <v-bottom-navigation>
    <v-btn id="next_button" color="purple">({{ indexer + 1 }} / 10) Next </v-btn>
  </v-bottom-navigation>
</template>

<script setup>
let indexer = ref(0);
</script>

<style scoped>
#next_button {
  background: #111827 !important;
  color: white !important;
}
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

  img {
    max-width: 90vw !important;
  }
}
</style>
