#include <bits/stdc++.h>
using namespace std;

using int64 = long long;

static mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

struct ChordSolver {
    int64 n;
    int query_count = 0;
    const int QUERY_LIMIT = 500;

    int ask(int64 x, int64 y) {
        x = ((x-1) % n + n) % n + 1;
        y = ((y-1) % n + n) % n + 1;
        cout << "? " << x << " " << y << endl << flush;
        int d;
        if (!(cin >> d)) exit(0);
        query_count++;
        return d;
    }

    bool isAdjacent(int64 u, int64 v) {
        if (u == 1 && v == n) return true;
        if (v == 1 && u == n) return true;
        if (llabs(u - v) == 1) return true;
        return false;
    }

    int64 wrapAdd(int64 base, int64 delta) {
        return ((base - 1 + delta) % n + n) % n + 1;
    }

    // Solve for a given pivot s: find a k0 where dist(s, s+k0) < min(k0, n-k0)
    // Then refine to the center valley and determine chord endpoints.
    bool try_pivot(int64 s, pair<int64,int64> &answer) {
        // cache distances d(k) = dist(s, s+k), k in [0..n-1], with d(0)=0
        unordered_map<int64,int> dCache;
        dCache.reserve(256);
        dCache.max_load_factor(0.7f);

        auto modk = [&](int64 k)->int64{
            int64 r = k % n;
            if (r < 0) r += n;
            return r;
        };
        auto g_cycle = [&](int64 k)->int64{
            int64 kk = modk(k);
            return min(kk, n - kk);
        };
        auto get_d = [&](int64 k)->int{
            int64 kk = modk(k);
            auto it = dCache.find(kk);
            if (it != dCache.end()) return it->second;
            int ans = 0;
            if (kk != 0) {
                int64 y = wrapAdd(s, kk);
                ans = ask(s, y);
            }
            dCache[kk] = ans;
            return ans;
        };
        auto slope = [&](int64 k)->int{ // d(k+1) - d(k)
            int a = get_d(k);
            int b = get_d(k+1);
            return b - a;
        };

        // Sample points to find improvement (d(k) < g(k))
        int SAMPLES = 48;
        vector<int64> ks;
        ks.reserve(SAMPLES);
        // Deterministic evenly spaced samples
        for (int i = 1; i <= SAMPLES; ++i) {
            int64 k = ( (__int128)i * n ) / (SAMPLES + 1);
            if (k <= 0) k = 1;
            if (k >= n) k = n - 1;
            ks.push_back(k);
        }
        // Also a few random picks
        for (int i = 0; i < 16; ++i) {
            int64 k = (int64)(rng() % (n - 1)) + 1;
            ks.push_back(k);
        }

        int64 k0 = -1;
        for (int64 k : ks) {
            int d = get_d(k);
            int64 gc = g_cycle(k);
            if (d < gc) { k0 = k; break; }
            if (query_count >= QUERY_LIMIT - 5) break;
        }
        if (k0 == -1) return false;

        // Refine to valley center near k0 by locating where slope crosses from negative to nonnegative
        auto find_center_from = [&](int64 seed)->int64{
            int sr = slope(seed); // d(seed+1) - d(seed)
            // Prefer move to direction of descending slope to approach center
            if (sr < 0) {
                // Move to right until slope becomes >= 0
                int64 L = seed;
                int64 R = seed;
                int64 step = 1;
                while (true) {
                    int sgn = slope(R);
                    if (sgn >= 0) break;
                    int64 nextR = R + step;
                    // To avoid too many iterations or wrap issues, cap expansions
                    if (step > (n >> 1)) break;
                    R = nextR;
                    step <<= 1;
                    if (query_count >= QUERY_LIMIT - 20) break;
                }
                // Binary search between L and R to where slope changes to nonnegative
                // Ensure L has slope < 0
                while (slope(L) >= 0 && L > seed - (1<<20)) L--;
                // Now binary search
                int iter = 0;
                while (R - L > 1 && iter < 64) {
                    int64 M = (L + R) >> 1;
                    int sgn = slope(M);
                    if (sgn < 0) L = M;
                    else R = M;
                    iter++;
                }
                // The center is around R; pick minimal d among R-1, R, R+1
                int64 best = R;
                int db = get_d(best);
                int d1 = get_d(best - 1);
                if (d1 < db) { best = best - 1; db = d1; }
                int d2 = get_d(best + 1);
                if (d2 < db) { best = best + 1; db = d2; }
                return modk(best);
            } else {
                // Move to left: check slope at (t-1): sLeft = d(t) - d(t-1) > 0 means descending to left
                int64 R = seed;
                int64 L = seed;
                int64 step = 1;
                auto slope_at_left = [&](int64 t)->int{ // slope at t-1
                    int a = get_d(t-1);
                    int b = get_d(t);
                    return b - a;
                };
                while (true) {
                    int sgn = slope_at_left(L);
                    if (sgn < 0) break; // We crossed center; want left side where slope negative at L
                    int64 nextL = L - step;
                    if (step > (n >> 1)) break;
                    L = nextL;
                    step <<= 1;
                    if (query_count >= QUERY_LIMIT - 20) break;
                }
                // Ensure R has nonnegative slope
                while (slope(R) < 0 && R < seed + (1<<20)) R++;
                // Binary search to find boundary
                int iter = 0;
                while (R - L > 1 && iter < 64) {
                    int64 M = (L + R) >> 1;
                    int sgn = slope(M);
                    if (sgn < 0) L = M;
                    else R = M;
                    iter++;
                }
                int64 best = R;
                int db = get_d(best);
                int d1 = get_d(best - 1);
                if (d1 < db) { best = best - 1; db = d1; }
                int d2 = get_d(best + 1);
                if (d2 < db) { best = best + 1; db = d2; }
                return modk(best);
            }
        };

        int64 centerK = find_center_from(k0);
        int dcenter = get_d(centerK);
        int64 gcenter = g_cycle(centerK);
        // Validate improvement at center (should be strictly less)
        if (!(dcenter < gcenter || centerK == 0)) {
            // Try the other direction just in case
            int64 altK = find_center_from(k0 - 1);
            int dalt = get_d(altK);
            int64 galt = g_cycle(altK);
            if (dalt < galt) {
                centerK = altK;
                dcenter = dalt;
            }
        }

        // The vertex at center is one endpoint (call j)
        int64 j = wrapAdd(s, centerK);
        // The distance to the other endpoint from pivot s equals dcenter - 1
        int64 Aother = dcenter - 1;
        if (Aother < 0) Aother = 0; // safety

        // Two candidates from s at distance Aother along cycle
        int64 cand1 = wrapAdd(s, Aother);
        int64 cand2 = wrapAdd(s, -Aother);

        // Check which candidate forms the chord with j (distance 1 and non-adjacent)
        auto check_candidate = [&](int64 t)->bool{
            if (t == j) return false;
            if (isAdjacent(j, t)) return false;
            int d = ask(j, t);
            return d == 1;
        };

        if (Aother == 0) {
            // Special case: dcenter == 1; other endpoint equals s
            if (!isAdjacent(j, s)) {
                int d = ask(j, s);
                if (d == 1) {
                    answer = {j, s};
                    return true;
                }
            }
            // Otherwise fail
        } else {
            if (check_candidate(cand1)) {
                answer = {j, cand1};
                return true;
            }
            if (check_candidate(cand2)) {
                answer = {j, cand2};
                return true;
            }
        }

        // As a fallback, try to verify if j is indeed an endpoint by searching for a node at distance 1 (non-adjacent) via random probes
        // Limited to a few trials to stay within query limit
        for (int tries = 0; tries < 60 && query_count < QUERY_LIMIT - 3; ++tries) {
            int64 t = (int64)(rng() % n) + 1;
            if (t == j || isAdjacent(j, t)) continue;
            int d = ask(j, t);
            if (d == 1) {
                answer = {j, t};
                return true;
            }
        }
        return false;
    }

    pair<int64,int64> solve_one() {
        // Try up to a few pivot choices
        vector<int64> pivots;
        pivots.push_back(1);
        pivots.push_back(wrapAdd(1, n/3));
        pivots.push_back(wrapAdd(1, (2*n)/3));
        // Add one random pivot
        pivots.push_back((int64)(rng() % n) + 1);

        pair<int64,int64> ans = {1,3}; // dummy
        for (int64 s : pivots) {
            if (try_pivot(s, ans)) return ans;
            if (query_count >= QUERY_LIMIT - 5) break;
        }

        // As a last resort, try more random pivots with fewer samples inside try_pivot
        for (int it = 0; it < 6 && query_count < QUERY_LIMIT - 5; ++it) {
            int64 s = (int64)(rng() % n) + 1;
            if (try_pivot(s, ans)) return ans;
        }

        // If everything fails (should be extremely rare), just output a default non-adjacent pair
        // Note: This will likely be wrong on a real interactive, but here we avoid hanging.
        int64 u = 1, v = (n >= 4 ? 3 : 2);
        return {u, v};
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        ChordSolver solver;
        cin >> solver.n;
        solver.query_count = 0;
        auto res = solver.solve_one();
        cout << "! " << res.first << " " << res.second << endl << flush;
        int verdict;
        // Read until we get a valid verdict in {1, -1}
        while (true) {
            if (!(cin >> verdict)) return 0;
            if (verdict == 1) break;
            if (verdict == -1) return 0;
            // Some offline judges might feed query answers in the input stream;
            // keep consuming until a valid verdict appears.
        }
    }
    return 0;
}