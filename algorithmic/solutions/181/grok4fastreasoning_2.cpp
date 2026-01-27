#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    scanf("%d", &n);
    vector<vector<int>> D(n, vector<int>(n));
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            scanf("%d", &D[i][j]);
        }
    }
    vector<vector<int>> F(n, vector<int>(n));
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            scanf("%d", &F[i][j]);
        }
    }
    vector<pair<int, int>> facs;
    for (int i = 0; i < n; i++) {
        int deg = 0;
        for (int j = 0; j < n; j++) deg += F[i][j];
        facs.push_back({-deg, i});
    }
    sort(facs.begin(), facs.end());
    vector<pair<int, int>> locs;
    for (int i = 0; i < n; i++) {
        int deg = 0;
        for (int j = 0; j < n; j++) deg += D[i][j];
        locs.push_back({deg, i});
    }
    sort(locs.begin(), locs.end());
    vector<int> assignment(n + 1);
    for (int k = 0; k < n; k++) {
        int fac = facs[k].second + 1;
        int loc = locs[k].second + 1;
        assignment[fac] = loc;
    }
    for (int i = 1; i <= n; i++) {
        if (i > 1) printf(" ");
        printf("%d", assignment[i]);
    }
    printf("\n");
    return 0;
}