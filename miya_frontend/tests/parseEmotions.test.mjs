import assert from 'node:assert/strict'
import test from 'node:test'
import { parseEmotions } from '../src/utils/parseEmotions.ts'

test('accepts structured and JSON encoded emotions', () => {
  assert.deepEqual(parseEmotions({ happy: 0.8 }), { happy: 0.8 })
  assert.deepEqual(parseEmotions('{"happy":0.8}'), { happy: 0.8 })
})

test('rejects executable expressions without evaluating them', () => {
  globalThis.emotionCodeRan = false
  assert.equal(parseEmotions('(()=>{globalThis.emotionCodeRan=true; return {happy:1}})()'), null)
  assert.equal(globalThis.emotionCodeRan, false)
})

test('rejects arrays and nonnumeric values', () => {
  assert.equal(parseEmotions('[1,2]'), null)
  assert.equal(parseEmotions('{"happy":"high"}'), null)
})
