#include <bits/stdc++.h>
using namespace std;

struct Solver {
    long long n = 0;
    int queries = 0;
    unordered_map<long long, int> cache;

    long long key(long long a, long long b) const {
        if (a > b) swap(a, b);
        return (a << 32) ^ b;
    }

    long long nxt(long long x) const { return (x == n) ? 1 : x + 1; }
    long long prv(long long x) const { return (x == 1) ? n : x - 1; }

    long long move_dir(long long x, int dir, long long k) const {
        if (k == 0) return x;
        long long kk = k % n;
        long long base = x - 1;
        if (dir == 1) {
            return (base + kk) % n + 1;
        } else {
            return (base - kk + n) % n + 1;
        }
    }

    long long cycleDist(long long a, long long b) const {
        long long d = llabs(a - b);
        return min(d, n - d);
    }

    int ask(long long x, long long y) {
        if (x == y) return 0;
        long long k = key(x, y);
        auto it = cache.find(k);
        if (it != cache.end()) return it->second;

        cout << "? " << x << " " << y << endl;
        cout.flush();

        int d;
        if (!(cin >> d)) exit(0);
        queries++;
        cache.emplace(k, d);
        return d;
    }

    long long binary_search_endpoint(long long p, long long q, int D, int dir) {
        long long lo = 0, hi = D, ans = 0;
        while (lo <= hi) {
            long long mid = (lo + hi) >> 1;
            long long x = move_dir(p, dir, mid);
            int dpx = ask(p, x);
            bool ok = false;
            if (dpx == (int)mid) {
                int dxq = ask(x, q);
                ok = (dpx + dxq == D);
            }
            if (ok) {
                ans = mid;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }
        return move_dir(p, dir, ans);
    }

    vector<long long> endpoints_from_side(long long p, long long q, int D) {
        vector<pair<int,int>> dirs; // (dir, neighbor)
        long long p_cw = nxt(p);
        long long p_ccw = prv(p);

        if (ask(p_cw, q) == D - 1) dirs.push_back({1, (int)p_cw});
        if (ask(p_ccw, q) == D - 1) dirs.push_back({-1, (int)p_ccw});

        vector<long long> res;
        if (dirs.empty()) {
            res.push_back(p);
        } else {
            for (auto [dir, nb] : dirs) {
                (void)nb;
                long long e = binary_search_endpoint(p, q, D, dir);
                res.push_back(e);
            }
        }
        sort(res.begin(), res.end());
        res.erase(unique(res.begin(), res.end()), res.end());
        return res;
    }

    optional<pair<long long,long long>> solve_with_pair(long long p, long long q) {
        int D = ask(p, q);
        auto A = endpoints_from_side(p, q, D);
        auto B = endpoints_from_side(q, p, D);

        vector<long long> cand = A;
        cand.insert(cand.end(), B.begin(), B.end());
        sort(cand.begin(), cand.end());
        cand.erase(unique(cand.begin(), cand.end()), cand.end());

        for (int i = 0; i < (int)cand.size(); i++) {
            for (int j = i + 1; j < (int)cand.size(); j++) {
                long long u = cand[i], v = cand[j];
                if (cycleDist(u, v) <= 1) continue;
                if (ask(u, v) == 1) return make_pair(u, v);
            }
        }
        return nullopt;
    }

    void answer(long long u, long long v) {
        cout << "! " << u << " " << v << endl;
        cout.flush();
        int r;
        if (!(cin >> r)) exit(0);
        if (r == -1) exit(0);
    }

    void solve_case(long long nn) {
        n = nn;
        queries = 0;
        cache.clear();
        cache.reserve(2048);

        if (n <= 32) {
            for (long long u = 1; u <= n; u++) {
                for (long long v = u + 1; v <= n; v++) {
                    if (cycleDist(u, v) <= 1) continue;
                    if (ask(u, v) == 1) {
                        answer(u, v);
                        return;
                    }
                }
            }
            // Should never happen
            answer(1, 3);
            return;
        }

        const int m = 20;
        vector<long long> s(m);
        for (int i = 0; i < m; i++) {
            s[i] = (long long)i * n / m + 1;
        }

        struct PairInfo {
            long long a, b;
            int delta;
        };
        vector<PairInfo> reduced;

        for (int i = 0; i < m; i++) {
            for (int j = i + 1; j < m; j++) {
                int d = ask(s[i], s[j]);
                long long expd = cycleDist(s[i], s[j]);
                if (d < expd) reduced.push_back({s[i], s[j], (int)(expd - d)});
            }
        }

        if (reduced.empty()) {
            // Extremely unlikely; fallback: try a few deterministic pairs
            vector<pair<long long,long long>> tries = {
                {1, (n/2)+1},
                {1, (n/3)+1},
                {(n/3)+1, (2*n/3)+1}
            };
            for (auto [p,q]: tries) {
                int d = ask(p,q);
                if (d < (int)cycleDist(p,q)) reduced.push_back({p,q,(int)(cycleDist(p,q)-d)});
            }
        }

        sort(reduced.begin(), reduced.end(), [](const PairInfo& x, const PairInfo& y){
            return x.delta > y.delta;
        });

        for (int t = 0; t < (int)reduced.size() && t < 2; t++) {
            auto res = solve_with_pair(reduced[t].a, reduced[t].b);
            if (res) {
                answer(res->first, res->second);
                return;
            }
        }

        // Last resort: try first reduced pair (if any), otherwise arbitrary (shouldn't happen)
        if (!reduced.empty()) {
            auto res = solve_with_pair(reduced[0].a, reduced[0].b);
            if (res) {
                answer(res->first, res->second);
                return;
            }
        }
        answer(1, 3);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    Solver solver;
    while (T--) {
        long long n;
        cin >> n;
        solver.solve_case(n);
    }
    return 0;
}