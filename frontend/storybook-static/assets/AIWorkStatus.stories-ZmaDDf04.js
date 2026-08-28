import{j as e}from"./jsx-runtime-DiklIkkE.js";/* empty css              */import"./index-DRjF_FHU.js";const h={working:{label:"工作中",color:"#4cc9f0",bg:"rgba(76,201,240,0.12)",pulse:!0},idle:{label:"空闲中",color:"#8fa0e0",bg:"rgba(143,160,224,0.10)",pulse:!1},waiting:{label:"等待任务",color:"#facc15",bg:"rgba(250,204,21,0.12)",pulse:!1},completed:{label:"已完成",color:"#4ade80",bg:"rgba(74,222,128,0.10)",pulse:!1},error:{label:"异常",color:"#ff6b6b",bg:"rgba(255,107,107,0.12)",pulse:!0},offline:{label:"离线",color:"#666",bg:"rgba(102,102,102,0.08)",pulse:!1}};function t({name:o,status:n,currentTask:a,todayCompleted:i,recentActivity:w,suggestion:b,position:I,model:D,compact:he}){const s=h[n]??h.offline,C=s.pulse?{animation:"ai-pulse 2s ease-in-out infinite"}:{};return he?e.jsxs("div",{className:"ai-status-compact",style:{borderLeft:`3px solid ${s.color}`,paddingLeft:10,marginBottom:8},children:[e.jsxs("div",{style:{display:"flex",alignItems:"center",gap:8},children:[e.jsx("span",{className:"ai-status-dot",style:{...C,background:s.color,boxShadow:`0 0 6px ${s.color}`}}),e.jsx("strong",{style:{fontSize:13},children:o}),e.jsx("span",{style:{fontSize:11,color:s.color,background:s.bg,padding:"1px 8px",borderRadius:8},children:s.label})]}),a&&e.jsx("div",{style:{fontSize:11,color:"rgba(255,255,255,0.6)",marginTop:2},children:a})]}):e.jsxs("div",{className:"ai-status-card",style:{borderTop:`3px solid ${s.color}`},children:[e.jsxs("div",{className:"ai-status-header",children:[e.jsxs("div",{className:"ai-status-left",children:[e.jsx("span",{className:"ai-status-dot",style:{...C,background:s.color,boxShadow:`0 0 8px ${s.color}`}}),e.jsxs("div",{children:[e.jsx("strong",{className:"ai-status-name",children:o}),I&&e.jsx("span",{className:"ai-status-position",children:I})]})]}),e.jsx("span",{className:"ai-status-badge",style:{color:s.color,background:s.bg},children:s.label})]}),D&&e.jsxs("div",{className:"ai-status-meta",children:["模型: ",D]}),e.jsxs("div",{className:"ai-status-body",children:[a&&e.jsxs("div",{className:"ai-status-row",children:[e.jsx("span",{className:"ai-status-label",children:"当前任务"}),e.jsx("span",{className:"ai-status-value",children:a})]}),i!=null&&e.jsxs("div",{className:"ai-status-row",children:[e.jsx("span",{className:"ai-status-label",children:"今日完成"}),e.jsxs("span",{className:"ai-status-value",children:[i," 项"]})]}),w&&e.jsxs("div",{className:"ai-status-row",children:[e.jsx("span",{className:"ai-status-label",children:"最近活动"}),e.jsx("span",{className:"ai-status-value",children:w})]})]}),b&&e.jsxs("div",{className:"ai-status-suggestion",style:{borderLeft:`2px solid ${s.color}`},children:[e.jsx("span",{className:"ai-status-suggestion-icon",children:"💡"}),b]})]})}function r({status:o,size:n=10}){const a=h[o]??h.offline,i=a.pulse?{animation:"ai-pulse 2s ease-in-out infinite"}:{};return e.jsx("span",{className:"ai-status-dot",style:{...i,width:n,height:n,background:a.color,boxShadow:`0 0 6px ${a.color}`,display:"inline-block",borderRadius:"50%"}})}t.__docgenInfo={description:"",methods:[],displayName:"AIWorkStatus",props:{name:{required:!0,tsType:{name:"string"},description:""},status:{required:!0,tsType:{name:"union",raw:"'working' | 'idle' | 'waiting' | 'completed' | 'error' | 'offline'",elements:[{name:"literal",value:"'working'"},{name:"literal",value:"'idle'"},{name:"literal",value:"'waiting'"},{name:"literal",value:"'completed'"},{name:"literal",value:"'error'"},{name:"literal",value:"'offline'"}]},description:""},currentTask:{required:!1,tsType:{name:"string"},description:""},todayCompleted:{required:!1,tsType:{name:"number"},description:""},recentActivity:{required:!1,tsType:{name:"string"},description:""},suggestion:{required:!1,tsType:{name:"string"},description:""},position:{required:!1,tsType:{name:"string"},description:""},model:{required:!1,tsType:{name:"string"},description:""},compact:{required:!1,tsType:{name:"boolean"},description:"紧凑模式，用于侧边栏/小卡片"}}};r.__docgenInfo={description:"工作状态指示灯（纯圆点）",methods:[],displayName:"AIStatusDot",props:{status:{required:!0,tsType:{name:"union",raw:"'working' | 'idle' | 'waiting' | 'completed' | 'error' | 'offline'",elements:[{name:"literal",value:"'working'"},{name:"literal",value:"'idle'"},{name:"literal",value:"'waiting'"},{name:"literal",value:"'completed'"},{name:"literal",value:"'error'"},{name:"literal",value:"'offline'"}]},description:""},size:{required:!1,tsType:{name:"number"},description:"",defaultValue:{value:"10",computed:!1}}}};const De={title:"Components/AIWorkStatus",component:t,tags:["autodocs"],parameters:{layout:"padded",backgrounds:{default:"dark"}},argTypes:{status:{control:"select",options:["working","idle","waiting","completed","error","offline"],description:"AI 工作状态"},name:{control:"text",description:"AI 员工名称"},position:{control:"text",description:"职位"},model:{control:"text",description:"使用模型"},currentTask:{control:"text",description:"当前任务描述"},todayCompleted:{control:"number",description:"今日完成任务数"},recentActivity:{control:"text",description:"最近活动"},suggestion:{control:"text",description:"AI 建议"},compact:{control:"boolean",description:"紧凑模式"}}},c={args:{name:"DeepSeek",status:"working",position:"数据分析师",model:"deepseek-chat",currentTask:"分析东南亚市场趋势",todayCompleted:5,recentActivity:"完成市场分析报告",suggestion:"建议查看最新的市场分析输出。"}},l={args:{name:"Claude",status:"idle",position:"代码审查员",model:"claude-3-opus",currentTask:"等待任务分配",suggestion:"该员工已就绪，可以分配代码审查任务。"}},d={args:{name:"GPT",status:"waiting",position:"策略分析师",model:"gpt-4",currentTask:"配置 AI 能力中",suggestion:"该员工正在配置中，完成后即可分配任务。"}},p={args:{name:"Kimi",status:"completed",position:"客户关系专员",model:"moonshot-v1",currentTask:"客户资料更新完成",todayCompleted:12,recentActivity:"完成 50 条客户资料更新",suggestion:"该员工已完成当前批次任务，可分配新任务。"}},u={args:{name:"Gemini",status:"error",position:"市场研究员",model:"gemini-pro",currentTask:"供应商分析任务异常",todayCompleted:3,recentActivity:"任务执行中断",suggestion:"检测到任务执行异常，建议检查日志并重新调度。"}},m={args:{name:"Grok",status:"offline",position:"趋势预测师",model:"grok-1",currentTask:"已暂停",suggestion:"该员工已暂停，需激活后才能使用。"}},g={args:{name:"AI 助手",status:"working"},parameters:{docs:{description:{story:"仅显示名称和状态，无额外信息。"}}}},x={args:{name:"GPT",status:"working",position:"数据科学家",model:"gpt-4-turbo",currentTask:"分析客户行为模式",todayCompleted:8,recentActivity:"完成客户分群报告",suggestion:"建议将分析结果同步到 CRM 系统。"},parameters:{docs:{description:{story:"所有可选属性同时传入，展示完整信息卡片。"}}}},k={args:{name:"DeepSeek",status:"working",position:"数据分析师",currentTask:"处理数据中",todayCompleted:3},parameters:{docs:{description:{story:"不显示建议区域，仅显示任务和完成数据。"}}}},f={args:{name:"DeepSeek",status:"working",currentTask:"分析市场数据",compact:!0},parameters:{docs:{description:{story:"紧凑模式，适合侧边栏或小卡片场景。"}}}},y={args:{name:"Gemini",status:"error",currentTask:"任务执行异常",compact:!0}},S={args:{name:"Grok",status:"offline",compact:!0}},v={render:()=>e.jsxs("div",{style:{display:"flex",flexDirection:"column",gap:12,maxWidth:400},children:[e.jsx(t,{name:"DeepSeek",status:"working",position:"分析师",currentTask:"分析市场数据"}),e.jsx(t,{name:"Claude",status:"idle",position:"审查员"}),e.jsx(t,{name:"GPT",status:"waiting",position:"策略师",currentTask:"配置中"}),e.jsx(t,{name:"Kimi",status:"completed",position:"专员",todayCompleted:10}),e.jsx(t,{name:"Gemini",status:"error",position:"研究员",currentTask:"任务异常"}),e.jsx(t,{name:"Grok",status:"offline",position:"预测师"})]}),parameters:{docs:{description:{story:"6 种状态并排对比，方便视觉验收。"}}}},j={render:()=>e.jsxs("div",{style:{display:"flex",flexDirection:"column",gap:8,maxWidth:300},children:[e.jsx(t,{name:"DeepSeek",status:"working",compact:!0,currentTask:"分析中"}),e.jsx(t,{name:"Claude",status:"idle",compact:!0}),e.jsx(t,{name:"GPT",status:"waiting",compact:!0,currentTask:"配置中"}),e.jsx(t,{name:"Kimi",status:"completed",compact:!0}),e.jsx(t,{name:"Gemini",status:"error",compact:!0,currentTask:"异常"}),e.jsx(t,{name:"Grok",status:"offline",compact:!0})]}),parameters:{docs:{description:{story:"6 种状态紧凑模式并排对比。"}}}},T={render:()=>e.jsxs("div",{style:{display:"flex",gap:16,alignItems:"center",padding:20},children:[e.jsxs("div",{style:{textAlign:"center"},children:[e.jsx(r,{status:"working"}),e.jsx("div",{style:{fontSize:10,marginTop:4},children:"working"})]}),e.jsxs("div",{style:{textAlign:"center"},children:[e.jsx(r,{status:"idle"}),e.jsx("div",{style:{fontSize:10,marginTop:4},children:"idle"})]}),e.jsxs("div",{style:{textAlign:"center"},children:[e.jsx(r,{status:"waiting"}),e.jsx("div",{style:{fontSize:10,marginTop:4},children:"waiting"})]}),e.jsxs("div",{style:{textAlign:"center"},children:[e.jsx(r,{status:"completed"}),e.jsx("div",{style:{fontSize:10,marginTop:4},children:"completed"})]}),e.jsxs("div",{style:{textAlign:"center"},children:[e.jsx(r,{status:"error"}),e.jsx("div",{style:{fontSize:10,marginTop:4},children:"error"})]}),e.jsxs("div",{style:{textAlign:"center"},children:[e.jsx(r,{status:"offline"}),e.jsx("div",{style:{fontSize:10,marginTop:4},children:"offline"})]})]}),parameters:{docs:{description:{story:"AIStatusDot 纯圆点组件，6 种状态颜色对比。"}}}},A={render:()=>e.jsxs("div",{style:{display:"flex",gap:24,alignItems:"center",padding:20},children:[e.jsx(r,{status:"working",size:8}),e.jsx(r,{status:"working",size:12}),e.jsx(r,{status:"working",size:16}),e.jsx(r,{status:"working",size:24})]}),parameters:{docs:{description:{story:"AIStatusDot 支持自定义尺寸（8px / 12px / 16px / 24px）。"}}}};var N,W,z;c.parameters={...c.parameters,docs:{...(N=c.parameters)==null?void 0:N.docs,source:{originalSource:`{
  args: {
    name: 'DeepSeek',
    status: 'working',
    position: '数据分析师',
    model: 'deepseek-chat',
    currentTask: '分析东南亚市场趋势',
    todayCompleted: 5,
    recentActivity: '完成市场分析报告',
    suggestion: '建议查看最新的市场分析输出。'
  }
}`,...(z=(W=c.parameters)==null?void 0:W.docs)==null?void 0:z.source}}};var G,q,_;l.parameters={...l.parameters,docs:{...(G=l.parameters)==null?void 0:G.docs,source:{originalSource:`{
  args: {
    name: 'Claude',
    status: 'idle',
    position: '代码审查员',
    model: 'claude-3-opus',
    currentTask: '等待任务分配',
    suggestion: '该员工已就绪，可以分配代码审查任务。'
  }
}`,...(_=(q=l.parameters)==null?void 0:q.docs)==null?void 0:_.source}}};var P,E,K;d.parameters={...d.parameters,docs:{...(P=d.parameters)==null?void 0:P.docs,source:{originalSource:`{
  args: {
    name: 'GPT',
    status: 'waiting',
    position: '策略分析师',
    model: 'gpt-4',
    currentTask: '配置 AI 能力中',
    suggestion: '该员工正在配置中，完成后即可分配任务。'
  }
}`,...(K=(E=d.parameters)==null?void 0:E.docs)==null?void 0:K.source}}};var O,$,R;p.parameters={...p.parameters,docs:{...(O=p.parameters)==null?void 0:O.docs,source:{originalSource:`{
  args: {
    name: 'Kimi',
    status: 'completed',
    position: '客户关系专员',
    model: 'moonshot-v1',
    currentTask: '客户资料更新完成',
    todayCompleted: 12,
    recentActivity: '完成 50 条客户资料更新',
    suggestion: '该员工已完成当前批次任务，可分配新任务。'
  }
}`,...(R=($=p.parameters)==null?void 0:$.docs)==null?void 0:R.source}}};var M,L,B;u.parameters={...u.parameters,docs:{...(M=u.parameters)==null?void 0:M.docs,source:{originalSource:`{
  args: {
    name: 'Gemini',
    status: 'error',
    position: '市场研究员',
    model: 'gemini-pro',
    currentTask: '供应商分析任务异常',
    todayCompleted: 3,
    recentActivity: '任务执行中断',
    suggestion: '检测到任务执行异常，建议检查日志并重新调度。'
  }
}`,...(B=(L=u.parameters)==null?void 0:L.docs)==null?void 0:B.source}}};var F,U,V;m.parameters={...m.parameters,docs:{...(F=m.parameters)==null?void 0:F.docs,source:{originalSource:`{
  args: {
    name: 'Grok',
    status: 'offline',
    position: '趋势预测师',
    model: 'grok-1',
    currentTask: '已暂停',
    suggestion: '该员工已暂停，需激活后才能使用。'
  }
}`,...(V=(U=m.parameters)==null?void 0:U.docs)==null?void 0:V.source}}};var H,J,Q;g.parameters={...g.parameters,docs:{...(H=g.parameters)==null?void 0:H.docs,source:{originalSource:`{
  args: {
    name: 'AI 助手',
    status: 'working'
  },
  parameters: {
    docs: {
      description: {
        story: '仅显示名称和状态，无额外信息。'
      }
    }
  }
}`,...(Q=(J=g.parameters)==null?void 0:J.docs)==null?void 0:Q.source}}};var X,Y,Z;x.parameters={...x.parameters,docs:{...(X=x.parameters)==null?void 0:X.docs,source:{originalSource:`{
  args: {
    name: 'GPT',
    status: 'working',
    position: '数据科学家',
    model: 'gpt-4-turbo',
    currentTask: '分析客户行为模式',
    todayCompleted: 8,
    recentActivity: '完成客户分群报告',
    suggestion: '建议将分析结果同步到 CRM 系统。'
  },
  parameters: {
    docs: {
      description: {
        story: '所有可选属性同时传入，展示完整信息卡片。'
      }
    }
  }
}`,...(Z=(Y=x.parameters)==null?void 0:Y.docs)==null?void 0:Z.source}}};var ee,se,te;k.parameters={...k.parameters,docs:{...(ee=k.parameters)==null?void 0:ee.docs,source:{originalSource:`{
  args: {
    name: 'DeepSeek',
    status: 'working',
    position: '数据分析师',
    currentTask: '处理数据中',
    todayCompleted: 3
  },
  parameters: {
    docs: {
      description: {
        story: '不显示建议区域，仅显示任务和完成数据。'
      }
    }
  }
}`,...(te=(se=k.parameters)==null?void 0:se.docs)==null?void 0:te.source}}};var re,ae,oe;f.parameters={...f.parameters,docs:{...(re=f.parameters)==null?void 0:re.docs,source:{originalSource:`{
  args: {
    name: 'DeepSeek',
    status: 'working',
    currentTask: '分析市场数据',
    compact: true
  },
  parameters: {
    docs: {
      description: {
        story: '紧凑模式，适合侧边栏或小卡片场景。'
      }
    }
  }
}`,...(oe=(ae=f.parameters)==null?void 0:ae.docs)==null?void 0:oe.source}}};var ne,ie,ce;y.parameters={...y.parameters,docs:{...(ne=y.parameters)==null?void 0:ne.docs,source:{originalSource:`{
  args: {
    name: 'Gemini',
    status: 'error',
    currentTask: '任务执行异常',
    compact: true
  }
}`,...(ce=(ie=y.parameters)==null?void 0:ie.docs)==null?void 0:ce.source}}};var le,de,pe;S.parameters={...S.parameters,docs:{...(le=S.parameters)==null?void 0:le.docs,source:{originalSource:`{
  args: {
    name: 'Grok',
    status: 'offline',
    compact: true
  }
}`,...(pe=(de=S.parameters)==null?void 0:de.docs)==null?void 0:pe.source}}};var ue,me,ge;v.parameters={...v.parameters,docs:{...(ue=v.parameters)==null?void 0:ue.docs,source:{originalSource:`{
  render: () => <div style={{
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
    maxWidth: 400
  }}>\r
      <AIWorkStatus name="DeepSeek" status="working" position="分析师" currentTask="分析市场数据" />\r
      <AIWorkStatus name="Claude" status="idle" position="审查员" />\r
      <AIWorkStatus name="GPT" status="waiting" position="策略师" currentTask="配置中" />\r
      <AIWorkStatus name="Kimi" status="completed" position="专员" todayCompleted={10} />\r
      <AIWorkStatus name="Gemini" status="error" position="研究员" currentTask="任务异常" />\r
      <AIWorkStatus name="Grok" status="offline" position="预测师" />\r
    </div>,
  parameters: {
    docs: {
      description: {
        story: '6 种状态并排对比，方便视觉验收。'
      }
    }
  }
}`,...(ge=(me=v.parameters)==null?void 0:me.docs)==null?void 0:ge.source}}};var xe,ke,fe;j.parameters={...j.parameters,docs:{...(xe=j.parameters)==null?void 0:xe.docs,source:{originalSource:`{
  render: () => <div style={{
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    maxWidth: 300
  }}>\r
      <AIWorkStatus name="DeepSeek" status="working" compact currentTask="分析中" />\r
      <AIWorkStatus name="Claude" status="idle" compact />\r
      <AIWorkStatus name="GPT" status="waiting" compact currentTask="配置中" />\r
      <AIWorkStatus name="Kimi" status="completed" compact />\r
      <AIWorkStatus name="Gemini" status="error" compact currentTask="异常" />\r
      <AIWorkStatus name="Grok" status="offline" compact />\r
    </div>,
  parameters: {
    docs: {
      description: {
        story: '6 种状态紧凑模式并排对比。'
      }
    }
  }
}`,...(fe=(ke=j.parameters)==null?void 0:ke.docs)==null?void 0:fe.source}}};var ye,Se,ve;T.parameters={...T.parameters,docs:{...(ye=T.parameters)==null?void 0:ye.docs,source:{originalSource:`{
  render: () => <div style={{
    display: 'flex',
    gap: 16,
    alignItems: 'center',
    padding: 20
  }}>\r
      <div style={{
      textAlign: 'center'
    }}><AIStatusDot status="working" /><div style={{
        fontSize: 10,
        marginTop: 4
      }}>working</div></div>\r
      <div style={{
      textAlign: 'center'
    }}><AIStatusDot status="idle" /><div style={{
        fontSize: 10,
        marginTop: 4
      }}>idle</div></div>\r
      <div style={{
      textAlign: 'center'
    }}><AIStatusDot status="waiting" /><div style={{
        fontSize: 10,
        marginTop: 4
      }}>waiting</div></div>\r
      <div style={{
      textAlign: 'center'
    }}><AIStatusDot status="completed" /><div style={{
        fontSize: 10,
        marginTop: 4
      }}>completed</div></div>\r
      <div style={{
      textAlign: 'center'
    }}><AIStatusDot status="error" /><div style={{
        fontSize: 10,
        marginTop: 4
      }}>error</div></div>\r
      <div style={{
      textAlign: 'center'
    }}><AIStatusDot status="offline" /><div style={{
        fontSize: 10,
        marginTop: 4
      }}>offline</div></div>\r
    </div>,
  parameters: {
    docs: {
      description: {
        story: 'AIStatusDot 纯圆点组件，6 种状态颜色对比。'
      }
    }
  }
}`,...(ve=(Se=T.parameters)==null?void 0:Se.docs)==null?void 0:ve.source}}};var je,Te,Ae;A.parameters={...A.parameters,docs:{...(je=A.parameters)==null?void 0:je.docs,source:{originalSource:`{
  render: () => <div style={{
    display: 'flex',
    gap: 24,
    alignItems: 'center',
    padding: 20
  }}>\r
      <AIStatusDot status="working" size={8} />\r
      <AIStatusDot status="working" size={12} />\r
      <AIStatusDot status="working" size={16} />\r
      <AIStatusDot status="working" size={24} />\r
    </div>,
  parameters: {
    docs: {
      description: {
        story: 'AIStatusDot 支持自定义尺寸（8px / 12px / 16px / 24px）。'
      }
    }
  }
}`,...(Ae=(Te=A.parameters)==null?void 0:Te.docs)==null?void 0:Ae.source}}};const Ce=["Working","Idle","Waiting","Completed","Error_","Offline","Minimal","WithAllData","NoSuggestions","CompactWorking","CompactError","CompactOffline","AllStates","AllStatesCompact","StatusDot","StatusDotSizes"];export{v as AllStates,j as AllStatesCompact,y as CompactError,S as CompactOffline,f as CompactWorking,p as Completed,u as Error_,l as Idle,g as Minimal,k as NoSuggestions,m as Offline,T as StatusDot,A as StatusDotSizes,d as Waiting,x as WithAllData,c as Working,Ce as __namedExportsOrder,De as default};
