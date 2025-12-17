//960/64=15
let tower=[
  3,
3,
4,
4,
4,
5,
5,
6,
6,
7,
8,
9,
10,
12,
13,
14,
16,
17,
19,
20,
22,
24,
26,
28,
30,
30,
32,
32,
34,
34,
35,
35,
35,
34,
34,
32,
32,
30,
30,
28,
26,
24,
22,
20,
19,
17,
16,
14,
13,
12,
10,
9,
8,
7,
6,
6,
5,
5,
4,
4,
4,
3,
3
]

let svg = document.querySelector('svg');

tower.forEach((dot, idx) => {
  
  for(let i=0; i<dot; i++){
      let circle = document.createElementNS('http://www.w3.org/2000/svg',"circle");
      circle.setAttribute("r", 7);
      circle.setAttribute("cx", (idx*15)+10);
      circle.setAttribute("cy", 590- (i*15));
      circle.setAttribute("class", `column${idx}`);
      if(idx<30)
      {
        circle.setAttribute("fill", "blue");
      }
      else if(idx==30 || idx==31 || idx==32){
        circle.setAttribute("fill", "purple");
      }
      else{
        circle.setAttribute("fill", "red");
      }

      svg.prepend(circle);
  }

});

gsap.to(".column4", .5, {y:"-=30", yoyo:true, repeat:1});