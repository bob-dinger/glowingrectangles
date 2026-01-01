// https://nuxt.com/docs/api/configuration/nuxt-config
import vuetify, { transformAssetUrls } from 'vite-plugin-vuetify'


export default defineNuxtConfig({
  devtools: { enabled: true },
  build: {
    transpile: ['vuetify'],
  },
  modules: ['@vueuse/nuxt',
    (_options, nuxt) => {
      nuxt.hooks.hook('vite:extendConfig', (config) => {
        // @ts-expect-error
        config.plugins.push(vuetify({ autoImport: true }))
      })
    },
    //...
  ],
  vite: {
    vue: {
      template: {
        transformAssetUrls,
      },
    },
  },
  app:{
    head:{
      title:'Glowing Gardens',
      meta:[
        { name:'description', content:'News Coverage'},
        { name: 'viewport', content: 'width=device-width, initial-scale=1, viewport-fit=cover' },
      ],
      link:[
        { rel: 'icon', type: 'image/x-icon', href: 'https://glowinggardensstorage.blob.core.windows.net/images/favicon.ico' },
        {rel:'stylesheet', href:'https://fonts.googleapis.com/icon?family=Material+Icons'},
        {rel:'stylesheet', href:"https://fonts.googleapis.com/css2?family=Carlito:ital,wght@0,400;0,700;1,400;1,700&display=swap"  },

      ],
      script: [{ src: "https://cdn.iframe.ly/embed.js?card=small&api_key=f01308556542a43a1b7a01&iframe=card" },
      {src:"https://glowinggardensstorage.blob.core.windows.net/glyfs/glyfs1.js"}
  

]
    }
  } 
});
