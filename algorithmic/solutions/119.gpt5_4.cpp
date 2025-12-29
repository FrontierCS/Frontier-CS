#include <bits/stdc++.h>
using namespace std;

static const long long MOD = 1000000007LL;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    auto query = [&](int idx_set_two) -> long long {
        // idx_set_two: index i in [1..n] to set a_i = 2; if 0, set none (baseline)
        cout << "?";
        // a0
        cout << " " << 2;
        // a1..an
        for (int i = 1; i <= n; ++i) {
            if (i == idx_set_two) cout << " " << 2;
            else cout << " " << 1;
        }
        cout << "\n";
        cout.flush();
        long long res;
        if (!(cin >> res)) exit(0);
        if (res == -1) exit(0);
        return res;
    };

    // Baseline query (all ones except a0 = 2)
    long long R0 = query(0);
    long long P = (R0 - 2) % MOD;
    if (P < 0) P += MOD;

    vector<int> op(n+1, 0); // 1..n, 0 for '+', 1 for '*'
    int plus_count = 0;

    // Query for i = 1..n-1
    for (int i = 1; i <= n - 1; ++i) {
        long long Ri = query(i);
        long long diff = (Ri - R0) % MOD;
        if (diff < 0) diff += MOD;
        if (diff == 1) {
            op[i] = 0; // '+'
            plus_count++;
        } else {
            op[i] = 1; // '*'
        }
    }

    // Deduce last operator using total P = number of '+' operators
    // Since R0 = 2 + P (no wrap as P <= n <= 600 < MOD)
    long long total_plus = (R0 - 2 + MOD) % MOD;
    if (total_plus < 0) total_plus += MOD;
    // total_plus should be small integer in [0, n]
    if (plus_count < total_plus) op[n] = 0; else op[n] = 1;

    // Output result
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << (op[i] == 1 ? 1 : 0);
    }
    cout << "\n";
    cout.flush();

    return 0;
}