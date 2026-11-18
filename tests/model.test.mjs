import test from 'node:test';
import assert from 'node:assert/strict';
import {unpack,matching,continuousRuns,yearsFor,csv} from '../web/model.mjs';
const adams=unpack(['46239-220','Adams River Late Sockeye','ADAMS RIVER','Sockeye','29K','LATE']);
const yorkson=unpack(['47959-26','Yorkson Creek Coho','YORKSON CREEK','Coho','29B','']);
test('population and site identities can be searched alongside waterbody names',()=>{
  assert.equal(matching([adams,yorkson],'RIVER adams','Sockeye','29K')[0],adams);
  assert.deepEqual(matching([adams,yorkson],'26','Sockeye'),[]);
  assert.equal(matching([adams,yorkson],'47959')[0],yorkson);
});
test('a zero is plotted and years without estimates break the line',()=>{
  assert.deepEqual(continuousRuns([[2000,0],[2001,null],[2002,3],[2003,8],[2006,2]]),[[[2000,0]],[[2002,3],[2003,8]],[[2006,2]]]);
});
test('axis includes missing years and both series; recent ranges end at source maximum',()=>{
  assert.deepEqual(yearsFor([[[1999,7],[2001,9]],[[2003,2]]],'all',2025),[1999,2000,2001,2002,2003]);
  assert.equal(yearsFor([[[1999,7]]],'10',2025)[0],2016);
});
test('CSV distinguishes blank, zero and quoted text',()=>assert.equal(csv([[null,0,'a "quote"']]),'"","0","a ""quote"""\r\n'));
