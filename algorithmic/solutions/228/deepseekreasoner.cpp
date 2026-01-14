#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    string s;
    cin >> s;
    int n = s.length();
    vector<int> pos;
    for (int i = 0; i < n; ++i) {
        if (s[i] == '1') {
            pos.push_back(i);
        }
    }
    int m = pos.size();
    if (m == 0) {
        cout << 0 << '\n';
        return 0;
    }
    vector<int> left_gap(m), right_gap(m);
    left_gap[0] = pos[0];
    for (int i = 1; i < m; ++i) {
        left_gap[i] = pos[i] - pos[i-1] - 1;
    }
    right_gap[m-1] = (n-1) - pos[m-1];
    for (int i = 0; i < m-1; ++i) {
        right_gap[i] = pos[i+1] - pos[i] - 1;
    }
    ll ans = 0;
    for (int i = 0; i < m; ++i) {
        int left_avail = left_gap[i];
        for (int x = 1; i + x - 1 < m; ++x) {
            int j = i + x - 1;
            int span = pos[j] - pos[i] + 1;
            ll L = 1LL * x * (x + 1);
            if (L > n) break;
            if (L < span) continue;
            ll max_len = span + left_avail + right_gap[j];
            if (L > max_len) break;
            ll extra = L - span;
            ll min_a = max(0LL, extra - right_gap[j]);
            ll max_a = min((ll)left_avail, extra);
            if (max_a >= min_a) {
                ans += (max_a - min_a + 1);
            }
        }
    }
    cout << ans << '\n';
    return 0;
}