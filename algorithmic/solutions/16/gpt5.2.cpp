#include <bits/stdc++.h>
using namespace std;

struct Solver {
    long long n;
    int q = 0;
    mt19937_64 rng;

    Solver(long long n_, uint64_t seed) : n(n_), rng(seed) {}

    static long long cycDist(long long n, long long a, long long b) {
        long long d = llabs(a - b);
        return min(d, n - d);
    }

    long long move(long long x, int dir, long long steps) const {
        long long s = steps % n;
        long long z = x - 1;
        if (dir == 1) z = (z + s) % n;
        else z = (z - s + n) % n;
        return z + 1;
    }

    long long ask(long long x, long long y) {
        ++q;
        if (q > 500) exit(0);
        cout << "? " << x << " " << y << endl;
        cout.flush();
        long long d;
        if (!(cin >> d)) exit(0);
        return d;
    }

    void answer(long long u, long long v) {
        cout << "! " << u << " " << v << endl;
        cout.flush();
        int r;
        if (!(cin >> r)) exit(0);
        if (r == -1) exit(0);
    }

    vector<long long> candidatesFrom(long long s, long long t, long long dst) {
        vector<long long> cand;
        long long s1 = move(s, +1, 1);
        long long s2 = move(s, -1, 1);
        long long d1 = ask(s1, t);
        long long d2 = ask(s2, t);

        vector<int> dirs;
        if (d1 == dst - 1) dirs.push_back(+1);
        if (d2 == dst - 1) dirs.push_back(-1);

        if (dirs.empty()) {
            cand.push_back(s);
            return cand;
        }

        for (int dir : dirs) {
            long long lo = 0, hi = dst;
            while (lo < hi) {
                long long mid = (lo + hi + 1) >> 1;
                long long x = move(s, dir, mid);
                long long dm = ask(x, t);
                if (dm == dst - mid) lo = mid;
                else hi = mid - 1;
            }
            cand.push_back(move(s, dir, lo));
        }

        sort(cand.begin(), cand.end());
        cand.erase(unique(cand.begin(), cand.end()), cand.end());
        return cand;
    }

    bool isAdjacent(long long a, long long b) const {
        return cycDist(n, a, b) == 1;
    }

    optional<tuple<long long,long long,long long>> tryPair(long long a, long long b) {
        if (a == b) return nullopt;
        long long cd = cycDist(n, a, b);
        if (cd <= 1) return nullopt;
        long long d = ask(a, b);
        if (d < cd) return tuple<long long,long long,long long>(a, b, d);
        return nullopt;
    }

    optional<tuple<long long,long long,long long>> findAffectedPair() {
        auto norm = [&](long long x) -> long long {
            x %= n;
            if (x <= 0) x += n;
            return x;
        };

        vector<long long> piv;
        piv.push_back(1);
        piv.push_back(norm(1 + n / 2));
        piv.push_back(norm(1 + n / 3));
        piv.push_back(norm(1 + (2 * n) / 3));
        piv.push_back(norm(1 + n / 4));
        piv.push_back(norm(1 + (3 * n) / 4));
        sort(piv.begin(), piv.end());
        piv.erase(unique(piv.begin(), piv.end()), piv.end());

        for (int i = 0; i < (int)piv.size(); i++) {
            for (int j = i + 1; j < (int)piv.size(); j++) {
                auto got = tryPair(piv[i], piv[j]);
                if (got) return got;
            }
        }

        auto randVertex = [&]() -> long long {
            uniform_int_distribution<long long> dist(1, n);
            return dist(rng);
        };

        // Biased random pairs with large cyclic distances.
        for (int it = 0; it < 160; it++) {
            long long a = randVertex();
            long long offL = max(2LL, n / 3);
            long long offR = max(offL, (2 * n) / 3);
            uniform_int_distribution<long long> distOff(offL, offR);
            long long off = distOff(rng);
            long long b = move(a, +1, off);
            auto got = tryPair(a, b);
            if (got) return got;
        }

        // Structured sampling: random set, test against few anchors.
        vector<long long> anchors = piv;
        while ((int)anchors.size() < 10) anchors.push_back(randVertex());
        anchors.resize(10);

        for (int it = 0; it < 140; it++) {
            long long a = randVertex();
            for (int k = 0; k < (int)anchors.size(); k++) {
                auto got = tryPair(a, anchors[k]);
                if (got) return got;
            }
        }

        // Pure random pairs.
        for (int it = 0; it < 200; it++) {
            long long a = randVertex();
            long long b = randVertex();
            if (a == b) continue;
            auto got = tryPair(a, b);
            if (got) return got;
        }

        return nullopt;
    }

    pair<long long,long long> extractChord(long long a, long long b, long long d_ab) {
        long long cd = cycDist(n, a, b);
        if (d_ab == 1 && cd > 1) return {a, b};

        vector<long long> cU = candidatesFrom(a, b, d_ab);
        vector<long long> cV = candidatesFrom(b, a, d_ab);

        auto checkCandidates = [&](const vector<long long>& U, const vector<long long>& V) -> optional<pair<long long,long long>> {
            for (long long u : U) for (long long v : V) {
                if (u == v) continue;
                if (isAdjacent(u, v)) continue;
                long long d = ask(u, v);
                if (d == 1) return pair<long long,long long>(u, v);
            }
            return nullopt;
        };

        if (auto ok = checkCandidates(cU, cV)) return *ok;

        // Fallback: local neighborhood around candidates.
        vector<long long> aroundU, aroundV;
        for (long long u : cU) {
            for (int delta = -4; delta <= 4; delta++) {
                long long p = move(u, +1, (delta % (int)n + (int)n) % (int)n);
                aroundU.push_back(p);
            }
        }
        for (long long v : cV) {
            for (int delta = -4; delta <= 4; delta++) {
                long long p = move(v, +1, (delta % (int)n + (int)n) % (int)n);
                aroundV.push_back(p);
            }
        }
        sort(aroundU.begin(), aroundU.end());
        aroundU.erase(unique(aroundU.begin(), aroundU.end()), aroundU.end());
        sort(aroundV.begin(), aroundV.end());
        aroundV.erase(unique(aroundV.begin(), aroundV.end()), aroundV.end());

        if (auto ok = checkCandidates(aroundU, aroundV)) return *ok;

        // Last resort: search for distance-1 non-adjacent from some promising node.
        vector<long long> seeds = cU;
        seeds.insert(seeds.end(), cV.begin(), cV.end());
        sort(seeds.begin(), seeds.end());
        seeds.erase(unique(seeds.begin(), seeds.end()), seeds.end());
        if (seeds.empty()) seeds.push_back(a);

        uniform_int_distribution<long long> distV(1, n);
        for (int it = 0; it < 120; it++) {
            long long u = seeds[it % (int)seeds.size()];
            long long x = distV(rng);
            if (x == u) continue;
            if (isAdjacent(u, x)) continue;
            long long d = ask(u, x);
            if (d == 1) return {u, x};
        }

        // Should not happen; return something.
        return {1, 3 <= n ? 3 : 2};
    }

    void solveOne() {
        auto got = findAffectedPair();
        if (!got) {
            // Very unlikely; attempt a couple more pairs.
            for (int it = 0; it < 50 && !got; it++) {
                uniform_int_distribution<long long> distV(1, n);
                long long a = distV(rng), b = distV(rng);
                if (a == b) continue;
                long long cd = cycDist(n, a, b);
                if (cd <= 1) continue;
                long long d = ask(a, b);
                if (d < cd) got = tuple<long long,long long,long long>(a, b, d);
            }
        }

        long long a, b, d;
        if (got) {
            tie(a, b, d) = *got;
        } else {
            // As a last fallback, try fixed pair set.
            a = 1;
            b = (n >= 3 ? 3 : 2);
            d = ask(a, b);
        }

        auto [u, v] = extractChord(a, b, d);
        answer(u, v);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    for (int tc = 0; tc < T; tc++) {
        long long n;
        cin >> n;
        Solver solver(n, seed ^ (uint64_t)tc * 0x9e3779b97f4a7c15ULL);
        solver.solveOne();
    }
    return 0;
}