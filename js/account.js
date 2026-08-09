import { SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY } from "./supabase-config.js";

const SDK_URL = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.112.2/+esm";
const DIRTY_PREFIX = "marvel_archive_cloud_dirty:";
let client = null;
let currentUser = null;
let currentProfile = null;
let listener = () => {};
let syncStatus = "local";
let syncTimer = null;
let pendingState = null;

export function isCloudConfigured(){
  try{
    const url=new URL(SUPABASE_URL.trim());
    return url.protocol==="https:"&&SUPABASE_PUBLISHABLE_KEY.trim().length>20;
  }catch{return false}
}

function profileName(){
  return currentProfile?.display_name||currentUser?.user_metadata?.display_name||currentUser?.email?.split("@")[0]||"Lettore Marvel";
}

function snapshot(extra={}){
  return {configured:isCloudConfigured(),user:currentUser,profile:currentProfile,displayName:profileName(),syncStatus,...extra};
}

function notify(extra={}){listener(snapshot(extra))}

async function ensureClient(){
  if(client)return client;
  if(!isCloudConfigured())return null;
  const {createClient}=await import(SDK_URL);
  client=createClient(SUPABASE_URL.trim(),SUPABASE_PUBLISHABLE_KEY.trim(),{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});
  return client;
}

async function loadProfile(){
  if(!currentUser||!client)return null;
  const {data,error}=await client.from("profiles").select("display_name,avatar_color,updated_at").eq("id",currentUser.id).maybeSingle();
  if(error)throw error;
  return data;
}

async function applySession(session){
  const previousId=currentUser?.id||null;
  const nextId=session?.user?.id||null;
  if(previousId!==nextId){clearTimeout(syncTimer);syncTimer=null;pendingState=null}
  currentUser=session?.user||null;
  currentProfile=null;
  if(currentUser){
    try{currentProfile=await loadProfile()}catch(error){console.error("Profilo non disponibile",error)}
    syncStatus=navigator.onLine?"ready":"offline";
    notify({phase:"signed-in",userChanged:previousId!==currentUser.id});
  }else{
    syncStatus="local";
    notify({phase:"signed-out",userChanged:previousId!==null});
  }
}

export async function initAccount(onChange){
  listener=onChange||listener;
  notify({phase:"loading"});
  if(!isCloudConfigured()){
    notify({phase:"unconfigured"});
    return snapshot({phase:"unconfigured"});
  }
  try{
    const supabase=await ensureClient();
    const {data,error}=await supabase.auth.getSession();
    if(error)throw error;
    await applySession(data.session);
    supabase.auth.onAuthStateChange((_event,session)=>setTimeout(()=>void applySession(session),0));
    window.addEventListener("online",()=>{if(currentUser){syncStatus="ready";notify({reconnected:true})}});
    window.addEventListener("offline",()=>{if(currentUser){syncStatus="offline";notify()}});
    return snapshot();
  }catch(error){
    console.error("Inizializzazione cloud non riuscita",error);
    syncStatus="error";
    notify({phase:"error",error:error.message});
    return snapshot({phase:"error",error:error.message});
  }
}

export async function signIn(email,password){
  const supabase=await ensureClient();
  if(!supabase)throw new Error("Sincronizzazione non configurata.");
  notify({phase:"authenticating"});
  const {data,error}=await supabase.auth.signInWithPassword({email,password});
  if(error){notify({phase:"signed-out"});throw error}
  await applySession(data.session);
  return data;
}

export async function signUp(email,password,displayName){
  const supabase=await ensureClient();
  if(!supabase)throw new Error("Sincronizzazione non configurata.");
  notify({phase:"authenticating"});
  const emailRedirectTo=new URL(".",window.location.href).href;
  const {data,error}=await supabase.auth.signUp({email,password,options:{data:{display_name:displayName.trim()},emailRedirectTo}});
  if(error){notify({phase:"signed-out"});throw error}
  if(data.session)await applySession(data.session);else notify({phase:"signed-out",confirmationRequired:true});
  return {confirmationRequired:!data.session};
}

export async function signOut(){
  if(!client)return;
  if(pendingState)await flushCloudState().catch(()=>{});
  const {error}=await client.auth.signOut();
  if(error)throw error;
  await applySession(null);
}

export async function updateProfile({displayName,avatarColor}={}){
  const supabase=await ensureClient();
  if(!supabase||!currentUser)throw new Error("Devi accedere prima di modificare il profilo cloud.");
  const changes={};
  const cleanName=String(displayName||"").trim().slice(0,40);
  if(cleanName)changes.display_name=cleanName;
  if(/^#[0-9a-f]{6}$/i.test(String(avatarColor||"")))changes.avatar_color=avatarColor;
  if(!Object.keys(changes).length)return currentProfile;
  const {data,error}=await supabase.from("profiles").update(changes).eq("id",currentUser.id).select("display_name,avatar_color,updated_at").single();
  if(error)throw error;
  currentProfile=data;
  if(cleanName&&currentUser.user_metadata?.display_name!==cleanName){
    const {data:authData,error:authError}=await supabase.auth.updateUser({data:{display_name:cleanName}});
    if(authError)console.warn("Metadati del profilo non aggiornati",authError);
    else if(authData?.user)currentUser=authData.user;
  }
  notify();
  return currentProfile;
}

export async function fetchCloudState(){
  if(!client||!currentUser)return null;
  const {data,error}=await client.from("tracker_states").select("state,updated_at").eq("user_id",currentUser.id).maybeSingle();
  if(error){syncStatus=navigator.onLine?"error":"offline";notify({error:error.message});throw error}
  syncStatus="synced";
  notify();
  return data;
}

export function hasUnsyncedState(){
  return !!currentUser&&localStorage.getItem(DIRTY_PREFIX+currentUser.id)==="1";
}

export function queueCloudState(state){
  if(!client||!currentUser)return;
  pendingState=JSON.parse(JSON.stringify(state));
  localStorage.setItem(DIRTY_PREFIX+currentUser.id,"1");
  clearTimeout(syncTimer);
  syncTimer=setTimeout(()=>void flushCloudState(),900);
}

export async function flushCloudState(state=null){
  if(state)pendingState=JSON.parse(JSON.stringify(state));
  if(!client||!currentUser||!pendingState)return false;
  if(!navigator.onLine){syncStatus="offline";notify();return false}
  clearTimeout(syncTimer);
  const payload=pendingState;
  pendingState=null;
  syncStatus="syncing";
  notify();
  const {error}=await client.from("tracker_states").upsert({user_id:currentUser.id,state:payload,client_updated_at:new Date().toISOString()},{onConflict:"user_id"});
  if(error){
    pendingState=pendingState||payload;
    localStorage.setItem(DIRTY_PREFIX+currentUser.id,"1");
    syncStatus=navigator.onLine?"error":"offline";
    notify({error:error.message});
    throw error;
  }
  if(!pendingState)localStorage.removeItem(DIRTY_PREFIX+currentUser.id);
  syncStatus=pendingState?"syncing":"synced";
  notify();
  if(pendingState){clearTimeout(syncTimer);syncTimer=setTimeout(()=>void flushCloudState(),500)}
  return true;
}
