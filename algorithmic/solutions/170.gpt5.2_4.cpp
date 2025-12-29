#include <bits/stdc++.h>
using namespace std;

struct Xoroshiro128Plus {
    using ull = unsigned long long;
    ull s[2];
    static ull splitmix64(ull &x) {
        ull z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    explicit Xoroshiro128Plus(ull seed = 1) {
        ull x = seed;
        s[0] = splitmix64(x);
        s[1] = splitmix64(x);
    }
    inline ull nextU64() {
        ull s0 = s[0];
        ull s1 = s[1];
        ull result = s0 + s1;
        s1 ^= s0;
        s[0] = (s0 << 55) | (s0 >> (64 - 55));
        s[0] ^= s1 ^ (s1 << 14);
        s[1] = (s1 << 36) | (s1 >> (64 - 36));
        return result;
    }
    inline uint32_t nextU32() { return (uint32_t)nextU64(); }
    inline int nextInt(int lo, int hi) { return lo + (int)(nextU32() % (uint32_t)(hi - lo + 1)); }
    inline double nextDouble() { return (nextU64() >> 11) * (1.0 / 9007199254740992.0); }
};

struct Plan {
    vector<int> a, b;
};

static inline long long llabsll(long long x) { return x < 0 ? -x : x; }

struct Solver {
    int N, L;
    vector<int> T;
    Xoroshiro128Plus rng;

    Solver(int N_, int L_, vector<int> T_, unsigned long long seed) : N(N_), L(L_), T(std::move(T_)), rng(seed) {}

    int sampleByWeights(const vector<long long>& w) {
        long long sum = 0;
        for (long long x : w) sum += x;
        if (sum <= 0) return rng.nextInt(0, N - 1);
        unsigned long long r = rng.nextU64() % (unsigned long long)sum;
        long long pref = 0;
        for (int i = 0; i < N; i++) {
            pref += w[i];
            if ((unsigned long long)pref > r) return i;
        }
        return N - 1;
    }

    long long simulate(const Plan& p, array<int, 100>& cnt) {
        cnt.fill(0);
        int cur = 0;
        for (int step = 0; step < L; step++) {
            int c = ++cnt[cur];
            if (step + 1 == L) break;
            cur = (c & 1) ? p.a[cur] : p.b[cur];
        }
        long long E = 0;
        for (int i = 0; i < N; i++) E += llabsll((long long)cnt[i] - (long long)T[i]);
        return E;
    }

    Plan greedyInit() {
        struct EdgeItem {
            int src;
            int isA;
            int cap;
        };
        vector<long long> dem(N);
        for (int i = 0; i < N; i++) dem[i] = T[i];
        if (0 < N) dem[0] = max(0LL, dem[0] - 1); // slightly account for the start

        vector<EdgeItem> edges;
        edges.reserve(2 * N);
        for (int i = 0; i < N; i++) {
            int capA = (T[i] + 1) / 2;
            int capB = T[i] / 2;
            edges.push_back({i, 1, capA});
            edges.push_back({i, 0, capB});
        }
        sort(edges.begin(), edges.end(), [](const EdgeItem& x, const EdgeItem& y) {
            return x.cap > y.cap;
        });

        Plan p;
        p.a.assign(N, 0);
        p.b.assign(N, 0);

        for (auto &e : edges) {
            long long best = LLONG_MIN;
            int bestj = 0;
            int ties = 0;
            for (int j = 0; j < N; j++) {
                long long v = dem[j];
                if (v > best) {
                    best = v;
                    bestj = j;
                    ties = 1;
                } else if (v == best) {
                    ties++;
                    if (rng.nextInt(1, ties) == 1) bestj = j;
                }
            }
            if (e.isA) p.a[e.src] = bestj;
            else p.b[e.src] = bestj;
            dem[bestj] -= e.cap;
        }

        // Small mixing to avoid degenerate trapping (light touch)
        for (int i = 0; i < N; i++) {
            if (rng.nextInt(0, 99) < 8) {
                int j = rng.nextInt(0, N - 1);
                if (rng.nextInt(0, 1)) p.a[i] = j;
                else p.b[i] = j;
            }
        }
        return p;
    }

    Plan randomInit() {
        Plan p;
        p.a.assign(N, 0);
        p.b.assign(N, 0);
        vector<long long> w(N);
        for (int i = 0; i < N; i++) w[i] = (long long)T[i] + 1;
        for (int i = 0; i < N; i++) {
            p.a[i] = sampleByWeights(w);
            p.b[i] = sampleByWeights(w);
            if (rng.nextInt(0, 99) < 25) p.b[i] = p.a[i];
        }
        return p;
    }

    Plan solve() {
        array<int, 100> cnt, bestCnt, curCnt;

        Plan best = greedyInit();
        long long bestE = simulate(best, bestCnt);

        Plan cur = best;
        long long curE = bestE;
        curCnt = bestCnt;

        // Multi-start
        for (int k = 0; k < 6; k++) {
            Plan p = randomInit();
            long long e = simulate(p, cnt);
            if (e < bestE) {
                bestE = e;
                best = p;
                bestCnt = cnt;
            }
        }
        cur = best;
        curE = bestE;
        curCnt = bestCnt;

        auto tStart = chrono::steady_clock::now();
        const double TL = 1.85;
        const double temp0 = 12000.0;
        const double temp1 = 5.0;

        vector<long long> wSrc(N), wDst(N);

        int iter = 0;
        while (true) {
            auto now = chrono::steady_clock::now();
            double t = chrono::duration<double>(now - tStart).count();
            if (t >= TL) break;
            double prog = min(1.0, t / TL);
            double temp = temp0 * (1.0 - prog) + temp1 * prog;

            for (int i = 0; i < N; i++) {
                long long surplus = (long long)curCnt[i] - (long long)T[i];
                wSrc[i] = max(0LL, surplus) + 1;
                long long deficit = (long long)T[i] - (long long)curCnt[i];
                wDst[i] = max(0LL, deficit) + 1;
            }

            int i = sampleByWeights(wSrc);
            int which = rng.nextInt(0, 1);

            int nd;
            if (rng.nextInt(0, 99) < 85) nd = sampleByWeights(wDst);
            else nd = rng.nextInt(0, N - 1);

            Plan np = cur;
            if (which == 0) np.a[i] = nd;
            else np.b[i] = nd;

            // occasional 2-edge perturbation
            if (rng.nextInt(0, 99) < 6) {
                int nd2 = sampleByWeights(wDst);
                if (which == 0) np.b[i] = nd2;
                else np.a[i] = nd2;
            }

            long long nE = simulate(np, cnt);
            long long delta = nE - curE;

            bool accept = false;
            if (delta <= 0) accept = true;
            else {
                double prob = exp(-(double)delta / temp);
                accept = (rng.nextDouble() < prob);
            }

            if (accept) {
                cur = std::move(np);
                curE = nE;
                curCnt = cnt;
                if (curE < bestE) {
                    best = cur;
                    bestE = curE;
                    bestCnt = curCnt;
                }
            }

            iter++;
        }

        (void)iter;
        return best;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, L;
    cin >> N >> L;
    vector<int> T(N);
    for (int i = 0; i < N; i++) cin >> T[i];

    unsigned long long seed =
        (unsigned long long)chrono::high_resolution_clock::now().time_since_epoch().count() ^
        (unsigned long long)(uintptr_t)&N;

    Solver solver(N, L, T, seed);
    Plan ans = solver.solve();

    for (int i = 0; i < N; i++) {
        int ai = ans.a[i];
        int bi = ans.b[i];
        if (ai < 0 || ai >= N) ai = 0;
        if (bi < 0 || bi >= N) bi = 0;
        cout << ai << ' ' << bi << "\n";
    }
    return 0;
}