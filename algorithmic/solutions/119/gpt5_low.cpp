#include <bits/stdc++.h>
using namespace std;

static const long long MOD = 1000000007LL;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;

    vector<long long> base(n+1, 1);
    base[0] = 2; // set a0 = 2, others = 1

    // Send baseline query
    cout << "?";
    for (int i = 0; i <= n; ++i) {
        cout << " " << base[i];
    }
    cout << "\n" << flush;

    long long R0;
    if(!(cin >> R0)) return 0;

    vector<int> op(n, -1); // 0 for '+', 1 for '×'
    int plus_prefix = 0;

    int skip_idx = n; // 1-based index to skip querying
    for (int i = 1; i <= n; ++i) {
        if (i == skip_idx) continue;

        vector<long long> q = base;
        q[i] = 2; // change a_i from 1 to 2

        cout << "?";
        for (int j = 0; j <= n; ++j) {
            cout << " " << q[j];
        }
        cout << "\n" << flush;

        long long Ri;
        if(!(cin >> Ri)) return 0;

        long long Di = (Ri - R0) % MOD;
        if (Di < 0) Di += MOD;

        long long S_prev = 2 + plus_prefix; // S_{i-1} under baseline

        if (Di == 1) {
            op[i-1] = 0; // '+'
            plus_prefix++;
        } else if (Di == S_prev) {
            op[i-1] = 1; // '×'
        } else {
            // Should not happen in correct interaction; fallback decide by comparison
            // If Di equals 1 mod MOD treat as '+', else '×'
            if (Di == 1) {
                op[i-1] = 0;
                plus_prefix++;
            } else {
                op[i-1] = 1;
            }
        }
    }

    // Deduce the skipped operator using total number of '+'
    long long total_plus = (R0 - 2) % MOD;
    if (total_plus < 0) total_plus += MOD;
    // total_plus should be small (<= n), safe to cast
    long long plus_so_far = plus_prefix;
    long long remaining_plus = (total_plus - plus_so_far) % MOD;
    if (remaining_plus < 0) remaining_plus += MOD;
    // remaining_plus must be either 0 or 1 since only one operator skipped
    op[skip_idx - 1] = (remaining_plus == 1 ? 0 : 1);

    // Output the operators
    cout << "!";
    for (int i = 0; i < n; ++i) {
        cout << " " << op[i];
    }
    cout << "\n" << flush;

    return 0;
}