#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct Solver {
    ll n;
    int query_count = 0;

    unordered_map<ll, ll> d1_cache;
    unordered_map<ll, ll> d2_cache;

    ll norm(ll x) {
        x %= n;
        if (x <= 0) x += n;
        return x;
    }

    ll cycDist(ll a, ll b) {
        ll d = llabs(a - b);
        return min(d, n - d);
    }

    ll ask(ll x, ll y) {
        cout << "? " << x << " " << y << endl;
        cout.flush();
        ll res;
        if (!(cin >> res)) exit(0);
        return res;
    }

    ll getD1(ll i) {
        auto it = d1_cache.find(i);
        if (it != d1_cache.end()) return it->second;
        ll d = ask(1, i);
        d1_cache[i] = d;
        return d;
    }

    ll getD2(ll i) {
        auto it = d2_cache.find(i);
        if (it != d2_cache.end()) return it->second;
        ll d = ask(2, i);
        d2_cache[i] = d;
        return d;
    }

    ll F(ll i) {
        ll s1 = cycDist(1, i) - getD1(i);
        ll s2 = cycDist(2, i) - getD2(i);
        return s1 + s2;
    }

    pair<ll,ll> try_from_candidate(ll b) {
        ll d1b = getD1(b);
        if (d1b <= 0) return {-1,-1};
        ll r = d1b - 1;
        ll a1 = norm(1 + r);
        ll a2 = norm(1 - r);

        // Ensure non-adjacent along cycle
        if (cycDist(a1, b) > 1) {
            ll d = ask(a1, b);
            if (d == 1) return {a1, b};
        }
        if (cycDist(a2, b) > 1) {
            ll d = ask(a2, b);
            if (d == 1) return {a2, b};
        }
        return {-1,-1};
    }

    pair<ll,ll> solve_one() {
        d1_cache.clear();
        d2_cache.clear();

        // Steps for bit-lifting
        vector<ll> steps;
        for (ll s = 1; s <= n/2; s <<= 1) steps.push_back(s);
        reverse(steps.begin(), steps.end());

        // Start near opposite of 1
        ll pos = norm(1 + n/2);
        ll curF = F(pos);

        for (ll s : steps) {
            ll p1 = norm(pos + s);
            ll p2 = norm(pos - s);
            ll f1 = F(p1);
            ll f2 = F(p2);
            if (f1 >= f2 && f1 > curF) {
                pos = p1;
                curF = f1;
            } else if (f2 > curF) {
                pos = p2;
                curF = f2;
            }
        }

        // Collect candidate indices around pos and using grid sampling
        unordered_set<ll> used;
        vector<ll> candidates;

        auto add_cand = [&](ll x){
            if (!used.count(x)) { used.insert(x); candidates.push_back(x); }
        };

        add_cand(pos);
        for (ll s : steps) {
            add_cand(norm(pos + s));
            add_cand(norm(pos - s));
        }

        // Grid sampling
        ll M = (n <= 200 ? n : 200);
        for (ll k = 0; k < M; ++k) {
            ll idx = norm(1 + (k * (n / M)));
            add_cand(idx);
        }

        // Evaluate F for candidates
        vector<pair<ll,ll>> scored; // (score, index)
        scored.reserve(candidates.size());
        for (ll idx : candidates) {
            scored.push_back({F(idx), idx});
        }
        sort(scored.begin(), scored.end(), [&](const pair<ll,ll>& a, const pair<ll,ll>& b){
            if (a.first != b.first) return a.first > b.first;
            // Tie-breaker: closer to pos preferred
            ll da = min((ll)abs(a.second - pos), n - (ll)abs(a.second - pos));
            ll db = min((ll)abs(b.second - pos), n - (ll)abs(b.second - pos));
            return da < db;
        });

        // Try top candidates first
        for (size_t i = 0; i < scored.size() && i < 300; ++i) {
            ll b = scored[i].second;
            auto res = try_from_candidate(b);
            if (res.first != -1) return res;
        }

        // If not found, expand local search around pos
        ll R = min( (ll)256, n/2 );
        vector<pair<ll,ll>> local;
        for (ll d = 0; d <= R; ++d) {
            ll i1 = norm(pos + d);
            ll i2 = norm(pos - d);
            if (!used.count(i1)) { used.insert(i1); local.push_back({F(i1), i1}); }
            if (!used.count(i2)) { used.insert(i2); local.push_back({F(i2), i2}); }
        }
        sort(local.begin(), local.end(), greater<pair<ll,ll>>());
        for (auto &p : local) {
            auto res = try_from_candidate(p.second);
            if (res.first != -1) return res;
        }

        // As a last resort, scan more grid points if budget permits
        ll extra = 300;
        for (ll k = 0; k < extra; ++k) {
            ll idx = norm(1 + (k * (n / max(1LL, extra))));
            if (used.count(idx)) continue;
            used.insert(idx);
            (void)F(idx);
            auto res = try_from_candidate(idx);
            if (res.first != -1) return res;
        }

        // Fallback (should not happen): output some non-adjacent pair based on heuristic
        // Use the best scored candidate and derive A from it ignoring adjacency (but enforce non-adjacent)
        if (!scored.empty()) {
            ll b = scored[0].second;
            ll d1b = getD1(b);
            ll r = d1b - 1;
            ll a1 = norm(1 + r);
            ll a2 = norm(1 - r);
            if (cycDist(a1,b) > 1) return {a1,b};
            if (cycDist(a2,b) > 1) return {a2,b};
        }
        // Absolute fallback: choose 1 and 1+2
        return {1, norm(1 + 2)};
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        Solver solver;
        cin >> solver.n;

        auto ans = solver.solve_one();
        cout << "! " << ans.first << " " << ans.second << endl;
        cout.flush();

        int r;
        if (!(cin >> r)) return 0;
        if (r == -1) return 0;
    }
    return 0;
}