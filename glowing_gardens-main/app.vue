<template>
  <v-app>
    <NuxtPage />
  </v-app>
</template>
<style>
img {
  max-width: 600px !important;
}
.markdown p {
  margin-bottom: 8px;
}
.markdown blockquote {
  padding: 0.5em 1em;
  border-left: 5px solid #eee;
  margin: 0;
  background-color: #f9f9f9;
  color: #333;
}
@media (max-width: 600px) {
  img {
    max-width: 90vw !important;
  }
}
</style>
