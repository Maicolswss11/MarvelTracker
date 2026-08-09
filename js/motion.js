(function(){
  "use strict";

  const root = document.documentElement;
  const reducedQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  const finePointerQuery = window.matchMedia("(hover: hover) and (pointer: fine)");
  const revealSelector = [
    ".homeDashboardHero",
    ".homeStats .homeStat",
    ".hubExplorerHeading",
    ".hubCard",
    ".hubDetailHero",
    ".hubPathCard",
    ".heroPanel",
    ".nextPanel",
    ".routeCard",
    ".notice",
    ".filterBar",
    ".seriesHead",
    ".profileHero",
    ".profileStats article",
    ".profileTabs",
    ".profileOverviewCard",
    ".editionChoice"
  ].join(",");
  const surfaceSelector = [
    ".homeDashboardHero",
    ".homeContinue",
    ".homeStat",
    ".hubCard",
    ".hubPathCard",
    ".hubDetailHero",
    ".heroPanel",
    ".nextPanel",
    ".profileHero",
    ".profileStats article",
    ".profileOverviewCard"
  ].join(",");
  const tiltSelector = [
    ".homeContinue",
    ".homeStat",
    ".hubCard",
    ".hubDetailHero",
    ".nextPanel",
    ".profileOverviewCard"
  ].join(",");
  const magneticSelector = [
    ".homePrimary",
    ".homeSecondary",
    ".homeTopAction",
    ".hubHomeLevelsBtn",
    ".trackerHomeBtn",
    ".profileHomeButton"
  ].join(",");
  const countSelector = ".homeStat>b,.profileStats article>b,.profileMegaNumber,.hubDetailStats b,.bigNum b";

  let ready = false;
  let transitionInFlight = false;
  let enhanceFrame = 0;
  let scrollFrame = 0;
  let pointerFrame = 0;
  const revealedIssues = new Set();
  const pendingReveals = new Set();

  root.classList.add("js-motion");

  const delay = milliseconds => new Promise(resolve => setTimeout(resolve,milliseconds));
  const isReduced = () => reducedQuery.matches;

  const revealObserver = "IntersectionObserver" in window ? new IntersectionObserver(entries => {
    for(const entry of entries){
      if(!entry.isIntersecting) continue;
      entry.target.classList.add("is-visible");
      pendingReveals.delete(entry.target);
      revealObserver.unobserve(entry.target);
    }
  },{rootMargin:"80px 0px -7%",threshold:.04}) : null;

  function markRevealElements(scope=document){
    const elements = scope.querySelectorAll?.(revealSelector) || [];
    let index = 0;
    for(const element of elements){
      if(element.dataset.motionReveal === "1") continue;
      element.dataset.motionReveal = "1";
      if(!finePointerQuery.matches && element.matches(".hubCard,.hubPathCard")){
        element.classList.add("is-visible");
        continue;
      }
      element.classList.add("motionReveal");
      element.style.setProperty("--reveal-index",String(index++ % 10));
      if(isReduced() || !revealObserver){
        element.classList.add("is-visible");
        continue;
      }
      if(element.matches(".hubCard,.hubPathCard")){
        requestAnimationFrame(() => element.classList.add("is-visible"));
        continue;
      }
      pendingReveals.add(element);
      revealObserver.observe(element);
    }
  }

  function animateNearbyIssues(scope=document){
    let index = 0;
    for(const element of scope.querySelectorAll?.(".issue[data-issue-id]") || []){
      if(element.dataset.motionIssue === "1") continue;
      element.dataset.motionIssue = "1";
      const key = element.dataset.issueId;
      if(isReduced() || revealedIssues.has(key)) continue;
      const rect = element.getBoundingClientRect();
      if(rect.top > window.innerHeight*1.45 || rect.bottom < -100) continue;
      revealedIssues.add(key);
      element.style.setProperty("--issue-index",String(index++ % 9));
      element.classList.add("motionIssueIn");
    }
  }

  function revealVisibleElements(){
    if(isReduced()){
      for(const element of pendingReveals) element.classList.add("is-visible");
      pendingReveals.clear();
      return;
    }
    for(const element of pendingReveals){
      if(!element.isConnected){pendingReveals.delete(element);continue;}
      const rect = element.getBoundingClientRect();
      if(rect.top > window.innerHeight+150 || rect.bottom < -150) continue;
      element.classList.add("is-visible");
      pendingReveals.delete(element);
      revealObserver?.unobserve(element);
    }
  }

  function bindSurface(element){
    const alreadyBound = element.dataset.motionSurface === "1";
    element.classList.add("motionSurface");
    const interactive = finePointerQuery.matches && !isReduced();
    element.classList.toggle("motionTilt",interactive && element.matches(tiltSelector));
    if(!interactive){
      element.querySelector(":scope > .motionSpotlightLayer")?.remove();
      return;
    }
    if(!element.querySelector(":scope > .motionSpotlightLayer")){
      const light = document.createElement("span");
      light.className = "motionSpotlightLayer";
      light.setAttribute("aria-hidden","true");
      element.append(light);
    }
    if(alreadyBound) return;
    element.dataset.motionSurface = "1";
    element.addEventListener("pointermove",event => {
      const rect = element.getBoundingClientRect();
      const x = Math.max(0,Math.min(rect.width,event.clientX-rect.left));
      const y = Math.max(0,Math.min(rect.height,event.clientY-rect.top));
      element.style.setProperty("--spot-x",`${x}px`);
      element.style.setProperty("--spot-y",`${y}px`);
      if(!element.matches(tiltSelector) || isReduced()) return;
      const horizontal = x / Math.max(1,rect.width) - .5;
      const vertical = y / Math.max(1,rect.height) - .5;
      element.style.setProperty("--tilt-x",`${(-vertical*4.6).toFixed(2)}deg`);
      element.style.setProperty("--tilt-y",`${(horizontal*5.4).toFixed(2)}deg`);
    },{passive:true});
    element.addEventListener("pointerleave",() => {
      element.style.setProperty("--tilt-x","0deg");
      element.style.setProperty("--tilt-y","0deg");
    },{passive:true});
  }

  function bindSurfaces(scope=document){
    for(const element of scope.querySelectorAll?.(surfaceSelector) || []){
      bindSurface(element);
    }
  }

  function bindMagnetic(element){
    if(element.dataset.motionMagnetic === "1") return;
    element.dataset.motionMagnetic = "1";
    element.classList.add("motionMagnetic");
    if(!finePointerQuery.matches) return;
    element.addEventListener("pointermove",event => {
      if(isReduced()) return;
      const rect = element.getBoundingClientRect();
      const x = ((event.clientX-rect.left)/Math.max(1,rect.width)-.5)*7;
      const y = ((event.clientY-rect.top)/Math.max(1,rect.height)-.5)*5;
      element.style.setProperty("--mag-x",`${x.toFixed(2)}px`);
      element.style.setProperty("--mag-y",`${y.toFixed(2)}px`);
    },{passive:true});
    element.addEventListener("pointerleave",() => {
      element.style.setProperty("--mag-x","0px");
      element.style.setProperty("--mag-y","0px");
    },{passive:true});
  }

  function bindMagneticElements(scope=document){
    for(const element of scope.querySelectorAll?.(magneticSelector) || []) bindMagnetic(element);
  }

  function parseCounter(text){
    const suffix = text.trim().endsWith("%") ? "%" : "";
    const digits = text.replace(/[^0-9-]/g,"");
    const value = Number(digits);
    return Number.isFinite(value) ? {value,suffix,raw:text} : null;
  }

  function animateCounter(element){
    if(element.dataset.motionCounting === "1") return;
    const parsed = parseCounter(element.textContent || "");
    if(!parsed || parsed.value < 0 || parsed.value > 999999) return;
    if(element.dataset.motionValue === parsed.raw) return;
    element.dataset.motionValue = parsed.raw;
    element.setAttribute("aria-label",parsed.raw);
    if(isReduced()) return;
    element.dataset.motionCounting = "1";
    const duration = 760 + Math.min(520,parsed.value/8);
    const formatter = new Intl.NumberFormat("it-IT");
    const start = performance.now();
    const tick = now => {
      const progress = Math.min(1,(now-start)/duration);
      const eased = 1-Math.pow(1-progress,4);
      element.textContent = `${formatter.format(Math.round(parsed.value*eased))}${parsed.suffix}`;
      if(progress < 1) requestAnimationFrame(tick);
      else{
        element.textContent = parsed.raw;
        delete element.dataset.motionCounting;
      }
    };
    requestAnimationFrame(tick);
  }

  function animateCounters(scope=document){
    for(const element of scope.querySelectorAll?.(countSelector) || []) animateCounter(element);
  }

  function enhance(scope=document){
    markRevealElements(scope);
    animateNearbyIssues(scope);
    bindSurfaces(scope);
    bindMagneticElements(scope);
    animateCounters(scope);
    requestAnimationFrame(revealVisibleElements);
  }

  function scheduleEnhance(){
    cancelAnimationFrame(enhanceFrame);
    enhanceFrame = requestAnimationFrame(() => enhance(document));
  }

  function updateScrollProgress(){
    scrollFrame = 0;
    revealVisibleElements();
    const bar = document.getElementById("marvelScrollProgressBar");
    if(!bar) return;
    const maximum = Math.max(1,document.documentElement.scrollHeight-window.innerHeight);
    const progress = Math.max(0,Math.min(1,window.scrollY/maximum));
    bar.style.transform = `scaleX(${progress})`;
  }

  function scheduleScrollProgress(){
    if(scrollFrame) return;
    scrollFrame = requestAnimationFrame(updateScrollProgress);
  }

  function updateAmbientPointer(event){
    if(!finePointerQuery.matches || isReduced()) return;
    if(pointerFrame) cancelAnimationFrame(pointerFrame);
    pointerFrame = requestAnimationFrame(() => {
      const x = (event.clientX/window.innerWidth-.5)*22;
      const y = (event.clientY/window.innerHeight-.5)*16;
      root.style.setProperty("--ambient-x",`${x.toFixed(1)}px`);
      root.style.setProperty("--ambient-y",`${y.toFixed(1)}px`);
      pointerFrame = 0;
    });
  }

  function addRipple(event){
    if(isReduced()) return;
    const button = event.target.closest?.("button,.sideActions label");
    if(!button || button.disabled) return;
    button.classList.add("motionClick");
    if(getComputedStyle(button).position === "static") button.classList.add("motionClickHost");
    const rect = button.getBoundingClientRect();
    const ripple = document.createElement("span");
    ripple.className = "motionRipple";
    ripple.style.left = `${event.clientX-rect.left}px`;
    ripple.style.top = `${event.clientY-rect.top}px`;
    ripple.setAttribute("aria-hidden","true");
    button.append(ripple);
    ripple.addEventListener("animationend",() => {
      ripple.remove();
      if(!button.querySelector(":scope > .motionRipple")) button.classList.remove("motionClick","motionClickHost");
    },{once:true});
  }

  function addBurst(event){
    if(isReduced()) return;
    const button = event.target.closest?.(".status button,.nextBtns button,.homePrimary,.homeContinue button,.profileIssueActions button");
    if(!button || button.disabled) return;
    const burst = document.createElement("span");
    burst.className = "motionBurst";
    burst.setAttribute("aria-hidden","true");
    burst.innerHTML = "<i></i>".repeat(8);
    button.append(burst);
    setTimeout(() => burst.remove(),700);
  }

  function setupMobileDrawer(){
    const actions = document.querySelector(".trackerTopActions");
    if(!actions || document.getElementById("mobileNavToggle")) return;
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.id = "mobileNavToggle";
    toggle.className = "mobileNavToggle";
    toggle.setAttribute("aria-controls","hubSidebarNav");
    toggle.setAttribute("aria-expanded","false");
    toggle.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg><span>Percorsi</span>';
    actions.prepend(toggle);
    const scrim = document.createElement("button");
    scrim.type = "button";
    scrim.className = "mobileNavScrim";
    scrim.setAttribute("aria-label","Chiudi il menu dei percorsi");
    (document.querySelector(".app") || document.body).append(scrim);
    const sidebar = document.querySelector(".sidebar");
    const close = document.createElement("button");
    close.type = "button";
    close.className = "mobileNavClose";
    close.setAttribute("aria-label","Chiudi il menu dei percorsi");
    close.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg>';
    sidebar?.prepend(close);
    const setOpen = open => {
      document.body.classList.toggle("mobileNavOpen",open);
      toggle.setAttribute("aria-expanded",String(open));
      if(open) requestAnimationFrame(() => document.querySelector(".sidebar button")?.focus({preventScroll:true}));
      else toggle.focus({preventScroll:true});
    };
    toggle.addEventListener("click",() => setOpen(!document.body.classList.contains("mobileNavOpen")));
    close.addEventListener("click",() => setOpen(false));
    scrim.addEventListener("click",() => setOpen(false));
    document.addEventListener("keydown",event => {
      if(event.key === "Escape" && document.body.classList.contains("mobileNavOpen")) setOpen(false);
    });
    sidebar?.addEventListener("click",event => {
      if(event.target.closest("[data-side-path],[data-side-back],#homeBtn") && window.innerWidth <= 1120) setOpen(false);
    });
    window.addEventListener("hashchange",() => {
      if(document.body.classList.contains("mobileNavOpen")) setOpen(false);
    });
  }

  async function transition(update){
    if(typeof update !== "function") return undefined;
    if(!ready || isReduced() || transitionInFlight) return update();
    transitionInFlight = true;
    try{
      if(typeof document.startViewTransition === "function"){
        let result;
        const viewTransition = document.startViewTransition(async() => { result = await update(); });
        await viewTransition.finished.catch(() => {});
        scheduleEnhance();
        return result;
      }
      root.classList.add("motionFallback");
      document.body.classList.add("motionLeaving");
      await delay(130);
      const result = await update();
      document.body.classList.remove("motionLeaving");
      document.body.classList.add("motionEntering");
      scheduleEnhance();
      await delay(470);
      document.body.classList.remove("motionEntering");
      return result;
    } finally {
      transitionInFlight = false;
    }
  }

  async function sectionTransition(container,update){
    if(!container || typeof update !== "function" || !ready || isReduced()) return update?.();
    const oldHeight = container.getBoundingClientRect().height;
    container.style.minHeight = `${oldHeight}px`;
    const out = container.animate([
      {opacity:1,transform:"translateY(0)",filter:"blur(0)"},
      {opacity:0,transform:"translateY(10px)",filter:"blur(4px)"}
    ],{duration:170,easing:"ease",fill:"forwards"});
    await out.finished.catch(() => {});
    const result = await update();
    container.getAnimations().forEach(animation => animation.cancel());
    container.style.minHeight = "";
    enhance(container);
    const incoming = container.animate([
      {opacity:0,transform:"translateY(24px) scale(.99)",filter:"blur(6px)"},
      {opacity:1,transform:"none",filter:"none"}
    ],{duration:560,easing:"cubic-bezier(.16,1,.3,1)",fill:"both"});
    await incoming.finished.catch(() => {});
    return result;
  }

  function markReady(){
    if(ready) return;
    ready = true;
    root.classList.add("appLoaded");
    scheduleEnhance();
    updateScrollProgress();
    setTimeout(() => document.getElementById("marvelBoot")?.remove(),1250);
  }

  function init(){
    setupMobileDrawer();
    enhance(document);
    updateScrollProgress();
    const app = document.querySelector(".app");
    if(app){
      const observer = new MutationObserver(scheduleEnhance);
      observer.observe(app,{childList:true,subtree:true});
    }
    if(root.classList.contains("appLoaded")) markReady();
  }

  window.MarvelMotion = {transition,sectionTransition,enhance:scheduleEnhance,ready:markReady};
  document.addEventListener("marvel:render",scheduleEnhance);
  document.addEventListener("marvel:ready",markReady,{once:true});
  document.addEventListener("pointerdown",addRipple,{passive:true});
  document.addEventListener("click",addBurst);
  document.addEventListener("pointermove",updateAmbientPointer,{passive:true});
  window.addEventListener("scroll",scheduleScrollProgress,{passive:true});
  window.addEventListener("resize",scheduleScrollProgress,{passive:true});
  document.addEventListener("visibilitychange",() => document.body.classList.toggle("motionPaused",document.hidden));
  reducedQuery.addEventListener?.("change",() => {
    if(isReduced()) document.querySelectorAll(".motionReveal").forEach(element => element.classList.add("is-visible"));
  });
  document.addEventListener("DOMContentLoaded",init,{once:true});
  if(document.readyState !== "loading") init();
  setTimeout(markReady,6000);
})();
