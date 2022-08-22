package com.tesec.logfilter;

import java.util.Scanner;

public class Test {
    // main -> mains
    public static void main(String[] args) throws Exception {
        Scanner sc = new Scanner(System.in);
        while (true) {
            int number = sc.nextInt();
            Trigger.debug(number);
        }
        // System.out.println("222");
    }
}
