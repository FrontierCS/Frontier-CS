#include <bits/stdc++.h>
using namespace std;

using ll = long long;
using i128 = __int128_t;
using u128 = __uint128_t;

struct RNG {
    mt19937_64 rng;
    uniform_real_distribution<long double> dist01;
    RNG() : rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count()), dist01(0.0L, 1.0L) {}
    long double rnd() { return dist01(rng); }
    ll randll(ll L, ll R) {
        uniform_int_distribution<ll> d(L, R);
        return d(rng);
    }
};

struct Line {
    ll px, py, qx, qy;
    ll A, B, C;
};

static const long double RADIUS = 10000.0L;
static const ll LIMC = 1000000000LL;

static inline void compute_ABC(Line &L) {
    // From endpoints compute A,B,C for line Ax + By + C = 0
    // A = y1 - y2, B = x2 - x1, C = -(A*x1 + B*y1)
    ll x1 = L.px, y1 = L.py, x2 = L.qx, y2 = L.qy;
    L.A = y1 - y2;
    L.B = x2 - x1;
    // Use __int128 to compute C then cast to ll (fits in 64-bit range here)
    i128 tmp = (i128)L.A * (i128)x1 + (i128)L.B * (i128)y1;
    tmp = -tmp;
    L.C = (ll)tmp;
}

static inline int sign_at_point(const Line &L, ll x, ll y) {
    i128 val = (i128)L.A * (i128)x + (i128)L.B * (i128)y + (i128)L.C;
    if (val > 0) return 1;
    if (val < 0) return -1;
    return 0;
}

static inline bool line_crosses_circle(const Line &L) {
    // distance from origin to line: |C| / sqrt(A^2+B^2) <= RADIUS
    long double A = (long double)L.A;
    long double B = (long double)L.B;
    long double C = (long double)L.C;
    long double denom = sqrtl(A*A + B*B);
    if (denom == 0.0L) return false;
    long double dist = fabsl(C) / denom;
    return dist <= RADIUS + 1e-9L;
}

static Line generate_random_line(RNG &rng) {
    // Generate a line that surely crosses the circle using (phi, t) param, then round endpoints
    // P(s) = t*n + s*d where n=(cos phi, sin phi), d=(-sin phi, cos phi), t in [-R, R]
    for (int tries = 0; tries < 1000; ++tries) {
        long double phi = rng.rnd() * acosl(-1.0L); // [0, pi)
        long double c = cosl(phi), s = sinl(phi);
        long double t = (rng.rnd() * 2.0L - 1.0L) * (RADIUS * 0.95L);
        long double nx = c, ny = s;
        long double dx = -s, dy = c;
        long double S = 9.0e8L;
        long double x1 = t * nx + S * dx;
        long double y1 = t * ny + S * dy;
        long double x2 = t * nx - S * dx;
        long double y2 = t * ny - S * dy;
        ll px = llround(x1), py = llround(y1), qx = llround(x2), qy = llround(y2);
        // Clamp to limits if necessary (shouldn't be needed)
        px = max(-LIMC, min(LIMC, px));
        py = max(-LIMC, min(LIMC, py));
        qx = max(-LIMC, min(LIMC, qx));
        qy = max(-LIMC, min(LIMC, qy));
        if (px == qx && py == qy) continue;
        Line L{px, py, qx, qy, 0, 0, 0};
        compute_ABC(L);
        if (line_crosses_circle(L)) return L;
    }
    // Fallback: vertical line x = 0
    Line L{0, -LIMC, 0, LIMC, 0, 0, 0};
    compute_ABC(L);
    return L;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    if (!(cin >> N >> K)) {
        return 0;
    }
    vector<int> a(11, 0);
    for (int d = 1; d <= 10; ++d) cin >> a[d];
    vector<ll> xs(N), ys(N);
    for (int i = 0; i < N; ++i) cin >> xs[i] >> ys[i];

    RNG rng;

    // Initialize masks for points; store positive-side bits
    vector<uint64_t> maskLo(N, 0), maskHi(N, 0);
    vector<int> aliveIdx(N);
    iota(aliveIdx.begin(), aliveIdx.end(), 0);

    vector<Line> chosen;
    chosen.reserve(K);

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.95;

    int kcur = 0;

    // Helper buffer for candidate evaluation
    vector<u128> tmpMasks;
    tmpMasks.reserve(N);

    // Current best score (for info; not used to select candidates apart from relative)
    auto compute_score_from_masks = [&](int current_bits) -> int {
        tmpMasks.clear();
        tmpMasks.reserve(aliveIdx.size());
        for (int idx : aliveIdx) {
            u128 m = ((u128)maskHi[idx] << 64) | (u128)maskLo[idx];
            tmpMasks.push_back(m);
        }
        sort(tmpMasks.begin(), tmpMasks.end());
        int bcnt[11] = {0};
        for (size_t i = 0; i < tmpMasks.size();) {
            size_t j = i + 1;
            while (j < tmpMasks.size() && tmpMasks[j] == tmpMasks[i]) ++j;
            int cnt = (int)(j - i);
            if (1 <= cnt && cnt <= 10) bcnt[cnt]++;
            i = j;
        }
        int sc = 0;
        for (int d = 1; d <= 10; ++d) sc += min(a[d], bcnt[d]);
        return sc;
    };

    int current_score = 0;

    while (kcur < K) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > TIME_LIMIT) break;

        int CAND = 20;
        if (K - kcur > 50 && elapsed < 0.5) CAND = 25;
        if (elapsed > 1.6) CAND = 12;
        if ((int)aliveIdx.size() > 4000) CAND = max(12, CAND - 4);
        if ((int)aliveIdx.size() > 5000) CAND = max(10, CAND - 6);

        int best_score = -1;
        int best_killed = INT_MAX;
        Line best_line;
        bool found = false;

        for (int c = 0; c < CAND; ++c) {
            Line cand = generate_random_line(rng);
            // Evaluate candidate
            tmpMasks.clear();
            tmpMasks.reserve(aliveIdx.size());
            int killed = 0;
            for (int idx : aliveIdx) {
                int sgn = sign_at_point(cand, xs[idx], ys[idx]);
                if (sgn == 0) {
                    killed++;
                    continue; // this strawberry is removed by this line
                }
                uint64_t lo = maskLo[idx];
                uint64_t hi = maskHi[idx];
                if (kcur < 64) {
                    if (sgn > 0) lo |= (1ULL << kcur);
                } else {
                    if (sgn > 0) hi |= (1ULL << (kcur - 64));
                }
                u128 m = ((u128)hi << 64) | (u128)lo;
                tmpMasks.push_back(m);
            }
            sort(tmpMasks.begin(), tmpMasks.end());
            int bcnt[11] = {0};
            for (size_t i = 0; i < tmpMasks.size();) {
                size_t j = i + 1;
                while (j < tmpMasks.size() && tmpMasks[j] == tmpMasks[i]) ++j;
                int cnt = (int)(j - i);
                if (1 <= cnt && cnt <= 10) bcnt[cnt]++;
                i = j;
            }
            int sc = 0;
            for (int d = 1; d <= 10; ++d) sc += min(a[d], bcnt[d]);

            if (sc > best_score || (sc == best_score && killed < best_killed)) {
                best_score = sc;
                best_killed = killed;
                best_line = cand;
                found = true;
            }
        }

        if (!found) break;

        // Apply best_line: update masks and aliveIdx
        vector<int> newAlive;
        newAlive.reserve(aliveIdx.size());
        for (int idx : aliveIdx) {
            int sgn = sign_at_point(best_line, xs[idx], ys[idx]);
            if (sgn == 0) {
                // removed
                continue;
            }
            if (kcur < 64) {
                if (sgn > 0) maskLo[idx] |= (1ULL << kcur);
            } else {
                if (sgn > 0) maskHi[idx] |= (1ULL << (kcur - 64));
            }
            newAlive.push_back(idx);
        }
        aliveIdx.swap(newAlive);
        chosen.push_back(best_line);
        kcur++;

        current_score = best_score;
        // optional: if aliveIdx is empty, further cuts won't help
        if (aliveIdx.empty()) break;

        now = chrono::steady_clock::now();
        elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > TIME_LIMIT) break;
    }

    // Output
    cout << chosen.size() << '\n';
    for (auto &L : chosen) {
        cout << L.px << ' ' << L.py << ' ' << L.qx << ' ' << L.qy << '\n';
    }
    return 0;
}