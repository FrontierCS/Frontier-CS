#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    // Construct words: w_i = X^i O^i
    for (int i = 1; i <= n; ++i) {
        string s(i, 'X');
        s += string(i, 'O');
        cout << s << "\n";
    }
    cout.flush();

    int q;
    if (!(cin >> q)) return 0;

    // Precompute S_i = 2*i and P_i = i*i
    vector<long long> S(n+1), P(n+1);
    for (int i = 1; i <= n; ++i) {
        S[i] = 2LL * i;
        P[i] = 1LL * i * i;
    }

    while (q--) {
        long long p;
        cin >> p;
        bool found = false;

        // Try assuming j is the max index:
        for (int j = 1; j <= n && !found; ++j) {
            long long T = p - (P[j] + S[j]);
            if (T < 0) continue;
            if (T % S[j] != 0) continue;
            long long K = T / S[j]; // K = S_i
            if (K <= 0) continue;
            if (K % 2 != 0) continue;
            int i = (int)(K / 2);
            if (i >= 1 && i <= j) {
                cout << i << " " << j << "\n";
                cout.flush();
                found = true;
            }
        }

        // Fallback: assume i is the max index
        if (!found) {
            for (int i = 1; i <= n && !found; ++i) {
                long long T = p - P[i];
                if (T <= 0) continue;
                if (T % S[i] != 0) continue;
                long long val = T / S[i]; // val = S_j + 1
                long long Sj = val - 1;
                if (Sj <= 0) continue;
                if (Sj % 2 != 0) continue;
                int j = (int)(Sj / 2);
                if (j >= i && j <= n) {
                    cout << i << " " << j << "\n";
                    cout.flush();
                    found = true;
                }
            }
        }

        if (!found) {
            // As a last resort (shouldn't happen if inputs are consistent with our words)
            cout << 1 << " " << 1 << "\n";
            cout.flush();
        }
    }

    return 0;
}