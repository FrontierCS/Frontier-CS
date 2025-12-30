#include <bits/stdc++.h>
using namespace std;

struct Point {
    double x, y, z;
};

static inline double sqr(double a) { return a * a; }

static inline double diam2_to_faces(const Point& p) {
    double m = min({p.x, 1.0 - p.x, p.y, 1.0 - p.y, p.z, 1.0 - p.z});
    double d = 2.0 * m;
    return d * d;
}

static inline double dist2(const Point& a, const Point& b) {
    double dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
    return dx*dx + dy*dy + dz*dz;
}

static uint64_t splitmix64_state = 0x123456789abcdefULL;
static inline uint64_t splitmix64() {
    uint64_t z = (splitmix64_state += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

static inline double rnd01() {
    // [0,1)
    return (splitmix64() >> 11) * (1.0 / 9007199254740992.0);
}

static double vdc(int n, int base) {
    double v = 0.0;
    double denom = 1.0;
    while (n > 0) {
        denom *= base;
        v += (n % base) / denom;
        n /= base;
    }
    return v;
}

enum class LatticeType { SC, BCC, FCC };

static long long countSC(int s) {
    return 1LL * s * s * s;
}
static long long countBCC(int s) {
    long long a = 1LL * s * s * s;
    long long b = (s >= 2) ? 1LL * (s - 1) * (s - 1) * (s - 1) : 0LL;
    return a + b;
}
static long long countFCC(int s) {
    long long a = 1LL * s * s * s;
    long long b = (s >= 2) ? 3LL * s * (s - 1) * (s - 1) : 0LL;
    return a + b;
}

static vector<Point> genSC(int s) {
    vector<Point> v;
    v.reserve(1LL * s * s * s);
    double inv = 1.0 / s;
    for (int k = 0; k < s; k++) {
        double z = (k + 0.5) * inv;
        for (int j = 0; j < s; j++) {
            double y = (j + 0.5) * inv;
            for (int i = 0; i < s; i++) {
                double x = (i + 0.5) * inv;
                v.push_back({x, y, z});
            }
        }
    }
    return v;
}

static vector<Point> genBCC(int s) {
    vector<Point> v;
    long long total = countBCC(s);
    v.reserve((size_t)total);
    double inv = 1.0 / s;

    // A points: (i+0.5)/s
    for (int k = 0; k < s; k++) {
        double z = (k + 0.5) * inv;
        for (int j = 0; j < s; j++) {
            double y = (j + 0.5) * inv;
            for (int i = 0; i < s; i++) {
                double x = (i + 0.5) * inv;
                v.push_back({x, y, z});
            }
        }
    }

    // B points: (i+1)/s, ranges 0..s-2
    if (s >= 2) {
        for (int k = 0; k < s - 1; k++) {
            double z = (k + 1.0) * inv;
            for (int j = 0; j < s - 1; j++) {
                double y = (j + 1.0) * inv;
                for (int i = 0; i < s - 1; i++) {
                    double x = (i + 1.0) * inv;
                    v.push_back({x, y, z});
                }
            }
        }
    }
    return v;
}

static vector<Point> genFCC(int s) {
    vector<Point> v;
    long long total = countFCC(s);
    v.reserve((size_t)total);
    double inv = 1.0 / s;

    // P0: (i,j,k)
    for (int k = 0; k < s; k++) {
        double z = (k + 0.5) * inv;
        for (int j = 0; j < s; j++) {
            double y = (j + 0.5) * inv;
            for (int i = 0; i < s; i++) {
                double x = (i + 0.5) * inv;
                v.push_back({x, y, z});
            }
        }
    }

    if (s >= 2) {
        // P1: (i+0.5, j+0.5, k)
        for (int k = 0; k < s; k++) {
            double z = (k + 0.5) * inv;
            for (int j = 0; j < s - 1; j++) {
                double y = (j + 1.0) * inv;
                for (int i = 0; i < s - 1; i++) {
                    double x = (i + 1.0) * inv;
                    v.push_back({x, y, z});
                }
            }
        }
        // P2: (i+0.5, j, k+0.5)
        for (int k = 0; k < s - 1; k++) {
            double z = (k + 1.0) * inv;
            for (int j = 0; j < s; j++) {
                double y = (j + 0.5) * inv;
                for (int i = 0; i < s - 1; i++) {
                    double x = (i + 1.0) * inv;
                    v.push_back({x, y, z});
                }
            }
        }
        // P3: (i, j+0.5, k+0.5)
        for (int k = 0; k < s - 1; k++) {
            double z = (k + 1.0) * inv;
            for (int j = 0; j < s - 1; j++) {
                double y = (j + 1.0) * inv;
                for (int i = 0; i < s; i++) {
                    double x = (i + 0.5) * inv;
                    v.push_back({x, y, z});
                }
            }
        }
    }
    return v;
}

struct GreedyResult {
    vector<int> idx;
    double minDiam2;
};

static GreedyResult greedySelect(const vector<Point>& cand, const vector<double>& face2, int n, int startIdx,
                                vector<double>& best, vector<unsigned char>& used, bool computeMinDiam2) {
    int M = (int)cand.size();
    used.assign(M, 0);
    best = face2;

    GreedyResult res;
    res.idx.reserve(n);
    res.minDiam2 = numeric_limits<double>::infinity();

    auto addPoint = [&](int sel) {
        used[sel] = 1;

        if (computeMinDiam2) {
            res.minDiam2 = min(res.minDiam2, face2[sel]);
            for (int prev : res.idx) {
                res.minDiam2 = min(res.minDiam2, dist2(cand[sel], cand[prev]));
            }
        }

        // Update best distances for candidates not selected.
        const Point& p = cand[sel];
        for (int j = 0; j < M; j++) {
            if (!used[j]) {
                double d2 = dist2(p, cand[j]);
                if (d2 < best[j]) best[j] = d2;
            }
        }

        res.idx.push_back(sel);
    };

    if (startIdx < 0) {
        int sel = -1;
        double mx = -1.0;
        for (int i = 0; i < M; i++) {
            if (best[i] > mx) {
                mx = best[i];
                sel = i;
            }
        }
        startIdx = sel;
    }

    addPoint(startIdx);

    while ((int)res.idx.size() < n) {
        int sel = -1;
        double mx = -1.0;
        for (int i = 0; i < M; i++) {
            if (!used[i] && best[i] > mx) {
                mx = best[i];
                sel = i;
            }
        }
        if (sel < 0) break; // should not happen if M>=n
        addPoint(sel);
    }

    if (!computeMinDiam2) res.minDiam2 = -1.0;
    return res;
}

static int ceil_cuberoot_int(long long n) {
    long long s = pow((long double)n, 1.0L / 3.0L);
    while (s*s*s < n) s++;
    while ((s-1) > 0 && (s-1)*(s-1)*(s-1) >= n) s--;
    return (int)s;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    cout << setprecision(17);

    if (n == 2) {
        double rt3 = sqrt(3.0);
        double r = rt3 / (2.0 * (1.0 + rt3));
        Point a{r, r, r};
        Point b{1.0 - r, 1.0 - r, 1.0 - r};
        cout << a.x << ' ' << a.y << ' ' << a.z << "\n";
        cout << b.x << ' ' << b.y << ' ' << b.z << "\n";
        return 0;
    }

    if (n > 50000) {
        int s = ceil_cuberoot_int(n);
        double inv = 1.0 / s;
        int printed = 0;
        for (int k = 0; k < s && printed < n; k++) {
            double z = (k + 0.5) * inv;
            for (int j = 0; j < s && printed < n; j++) {
                double y = (j + 0.5) * inv;
                for (int i = 0; i < s && printed < n; i++) {
                    double x = (i + 0.5) * inv;
                    cout << x << ' ' << y << ' ' << z << "\n";
                    printed++;
                }
            }
        }
        return 0;
    }

    // Choose best lattice among SC/BCC/FCC by predicted radius (based on minimal s meeting count).
    struct Opt { LatticeType type; int s; long long cnt; double predR; };
    vector<Opt> opts;

    {
        int s = 1;
        while (countSC(s) < n) s++;
        double predR = 0.5 / s;
        opts.push_back({LatticeType::SC, s, countSC(s), predR});
    }
    {
        int s = 1;
        while (countBCC(s) < n) s++;
        double predR = (sqrt(3.0) / 4.0) / s;
        opts.push_back({LatticeType::BCC, s, countBCC(s), predR});
    }
    {
        int s = 1;
        while (countFCC(s) < n) s++;
        double predR = (1.0 / (2.0 * sqrt(2.0))) / s;
        opts.push_back({LatticeType::FCC, s, countFCC(s), predR});
    }

    Opt bestOpt = opts[0];
    for (auto &o : opts) {
        if (o.predR > bestOpt.predR) bestOpt = o;
    }

    vector<Point> cand;
    if (bestOpt.type == LatticeType::SC) cand = genSC(bestOpt.s);
    else if (bestOpt.type == LatticeType::BCC) cand = genBCC(bestOpt.s);
    else cand = genFCC(bestOpt.s);

    // Add extra candidates for small n to improve flexibility
    if (n <= 128) {
        int targetM = (n <= 64) ? 60000 : 40000;
        const double eps = 1e-6;
        int needHalton = max(0, targetM - (int)cand.size());
        cand.reserve(cand.size() + needHalton + targetM / 5 + 1024);

        for (int i = 1; i <= needHalton; i++) {
            double x = vdc(i, 2);
            double y = vdc(i, 3);
            double z = vdc(i, 5);
            x = eps + (1.0 - 2.0 * eps) * x;
            y = eps + (1.0 - 2.0 * eps) * y;
            z = eps + (1.0 - 2.0 * eps) * z;
            cand.push_back({x, y, z});
        }

        int extraRand = targetM / 5;
        for (int i = 0; i < extraRand; i++) {
            double x = eps + (1.0 - 2.0 * eps) * rnd01();
            double y = eps + (1.0 - 2.0 * eps) * rnd01();
            double z = eps + (1.0 - 2.0 * eps) * rnd01();
            cand.push_back({x, y, z});
        }
    }

    int M = (int)cand.size();
    vector<double> face2(M);
    for (int i = 0; i < M; i++) face2[i] = diam2_to_faces(cand[i]);

    vector<double> bestArr;
    vector<unsigned char> usedArr;

    // Build starting points list for multi-start on small n
    int K = 1;
    if (n <= 16) K = 24;
    else if (n <= 32) K = 16;
    else if (n <= 64) K = 8;
    else if (n <= 128) K = 4;

    vector<int> starts;
    starts.reserve(K);

    // Sort indices by face2 descending, take top bucket for diversified starts
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    int top = min(M, 1000);
    nth_element(order.begin(), order.begin() + top, order.end(), [&](int a, int b) {
        return face2[a] > face2[b];
    });
    order.resize(top);
    sort(order.begin(), order.end(), [&](int a, int b) {
        return face2[a] > face2[b];
    });

    if (!order.empty()) starts.push_back(order[0]);
    while ((int)starts.size() < K && !order.empty()) {
        int pick = order[splitmix64() % order.size()];
        bool ok = true;
        for (int s : starts) if (s == pick) { ok = false; break; }
        if (ok) starts.push_back(pick);
    }
    while ((int)starts.size() < K) {
        int pick = (int)(splitmix64() % M);
        bool ok = true;
        for (int s : starts) if (s == pick) { ok = false; break; }
        if (ok) starts.push_back(pick);
    }

    GreedyResult bestRes;
    bestRes.minDiam2 = -1.0;

    bool computeMinDiam2 = (K > 1);

    for (int si = 0; si < K; si++) {
        int startIdx = starts[si];
        auto res = greedySelect(cand, face2, n, startIdx, bestArr, usedArr, computeMinDiam2);
        if ((int)res.idx.size() != n) continue;

        if (!computeMinDiam2) {
            bestRes = std::move(res);
            break;
        } else {
            if (bestRes.minDiam2 < 0 || res.minDiam2 > bestRes.minDiam2) {
                bestRes = std::move(res);
            }
        }
    }

    // Fallback if something went wrong
    if ((int)bestRes.idx.size() != n) {
        auto res = greedySelect(cand, face2, n, -1, bestArr, usedArr, false);
        bestRes = std::move(res);
    }

    for (int i = 0; i < n; i++) {
        const Point& p = cand[bestRes.idx[i]];
        double x = p.x, y = p.y, z = p.z;
        if (x < 0) x = 0; if (x > 1) x = 1;
        if (y < 0) y = 0; if (y > 1) y = 1;
        if (z < 0) z = 0; if (z > 1) z = 1;
        cout << x << ' ' << y << ' ' << z << "\n";
    }

    return 0;
}