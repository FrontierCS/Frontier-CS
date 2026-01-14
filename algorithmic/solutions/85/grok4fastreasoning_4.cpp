#include <bits/stdc++.h>
using namespace std;

int main() {
    int current_d;
    scanf("%d", &current_d);
    while (current_d > 0) {
        bool progressed = false;
        for (int c = 0; c < 3; ++c) {
            printf("move %d\n", c);
            fflush(stdout);
            int r;
            scanf("%d", &r);
            if (r == 1) {
                current_d = 0;
                progressed = true;
                break;
            }
            int nd;
            scanf("%d", &nd);
            if (nd == current_d - 1) {
                current_d = nd;
                progressed = true;
                break;
            }
            // go back
            printf("move %d\n", c);
            fflush(stdout);
            int r2;
            scanf("%d", &r2);
        }
        // If no progress after 3 tries, something wrong, but shouldn't happen
    }
    return 0;
}