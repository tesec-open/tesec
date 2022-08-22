package com.tesec.logfilter;

public class Trigger {
    public native void trigger(int number);

    static {
        System.loadLibrary("trigger");
    }

    public static void debug(int number) {
        new Trigger().trigger(number);
    }
}

