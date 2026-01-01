<template>
  <div
    id="texter"
    style="
      width: 50%;
      height: 100%;
      margin-left: 25%;
      position: absolute;
      font-size: 20px;
    "
  >
    Pancakes
  </div>
  <svg viewBox="0 0 800 800">
    <circle
      cx="400"
      cy="400"
      r="200"
      fill="red"
      stroke="navy"
      stroke-width="4"
      opacity=".4"
    />
    <image
      href="https://glowinggardensstorage.blob.core.windows.net/glyfs/images/food/pancakes.png"
      preserveAspectRatio="none"
      width="50"
      height="50"
      x="375"
      y="375"
    ></image>
  </svg>
</template>

<script setup>
import { gsap } from "gsap";
import { TextPlugin } from "gsap/TextPlugin";
gsap.registerPlugin(TextPlugin);

onMounted(() => {
  let tl = gsap.timeline();
  gsap.to("image", { duration: 2, scale: 4, transformOrigin: "center" });
  tl.set("#texter", { text: "" });
  tl.to("#texter", {
    duration: 5,
    text:
      "Pancakes are, without a doubt, the most delicious food ever conceived by Man...",
    ease: "none",
  });
  tl.set("#texter", { text: "" });
  tl.to("#texter", {
    duration: 5,
    text:
      "If you doubt me, simply eat one. Just one. Eat it! Then come back to me with that smug attitude!",
    ease: "none",
  });
});
</script>

<style scoped>
svg {
  border: 1px solid navy;
  width: 100%;
  height: auto;
  position: absolute;
  left: 0;
  top: 0;
}
</style>
