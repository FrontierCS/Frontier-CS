#include <bits/stdc++.h>
using namespace std;

struct CustomHash {
    static uint64_t splitmix64(uint64_t x) {
        x += 0x9e3779b97f4a7c15ULL;
        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
        x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
    size_t operator()(uint64_t x) const {
        static const uint64_t FIXED_RANDOM =
            (uint64_t)chrono::steady_clock::now().time_since_epoch().count();
        return (size_t)splitmix64(x + FIXED_RANDOM);
    }
};

static inline uint64_t packPair32(uint32_t a, uint32_t b) {
    if (a > b) swap(a, b);
    return (uint64_t(a) << 32) | uint64_t(b);
}

static int isqrt_int(int x) {
    int r = (int)floor(sqrt((long double)x));
    while ((long long)(r + 1) * (r + 1) <= x) ++r;
    while ((long long)r * r > x) --r;
    return r;
}

static vector<pair<int,int>> baseline_one_per_column(int n, int m) {
    vector<pair<int,int>> e;
    e.reserve(m);
    for (int c = 1; c <= m; ++c) {
        int r = (c - 1) % n + 1;
        e.emplace_back(r, c);
    }
    return e;
}

static vector<pair<int,int>> baseline_one_per_row(int n, int m) {
    vector<pair<int,int>> e;
    e.reserve(n);
    for (int r = 1; r <= n; ++r) {
        int c = (r - 1) % m + 1;
        e.emplace_back(r, c);
    }
    return e;
}

// Greedy: for each left vertex (1..L), pick up to targetDeg right vertices (1..R)
// while ensuring no unordered pair of right vertices is used in two different left vertices.
// outputSwap=false => edges are (left, right); outputSwap=true => edges are (right, left).
static vector<pair<int,int>> greedy_unique_right_pairs(int L, int R, int targetDeg, bool outputSwap) {
    const int DEG_CAP = 600;
    const long long PAIRS_CAP = 2000000LL;

    targetDeg = min(targetDeg, R);
    targetDeg = min(targetDeg, DEG_CAP);
    if (targetDeg < 1) targetDeg = 1;

    // Reduce degree if worst-case pair storage is too big
    while (targetDeg >= 2) {
        long long worstPairs = 1LL * L * targetDeg * (targetDeg - 1) / 2;
        if (worstPairs <= PAIRS_CAP) break;
        --targetDeg;
    }
    if (targetDeg < 1) targetDeg = 1;

    vector<pair<int,int>> edges;
    edges.reserve(min<long long>(1LL * L * targetDeg, 100000LL));

    if (targetDeg == 1) {
        // Fast: choose one right per left in cyclic manner
        for (int left = 1; left <= L; ++left) {
            int right = (left - 1) % R + 1;
            if (!outputSwap) edges.emplace_back(left, right);
            else edges.emplace_back(right, left);
        }
        return edges;
    }

    long long reservePairs = 1LL * L * targetDeg * (targetDeg - 1) / 2;
    reservePairs = min<long long>(reservePairs, PAIRS_CAP);
    unordered_set<uint64_t, CustomHash> usedPairs;
    usedPairs.reserve((size_t)(reservePairs * 1.3) + 16);

    vector<int> seen(R + 1, 0);
    vector<int> chosen;
    chosen.reserve(targetDeg);

    mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    for (int left = 1; left <= L; ++left) {
        chosen.clear();
        int start = (int)(rng() % (uint64_t)R) + 1;

        for (int t = 0; t < R && (int)chosen.size() < targetDeg; ++t) {
            int v = start + t;
            if (v > R) v -= R;
            if (seen[v] == left) continue;

            bool ok = true;
            for (int u : chosen) {
                uint64_t key = packPair32((uint32_t)u, (uint32_t)v);
                if (usedPairs.find(key) != usedPairs.end()) { ok = false; break; }
            }
            if (!ok) continue;

            seen[v] = left;
            chosen.push_back(v);
        }

        // Commit: store pairs and edges
        int s = (int)chosen.size();
        for (int i = 0; i < s; ++i) {
            for (int j = i + 1; j < s; ++j) {
                uint64_t key = packPair32((uint32_t)chosen[i], (uint32_t)chosen[j]);
                usedPairs.insert(key);
            }
        }
        for (int v : chosen) {
            if (!outputSwap) edges.emplace_back(left, v);
            else edges.emplace_back(v, left);
        }
    }
    return edges;
}

// Affine-plane-like construction (C4-free) on a q^2 by q^2 subgrid, with extra singleton points.
static vector<pair<int,int>> affine_construct_rows_cols(int n, int m) {
    vector<pair<int,int>> edges;
    int q = isqrt_int(m);
    if (q < 1) return edges;
    int colsUsed = q * q;
    int baseRows = min(n, q * q);

    edges.reserve(min<long long>(1LL * baseRows * q + (n - baseRows) + (m - colsUsed), 100000LL));

    for (int i = 0; i < baseRows; ++i) {
        int x = i / q;
        int y = i % q;
        int r = i + 1;
        for (int a = 0; a < q; ++a) {
            int b = y - a * x;
            b %= q;
            if (b < 0) b += q;
            int c = a * q + b + 1;
            edges.emplace_back(r, c);
        }
    }
    // Extra rows: single point in col 1
    for (int r = baseRows + 1; r <= n; ++r) edges.emplace_back(r, 1);
    // Extra cols: single point in row 1 (if exists)
    if (n >= 1) {
        for (int c = colsUsed + 1; c <= m; ++c) edges.emplace_back(1, c);
    }
    return edges;
}

static vector<pair<int,int>> affine_construct_cols_rows(int n, int m) {
    // Build on swapped dimensions then swap back
    auto e = affine_construct_rows_cols(m, n);
    for (auto &p : e) swap(p.first, p.second);
    return e;
}

static vector<pair<int,int>> best_greedy_by_rows(int n, int m) {
    int sq = isqrt_int(m);
    int extra = (m + n - 1) / n; // ~ ceil(m/n)
    int deg = sq + extra;
    deg = min(deg, m);
    deg = min(deg, 600);

    auto e1 = greedy_unique_right_pairs(n, m, deg, false);
    auto e2 = greedy_unique_right_pairs(n, m, max(1, deg - 1), false);
    return (e2.size() > e1.size()) ? e2 : e1;
}

static vector<pair<int,int>> best_greedy_by_cols(int n, int m) {
    int sq = isqrt_int(n);
    int extra = (n + m - 1) / m; // ~ ceil(n/m)
    int deg = sq + extra;
    deg = min(deg, n);
    deg = min(deg, 600);

    auto e1 = greedy_unique_right_pairs(m, n, deg, true);
    auto e2 = greedy_unique_right_pairs(m, n, max(1, deg - 1), true);
    return (e2.size() > e1.size()) ? e2 : e1;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    // Special easy cases
    if (n == 1) {
        cout << m << "\n";
        for (int c = 1; c <= m; ++c) cout << 1 << " " << c << "\n";
        return 0;
    }
    if (m == 1) {
        cout << n << "\n";
        for (int r = 1; r <= n; ++r) cout << r << " " << 1 << "\n";
        return 0;
    }
    if (n == 2) {
        vector<pair<int,int>> e;
        e.reserve(min(100000, m + 1));
        for (int c = 1; c <= m; ++c) e.emplace_back(1, c);
        e.emplace_back(2, 1);
        cout << e.size() << "\n";
        for (auto &p : e) cout << p.first << " " << p.second << "\n";
        return 0;
    }
    if (m == 2) {
        vector<pair<int,int>> e;
        e.reserve(min(100000, n + 1));
        for (int r = 1; r <= n; ++r) e.emplace_back(r, 1);
        e.emplace_back(1, 2);
        cout << e.size() << "\n";
        for (auto &p : e) cout << p.first << " " << p.second << "\n";
        return 0;
    }

    vector<pair<int,int>> best;

    auto consider = [&](vector<pair<int,int>> cand) {
        if (cand.size() > best.size()) best.swap(cand);
    };

    consider(baseline_one_per_column(n, m));
    consider(baseline_one_per_row(n, m));
    consider(affine_construct_rows_cols(n, m));
    consider(affine_construct_cols_rows(n, m));
    consider(best_greedy_by_rows(n, m));
    consider(best_greedy_by_cols(n, m));

    cout << best.size() << "\n";
    for (auto &p : best) cout << p.first << " " << p.second << "\n";
    return 0;
}