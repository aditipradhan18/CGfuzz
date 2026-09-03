#include <stdio.h>
#include <string.h>

int main(void) {
    char input[16];

    if (fgets(input, sizeof(input), stdin) == NULL) {
        return 0;
    }

    /*
     * Intentional deterministic crash trigger.
     * Used to validate CGFuzz's native crash detection,
     * classification, minimization, and reproduction pipeline.
     */
    if (strncmp(input, "CRASH", 5) == 0) {
        volatile int *ptr = NULL;
        *ptr = 1;
    }

    if (strncmp(input, "FUZZ", 4) == 0) {
        printf("FUZZ_PATH\n");
    } else if (strncmp(input, "TEST", 4) == 0) {
        printf("TEST_PATH\n");
    } else {
        printf("NORMAL_PATH\n");
    }

    return 0;
}