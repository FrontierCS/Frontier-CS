#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    if (scanf("%d", &n) != 1) return 0;

    vector<int> degD(n, 0), degF(n, 0);

    // Read distance matrix D and compute degrees for locations
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int x;
            scanf("%d", &x);
            if (x) {
                ++degD[i];
                ++degD[j];
            }
        }
    }

    // Read flow matrix F and compute degrees for facilities
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int x;
            scanf("%d", &x);
            if (x) {
                ++degF[i];
                ++degF[j];
            }
        }
    }

    vector<int> fac(n), loc(n);
    for (int i = 0; i < n; ++i) {
        fac[i] = i;
        loc[i] = i;
    }

    // Facilities: sort by decreasing flow degree
    sort(fac.begin(), fac.end(), [&](int a, int b) {
        if (degF[a] != degF[b]) return degF[a] > degF[b];
        return a < b;
    });

    // Locations: sort by increasing distance degree
    sort(loc.begin(), loc.end(), [&](int a, int b) {
        if (degD[a] != degD[b]) return degD[a] < degD[b];
        return a < b;
    });

    // Assign facilities to locations
    vector<int> p(n);
    for (int k = 0; k < n; ++k) {
        int fi = fac[k];
        int lo = loc[k];
        p[fi] = lo;
    }

    // Output permutation (1-based locations)
    for (int i = 0; i < n; ++i) {
        if (i) printf(" ");
        printf("%d", p[i] + 1);
    }
    printf("\n");

    return 0;
}