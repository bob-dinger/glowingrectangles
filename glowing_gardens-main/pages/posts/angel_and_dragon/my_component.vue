<template>
  <svg viewbox="0 0 600 600">
    <circle id="circler" cx="300" cy="300" r="100" fill="red"/>
  </svg>
</template>

<script setup>
onMounted(() => {
//   let circler = document.querySelector('#circler');
//   circler.setAttribute('fill', 'blue');
    let svg = document.querySelector('svg');
    svg.addEventListener('mouseover', () => {
        let circler = document.querySelector('#circler');
        circler.setAttribute("fill", "green");
    })
});


</script>

<style  scoped>
svg{
    width:600px;
    border:1px solid navy;
}
</style>