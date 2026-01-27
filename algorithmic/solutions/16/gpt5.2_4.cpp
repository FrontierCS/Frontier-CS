#include <bits/stdc++.h>
using namespace std;

struct InteractiveSolver {
    long long n;
    int qcnt = 0;
    unordered_map<uint64_t, long long> cache;

    InteractiveSolver(long long n_) : n(n_) {
        cache.reserve(2048);
        cache.max_load_factor(0.7f);
    }

    static uint64_t keyPair(uint32_t a, uint32_t b) {
        if (a > b) swap(a, b);
        return (uint64_t(a) << 32) | uint64_t(b);
    }

    long long cycDist(long long a, long long b) const {
        long long diff = llabs(a - b);
        return min(diff, n - diff);
    }

    long long nxt(long long v) const { return (v == n) ? 1 : (v + 1); }
    long long prv(long long v) const { return (v == 1) ? n : (v - 1); }

    long long step(long long v, long long t, int dir) const {
        t %= n;
        long long pos = v - 1;
        if (dir == 1) pos = (pos + t) % n;
        else {
            pos = (pos - t) % n;
            if (pos < 0) pos += n;
        }
        return pos + 1;
    }

    long long ask(long long x, long long y) {
        if (x == y) return 0;
        uint32_t a = (uint32_t)x, b = (uint32_t)y;
        uint64_t k = keyPair(a, b);
        auto it = cache.find(k);
        if (it != cache.end()) return it->second;

        if (qcnt >= 500) exit(0);
        cout << "? " << x << " " << y << "\n";
        cout.flush();

        long long ans;
        if (!(cin >> ans)) exit(0);
        qcnt++;
        cache.emplace(k, ans);
        return ans;
    }

    long long endpointInDir(long long s, long long t, long long d, int dir) {
        long long lo = 0, hi = d;
        while (lo < hi) {
            long long mid = (lo + hi + 1) >> 1;
            long long x = step(s, mid, dir);
            long long dx = ask(x, t);
            if (dx == d - mid) lo = mid;
            else hi = mid - 1;
        }
        return step(s, lo, dir);
    }

    vector<long long> endpointsFromOneSide(long long s, long long t, long long d) {
        vector<int> dirs;
        long long cw = nxt(s);
        long long ccw = prv(s);

        long long dcw = ask(cw, t);
        long long dccw = ask(ccw, t);
        if (dcw == d - 1) dirs.push_back(1);
        if (dccw == d - 1) dirs.push_back(-1);

        vector<long long> res;
        if (dirs.empty()) {
            res.push_back(s);
        } else {
            for (int dir : dirs) {
                long long e = endpointInDir(s, t, d, dir);
                res.push_back(e);
            }
            sort(res.begin(), res.end());
            res.erase(unique(res.begin(), res.end()), res.end());
        }
        return res;
    }

    optional<pair<long long, long long>> attemptFromPair(long long S, long long T, long long d) {
        if (d == 1) {
            if (cycDist(S, T) > 1) return make_pair(S, T);
            return nullopt;
        }

        auto Ulist = endpointsFromOneSide(S, T, d);
        auto Vlist = endpointsFromOneSide(T, S, d);

        for (long long u : Ulist) {
            for (long long v : Vlist) {
                if (cycDist(u, v) <= 1) continue;
                if (ask(u, v) == 1) return make_pair(u, v);
            }
        }
        return nullopt;
    }

    pair<long long, long long> solve() {
        int m = (int)min<long long>(27, n);
        vector<long long> p(m);
        if (n <= 27) {
            for (int i = 0; i < m; i++) p[i] = i + 1;
        } else {
            for (int i = 0; i < m; i++) p[i] = 1 + (long long)i * n / m;
        }

        vector<vector<long long>> D(m, vector<long long>(m, 0));
        struct Cand { long long sav; int i, j; };
        vector<Cand> cands;
        cands.reserve(m * (m - 1) / 2);

        for (int i = 0; i < m; i++) {
            for (int j = i + 1; j < m; j++) {
                long long dij = ask(p[i], p[j]);
                D[i][j] = D[j][i] = dij;
                long long dc = cycDist(p[i], p[j]);
                long long sav = dc - dij;
                if (sav > 0) cands.push_back({sav, i, j});
            }
        }

        sort(cands.begin(), cands.end(), [](const Cand& a, const Cand& b) {
            if (a.sav != b.sav) return a.sav > b.sav;
            if (a.i != b.i) return a.i < b.i;
            return a.j < b.j;
        });

        int tries = 0;
        for (auto &c : cands) {
            if (tries >= 2) break;
            long long S = p[c.i], T = p[c.j], d = D[c.i][c.j];
            auto ans = attemptFromPair(S, T, d);
            if (ans) return *ans;
            tries++;
        }

        // Fallback: check some opposite pairs (deterministic).
        for (int k = 0; k < 16; k++) {
            long long x = 1 + (long long)k * n / 16;
            long long y = 1 + (long long)((k + 8) % 16) * n / 16;
            if (x == y) continue;
            long long d = ask(x, y);
            long long dc = cycDist(x, y);
            if (d < dc) {
                auto ans = attemptFromPair(x, y, d);
                if (ans) return *ans;
            }
        }

        // Last resort: deterministic pseudo-random search for an affected pair.
        uint64_t seed = 123456789;
        for (int it = 0; it < 60; it++) {
            seed = seed * 1103515245ULL + 12345ULL;
            long long x = (long long)(seed % (uint64_t)n) + 1;
            seed = seed * 1103515245ULL + 12345ULL;
            long long y = (long long)(seed % (uint64_t)n) + 1;
            if (x == y) continue;
            long long d = ask(x, y);
            long long dc = cycDist(x, y);
            if (d < dc) {
                auto ans = attemptFromPair(x, y, d);
                if (ans) return *ans;
            }
        }

        // Should never happen.
        return {1, 3};
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        long long n;
        cin >> n;

        InteractiveSolver solver(n);
        auto [u, v] = solver.solve();

        cout << "! " << u << " " << v << "\n";
        cout.flush();

        int r;
        if (!(cin >> r)) return 0;
        if (r == -1) return 0;
    }
    return 0;
}