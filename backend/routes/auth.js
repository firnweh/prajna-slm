const r=require('express').Router(); r.get('/health',(_,res)=>res.json({ok:true})); module.exports=r;
