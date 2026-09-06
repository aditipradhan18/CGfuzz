#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    char input[1024];

    size_t n = fread(input, 1, sizeof(input) - 1, stdin);
    input[n] = '\0';

    if (n == 0) {
        printf("EMPTY_PATH\n");
        return 0;
    }

    if (input[0] == 'A') {
        if (n > 1 && input[1] == 'B') {
            printf("PATH_AB\n");
        } else {
            printf("PATH_A\n");
        }
    }
    else if (input[0] == 'B') {
        if (n > 1 && input[1] == 'C') {
            printf("PATH_BC\n");
        } else {
            printf("PATH_B\n");
        }
    }
    else if (n >= 5 &&
             input[0] == 'C' &&
             input[1] == 'R' &&
             input[2] == 'A' &&
             input[3] == 'S' &&
             input[4] == 'H') {

        volatile int *ptr = NULL;
        *ptr = 1337;
    }
    else if (n >= 4 &&
             input[0] == 'F' &&
             input[1] == 'U' &&
             input[2] == 'Z' &&
             input[3] == 'Z') {

        printf("FUZZ_PATH\n");
    }
    else {
        printf("NORMAL_PATH\n");
    }

    return 0;
}