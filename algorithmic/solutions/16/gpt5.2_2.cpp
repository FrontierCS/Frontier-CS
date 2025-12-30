#include <bits/stdc++.h>
using namespace std;

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed = 0) : x(seed) {}
    static uint64_t splitmix64(uint64_t &x) {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint64_t next() { return splitmix64(x); }
};

struct Solver {
    long long n = 0;
    int q = 0;
    SplitMix64 rng;

    Solver() : rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count()) {}

    static long long cycleDist(long long n, long long a, long long b) {
        long long d = llabs(a - b);
        return min(d, n - d);
    }

    long long nxt(long long x, int dir, long long t) {
        long long r = (x - 1) + (dir == 1 ? t : -t);
        r %= n;
        if (r < 0) r += n;
        return r + 1;
    }

    long long ask(long long x, long long y) {
        cout << "? " << x << " " << y << "\n" << flush;
        long long d;
        if (!(cin >> d)) exit(0);
        q++;
        if (q > 500) exit(0);
        return d;
    }

    void answer(long long u, long long v) {
        cout << "! " << u << " " << v << "\n" << flush;
        int r;
        if (!(cin >> r)) exit(0);
        if (r == -1) exit(0);
    }

    long long randVertex() {
        return (long long)(rng.next() % (uint64_t)n) + 1;
    }

    struct ReducedPair {
        long long a = -1, b = -1, D = -1;
        bool ok() const { return a != -1; }
    };

    ReducedPair findReducedPairStructured() {
        vector<long long> S;
        int m = 24;
        S.reserve(m + 5);
        for (int i = 0; i < m; i++) {
            long long pos = 1 + (long long)((__int128)i * n / m);
            S.push_back(pos);
        }
        S.push_back(1);
        S.push_back(n);
        sort(S.begin(), S.end());
        S.erase(unique(S.begin(), S.end()), S.end());
        int sz = (int)S.size();
        vector<pair<long long,long long>> pairs;
        pairs.reserve(sz + sz/2 + 5);

        for (int i = 0; i < sz; i++) {
            pairs.push_back({S[i], S[(i + 1) % sz]});
        }
        for (int i = 0; i < sz/2; i++) {
            pairs.push_back({S[i], S[i + sz/2]});
        }

        for (auto [x,y] : pairs) {
            if (x == y) continue;
            long long D = ask(x, y);
            long long cd = cycleDist(n, x, y);
            if (D == 1 && cd > 1) return {x, y, D};
            if (D < cd) return {x, y, D};
        }
        return {};
    }

    ReducedPair findReducedPairRandom(int maxQueriesForFinding) {
        while (q < maxQueriesForFinding) {
            long long x = randVertex();
            long long y = randVertex();
            if (x == y) continue;
            long long D = ask(x, y);
            long long cd = cycleDist(n, x, y);
            if (D == 1 && cd > 1) return {x, y, D};
            if (D < cd) return {x, y, D};
        }
        return {};
    }

    long long endpointFromDir(long long start, long long target, long long D, int dir) {
        long long lo = 0, hi = D;
        while (lo < hi) {
            long long mid = (lo + hi + 1) / 2;
            long long x = nxt(start, dir, mid);
            long long dx = ask(x, target);
            if (dx == D - mid) lo = mid;
            else hi = mid - 1;
        }
        return nxt(start, dir, lo);
    }

    vector<long long> endpointCandidates(long long start, long long target, long long D) {
        vector<long long> res;
        long long cw = nxt(start, +1, 1);
        long long ccw = nxt(start, -1, 1);

        bool ok_cw = false, ok_ccw = false;
        if (D >= 1) {
            long long d1 = ask(cw, target);
            long long d2 = ask(ccw, target);
            ok_cw = (d1 == D - 1);
            ok_ccw = (d2 == D - 1);
        }

        if (!ok_cw && !ok_ccw) {
            res.push_back(start);
            return res;
        }
        if (ok_cw) res.push_back(endpointFromDir(start, target, D, +1));
        if (ok_ccw) res.push_back(endpointFromDir(start, target, D, -1));

        sort(res.begin(), res.end());
        res.erase(unique(res.begin(), res.end()), res.end());
        return res;
    }

    pair<long long,long long> chordFromReduced(long long a, long long b, long long D) {
        long long cd = cycleDist(n, a, b);
        if (D == 1 && cd > 1) return {a, b};

        auto candA = endpointCandidates(a, b, D);
        auto candB = endpointCandidates(b, a, D);

        for (long long u : candA) {
            for (long long v : candB) {
                if (u == v) continue;
                long long duv = ask(u, v);
                if (duv == 1 && cycleDist(n, u, v) > 1) return {u, v};
            }
        }
        return {-1, -1};
    }

    pair<long long,long long> solveSmall() {
        for (long long i = 1; i <= n; i++) {
            for (long long j = i + 1; j <= n; j++) {
                long long D = ask(i, j);
                if (D == 1 && cycleDist(n, i, j) > 1) return {i, j};
            }
        }
        return {-1, -1};
    }

    pair<long long,long long> solveOne(long long n_) {
        n = n_;
        q = 0;

        if (n <= 31) return solveSmall();

        // Budgeting
        const int reserveForSolve = 150;           // binary searches + verification
        const int maxFindQueries = 500 - reserveForSolve;

        // Try structured first
        ReducedPair rp = findReducedPairStructured();
        if (!rp.ok()) rp = findReducedPairRandom(maxFindQueries);

        // If still not found (unlikely), spend more remaining budget.
        if (!rp.ok()) rp = findReducedPairRandom(500 - 50);

        // As a last resort, just keep sampling until a reduced pair found or near limit.
        while (!rp.ok() && q < 500 - 10) {
            rp = findReducedPairRandom(500 - 10);
            if (rp.ok()) break;
        }

        if (!rp.ok()) return {-1, -1};

        // Try to compute chord endpoints; if something goes wrong, re-sample a few times.
        for (int tries = 0; tries < 3; tries++) {
            auto ans = chordFromReduced(rp.a, rp.b, rp.D);
            if (ans.first != -1) return ans;
            if (q >= maxFindQueries) break;
            rp = findReducedPairRandom(maxFindQueries);
            if (!rp.ok()) break;
        }

        return {-1, -1};
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
        auto [u, v] = solver.solveOne(n);
        if (u == -1) {
            // Should not happen; output something to avoid hanging.
            u = 1; v = 3;
        }
        solver.answer(u, v);
    }
    return 0;
}