#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

vector<ll> read_ints(int n) {
    vector<ll> res(n);
    for (int i = 0; i < n; ++i) cin >> res[i];
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(0);

    ll B;
    int k, w;
    cin >> B >> k >> w;

    // Wave 1: probes at (-B,-B) and (B,B)
    cout << "? 2 " << -B << " " << -B << " " << B << " " << B << endl;
    vector<ll> L1 = read_ints(2 * k);
    // Wave 2: probes at (-B,B) and (B,-B)
    cout << "? 2 " << -B << " " << B << " " << B << " " << -B << endl;
    vector<ll> L2 = read_ints(2 * k);

    sort(L1.begin(), L1.end());
    sort(L2.begin(), L2.end());

    // Pair distances from each deposit: i-th smallest with i-th largest
    vector<pair<ll, ll>> pairs1(k), pairs2(k);
    for (int i = 0; i < k; ++i) {
        pairs1[i] = {L1[i], L1[2 * k - 1 - i]};
        pairs2[i] = {L2[i], L2[2 * k - 1 - i]};
    }

    // Backtracking to find all possible point sets consistent with the two waves
    vector<bool> used2(k, false);
    vector<pair<ll, ll>> cur;
    set<vector<pair<ll, ll>>> candidates;

    function<void(int)> dfs = [&](int i) {
        if (i == k) {
            vector<pair<ll, ll>> sorted_pts = cur;
            sort(sorted_pts.begin(), sorted_pts.end());
            candidates.insert(sorted_pts);
            return;
        }
        ll a = pairs1[i].first, b = pairs1[i].second;   // a ≤ b
        ll S_mag = (b - a) / 2;                         // |x+y|
        ll c = pairs2[i].first, d = pairs2[i].second;   // c ≤ d
        ll D_mag = (d - c) / 2;                         // |x-y|

        // Try both signs for S = x+y and D = x-y
        for (int signS : {1, -1}) {
            ll S = signS * S_mag;
            for (int signD : {1, -1}) {
                ll D = signD * D_mag;
                if (((S + D) & 1) != 0) continue;   // x, y must be integers
                ll x = (S + D) / 2;
                ll y = (S - D) / 2;
                if (x < -B || x > B || y < -B || y > B) continue;

                bool duplicate = false;
                for (const auto& p : cur) {
                    if (p.first == x && p.second == y) {
                        duplicate = true;
                        break;
                    }
                }
                if (duplicate) continue;

                cur.push_back({x, y});
                dfs(i + 1);
                cur.pop_back();
            }
        }
    };

    dfs(0);

    int waves_used = 2;
    // Use additional waves to filter candidates if more than one remain
    while (candidates.size() > 1 && waves_used < w) {
        static const vector<pair<ll, ll>> extra_probes = {
            {0, 1}, {1, 0}, {0, -1}, {-1, 0},
            {1, 1}, {-1, 1}, {1, -1}, {-1, -1}
        };
        int idx = waves_used - 2;
        if (idx >= (int)extra_probes.size()) idx = extra_probes.size() - 1;
        ll sx = extra_probes[idx].first, sy = extra_probes[idx].second;

        cout << "? 1 " << sx << " " << sy << endl;
        vector<ll> dists = read_ints(k);
        sort(dists.begin(), dists.end());

        set<vector<pair<ll, ll>>> new_candidates;
        for (const auto& pts : candidates) {
            vector<ll> cur_dists;
            for (const auto& p : pts) {
                cur_dists.push_back(abs(p.first - sx) + abs(p.second - sy));
            }
            sort(cur_dists.begin(), cur_dists.end());
            if (cur_dists == dists) new_candidates.insert(pts);
        }
        candidates = new_candidates;
        ++waves_used;
    }

    // Output the answer (if multiple remain, pick any – problem guarantees uniqueness)
    vector<pair<ll, ll>> ans = *candidates.begin();
    cout << "!";
    for (const auto& p : ans) {
        cout << " " << p.first << " " << p.second;
    }
    cout << endl;

    return 0;
}