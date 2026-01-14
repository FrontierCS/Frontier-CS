#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    string s;
    if (!(cin >> s)) return 0;
    int n = (int)s.size();
    
    vector<int> p; // positions of '1' (1-indexed)
    p.reserve(n + 2);
    vector<int> z; // zeros runs: z[0] before first '1', z[i] between p[i] and p[i+1], z[m] after last '1'
    z.reserve(n + 2);
    
    int curZeros = 0;
    for (int i = 0; i < n; ++i) {
        if (s[i] == '1') {
            z.push_back(curZeros);
            p.push_back(i + 1);
            curZeros = 0;
        } else {
            ++curZeros;
        }
    }
    if (p.empty()) {
        cout << 0 << '\n';
        return 0;
    }
    z.push_back(curZeros);
    
    int m = (int)p.size();
    vector<int> pvec(m + 2);
    pvec[0] = 0;
    for (int i = 1; i <= m; ++i) pvec[i] = p[i - 1];
    pvec[m + 1] = n + 1;
    
    vector<int> zvec(m + 1);
    for (int i = 0; i <= m; ++i) zvec[i] = z[i];
    
    long long ans = 0;
    
    int Kmax = 0;
    while (1LL * (Kmax + 1) * (Kmax + 2) <= 2LL * n + 1) { // find max k with k(k+1) <= n
        ++Kmax;
    }
    while (1LL * Kmax * (Kmax + 1) > n) --Kmax;
    
    for (int k = 1; k <= Kmax; ++k) {
        int base = k * k + k - 1; // k^2 + k - 1
        int i = 1, j = k;
        for (; j <= m; ++i, ++j) {
            int D = pvec[j] - pvec[i];
            int S = base - D; // required x + y
            if (S < 0) continue;
            int zl = zvec[i - 1];
            int zr = zvec[j];
            int sumzr = zl + zr;
            if (S > sumzr) continue;
            int maxl = (S < zl ? S : zl);
            int minl = S - zr; if (minl < 0) minl = 0;
            ans += (long long)(maxl - minl + 1);
        }
    }
    
    cout << ans << '\n';
    return 0;
}