#include "com_tesec_logfilter_Trigger.h"

#include <SDKDDKVer.h>
#include <stdio.h>
#include <tchar.h>
#include <windows.h>
#include "ProcMonDebugOutput.h"
#include <string>

const wchar_t *GetWC(const char *c)
{
    const size_t cSize = strlen(c)+1;
    wchar_t* wc = new wchar_t[cSize];
    mbstowcs (wc, c, cSize);
    return wc;
}

void debug(const char *str) {
		const wchar_t *res = GetWC(str);
		ProcMonDebugOutput(res);
		delete[] res;
}

JNIEXPORT void JNICALL Java_com_tesec_logfilter_Trigger_trigger
(JNIEnv *, jobject, jint number) {
		char str[20];
		sprintf(str, "%d", number);
		debug(str);
		return;
}
