
// Load original resource bytes on demand. Parent descriptors are shared by frames.
(()=>{
const pending=new Map();
window.ctuavHydrate=async function(node){
 if(!node||!node.dataset.resource)return;
 if(!pending.has(node))pending.set(node,(async()=>{
  const r=await fetch(new URL(node.dataset.resource,document.baseURI));if(!r.ok)throw Error('Resource '+r.status);
  if(node.dataset.encoding==='base64'){
   node.ctuavBytes=new Uint8Array(await r.arrayBuffer());
  }else node.textContent=await r.text();
 })());return pending.get(node);
};
window.ctuavHydrateEncy=()=>Promise.all(['ctEncyThree','ctEncyMeshopt','ctEncyModel'].map(id=>window.ctuavHydrate(document.getElementById(id))));
})();
