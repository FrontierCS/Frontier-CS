#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int n = 100;
    const int denom = n - 4; // = 96
    const int MAXM = n * (n - 1) / 2; // 4950

    static long long A[n + 1];
    static int S[n + 1][n + 1];
    static long long deg[n + 1];
    static bool adj[n + 1][n + 1];

    // Query all triples
    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            for (int k = j + 1; k <= n; ++k) {
                cout << "? " << i << ' ' << j << ' ' << k << endl;
                int t;
                if (!(cin >> t)) return 0;
                if (t < 0) return 0; // in case of judge error signal

                A[i] += t;
                A[j] += t;
                A[k] += t;

                S[i][j] += t;
                S[i][k] += t;
                S[j][k] += t;
            }
        }
    }

    long long foundM = -1;

    for (long long M = 0; M <= MAXM; ++M) {
        bool ok = true;
        long long sumDeg = 0;

        for (int i = 1; i <= n; ++i) {
            long long Ai = A[i];
            if (Ai < M) { ok = false; break; }
            long long x = Ai - M;
            if (x % denom != 0) { ok = false; break; }
            long long d = x / denom;
            if (d < 0 || d > n - 1) { ok = false; break; }
            deg[i] = d;
            sumDeg += d;
        }
        if (!ok) continue;
        if (sumDeg != 2 * M) continue;

        // Check S constraints and build adjacency
        for (int i = 1; i <= n && ok; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                long long diff = (long long)S[i][j] - deg[i] - deg[j];
                if (diff == 0) {
                    adj[i][j] = adj[j][i] = false;
                } else if (diff == denom) {
                    adj[i][j] = adj[j][i] = true;
                } else {
                    ok = false;
                    break;
                }
            }
        }

        if (ok) {
            foundM = M;
            break;
        }
    }

    // Output the reconstructed graph
    cout << "!" << '\n';
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if (i == j) cout << '0';
            else cout << (adj[i][j] ? '1' : '0');
        }
        cout << '\n';
    }
    cout.flush();

    return 0;
}