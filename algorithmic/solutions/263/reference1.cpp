#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool nextInt(T &out) {
        char c = read();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = read();
            if (!c) return false;
        }
        bool neg = false;
        if (c == '-') {
            neg = true;
            c = read();
        }
        T val = 0;
        while (c >= '0' && c <= '9') {
            val = val * 10 + (c - '0');
            c = read();
        }
        out = neg ? -val : val;
        return true;
    }

    bool nextToken(string &s) {
        char c = read();
        if (!c) return false;
        while (c && isspace((unsigned char)c)) {
            c = read();
            if (!c) return false;
        }
        s.clear();
        while (c && !isspace((unsigned char)c)) {
            s.push_back(c);
            c = read();
        }
        return true;
    }
};

struct Item {
    double v;
    double w;
};

static inline uint64_t splitmix64(uint64_t &x) {
    uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

static inline double median3(double a, double b, double c) {
    if (a > b) swap(a, b);
    if (b > c) swap(b, c);
    if (a > b) swap(a, b);
    return b;
}

static inline double clipLog(double x, double LOGMAX) {
    if (x < 0.0) return 0.0;
    if (x > LOGMAX) return LOGMAX;
    return x;
}

double weightedMedian(vector<Item> &a, double totalW, uint64_t &seed) {
    int l = 0, r = (int)a.size();
    double target = totalW * 0.5;
    while (true) {
        if (r - l <= 32) {
            sort(a.begin() + l, a.begin() + r, [](const Item &A, const Item &B) {
                return A.v < B.v;
            });
            double pref = 0.0;
            for (int i = l; i < r; ++i) {
                pref += a[i].w;
                if (pref >= target) return a[i].v;
            }
            return a[r - 1].v;
        }

        int len = r - l;
        int i1 = l + (int)(splitmix64(seed) % (uint64_t)len);
        int i2 = l + (int)(splitmix64(seed) % (uint64_t)len);
        int i3 = l + (int)(splitmix64(seed) % (uint64_t)len);
        double pivot = median3(a[i1].v, a[i2].v, a[i3].v);

        int lt = l, i = l, gt = r;
        double wl = 0.0, we = 0.0;
        while (i < gt) {
            if (a[i].v < pivot) {
                wl += a[i].w;
                swap(a[lt++], a[i++]);
            } else if (a[i].v > pivot) {
                swap(a[i], a[--gt]);
            } else {
                we += a[i].w;
                ++i;
            }
        }

        if (target < wl) {
            r = lt;
        } else if (target <= wl + we) {
            return pivot;
        } else {
            target -= (wl + we);
            l = gt;
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, m, D;
    if (!fs.nextInt(n)) return 0;
    fs.nextInt(m);
    fs.nextInt(D);

    if (D == m) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << '\n' << m;
        for (int i = 1; i <= m; ++i) cout << ' ' << i;
        cout << '\n';
        return 0;
    }

    vector<uint16_t> U(m), V(m);
    vector<uint32_t> X(m);
    vector<uint16_t> W(m);
    vector<float> LX(m);

    vector<int> deg(n, 0);
    vector<double> sumW(n, 0.0), sumWL(n, 0.0);

    for (int e = 0; e < m; ++e) {
        int u, v, x, w;
        fs.nextInt(u);
        fs.nextInt(v);
        fs.nextInt(x);
        fs.nextInt(w);
        --u; --v;
        U[e] = (uint16_t)u;
        V[e] = (uint16_t)v;
        X[e] = (uint32_t)x;
        W[e] = (uint16_t)w;
        float lx = log((double)x);
        LX[e] = lx;
        deg[u]++;
        deg[v]++;
        sumW[u] += (double)w;
        sumW[v] += (double)w;
        sumWL[u] += (double)w * (double)lx;
        sumWL[v] += (double)w * (double)lx;
    }

    vector<int> off(n + 1, 0);
    for (int i = 0; i < n; ++i) off[i + 1] = off[i] + deg[i];
    vector<int> cur = off;
    vector<int> adj(2 * m);
    for (int e = 0; e < m; ++e) {
        adj[cur[U[e]]++] = e;
        adj[cur[V[e]]++] = e;
    }

    int maxDeg = 0;
    for (int i = 0; i < n; ++i) maxDeg = max(maxDeg, deg[i]);

    const double LOGMAX = log(1e9);
    vector<Item> temp;
    temp.reserve(maxDeg);
    uint64_t seed = 1234567891234567ULL;

    auto makeInitMean = [&]() {
        vector<double> y(n, 0.0);
        for (int i = 0; i < n; ++i) {
            if (sumW[i] > 0.0) y[i] = clipLog(0.5 * (sumWL[i] / sumW[i]), LOGMAX);
        }
        return y;
    };

    auto makeInitMedian = [&]() {
        vector<double> y(n, 0.0);
        for (int i = 0; i < n; ++i) {
            temp.clear();
            double totalW = 0.0;
            for (int p = off[i]; p < off[i + 1]; ++p) {
                int e = adj[p];
                double wt = (double)W[e];
                temp.push_back({(double)LX[e], wt});
                totalW += wt;
            }
            if (!temp.empty()) {
                double med = weightedMedian(temp, totalW, seed);
                y[i] = clipLog(0.5 * med, LOGMAX);
            }
        }
        return y;
    };

    auto logRefine = [&](vector<double> &y, const vector<unsigned char> *active, int passes) {
        for (int pass = 0; pass < passes; ++pass) {
            for (int i = 0; i < n; ++i) {
                temp.clear();
                double totalW = 0.0;
                for (int p = off[i]; p < off[i + 1]; ++p) {
                    int e = adj[p];
                    if (active && !(*active)[e]) continue;
                    int j = ((int)U[e] == i ? (int)V[e] : (int)U[e]);
                    double wt = (double)W[e];
                    temp.push_back({(double)LX[e] - y[j], wt});
                    totalW += wt;
                }
                if (!temp.empty()) {
                    double med = weightedMedian(temp, totalW, seed);
                    y[i] = clipLog(med, LOGMAX);
                }
            }
        }
    };

    auto yToA = [&](const vector<double> &y) {
        vector<uint32_t> a(n, 1);
        for (int i = 0; i < n; ++i) {
            double ev = exp(y[i]);
            long long ai = llround(ev);
            if (ai < 1) ai = 1;
            if (ai > 1000000000LL) ai = 1000000000LL;
            a[i] = (uint32_t)ai;
        }
        return a;
    };

    auto intRefine = [&](vector<uint32_t> &a, const vector<unsigned char> *active, int passes) {
        for (int pass = 0; pass < passes; ++pass) {
            for (int i = 0; i < n; ++i) {
                temp.clear();
                double totalW = 0.0;
                for (int p = off[i]; p < off[i + 1]; ++p) {
                    int e = adj[p];
                    if (active && !(*active)[e]) continue;
                    int j = ((int)U[e] == i ? (int)V[e] : (int)U[e]);
                    double aj = (double)a[j];
                    double target = (double)X[e] / aj;
                    double wt = (double)W[e] * aj / (double)X[e];
                    temp.push_back({target, wt});
                    totalW += wt;
                }
                if (!temp.empty()) {
                    double med = weightedMedian(temp, totalW, seed);
                    long long ai = llround(med);
                    if (ai < 1) ai = 1;
                    if (ai > 1000000000LL) ai = 1000000000LL;
                    a[i] = (uint32_t)ai;
                }
            }
        }
    };

    vector<double> errs(m);
    vector<int> ord(m);

    auto evaluate = [&](const vector<uint32_t> &a, vector<int> *badOut) -> long double {
        long double total = 0.0L;
        for (int e = 0; e < m; ++e) {
            unsigned long long p = (unsigned long long)a[U[e]] * (unsigned long long)a[V[e]];
            long double diff = (p >= (unsigned long long)X[e])
                ? (long double)p - (long double)X[e]
                : (long double)X[e] - (long double)p;
            double err = (double)((long double)W[e] * diff / (long double)X[e]);
            errs[e] = err;
            ord[e] = e;
            total += (long double)err;
        }
        if (D == 0) {
            if (badOut) badOut->clear();
            return total;
        }
        nth_element(ord.begin(), ord.begin() + D, ord.end(), [&](int aIdx, int bIdx) {
            return errs[aIdx] > errs[bIdx];
        });
        long double removed = 0.0L;
        if (badOut) badOut->assign(ord.begin(), ord.begin() + D);
        for (int i = 0; i < D; ++i) removed += (long double)errs[ord[i]];
        return total - removed;
    };

    vector<uint32_t> bestA(n, 1);
    long double bestLoss = evaluate(bestA, nullptr);

    vector<vector<double>> inits;
    inits.push_back(vector<double>(n, 0.0));
    inits.push_back(makeInitMean());
    inits.push_back(makeInitMedian());

    vector<unsigned char> active(m, 1);

    for (const auto &init : inits) {
        vector<double> y = init;
        logRefine(y, nullptr, 2);
        vector<uint32_t> a = yToA(y);
        intRefine(a, nullptr, 2);

        vector<int> bad;
        long double loss1 = evaluate(a, &bad);
        if (loss1 < bestLoss) {
            bestLoss = loss1;
            bestA = a;
        }

        if (D > 0 && !bad.empty()) {
            fill(active.begin(), active.end(), (unsigned char)1);
            for (int id : bad) active[id] = 0;
            vector<uint32_t> a2 = a;
            intRefine(a2, &active, 2);
            long double loss2 = evaluate(a2, nullptr);
            if (loss2 < bestLoss) {
                bestLoss = loss2;
                bestA = a2;
            }
        }
    }

    if (D > 0) {
        for (int iter = 0; iter < 2; ++iter) {
            vector<int> bad;
            long double curLoss = evaluate(bestA, &bad);
            if (curLoss < bestLoss) bestLoss = curLoss;
            fill(active.begin(), active.end(), (unsigned char)1);
            for (int id : bad) active[id] = 0;
            vector<uint32_t> cand = bestA;
            intRefine(cand, &active, 1);
            long double loss = evaluate(cand, nullptr);
            if (loss + 1e-12L < bestLoss) {
                bestLoss = loss;
                bestA.swap(cand);
            } else {
                break;
            }
        }
    }

    vector<int> finalBad;
    evaluate(bestA, &finalBad);
    sort(finalBad.begin(), finalBad.end());

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << bestA[i];
    }
    cout << '\n';
    cout << finalBad.size();
    for (int id : finalBad) cout << ' ' << (id + 1);
    cout << '\n';
    return 0;
}