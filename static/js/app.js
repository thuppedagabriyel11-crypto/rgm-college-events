(() => {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const fine = window.matchMedia('(pointer:fine)').matches;
  const q = s => document.querySelector(s);
  const qa = s => [...document.querySelectorAll(s)];

  // Mobile navigation
  const menu = q('[data-menu]'), nav = q('[data-nav]');
  if(menu && nav) menu.addEventListener('click', () => nav.classList.toggle('open'));

  // Button liquid-wave coordinates
  qa('.btn').forEach(btn => btn.addEventListener('pointermove', e => {
    const r = btn.getBoundingClientRect();
    btn.style.setProperty('--wave-x', `${e.clientX-r.left}px`);
    btn.style.setProperty('--wave-y', `${e.clientY-r.top}px`);
  }));

  // Magnetic button effect — cursor highlighter removed
  if(fine && !reduce){
    qa('.magnetic').forEach(el=>{
      el.addEventListener('pointermove',e=>{
        const r=el.getBoundingClientRect();
        const x=(e.clientX-(r.left+r.width/2))/r.width;
        const y=(e.clientY-(r.top+r.height/2))/r.height;
        el.style.transform=`translate(${x*7}px,${y*7}px)`;
      });
      el.addEventListener('pointerleave',()=>{el.style.transform=''});
    });
  }

  // 3D tilt
  if(fine && !reduce){qa('.tilt-card').forEach(card=>{card.addEventListener('pointermove',e=>{const r=card.getBoundingClientRect(),x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5;card.style.transform=`perspective(1000px) rotateX(${(-y*4).toFixed(2)}deg) rotateY(${(x*4).toFixed(2)}deg) translateY(-3px)`});card.addEventListener('pointerleave',()=>card.style.transform='')})}

  // Scroll progress + optional Lenis smooth inertia
  const progress=q('#scrollProgress');
  const updateProgress=()=>{const h=document.documentElement.scrollHeight-innerHeight; if(progress) progress.style.width=(h>0?(scrollY/h)*100:0)+'%'};
  addEventListener('scroll',updateProgress,{passive:true}); updateProgress();
  // Lenis smooth scrolling disabled for immediate native scrolling

  // GSAP reveal + scroll storytelling when CDN is available
  if(!reduce && window.gsap){if(window.ScrollTrigger){gsap.registerPlugin(ScrollTrigger);gsap.utils.toArray('.reveal').forEach(el=>gsap.fromTo(el,{opacity:0,y:30},{opacity:1,y:0,duration:.75,ease:'power3.out',scrollTrigger:{trigger:el,start:'top 88%',once:true}}))}else{gsap.utils.toArray('.reveal').forEach(el=>gsap.fromTo(el,{opacity:0,y:18},{opacity:1,y:0,duration:.6}))}}

  // Command palette
  const overlay=q('#commandOverlay'), input=q('#commandInput'), results=q('#commandResults');
  const openCommand=()=>{if(!overlay)return;overlay.classList.add('open');overlay.setAttribute('aria-hidden','false');setTimeout(()=>input?.focus(),40)};
  const closeCommand=()=>{overlay?.classList.remove('open');overlay?.setAttribute('aria-hidden','true')};
  q('[data-command]')?.addEventListener('click',openCommand); q('[data-command-close]')?.addEventListener('click',closeCommand);
  overlay?.addEventListener('click',e=>{if(e.target===overlay)closeCommand()});
  addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openCommand()}if(e.key==='Escape')closeCommand()});
  input?.addEventListener('input',()=>{const term=input.value.toLowerCase().trim();qa('[data-command-item]').forEach(item=>{item.style.display=item.textContent.toLowerCase().includes(term)?'flex':'none'})});

  // Click particle burst
  if(!reduce){document.addEventListener('click',e=>{const btn=e.target.closest('.btn');if(!btn)return;for(let i=0;i<8;i++){const p=document.createElement('i');p.className='click-particle';p.style.left=e.clientX+'px';p.style.top=e.clientY+'px';p.style.setProperty('--dx',`${(Math.random()-.5)*90}px`);p.style.setProperty('--dy',`${(Math.random()-.5)*90}px`);document.body.appendChild(p);setTimeout(()=>p.remove(),650)}})}

  // Optional Three.js hero object; page remains fully usable if CDN is unavailable.
  const canvas=q('#scene3d');
  if(canvas && window.THREE && !reduce){
    const scene=new THREE.Scene(), renderer=new THREE.WebGLRenderer({canvas,alpha:true,antialias:true}); renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));
    const resize=()=>{const r=canvas.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix()};
    const camera=new THREE.PerspectiveCamera(38,1,.1,100);camera.position.set(0,0,7);
    const group=new THREE.Group();scene.add(group);const geo=new THREE.IcosahedronGeometry(1.55,2);const mat=new THREE.MeshPhysicalMaterial({color:0xd14a28,metalness:.35,roughness:.22,transmission:.18,transparent:true,opacity:.9});const mesh=new THREE.Mesh(geo,mat);group.add(mesh);
    const wire=new THREE.Mesh(new THREE.IcosahedronGeometry(1.68,2),new THREE.MeshBasicMaterial({color:0xffb26f,wireframe:true,transparent:true,opacity:.28}));group.add(wire);
    scene.add(new THREE.AmbientLight(0xffffff,1.8));const light=new THREE.PointLight(0xffb26f,10,30);light.position.set(4,3,6);scene.add(light);const light2=new THREE.PointLight(0xc63d20,8,20);light2.position.set(-4,-2,3);scene.add(light2);
    const pointer={x:0,y:0};canvas.addEventListener('pointermove',e=>{const r=canvas.getBoundingClientRect();pointer.x=(e.clientX-r.left)/r.width-.5;pointer.y=(e.clientY-r.top)/r.height-.5},{passive:true});
    addEventListener('resize',resize);resize();const animate=t=>{group.rotation.y+=.0025;group.rotation.x+=(pointer.y*.25-group.rotation.x)*.03;group.rotation.y+=(pointer.x*.35+group.rotation.y)*.00001;mesh.position.y=Math.sin(t*.001)*.08;wire.rotation.z=-t*.00025;renderer.render(scene,camera);requestAnimationFrame(animate)};requestAnimationFrame(animate);
  }

  setTimeout(()=>qa('.toast').forEach(t=>{t.style.transition='opacity .4s,transform .4s';t.style.opacity='0';t.style.transform='translateY(-5px)';setTimeout(()=>t.remove(),450)}),5200);

  // Fee fields toggle in event forms
  const feeToggle=q('#feeEnabled'), feeFields=q('#feeFields');
  const syncFee=()=>{if(feeToggle&&feeFields){feeFields.style.display=feeToggle.checked?'grid':'none'}}; feeToggle?.addEventListener('change',syncFee);syncFee();
})();
