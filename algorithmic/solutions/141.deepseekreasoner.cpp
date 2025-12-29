#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, k;
    scanf("%d%d", &n, &k);
    vector<bool> visited(n + 1, false);
    int distinct = 0;
    for (int i = 1; i <= n; ++i) {
        if (visited[i]) continue;
        distinct++;
        // Reset memory
        printf("R\n");
        fflush(stdout);
        // Query the pivot i
        printf("? %d\n", i);
        fflush(stdout);
        char resp;
        scanf(" %c", &resp);  // read response (not needed)
        // Now memory contains only a_i
        for (int j = i + 1; j <= n; ++j) {
            if (visited[j]) continue;
            printf("? %d\n", j);
            fflush(stdout);
            scanf(" %c", &resp);
            if (resp == 'Y') {
                visited[j] = true;
            }
        }
        visited[i] = true;
    }
    printf("! %d\n", distinct);
    fflush(stdout);
    return 0;
}