<template>
  <Navbar />
  <div id="container" class="markdown">
    <v-carousel :show-arrows="false" :hide-delimiters="true" id="car" v-model="indexer">
      <v-carousel-item>
        <MarkdownContent
          :file_url="'https://raw.githubusercontent.com/bob-dinger/gg_markdown/main/hormones/intro.md'"
        />
      </v-carousel-item>
      <v-carousel-item>
        <MarkdownContent
          :file_url="'https://raw.githubusercontent.com/bob-dinger/gg_markdown/main/hormones/hormone_exp.md'"
        />
      </v-carousel-item>
      <v-carousel-item>
        <MarkdownContent
          :file_url="'https://raw.githubusercontent.com/bob-dinger/gg_markdown/main/hormones/how_many.md'"
        />
      </v-carousel-item>
    </v-carousel>
  </div>
  <v-bottom-navigation>
    <v-btn color="purple" @click="click_back_button">Back</v-btn>
    <v-btn color="purple" @click="click_next_button">Next</v-btn>
  </v-bottom-navigation>
</template>

<script setup>
let indexer = ref(0);
let card_count = 3;
const click_next_button = () => {
  //indexer.value = indexer.value + 1;
  if (indexer.value >= card_count - 1) {
    indexer.value = 0;
  } else {
    indexer.value = indexer.value + 1;
  }
};

const click_back_button = () => {
  if (indexer.value == 0) {
    indexer.value = card_count - 1;
  } else {
    indexer.value = indexer.value - 1;
  }
};
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
