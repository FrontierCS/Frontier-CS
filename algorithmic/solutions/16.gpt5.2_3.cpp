#include <bits/stdc++.h>
using namespace std;

using ll = long long;

static const int QUERY_LIMIT = 500;

struct Solver {
    ll n = 0;
    int qcnt = 0;
    unordered_map<unsigned long long, int> cache;
    mt19937_64 rng;

    Solver() : rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count()) {
        cache.reserve(2048);
        cache.max_load_factor(0.7f);
    }

    static unsigned long long key(ll x, ll y) {
        if (x > y) swap(x, y);
        return (unsigned long long)((unsigned long long)x << 32) ^ (unsigned long long)y;
    }

    ll nxt(ll v) const { return (v == n) ? 1 : (v + 1); }
    ll prv(ll v) const { return (v == 1) ? n : (v - 1); }

    bool adjacentCycle(ll a, ll b) const {
        return (nxt(a) == b) || (prv(a) == b);
    }

    ll step(ll v, ll k, int dir) const {
        k %= n;
        ll x = v - 1;
        if (dir == 1) {
            x = (x + k) % n;
        } else {
            x = (x - k) % n;
            x %= n;
            if (x < 0) x += n;
        }
        return x + 1;
    }

    int cycleDist(ll a, ll b) const {
        ll d = llabs(a - b);
        d = min(d, n - d);
        return (int)d;
    }

    int ask(ll x, ll y) {
        if (x == y) return 0;
        auto k = key(x, y);
        auto it = cache.find(k);
        if (it != cache.end()) return it->second;
        if (qcnt >= QUERY_LIMIT) exit(0);

        cout << "? " << x << " " << y << endl;
        cout.flush();

        int ans;
        if (!(cin >> ans)) exit(0);
        if (ans == -1) exit(0);

        qcnt++;
        cache.emplace(k, ans);
        return ans;
    }

    void answer(ll u, ll v) {
        cout << "! " << u << " " << v << endl;
        cout.flush();
        int r;
        if (!(cin >> r)) exit(0);
        if (r == -1) exit(0);
    }

    ll lastOnShortestFrom(ll s, ll t, int D, int dir) {
        ll lo = 0, hi = D;
        while (lo < hi) {
            ll mid = (lo + hi + 1) / 2;
            ll x = step(s, mid, dir);

            int ds = ask(s, x);
            if (ds != (int)mid) {
                hi = mid - 1;
                continue;
            }
            int dt = ask(x, t);
            if (ds + dt == D) lo = mid;
            else hi = mid - 1;
        }
        return step(s, lo, dir);
    }

    optional<pair<ll,ll>> solveFromPair(ll a, ll b, int d) {
        if (d == 1 && !adjacentCycle(a, b)) return pair<ll,ll>{a, b};

        vector<int> dirA, dirB;
        ll an = nxt(a), ap = prv(a);
        ll bn = nxt(b), bp = prv(b);

        int dan = ask(an, b);
        int dap = ask(ap, b);
        if (1 + dan == d) dirA.push_back(+1);
        if (1 + dap == d) dirA.push_back(-1);

        int dbn = ask(bn, a);
        int dbp = ask(bp, a);
        if (1 + dbn == d) dirB.push_back(+1);
        if (1 + dbp == d) dirB.push_back(-1);

        vector<ll> candA, candB;

        for (int dir : dirA) candA.push_back(lastOnShortestFrom(a, b, d, dir));
        for (int dir : dirB) candB.push_back(lastOnShortestFrom(b, a, d, dir));

        auto checkChord = [&](ll u, ll v) -> bool {
            if (u == v) return false;
            if (adjacentCycle(u, v)) return false;
            return ask(u, v) == 1;
        };

        if (dirA.empty() && !candB.empty()) {
            for (ll v : candB) if (checkChord(a, v)) return pair<ll,ll>{a, v};
        }
        if (dirB.empty() && !candA.empty()) {
            for (ll u : candA) if (checkChord(b, u)) return pair<ll,ll>{b, u};
        }

        for (ll u : candA) {
            for (ll v : candB) {
                if (checkChord(u, v)) return pair<ll,ll>{u, v};
            }
        }

        // Extra safety: check among all collected nodes
        vector<ll> all;
        all.reserve(8);
        all.push_back(a);
        all.push_back(b);
        for (ll x : candA) all.push_back(x);
        for (ll x : candB) all.push_back(x);
        sort(all.begin(), all.end());
        all.erase(unique(all.begin(), all.end()), all.end());
        for (int i = 0; i < (int)all.size(); i++) {
            for (int j = i + 1; j < (int)all.size(); j++) {
                if (checkChord(all[i], all[j])) return pair<ll,ll>{all[i], all[j]};
            }
        }

        return nullopt;
    }

    bool tryPair(ll x, ll y) {
        int d = ask(x, y);
        if (d == 1 && !adjacentCycle(x, y)) {
            answer(x, y);
            return true;
        }
        int cd = cycleDist(x, y);
        if (d < cd) {
            auto res = solveFromPair(x, y, d);
            if (res) {
                answer(res->first, res->second);
                return true;
            }
        }
        return false;
    }

    void solveOne(ll N) {
        n = N;
        qcnt = 0;
        cache.clear();

        if (n == 4) {
            int d13 = ask(1, 3);
            if (d13 == 1) answer(1, 3);
            else answer(2, 4);
            return;
        }

        // Keep some budget for the full solve-from-pair phase.
        const int SEARCH_LIMIT = 240;

        // Deterministic seeds: evenly spaced
        vector<ll> seeds;
        int m = 20;
        seeds.reserve(m);
        for (int i = 0; i < m; i++) {
            ll pos = 1 + (n * (ll)i) / m;
            if (pos < 1) pos = 1;
            if (pos > n) pos = n;
            seeds.push_back(pos);
        }
        sort(seeds.begin(), seeds.end());
        seeds.erase(unique(seeds.begin(), seeds.end()), seeds.end());

        // Try all pairs among seeds (bounded)
        for (int i = 0; i < (int)seeds.size() && qcnt <= SEARCH_LIMIT; i++) {
            for (int j = i + 1; j < (int)seeds.size() && qcnt <= SEARCH_LIMIT; j++) {
                if (tryPair(seeds[i], seeds[j])) return;
            }
        }

        // Random search with biased offsets
        int iters = 0;
        while (qcnt <= SEARCH_LIMIT && iters < 500) {
            iters++;
            ll x = (ll)(rng() % (unsigned long long)n) + 1;
            ll y;
            int mode = iters % 3;
            if (mode == 0) {
                ll k = n / 2;
                if (k == 0) k = 1;
                y = step(x, k, +1);
            } else if (mode == 1) {
                ll k = n / 3;
                if (k == 0) k = 1;
                y = step(x, k, +1);
            } else {
                y = (ll)(rng() % (unsigned long long)n) + 1;
                if (y == x) y = nxt(x);
            }
            if (x == y) continue;
            if (tryPair(x, y)) return;
        }

        // Last resort: try a few more random pairs (shouldn't happen)
        while (qcnt < QUERY_LIMIT - 5) {
            ll x = (ll)(rng() % (unsigned long long)n) + 1;
            ll y = (ll)(rng() % (unsigned long long)n) + 1;
            if (x == y) continue;
            if (tryPair(x, y)) return;
        }

        exit(0);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    Solver solver;
    while (T--) {
        ll n;
        cin >> n;
        solver.solveOne(n);
    }
    return 0;
}