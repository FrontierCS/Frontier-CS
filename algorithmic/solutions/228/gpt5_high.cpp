#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    string s;
    if(!(cin >> s)) return 0;
    int n = (int)s.size();
    
    // Build zero-runs array g: g[0] zeros before first '1', g[1] between first and second '1', ..., g[m] after last '1'
    vector<int> g;
    g.reserve(n + 1);
    int cnt0 = 0, m = 0;
    for (char c : s) {
        if (c == '0') {
            cnt0++;
        } else {
            g.push_back(cnt0);
            cnt0 = 0;
            m++;
        }
    }
    g.push_back(cnt0); // zeros after last '1'
    // Now g.size() == m + 1
    
    if (m == 0) {
        cout << 0 << '\n';
        return 0;
    }
    
    // Prefix sums of g for quick interior sums
    vector<int> pre(m + 2, 0);
    for (int i = 0; i <= m; ++i) pre[i + 1] = pre[i] + g[i];
    
    long long ans = 0;
    int kmax = (int)((sqrt(4.0 * n + 1.0) - 1.0) / 2.0);
    if (kmax > m) kmax = m;
    
    for (int k = 1; k <= kmax; ++k) {
        int k2 = k * k;
        // S(s) = sum g[s+1 .. s+k-1] = pre[s+k] - pre[s+1]
        int s_end = m - k;
        int S = pre[k] - pre[1]; // initial s=0
        int A = g[0];
        int B = g[k];
        for (int sidx = 0; sidx <= s_end; ++sidx) {
            int T = k2 - S;
            if (T >= 0) {
                int AB = A + B;
                if (T <= AB) {
                    int low = T - B;
                    if (low < 0) low = 0;
                    int high = (T < A) ? T : A;
                    if (high >= low) ans += (long long)(high - low + 1);
                }
            }
            // move to next s
            if (sidx < s_end) {
                // update S: remove g[s+1], add g[s+k]
                S = S - g[sidx + 1] + g[sidx + k];
                A = g[sidx + 1];
                B = g[sidx + k + 1];
            }
        }
    }
    
    cout << ans << '\n';
    return 0;
}