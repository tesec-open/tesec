#include <unistd.h>
#include <napi.h>

using namespace Napi;

Value Trigger(const CallbackInfo& info) {
  int arg0 = info[0].As<Number>().Int32Value();
  syscall(404, arg0);
  return info.Env().Undefined();
}

Value TriggerFile(const CallbackInfo& info) {
  int arg0 = info[0].As<Number>().Int32Value();
  int arg1 = info[0].As<Number>().Int32Value();
  syscall(403, arg0, arg1);
  return info.Env().Undefined();
}

Object Init(Env env, Object exports) {
  exports.Set(String::New(env, "trigger"), Function::New(env, Trigger));
  exports.Set(String::New(env, "triggerFile"), Function::New(env, TriggerFile));
  return exports;
}

NODE_API_MODULE(trigger, Init)
