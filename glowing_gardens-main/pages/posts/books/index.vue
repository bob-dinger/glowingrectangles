<template>
  <Navbar />
  <div id="container">
    <div class="pa-4">A collection of some of my favorite books:</div>
    <div class="mb-4" v-for="book in books" :key="book">
      <div class="iframely-embed">
        <div class="iframely-responsive">
          <a data-iframely-url :href="book.url"></a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
//my favorite books
import { nextTick } from "vue";

let books = ref([
  {
    title: "Behave",
    url: "https://www.amazon.com/Behave-Biology-Humans-Best-Worst/dp/1594205078",
  },
  {
    title: "The Brain that Changes Itself",
    url: "https://www.amazon.com/Brain-That-Changes-Itself-Frontiers/dp/0143113100",
  },
  {
    title: "Factfulness",
    url:
      "https://www.amazon.com/Factfulness-Reasons-World-Things-Better-ebook/dp/B0756J1LLV",
  },
  {
    title: "How Not to Be Wrong",
    url: "https://www.amazon.com/How-Not-Be-Wrong-Mathematical/dp/0143127535",
  },
  {
    title: "Being Wrong",
    url: "https://www.amazon.com/Being-Wrong-Adventures-Margin-Error/dp/0061176052",
  },
  {
    title: "The Joy of X",
    url: "https://www.amazon.com/Joy-Guided-Tour-Math-Infinity/dp/0544105850",
  },
  {
    title: "The Righteous Mind",
    url: "https://www.amazon.com/Righteous-Mind-Divided-Politics-Religion/dp/0307455777",
  },
  {
    title: "Moral Tribes",
    url: "https://www.amazon.com/Moral-Tribes-Emotion-Reason-Between/dp/0143126059",
  },
  {
    title: "Thinking Fast and Slow",
    url: "https://www.amazon.com/Thinking-Fast-Slow-Daniel-Kahneman-ebook/dp/B00555X8OA",
  },
  {
    title: "Predictably Irrational",
    url:
      "https://www.amazon.com/Predictably-Irrational-Revised-Expanded-Decisions/dp/0061353248",
  },
  {
    title: "A Short History of Nearly Everything",
    url: "https://www.amazon.com/Short-History-Nearly-Everything/dp/076790818X",
  },
]);

onMounted(() => {
  nextTick(() => {
    iframely.load();
  });
});
</script>

<style scoped>
#container {
  width: 600px;
  margin: 0 auto;
  margin-top: 84px;
}
</style>
