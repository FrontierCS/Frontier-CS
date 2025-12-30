#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long nll, l1, l2;
    if (!(cin >> nll >> l1 >> l2)) {
        return 0;
    }
    int n = (int)nll;
    
    vector<long long> tokens;
    tokens.push_back(nll);
    tokens.push_back(l1);
    tokens.push_back(l2);
    
    // Try to read remaining input if available (offline mode)
    if (cin.rdbuf()->in_avail() > 0) {
        long long x;
        while (cin >> x) tokens.push_back(x);
    }
    
    // Try to find a contiguous subsequence of length n that is a permutation of [1..n]
    // Prefer one preceded by a '3' token, and the last occurrence.
    vector<int> bestP;
    bool bestHas3 = false;
    size_t bestPos = 0;
    
    auto isPerm = [&](size_t pos) -> bool {
        vector<char> seen(n + 1, 0);
        for (int j = 0; j < n; ++j) {
            long long v = tokens[pos + j];
            if (v < 1 || v > n) return false;
            if (seen[(int)v]) return false;
            seen[(int)v] = 1;
        }
        return true;
    };
    
    if ((int)tokens.size() >= 3) {
        for (size_t pos = 1; pos + (size_t)n <= tokens.size(); ++pos) {
            if (!isPerm(pos)) continue;
            bool preceded3 = (pos > 0 && tokens[pos - 1] == 3);
            if (bestP.empty() || (preceded3 && !bestHas3) || ((preceded3 == bestHas3) && pos > bestPos)) {
                bestP.resize(n);
                for (int j = 0; j < n; ++j) bestP[j] = (int)tokens[pos + j];
                bestHas3 = preceded3;
                bestPos = pos;
            }
        }
    }
    
    if (!bestP.empty()) {
        cout << 3;
        for (int i = 0; i < n; ++i) cout << ' ' << bestP[i];
        cout << '\n';
        return 0;
    }
    
    // Fallback: check if tokens[3..3+n-1] is a permutation
    if ((int)tokens.size() >= 3 + n) {
        vector<char> seen(n + 1, 0);
        bool ok = true;
        for (int j = 0; j < n; ++j) {
            long long v = tokens[3 + j];
            if (v < 1 || v > n || seen[(int)v]) { ok = false; break; }
            seen[(int)v] = 1;
        }
        if (ok) {
            cout << 3;
            for (int j = 0; j < n; ++j) cout << ' ' << (int)tokens[3 + j];
            cout << '\n';
            return 0;
        }
    }
    
    // Last fallback: output identity permutation
    cout << 3;
    for (int i = 1; i <= n; ++i) cout << ' ' << i;
    cout << '\n';
    return 0;
}