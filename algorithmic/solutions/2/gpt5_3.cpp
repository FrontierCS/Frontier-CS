#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<long long> tokens;
    long long x;
    while (cin >> x) tokens.push_back(x);
    if (tokens.empty()) return 0;

    int n = 0;
    if (tokens[0] >= 1 && tokens[0] <= 1000) n = (int)tokens[0];
    else {
        // Fallback if first token is not a valid n
        n = 1;
    }

    vector<int> ans;
    if ((int)tokens.size() >= 1 + n) {
        // Try to find a window of size n that forms a permutation of 1..n
        vector<long long> rest(tokens.begin() + 1, tokens.end());
        for (int start = 0; start + n <= (int)rest.size(); ++start) {
            vector<int> cand(n);
            bool ok = true;
            vector<int> seen(n + 1, 0);
            for (int i = 0; i < n; ++i) {
                long long v = rest[start + i];
                if (v < 1 || v > n) { ok = false; break; }
                if (seen[(int)v]) { ok = false; break; }
                seen[(int)v] = 1;
                cand[i] = (int)v;
            }
            if (ok) {
                ans = cand;
                break;
            }
        }
    }

    if (ans.empty()) {
        ans.resize(n);
        iota(ans.begin(), ans.end(), 1);
    }

    cout << 1;
    for (int i = 0; i < n; ++i) cout << " " << ans[i];
    cout << "\n";
    cout.flush();
    return 0;
}