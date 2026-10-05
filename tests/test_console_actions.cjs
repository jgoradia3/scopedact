// Exercise the actual browser decision handler with controlled HTTP promises.
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const source=fs.readFileSync('src/scopedact/workspace/static/app.js','utf8');
const decision=source.slice(source.indexOf('async function submitDecision('),source.indexOf("for(const [id,approve] of [['approve',true]"));
async function scenario(failResume=false){
 let release;const waiting=new Promise(resolve=>release=resolve);const calls=[];let refreshes=0;
 const context={actionBusy:false,reviewed:{request:{request_id:'request:exact'},digest:'exact-digest'},isGuidedProposal:()=>true,
  setActionBusy(busy){context.actionBusy=busy;},$:()=>({close(){},textContent:''}),message(){},
  async api(path,body){calls.push({path,body});if(path==='/v1/decision')await waiting;if(failResume&&path==='/v1/lab/resume')throw Error('connection lost');},
  async refresh(){refreshes++;}};
 vm.createContext(context);vm.runInContext(decision,context);
 const first=context.submitDecision(true);await context.submitDecision(true);
 assert.equal(calls.length,1,'repeat clicks must not submit a second decision');release();
 if(failResume)await assert.rejects(first,/Approval was recorded/);else await first;
 assert.deepEqual(calls.map(c=>c.path),['/v1/decision','/v1/lab/resume']);
 assert.equal(calls[0].body.request_id,'request:exact');assert.equal(calls[0].body.digest,'exact-digest');
 assert.equal(context.actionBusy,false);assert.equal(refreshes,1);
}
(async()=>{await scenario();await scenario(true);console.log('Approval double-click and execution-error tests passed.');})().catch(e=>{console.error(e);process.exitCode=1;});

// Signing in and returning home both have no selected investigation/report.
const rendering=source.slice(source.indexOf('function renderRequests(){'),source.indexOf('async function review('));
let cleared=0;
const emptyContext={report:null,$:()=>({replaceChildren(){cleared++;}})};
vm.createContext(emptyContext);vm.runInContext(rendering,emptyContext);
emptyContext.renderRequests();emptyContext.renderRequests();
assert.equal(cleared,2);
console.log('No-selection request rendering passed (sign-in and return home).');
const pollingSource=source.slice(source.indexOf('async function pollConsole(){'),source.indexOf('async function showConsole(){'));
async function checkPolling(){
 const element={open:false,classList:{remove(){}},textContent:''};let attempts=0;
 const context={polling:false,actionBusy:false,document:{hidden:false,querySelector:()=>null},$:()=>element,guideTimer:1,clearInterval(){},async refresh(){attempts++;if(attempts===1)throw Error('temporary timeout');}};
 vm.createContext(context);vm.runInContext(pollingSource,context);
 await context.pollConsole();assert.match(element.textContent,/Reconnecting/);assert.equal(context.guideTimer,1);
 await context.pollConsole();assert.equal(attempts,2);assert.equal(context.polling,false);
 console.log('Transient status failure resumes polling.');
}
checkPolling().catch(e=>{console.error(e);process.exitCode=1;});

// A completed read-only run must explain findings without inventing a denial.
const outcomeSource=source.slice(source.indexOf('function renderInvestigationOutcome(){'),source.indexOf("$('compare-role').onclick"));
function node(tag='',text=''){return {tag,text,children:[],hidden:false,append(...children){this.children.push(...children);},replaceChildren(){this.children=[];}};}
const nodes={};
const outcomeContext={selected:'task:one',guideState:{task_id:'task:one',status:'model_finished',assessment:'<script>untrusted assessment</script>'},report:{assignment:{role:'Support intern'},actions:[{action:'read',resource:'doc:events',executed:true}],verifications:[]},$:id=>nodes[id]??=node(),el:node,resourceLabel:r=>r};
vm.createContext(outcomeContext);vm.runInContext(outcomeSource,outcomeContext);outcomeContext.renderInvestigationOutcome();
const output=JSON.stringify(nodes['investigation-outcome-body']);
assert.match(output,/No blocked requests were recorded/);assert.doesNotMatch(output,/untrusted assessment/);assert.match(output,/without submitting a repair/);
assert.equal(nodes['compare-role'].hidden,false);assert.equal(nodes['investigation-outcome'].hidden,false);
outcomeContext.report.actions.push({action:'read',resource:'doc:config',executed:false,decision:'PERMISSION_NOT_GRANTED'});outcomeContext.renderInvestigationOutcome();assert.match(JSON.stringify(nodes['investigation-outcome-body']),/does not have permission to access doc:config/);
outcomeContext.selected='task:old';outcomeContext.renderInvestigationOutcome();assert.equal(nodes['investigation-outcome'].hidden,true);
console.log('Read-only outcome and current-run attribution checks passed.');
