<template>
  <Navbar />
  <div id="container">
    <h2>DNA</h2>
    <div>Within each of our cells we have a full copy of all our DNA.</div>
    <div>These are wrapped up in chromosomes.</div>
    <img
      src="https://glowinggardensstorage.blob.core.windows.net/images/posts/PX000098_PRESENTATION.jpeg"
    />
    <div>Within each of our cells we have a full copy of all our DNA.</div>
    <div>These are wrapped up in chromosomes.</div>
    <div>Within each of our cells we have a full copy of all our DNA.</div>
    <div>These are wrapped up in chromosomes.</div>
    <div>Within each of our cells we have a full copy of all our DNA.</div>
    <div>These are wrapped up in chromosomes.</div>
    <div>Within each of our cells we have a full copy of all our DNA.</div>
    <div>These are wrapped up in chromosomes.</div>
    <PhenotypeCard />
  </div>
</template>

<script setup>
import PhenotypeCard from "./cards/phenotype";

//humans have 3 billion base pairs of DNA
//the genome is present in every cell of our body (in the nucleus)
//it is wrapped in a double helix
//the instructions for building and maintaining the body are stored in the DNA
</script>

<style scoped>
#container {
  width: 600px;
  margin: 0 auto;
  margin-top: 84px;
  box-shadow: 0 8px 10px -5px rgba(0, 0, 0, 0.2);
  padding: 16px;
}
#container img {
  width: 96%;
}
#container div {
  margin-bottom: 16px;
}
</style>
