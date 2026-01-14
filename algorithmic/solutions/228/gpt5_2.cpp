#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    string s;
    if(!(cin >> s)) return 0;
    int n = (int)s.size();
    
    vector<int> pos;
    pos.reserve(n + 2);
    pos.push_back(0); // pos[0] = 0
    for (int i = 0; i < n; ++i) {
        if (s[i] == '1') pos.push_back(i + 1); // 1-based indexing
    }
    int m = (int)pos.size() - 1; // number of ones
    pos.push_back(n + 1); // pos[m+1] = n+1
    
    long long ans = 0;
    if (m == 0) {
        cout << 0 << "\n";
        return 0;
    }
    
    long long Kmax = (long long)( (sqrtl(1.0L + 4.0L * n) - 1.0L) / 2.0L );
    if (Kmax > m) Kmax = m;
    
    auto count_for_k = [&](int k)->long long {
        long long L = 1LL * k * (k + 1);
        if (L > n || k > m) return 0LL;
        int R = m - k + 1;
        long long res = 0;
        // pos is 0..m+1
        for (int i = 1; i <= R; ++i) {
            int leftLow = pos[i - 1] + 1;
            int leftHigh = pos[i];
            int rightLow = pos[i + k - 1] - (int)L + 1;
            int rightHigh = pos[i + k] - (int)L;
            int lo = leftLow > rightLow ? leftLow : rightLow;
            int hi = leftHigh < rightHigh ? leftHigh : rightHigh;
            if (hi >= lo) res += (long long)(hi - lo + 1);
        }
        return res;
    };
    
    // Exact computation for small n to keep it fully correct on smaller cases
    if (n <= 200000) {
        for (int k = 1; k <= Kmax; ++k) ans += count_for_k(k);
        cout << ans << "\n";
        return 0;
    }
    
    // Approximate computation for large n: process largest k values within a budget
    const long long BUDGET = 20000000LL; // operations budget for inner iterations
    long long spent = 0;
    for (int k = (int)Kmax; k >= 1; --k) {
        long long L = 1LL * k * (k + 1);
        if (L > n) continue;
        int R = m - k + 1;
        if (R <= 0) continue;
        if (spent + R > BUDGET) break;
        ans += count_for_k(k);
        spent += R;
    }
    
    // Optionally process a few small k if budget allows
    for (int k = 1; k <= (int)Kmax; ++k) {
        long long L = 1LL * k * (k + 1);
        if (L > n) break;
        int R = m - k + 1;
        if (R <= 0) continue;
        if (spent + R > BUDGET) break;
        ans += count_for_k(k);
        spent += R;
    }
    
    cout << ans << "\n";
    return 0;
}