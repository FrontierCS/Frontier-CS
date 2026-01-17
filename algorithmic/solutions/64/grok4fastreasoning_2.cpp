#include <bits/stdc++.h>
using namespace std;
using ll = long long;
using lll = __int128;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    ll T;
    cin >> n >> T;
    vector<ll> a(n);
    for (auto &x : a) cin >> x;
    const int BEAM = 1 << 12; // 4096
    vector<pair<ll, lll>> curr = {{0, 0}};
    for (int i = 0; i < n; ++i) {
        vector<pair<ll, lll>> nxt;
        for (auto [s, m] : curr) {
            nxt.emplace_back(s, m);
            ll ns = s + a[i];
            lll nm = m | (static_cast<lll>(1) << i);
            nxt.emplace_back(ns, nm);
        }
        sort(nxt.begin(), nxt.end(), [&](const auto& p1, const auto& p2) {
            ll e1 = abs(p1.first - T);
            ll e2 = abs(p2.first - T);
            if (e1 != e2) return e1 < e2;
            return p1.first < p2.first;
        });
        if (nxt.size() > BEAM) nxt.resize(BEAM);
        curr = std::move(nxt);
    }
    auto [best_sum, mask] = curr[0];
    string res;
    res.reserve(n);
    for (int i = 0; i < n; ++i) {
        if (mask & (static_cast<lll>(1) << i)) {
            res += '1';
        } else {
            res += '0';
        }
    }
    cout << res << '\n';
    return 0;
}