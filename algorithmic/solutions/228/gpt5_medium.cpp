#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string s;
    if (!getline(cin, s)) return 0;
    int n = (int)s.size();
    vector<int> P(n+1, 0);
    for (int i = 0; i < n; ++i) P[i+1] = P[i] + (s[i] == '1');
    long long ans = 0;
    // t = number of ones; length L = t*(t+1)
    for (long long t = 1;; ++t) {
        long long L = t * (t + 1);
        if (L > n) break;
        int Li = (int)L;
        for (int r = Li; r <= n; ++r) {
            if (P[r] - P[r - Li] == t) ++ans;
        }
    }
    cout << ans << "\n";
    return 0;
}