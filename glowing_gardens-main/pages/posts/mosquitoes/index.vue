<template>
  <div :style="`width:${container_width}px;margin:0 auto;margin-top:8px;`">
    <svg
      viewBox="0 0 600 600"
      :style="`width:300px;height:300px;margin:0 auto;margin-left:16px;`"
    ></svg>
  </div>
</template>

<script setup>
// import { gsap } from "/gsap-core.js";
// import { drawSVG } from "/DrawSVGPlugin.js";
import { useDisplay } from "vuetify";
const { mdAndDown } = useDisplay();
let svg_width = ref(300);
let container_width = ref(610);
import { gsap } from "gsap";

/* The following plugin is a Club GSAP perk */
import { DrawSVGPlugin } from "gsap/DrawSVGPlugin";
import { TextPlugin } from "gsap/TextPlugin";

gsap.registerPlugin(DrawSVGPlugin);
// import { gsap } from "esm/gsap-core.js";
// import { DrawSVGPlugin } from "esm/DrawSVGPlugin.js";

// // Register the plugin
// gsap.registerPlugin(DrawSVGPlugin);

// //import { gsap } from "gsap";
// // Dynamically import gsap-core.js from the static folder
// const gsapModule = await import("/gsap-core.js");
// const gsap = gsapModule.gsap; // Adjust based on how gsap-core.js exports gsap

// // Do the same for the DrawSVGPlugin
// const drawSVGModule = await import("/DrawSVGPlugin.js");
// const drawSVG = drawSVGModule.drawSVG; // Adjust based on export

// definePageMeta({
//   script: [
//     { src: "/gsap.min.js", type: "text/javascript", async: true },
//     { src: "/DrawSVGPlugin.min.js", type: "text/javascript", async: true },
//   ],
// });

onMounted(() => {
  if (mdAndDown.value) {
    container_width.value = window.innerWidth - 8;
    svg_width.value = window.innerWidth - 48;
    console.log("md and down");
  } else {
    svg_width.value = 600;
    container_width.value = 620;
  }
  let svger = document.querySelector("svg");
  //svger.style.height = svg_width.value + "px";
  svger.addEventListener("click", function () {
    animate();
  });
});

const animate = () => {
  //let pather = document.querySelector("#pather");
  let svg = document.querySelector("svg");

  let choices = [-5, 5];
  let current_point = [300, 300];
  let current_string = "M300,300";

  for (let r = 0; r < 1000; r++) {
    const random_x = choices[Math.floor(Math.random() * 2)];
    const random_y = choices[Math.floor(Math.random() * 2)];
    // console.log(random_x);
    // console.log(random_y);

    let new_string = "";
    let rando = Math.random();

    if (rando < 0.5) {
      new_string =
        current_string + ` L${current_point[0] + random_x},${current_point[1]}`;
      current_string =
        current_string + ` L${current_point[0] + random_x},${current_point[1]}`;
      current_point[0] = current_point[0] + random_x;
    } else {
      new_string =
        current_string + ` L${current_point[0]},${current_point[1] + random_y}`;
      current_string =
        current_string + ` L${current_point[0]},${current_point[1] + random_y}`;
      current_point[1] = current_point[1] + random_y;
    }

    //gsap.to("#pather", {duration:1, d:new_string});

    //pather.setAttribute("d", new_string);
    svg.innerHTML = `<path id="pather" d="${new_string}" stroke="red" fill="none" stroke-width="2" stroke-opacity="1"/>`;
  }
  //console.log(current_string);

  //   let intro = gsap.timeline();

  //   intro.fromTo(
  //     "#pather",
  //     4,
  //     { drawSVG: "0%" },
  //     { drawSVG: "100%", ease: "Power2.easOut" }
  //   );

  let intro = gsap.timeline();
  //let tl = new TimelineMax();

  //tl.to('#recter', 2, {x:"+=300"});
  intro.fromTo("#pather", { drawSVG: "0%" }, { duration: 4, drawSVG: "100%" });

  //.to("#pather", { drawSVG: "100% 100%", delay: 1 });
};
</script>

<style scoped>
/* svg {
  box-shadow: 0 0 8px rgba(0, 150, 255, 0.6);
} */
#pather {
  transform: translate3d(0, 0, 0);
}
svg {
  border: 1px solid navy;
  height: 300px;
  width: 300px;
}
</style>
~/static/umd/gsap.js~/static/umd/DrawSVGPlugin.js
