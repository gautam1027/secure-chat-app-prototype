const canvas = document.getElementById("bgCanvas");
const ctx = canvas.getContext("2d");

let particles = [];
let mouse = {
    x: window.innerWidth / 2,
    y: window.innerHeight / 2,
    px: window.innerWidth / 2,
    py: window.innerHeight / 2,
    speed: 0,
    moving: false,
    lastMove: Date.now()
};

function resizeCanvas(){
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}
window.addEventListener("resize", resizeCanvas);
resizeCanvas();

window.addEventListener("mousemove", e => {
    mouse.px = mouse.x;
    mouse.py = mouse.y;

    mouse.x = e.clientX;
    mouse.y = e.clientY;

    const dx = mouse.x - mouse.px;
    const dy = mouse.y - mouse.py;

    mouse.speed = Math.sqrt(dx*dx + dy*dy);
    mouse.moving = true;
    mouse.lastMove = Date.now();
});

const colors = [
    "rgba(37,211,102,0.95)",
    "rgba(255,255,255,0.9)",
    "rgba(0,255,255,0.85)",
    "rgba(180,120,255,0.85)"
];

class Particle{
    constructor(){
        this.reset();
    }

    reset(){
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height;

        this.vx = (Math.random() - 0.5) * 0.8;
        this.vy = (Math.random() - 0.5) * 0.8;

        this.size = Math.random() * 2.2 + 0.7;
         let r = Math.random();

        if(r < 0.70){
        this.color = "rgba(255,255,255,1)";
        }
        else if(r < 0.95){
        this.color = "#2ad96a";
        }
        else{
        this.color = "rgba(0,255,255,0.85)";
        }

        this.offset = Math.random() * Math.PI * 2;
        }

    update(i){

    const idle = Date.now() - mouse.lastMove > 140;

    let dx = mouse.x - this.x;
    let dy = mouse.y - this.y;

    let dist = Math.sqrt(dx*dx + dy*dy) || 1;

    if(this.mode === "ambient"){

    this.vx += (Math.random() - 0.5) * 0.002;
    this.vy += (Math.random() - 0.5) * 0.002;

    this.vx *= 0.985;
    this.vy *= 0.985;

    this.x += this.vx;
    this.y += this.vy;

    if(this.x < -20) this.x = canvas.width + 20;
    if(this.x > canvas.width + 20) this.x = -20;
    if(this.y < -20) this.y = canvas.height + 20;
    if(this.y > canvas.height + 20) this.y = -20;

    return;
    }
    /* only 65% particles react strongly */
    const active = this.mode === "swarm";

    if(mouse.moving && mouse.speed > 1 && active){

        if(dist < 320){
            let force = (320 - dist) / 320;

            this.vx -= (dx / dist) * force * mouse.speed * 0.095;
            this.vy -= (dy / dist) * force * mouse.speed * 0.095;
        }

        if(dist < 420){
            this.vx += (dx / dist) * 0.010;
            this.vy += (dy / dist) * 0.010;
        }

    } else if(idle && active){

        /* multi-shell gather system */
        let shell;

        if(i % 4 === 0) shell = 45;
        else if(i % 4 === 1) shell = 90;
        else if(i % 4 === 2) shell = 145;
        else shell = 210;

        const angle =
            performance.now() * (0.0008 + (i % 5)*0.00008)
            + this.offset;

        const targetX = mouse.x + Math.cos(angle) * shell;
        const targetY = mouse.y + Math.sin(angle) * shell;

        this.vx += (targetX - this.x) * 0.0022;
        this.vy += (targetY - this.y) * 0.0022;
    }

    /* ambient drifting particles remain across screen */
    this.vx += (Math.random() - 0.5) * 0.003;
    this.vy += (Math.random() - 0.5) * 0.003;

    this.vx *= 0.965;
    this.vy *= 0.965;

    this.x += this.vx;
    this.y += this.vy;

    if(this.x < -20) this.x = canvas.width + 20;
    if(this.x > canvas.width + 20) this.x = -20;
    if(this.y < -20) this.y = canvas.height + 20;
    if(this.y > canvas.height + 20) this.y = -20;
}
    draw(){

    ctx.beginPath();
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);

    ctx.shadowBlur = this.mode === "swarm" ? 14 : 6;
    ctx.shadowColor = this.mode === "swarm" ? "#2ad96a" : this.color;

    ctx.fillStyle = this.color;
    ctx.fill();

    /* subtle twinkle */
    if(this.mode === "ambient" && Math.random() < 0.015){
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size * 2.2, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(255,255,255,0.08)";
        ctx.fill();
    }
}
}

function init(){

    particles = [];

    /* ambient field */
    for(let i = 0; i < 420; i++){
        let p = new Particle();
        p.mode = "ambient";
        p.size = Math.random() * 1.4 + 0.25;
        particles.push(p);
    }

    /* reactive swarm */
    for(let i = 0; i < 220; i++){
        let p = new Particle();
        p.mode = "swarm";
        p.size = Math.random() * 2 + 0.8;
        particles.push(p);
    }
}

function animate(){

    if(Date.now() - mouse.lastMove > 140){
        mouse.moving = false;
    }

    ctx.fillStyle = "rgba(0,0,0,1)";
    ctx.fillRect(0,0,canvas.width,canvas.height);

    particles.forEach((p,i)=>{
        p.update(i);
        p.draw();
    });

    requestAnimationFrame(animate);
}

init();
animate();
