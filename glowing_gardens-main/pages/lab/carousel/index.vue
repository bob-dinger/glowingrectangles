<template>
  <div :style="`width:${carousel_width}px;margin:0 auto;`">
    <v-carousel
      id="carouseler"
      v-if="loaded"
      height="100vh"
      :width="carousel_width"
      :show-arrows="false"
      :hide-delimiters="false"
      v-model="indexer"
      transition="fade-transition"
      class="mx-auto"
    >
      <v-carousel-item>
        <v-card
          height="100%"
          width="100%"
          class="mt-2 mx-auto"
          elevation="8"
          color="#EFEBE9"
          style="position: relative; overflow-y: scroll"
        >
          <v-container>
            <v-row>
              <v-col cols="12">
                <svg
                  id="svg1"
                  viewbox="0 0 600 600"
                  class="elevation-24"
                  width="98%"
                ></svg>
              </v-col>
            </v-row>

            <v-row class="mx-auto">
              <v-col cols="12">
                <div>
                  Lorem ipsum dolor sit amet, consectetur adipisicing elit. Libero beatae,
                  perferendis laborum magnam impedit tenetur optio veniam aliquam, rerum
                  soluta maiores praesentium illum, amet quia dolore excepturi. Reiciendis
                  animi molestias delectus, officia repudiandae ullam libero labore, fugit
                  doloremque vel quisquam velit laboriosam quos harum illo, deserunt eos
                  tempore amet tenetur earum assumenda. Incidunt unde praesentium placeat
                  optio ipsa ipsum, adipisci accusantium at reiciendis perferendis cum
                  quam temporibus, velit fuga! Aliquam, possimus optio repudiandae ducimus
                  dolorum deserunt sunt perferendis nemo cupiditate, iusto blanditiis!
                  Delectus, sed voluptates nemo amet fugit mollitia ex optio quidem veniam
                  dolorum corrupti voluptate aperiam fuga, hic explicabo quam eligendi
                  saepe assumenda! Nostrum libero facilis mollitia ex? Dolorem cum iste
                  iure unde eos harum, praesentium dolor, mollitia debitis itaque quae
                  necessitatibus doloribus hic neque esse modi nesciunt numquam. Odit
                  soluta hic rerum nihil? Nesciunt amet dignissimos at deleniti error
                  reprehenderit temporibus, mollitia reiciendis doloremque deserunt magni
                  velit facilis eligendi consequuntur provident laborum, veniam
                  necessitatibus numquam est cum harum! Totam exercitationem eaque
                  accusantium fuga, a repellendus at reiciendis quos saepe, veniam vel ut
                  distinctio doloremque, tempore quod. Distinctio, repudiandae. Magni iste
                  commodi reprehenderit quam labore minus nobis quaerat quae placeat. Illo
                  quas laboriosam facilis modi optio ducimus est sunt ipsum. Illo,
                  aperiam. Adipisci quas autem aliquid quam, rem dolore odit facilis quod
                  earum eligendi minima? Quidem, dolore! Aliquam sit, inventore,
                  voluptatem necessitatibus dicta voluptatum non natus, libero temporibus
                  at laborum quod minus unde sequi. Beatae cupiditate ab consequatur ex!
                  Illo fuga excepturi necessitatibus enim porro nihil, deserunt magnam,
                  doloremque accusantium cupiditate ipsam. Eius enim facilis, dicta, illum
                  officia numquam architecto iusto accusamus a eveniet quidem? Commodi
                  autem ea, hic aut harum nisi veniam corporis saepe expedita dicta, dolor
                  natus quis quo perferendis pariatur sed fugiat ipsa? Quam itaque atque
                  maxime, vel molestias eius perspiciatis sequi debitis a sed quae
                  consectetur cum unde deserunt quia architecto excepturi sunt saepe,
                  voluptatibus dicta ex dolorum quo. Eius excepturi, accusamus voluptatem
                  id aliquid exercitationem deserunt at? Maiores ex non modi rerum id
                  ducimus nesciunt tenetur aperiam accusantium corrupti totam a itaque
                  iste voluptate neque dolor, reiciendis obcaecati quibusdam voluptatem
                  temporibus ratione, enim facere repellat. Quasi, nostrum! Perspiciatis
                  maxime ad quis, iure aspernatur doloremque dicta numquam, alias labore,
                  officiis ratione nulla facilis deleniti non. Nam mollitia laborum ullam
                  culpa aut magni dolorum suscipit. Laborum in ipsum vero architecto cum
                  voluptas necessitatibus fuga, veritatis ullam facilis impedit incidunt
                  doloremque quidem et officia. Possimus, ut mollitia?
                </div>
              </v-col>
            </v-row>
          </v-container>
        </v-card>
      </v-carousel-item>

      <v-carousel-item>
        <v-card
          height="90%"
          width="90%"
          class="mx-auto mt-2"
          elevation="8"
          color="#EFEBE9"
          style="position: relative"
        >
          <v-container>
            <v-row>
              <v-col cols="12">
                <svg
                  id="svg2"
                  viewbox="0 0 600 600"
                  class="elevation-24"
                  width="98%"
                ></svg>
              </v-col>
            </v-row>

            <v-row>
              <v-col cols="12">
                <v-btn class="player" color="pink" fab dark>
                  <v-icon>mdi-plus</v-icon>
                </v-btn>
              </v-col>
            </v-row>
          </v-container>
        </v-card>
      </v-carousel-item>

      <v-carousel-item>
        <v-card
          height="98%"
          width="98%"
          class="mx-auto mt-2"
          elevation="8"
          color="#EFEBE9"
          style="position: relative; overflow-y: scroll"
        >
          <div class="d-flex flex-column" style="overflow-y: scroll">
            <svg
              id="svg3"
              viewbox="0 0 600 600"
              style="width: 98%; height: auto; background: blue"
            ></svg>
            <div class="pa-4">
              Lorem ipsum dolor sit amet consectetur adipisicing elit. Illum inventore,
              consectetur doloribus voluptate error quae, dolores temporibus expedita
              iste, esse officiis ut tenetur praesentium accusamus. Saepe eum blanditiis
              minima beatae necessitatibus quod harum iusto cupiditate tempore itaque
              consequuntur asperiores ducimus, laboriosam odio nihil illo et sapiente
              explicabo quibusdam expedita amet atque ea alias! Ab dolor officiis maiores
              dolores aspernatur eveniet optio a soluta minus! Aliquam eos reprehenderit
              tenetur eveniet! Vitae non libero neque modi dolores quasi impedit
              perspiciatis dolorum similique accusamus, sit magni corrupti culpa, odit
              ipsa deserunt tenetur eum nihil quod obcaecati maxime consequatur labore?
              Alias asperiores placeat iste officiis omnis quis dicta harum animi,
              quisquam assumenda commodi accusamus ad dolorem suscipit vitae quo, eius
              quod quidem consectetur distinctio eum! Sint saepe officia exercitationem?
              Tempore earum, voluptatibus, perspiciatis nihil eaque tenetur numquam
              blanditiis ipsum quae suscipit aperiam, odio sapiente ullam! Est nemo
              tenetur nam, sint et omnis vitae, iste sapiente ut ab sit unde deleniti odit
              corporis praesentium voluptas quo labore quis provident aspernatur fugiat?
              Iusto fugit odit ratione voluptatibus nobis dicta et, repellendus autem nam,
              dolorem, aut impedit. Numquam rem doloribus nisi a, itaque, optio at, quo
              facilis accusantium expedita blanditiis odio eaque. Suscipit deserunt libero
              deleniti! Incidunt.
            </div>
          </div>
        </v-card>
      </v-carousel-item>
    </v-carousel>
  </div>
</template>

<script setup>
let loaded = ref(true);
let indexer = ref(0);
import { nextTick } from "vue";
let carousel_width = ref(600);
import { useDisplay } from "vuetify";
const { mdAndDown } = useDisplay();

onMounted(() => {
  //loaded.value = true;

  if (mdAndDown.value) {
    console.log("md and down");
    carousel_width.value = window.innerWidth - 24;
  }

  nextTick().then(() => {
    let svg1 = document.querySelector("#svg1");
    let svg1_width = svg1.getBoundingClientRect().width;
    svg1.style.height = svg1_width + "px";
  });
});

//watch indexer
watch(indexer, (newIndex, oldIndex) => {
  if (newIndex === 1) {
    console.log("indexer changed to 1");
    nextTick().then(() => {
      let svg2 = document.querySelector("#svg2");
      if (svg2) {
        let svg2_width = svg2.getBoundingClientRect().width;
        svg2.style.height = svg2_width + "px";
      } else {
        console.log("SVG element not found");
      }
    });
  } else if (newIndex === 2) {
    nextTick().then(() => {
      let svg3 = document.querySelector("#svg3");
      if (svg3) {
        let svg3_width = svg3.getBoundingClientRect().width;
        svg3.style.height = svg3_width + "px";
      } else {
        console.log("SVG element not found");
      }
    });
  }
});
</script>

<style scoped>
#carouseler {
  margin: 0 auto;
}

::-webkit-scrollbar {
  width: 0.2em;
}

::-webkit-scrollbar-track {
  box-shadow: inset 0 0 6px white !important;
}

::-webkit-scrollbar-thumb {
  background-color: white !important;
  outline: 1px solid white !important;
}

.player {
  position: absolute;
  left: 45%;
  bottom: 100px;
}
</style>
