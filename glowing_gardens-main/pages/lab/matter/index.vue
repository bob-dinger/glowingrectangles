<template>
  <div ref="scene"></div>
</template>

<script setup>
import { onMounted, ref } from "vue";

const scene = ref(null);

onMounted(() => {
  if (import.meta.env.SSR) return; // Ensure we're not on server-side

  import("matter-js").then((Matter) => {
    // Alias the module for easier usage
    const { Engine, Render, Bodies, World } = Matter;

    // Create an engine
    const engine = Engine.create();

    // Create a renderer and attach it to the scene ref
    const render = Render.create({
      element: scene.value, // Use the ref's value as the element
      engine: engine,
      options: {
        width: 800,
        height: 600,
        wireframes: false,
      },
    });

    // Create two boxes and a ground
    const boxA = Bodies.rectangle(400, 200, 80, 80);
    const boxB = Bodies.rectangle(450, 50, 80, 80);
    const ground = Bodies.rectangle(400, 610, 810, 60, { isStatic: true });

    // Add the bodies to the world
    World.add(engine.world, [boxA, boxB, ground]);

    // Run the engine and renderer
    Engine.run(engine);
    Render.run(render);
  });
});
</script>

<style scoped>
div {
  width: 100%;
  height: 100%;
}
</style>
