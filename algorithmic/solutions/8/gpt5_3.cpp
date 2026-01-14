#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long k;
    if (!(cin >> k)) return 0;
    long long T = (k - 1) / 2; // sum of (2^m - 1)
    
    vector<int> msizes;
    for (int i = 30; i >= 1; --i) {
        long long val = (1LL << i) - 1;
        long long cnt = T / val;
        for (long long c = 0; c < cnt; ++c) msizes.push_back(i);
        T -= cnt * val;
    }
    // Now T should be zero
    long long sum_m = 0;
    for (int m : msizes) sum_m += m;
    
    if (msizes.empty()) {
        cout << 1 << "\n";
        cout << "HALT PUSH 1 GOTO 1\n";
        return 0;
    }
    
    int n = (int)sum_m + 1; // total instructions including final HALT
    cout << n << "\n";
    
    int cur = 1;
    int totalModules = (int)msizes.size();
    int HALT_idx = n;
    
    for (int j = 0; j < totalModules; ++j) {
        int m = msizes[j];
        int start = cur;
        int nextStart = (j + 1 < totalModules) ? (start + m) : HALT_idx;
        for (int t = 0; t < m; ++t) {
            int idx = start + t;
            int a = idx;
            int x = (t < m - 1) ? (idx + 1) : nextStart;
            int y = start;
            cout << "POP " << a << " GOTO " << x << " PUSH " << a << " GOTO " << y << "\n";
        }
        cur += m;
    }
    // HALT instruction
    cout << "HALT PUSH 1 GOTO " << HALT_idx << "\n";
    return 0;
}