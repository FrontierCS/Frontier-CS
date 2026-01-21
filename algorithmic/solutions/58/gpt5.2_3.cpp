#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    unsigned long long x;
    if (!(cin >> x)) return 0;

    int maxb = 63 - __builtin_clzll(x); // x >= 1
    int K = maxb + 1;                   // need bits 0..maxb
    int N = 2 * K + 2;                  // ensure base can't touch destination directly

    vector<vector<int>> a(N, vector<int>(N, 0));

    // Vertical spine to destination at last column
    for (int i = 0; i < N; i++) a[i][N - 1] = 1;

    // Base doubling chain (K blocks)
    for (int k = 1; k <= K; k++) {
        int rS = 2 * k - 1, cS = k;     // S_k
        int rA = 2 * k,     cA = k;     // A_k
        int rD = 2 * k,     cD = k + 1; // D_k
        int rB = 2 * k + 1, cB = k;     // B_k
        int rE = 2 * k + 1, cE = k + 1; // E_k

        a[rS - 1][cS - 1] = 1;
        a[rA - 1][cA - 1] = 1;
        a[rD - 1][cD - 1] = 1;
        a[rB - 1][cB - 1] = 1;
        a[rE - 1][cE - 1] = 1;
    }

    // Exit corridors for set bits: from D_{b+1} to the spine
    for (int b = 0; b < K; b++) {
        if ((x >> b) & 1ULL) {
            int k = b + 1;
            int r = 2 * k;      // row of D_k
            int c = k + 1;      // col of D_k
            for (int j = c; j <= N; j++) a[r - 1][j - 1] = 1;
        }
    }

    cout << N << "\n";
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (j) cout << ' ';
            cout << a[i][j];
        }
        cout << "\n";
    }
    return 0;
}