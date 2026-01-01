<template>
  <Navbar />
  <div id="container">
    <svg viewBox="0 0 500 500" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <path
          id="waver"
          d="M 703.375 545.703 L -82.666 549.136 C -82.666 549.136 -89.092 188.826 -76.659 206.522 C -64.226 224.218 -51.792 224.218 -39.359 206.522 C -26.926 188.825 -14.493 188.825 -2.059 206.522 C 10.374 224.218 22.807 224.218 35.241 206.522 C 47.674 188.825 60.107 188.825 72.54 206.522 C 84.973 224.218 97.407 224.218 109.84 206.522 C 122.273 188.825 134.706 188.825 147.14 206.522 C 159.573 224.218 172.006 224.218 184.44 206.522 C 196.873 188.825 209.306 188.825 221.739 206.522 C 234.173 224.218 246.606 224.218 259.039 206.522 C 271.472 188.825 283.905 188.825 296.339 206.522 C 308.772 224.218 321.205 224.218 333.639 206.522 C 346.072 188.825 358.505 188.825 370.939 206.522 C 383.372 224.218 395.805 224.218 408.238 206.522 C 420.671 188.825 433.105 188.825 445.538 206.522 C 457.971 224.218 470.404 224.218 482.838 206.522 C 495.271 188.825 507.704 188.825 520.138 206.522 C 532.571 224.218 545.004 224.218 557.437 206.522 C 569.871 188.825 582.304 188.825 594.737 206.522 C 607.17 224.218 619.603 224.218 632.037 206.522 C 644.47 188.825 656.903 188.825 669.337 206.522 L 703.375 545.703 Z"
          stroke="blue"
          stroke-width="2"
        ></path>
      </defs>
      <use
        xlink:href="#waver"
        x="0"
        y="-200"
        fill="rgba(25, 118, 210, 0.1)"
        class="wave"
      />
      <use
        xlink:href="#waver"
        x="0"
        y="-150"
        fill="rgba(25, 118, 210, 0.2)"
        class="wave"
      />
      <use
        xlink:href="#waver"
        x="0"
        y="-100"
        fill="rgba(25, 118, 210, 0.3)"
        class="wave"
      />
      <use
        xlink:href="#waver"
        x="0"
        y="-50"
        fill="rgba(25, 118, 210, 0.4)"
        class="wave"
      />
      <use xlink:href="#waver" x="0" y="0" fill="rgba(25, 118, 210, 0.5)" class="wave" />
      <use xlink:href="#waver" x="0" y="50" fill="rgba(25, 118, 210, 0.6)" class="wave" />
      <use
        xlink:href="#waver"
        x="0"
        y="100"
        fill="rgba(25, 118, 210, 0.7)"
        class="wave"
      />
      <use
        xlink:href="#waver"
        x="0"
        y="150"
        fill="rgba(25, 118, 210, 0.8)"
        class="wave"
      />
      <use
        xlink:href="#waver"
        x="0"
        y="200"
        fill="rgba(25, 118, 210, 0.9)"
        class="wave"
      />
      <use xlink:href="#waver" x="0" y="250" fill="rgba(25, 118, 210, 1)" class="wave" />
    </svg>
  </div>
</template>

<script setup>
import { gsap } from "gsap";

onMounted(() => {
  // Select all <use> elements with the class 'wave'
  const waves = gsap.utils.toArray(".wave");

  waves.forEach((wave) => {
    // For each wave, create a timeline that loops indefinitely
    const tl = gsap.timeline({ repeat: -1, yoyo: true });

    // Add a "to" animation to the timeline, randomizing the y movement, duration, and delay
    tl.to(wave, {
      y: `+=${gsap.utils.random(10, 30)}`, // Random movement in the y direction between 10 and 30 pixels
      duration: gsap.utils.random(1, 3), // Random duration between 1 and 3 seconds for each animation cycle
      ease: "sine.inOut", // Use a sine ease for smooth motion
      delay: gsap.utils.random(0, 0.5), // Random delay before starting the animation, to desynchronize the waves
    });
  });
});
</script>

<style scoped>
#container {
  width: 600px;
  margin: 0 auto;
  margin-top: 84px;
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
}
</style>
