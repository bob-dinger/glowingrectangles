<template>
  <v-app-bar id="app_bar" clipped="true">
    <!-- <v-app-bar-nav-icon @click="lefter = !lefter" /> -->
    <v-spacer></v-spacer>
    <v-avatar class="mr-2">
      <v-img
        alt="John"
        src="https://www.glowinggardens.io/assets/garden_clear.png"
      ></v-img>
    </v-avatar>

    <NuxtLink to="/">
      <v-btn color="white" style="background: #111827">Glowing Gardens</v-btn>
    </NuxtLink>
    <v-spacer></v-spacer>
  </v-app-bar>
</template>

<script setup>
//@click="lefter = !lefter"
</script>

<style scoped></style>
