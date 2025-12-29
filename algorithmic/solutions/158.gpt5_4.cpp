#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, K;
    if (!(cin >> N >> K)) return 0;
    vector<int> a(11);
    for (int d = 1; d <= 10; d++) cin >> a[d];
    vector<int> xs(N), ys(N);
    unordered_set<int> setX, setY;
    setX.reserve(N * 2);
    setY.reserve(N * 2);
    for (int i = 0; i < N; i++) {
        cin >> xs[i] >> ys[i];
        setX.insert(xs[i]);
        setY.insert(ys[i]);
    }

    const long long INFCOORD = 1000000000LL;
    const int R = 10000;
    auto approx_pieces = [&](int m1, int m2) -> long double {
        // Approximate number of pieces inside the circle for a grid with m1 vertical and m2 horizontal lines
        // M ≈ π * (m1+1) * (m2+1) / 4
        return (M_PI * (long double)(m1 + 1) * (long double)(m2 + 1)) / 4.0L;
    };

    auto expected_match = [&](int m1, int m2) -> long double {
        if (m1 < 0 || m2 < 0) return -1e100L;
        long double M = approx_pieces(m1, m2);
        if (M <= 0) return -1e100L;
        long double lambda = (long double)N / M;
        // Compute expected b_d = M * Poisson(lambda, d)
        // Then sum min(a_d, expected b_d)
        static long double fact[21];
        static bool fact_init = false;
        if (!fact_init) {
            fact[0] = 1.0L;
            for (int i = 1; i <= 20; i++) fact[i] = fact[i - 1] * (long double)i;
            fact_init = true;
        }
        long double e_term = expl(-lambda);
        long double sum = 0.0L;
        long double powl_cache = 1.0L;
        for (int d = 1; d <= 10; d++) {
            powl_cache *= lambda; // lambda^d
            long double bd = M * e_term * (powl_cache) / fact[d];
            sum += min((long double)a[d], bd);
        }
        return sum;
    };

    // Choose m1 (vertical), m2 (horizontal) to maximize expected matches, with m1 + m2 <= K
    int best_m1 = 0, best_m2 = 0;
    long double best_score = -1e100L;
    for (int m1 = 0; m1 <= K; m1++) {
        int rem = K - m1;
        // search m2 from 0..rem
        for (int m2 = 0; m2 <= rem; m2++) {
            long double sc = expected_match(m1, m2);
            if (sc > best_score) {
                best_score = sc;
                best_m1 = m1;
                best_m2 = m2;
            }
        }
    }
    int m1 = best_m1;
    int m2 = best_m2;

    // Build vertical and horizontal line positions
    auto adjustCoord = [&](long long base, const unordered_set<int>& avoid, unordered_set<long long>& used)->long long {
        if (base < -INFCOORD) base = -INFCOORD;
        if (base > INFCOORD) base = INFCOORD;
        if (!avoid.count((int)base) && !used.count(base)) return base;
        for (int d = 1; d <= 2000000; d++) {
            long long p = base + d;
            if (p <= INFCOORD && !avoid.count((int)p) && !used.count(p)) return p;
            long long q = base - d;
            if (q >= -INFCOORD && !avoid.count((int)q) && !used.count(q)) return q;
        }
        // Fallback (shouldn't happen)
        for (long long v = -INFCOORD; v <= INFCOORD; v++) {
            if (!avoid.count((int)v) && !used.count(v)) return v;
            if (v == INFCOORD) break;
        }
        return base; // as a last resort
    };

    vector<array<long long,4>> lines;
    lines.reserve(m1 + m2);
    unordered_set<long long> usedX, usedY;
    usedX.reserve(m1 * 2 + 10);
    usedY.reserve(m2 * 2 + 10);

    if (m1 > 0) {
        long double stepX = (2.0L * R) / (long double)(m1 + 1);
        for (int j = 1; j <= m1; j++) {
            long double pos = -R + j * stepX;
            long long c = llround(pos);
            c = adjustCoord(c, setX, usedX);
            usedX.insert(c);
            lines.push_back({c, -INFCOORD, c, INFCOORD});
        }
    }
    if (m2 > 0) {
        long double stepY = (2.0L * R) / (long double)(m2 + 1);
        for (int j = 1; j <= m2; j++) {
            long double pos = -R + j * stepY;
            long long d = llround(pos);
            d = adjustCoord(d, setY, usedY);
            usedY.insert(d);
            lines.push_back({-INFCOORD, d, INFCOORD, d});
        }
    }

    int k = (int)lines.size();
    if (k > K) {
        // Trim if somehow exceeded (shouldn't happen)
        k = K;
        lines.resize(k);
    }

    cout << k << "\n";
    for (int i = 0; i < k; i++) {
        cout << lines[i][0] << " " << lines[i][1] << " " << lines[i][2] << " " << lines[i][3] << "\n";
    }
    return 0;
}