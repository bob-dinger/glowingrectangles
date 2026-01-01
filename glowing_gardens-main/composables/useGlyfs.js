//create composable for nuxt 3 named useGlyfs

import { ref } from 'vue'

export default function useGlyfs() {

    const degrees_to_radians = (degrees)=>{
        return degrees * (Math.PI/180);
    }

    const radians_to_degrees = (radians)=>{
        return radians * (180/Math.PI);
    }

    const circle = (element, x, y, radius)=>{
        

    }

    const rect = (element, x, y, radius)=>{
        

    }

    const randbtw = (min, max)=>{
        return Math.random() * (max - min) + min;
    }

    const randomPoint = () =>{
        return {'x':randbtw(0, 800), 'y':randbtw(0, 800)};
    }

    const circle_points = (x, y, radius, nu_points)=>{
        let my_data=[];

        let stepper = 360/nu_points;
        
        for (let i=0; i<360; i=i+stepper){
                my_data.push({'x':x + (radius*Math.cos(degrees_to_radians(i))), 'y':y-(radius*Math.sin(degrees_to_radians(i)))});    
            }//end loop

        return my_data;
    };








    
    return { circle_points }
    }


