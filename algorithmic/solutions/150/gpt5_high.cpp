#include <bits/stdc++.h>
using namespace std;

struct Timer {
    chrono::steady_clock::time_point st;
    Timer() { reset(); }
    void reset() { st = chrono::steady_clock::now(); }
    double elapsed() const {
        return chrono::duration<double>(chrono::steady_clock::now() - st).count();
    }
};

struct XorShift64 {
    uint64_t x;
    XorShift64(uint64_t seed = 88172645463393265ull) { x = seed; if (!x) x = 88172645463393265ull; }
    inline uint64_t next() { x ^= x << 7; x ^= x >> 9; return x; }
    inline uint32_t nextU32() { return (uint32_t)next(); }
    inline int randint(int l, int r) { return l + (int)(nextU32() % (uint32_t)(r - l + 1)); }
    inline bool coin() { return (nextU32() & 1u) != 0u; }
    template<class It>
    void shuffle(It first, It last) {
        int n = (int)distance(first, last);
        for (int i = n - 1; i > 0; --i) {
            int j = (int)(nextU32() % (uint32_t)(i + 1));
            iter_swap(first + i, first + j);
        }
    }
};

static const int INF = 1e9;

inline int minAddCandidate(const string &s, const vector<string> &g, int &bestOri, int &bestI, int &bestJ, XorShift64 &rng) {
    int N = (int)g.size();
    int k = (int)s.size();
    int bestAdd = INF;
    // Orientation 0: horizontal, Orientation 1: vertical
    // Try horizontal
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int add = 0;
            bool ok = true;
            int jj = j;
            for (int p = 0; p < k; ++p) {
                if (jj >= N) jj -= N;
                char chg = g[i][jj];
                char chs = s[p];
                if (chg == '.') add++;
                else if (chg != chs) { ok = false; break; }
                ++jj;
            }
            if (!ok) continue;
            if (add < bestAdd || (add == bestAdd && rng.coin())) {
                bestAdd = add; bestOri = 0; bestI = i; bestJ = j;
                if (bestAdd == 0) return 0;
            }
        }
    }
    // Try vertical
    for (int j = 0; j < N; ++j) {
        for (int i = 0; i < N; ++i) {
            int add = 0;
            bool ok = true;
            int ii = i;
            for (int p = 0; p < k; ++p) {
                if (ii >= N) ii -= N;
                char chg = g[ii][j];
                char chs = s[p];
                if (chg == '.') add++;
                else if (chg != chs) { ok = false; break; }
                ++ii;
            }
            if (!ok) continue;
            if (add < bestAdd || (add == bestAdd && rng.coin())) {
                bestAdd = add; bestOri = 1; bestI = i; bestJ = j;
                if (bestAdd == 0) return 0;
            }
        }
    }
    return bestAdd;
}

inline void applyCandidate(const string &s, vector<string> &g, int ori, int i, int j) {
    int N = (int)g.size();
    int k = (int)s.size();
    if (ori == 0) {
        int jj = j;
        for (int p = 0; p < k; ++p) {
            if (jj >= N) jj -= N;
            if (g[i][jj] == '.') g[i][jj] = s[p];
            ++jj;
        }
    } else {
        int ii = i;
        for (int p = 0; p < k; ++p) {
            if (ii >= N) ii -= N;
            if (g[ii][j] == '.') g[ii][j] = s[p];
            ++ii;
        }
    }
}

inline bool existsMatch(const string &s, const vector<string> &g) {
    int N = (int)g.size();
    int k = (int)s.size();
    // horizontal
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            bool ok = true;
            int jj = j;
            for (int p = 0; p < k; ++p) {
                if (jj >= N) jj -= N;
                char chg = g[i][jj];
                if (chg != s[p]) { ok = false; break; }
                ++jj;
            }
            if (ok) return true;
        }
    }
    // vertical
    for (int j = 0; j < N; ++j) {
        for (int i = 0; i < N; ++i) {
            bool ok = true;
            int ii = i;
            for (int p = 0; p < k; ++p) {
                if (ii >= N) ii -= N;
                char chg = g[ii][j];
                if (chg != s[p]) { ok = false; break; }
                ++ii;
            }
            if (ok) return true;
        }
    }
    return false;
}

int countMatches(const vector<string> &g, const vector<string> &sList) {
    int cnt = 0;
    for (const auto &s : sList) {
        if (existsMatch(s, g)) ++cnt;
    }
    return cnt;
}

vector<string> constructGrid(const vector<string> &sList, int N, XorShift64 &rng, double time_limit_sec) {
    vector<string> g(N, string(N, '.'));
    int M = (int)sList.size();
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    // Sort by descending length initially
    stable_sort(order.begin(), order.end(), [&](int a, int b) {
        if ((int)sList[a].size() != (int)sList[b].size()) return (int)sList[a].size() > (int)sList[b].size();
        return a < b;
    });

    vector<bool> done(M, false);

    // Threshold schedule
    vector<int> thresholds = {0,1,2,3,4,6,8,12};

    Timer tmr;

    for (int ti = 0; ti < (int)thresholds.size(); ++ti) {
        int T = thresholds[ti];
        bool progress = true;
        int rounds = 0;
        while (progress) {
            progress = false;
            ++rounds;
            // Shuffle order slightly after first round at this threshold
            if (rounds > 1) rng.shuffle(order.begin(), order.end());
            for (int idx : order) {
                if (done[idx]) continue;
                int ori = 0, ii = 0, jj = 0;
                int add = minAddCandidate(sList[idx], g, ori, ii, jj, rng);
                if (add == INF) continue;
                if (add == 0) { done[idx] = true; continue; }
                if (add <= T) {
                    applyCandidate(sList[idx], g, ori, ii, jj);
                    done[idx] = true;
                    progress = true;
                }
                // Time guard
                if (tmr.elapsed() > time_limit_sec) return g;
            }
            if (tmr.elapsed() > time_limit_sec) return g;
        }
        if (tmr.elapsed() > time_limit_sec) break;
    }

    return g;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<string> sList(M);
    for (int i = 0; i < M; ++i) cin >> sList[i];

    Timer globalTimer;
    double TIME_LIMIT = 1.9; // seconds
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    XorShift64 rng(seed ^ (uint64_t)(N * 1009 + M * 9176));

    vector<string> bestGrid(N, string(N, '.'));
    int bestC = -1;

    int attempts = 0;
    while (globalTimer.elapsed() < TIME_LIMIT) {
        double remain = TIME_LIMIT - globalTimer.elapsed();
        if (remain < 0.05) break;
        vector<string> g = constructGrid(sList, N, rng, min(remain * 0.9, 0.7));
        int c = countMatches(g, sList);
        if (c > bestC) {
            bestC = c;
            bestGrid = g;
        }
        attempts++;
        if (attempts >= 5) break; // limit attempts for safety
    }

    for (int i = 0; i < N; ++i) {
        cout << bestGrid[i] << '\n';
    }
    return 0;
}