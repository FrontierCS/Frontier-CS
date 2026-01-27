#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 1024;

struct FastScanner {
    static inline int getChar() {
#ifdef _WIN32
        return getchar();
#else
        return getchar_unlocked();
#endif
    }
    template<typename T>
    bool readInt(T& out) {
        int c = getChar();
        if (c == EOF) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (c == EOF) return false;
        }
        T sign = 1;
        if (c == '-') { sign = -1; c = getChar(); }
        T val = 0;
        for (; c >= '0' && c <= '9'; c = getChar()) val = val * 10 + (c - '0');
        out = val * sign;
        return true;
    }
} In;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!In.readInt(N)) return 0;
    In.readInt(M);

    vector< bitset<MAXN> > g(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        In.readInt(u);
        In.readInt(v);
        --u; --v;
        if (u == v) continue;
        g[u].set(v);
        g[v].set(u);
    }

    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = (int)g[i].count();

    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT_SEC = 1.90;

    vector<int> bestClique;
    int bestSize = 0;

    auto timeElapsed = [&](){
        chrono::duration<double> diff = chrono::steady_clock::now() - start;
        return diff.count();
    };

    auto build_from_seed = [&](int seed, bool randomized)->vector<int> {
        vector<int> clique;
        clique.reserve(N);
        bitset<MAXN> cand = g[seed];
        clique.push_back(seed);

        while (cand.any()) {
            if ((int)clique.size() + (int)cand.count() <= bestSize) break;

            int next_v = -1;
            if (!randomized) {
                int bestScore = -1, bestDeg = -1;
                for (int v = 0; v < N; ++v) if (cand.test(v)) {
                    int sc = (int)(g[v] & cand).count();
                    if (sc > bestScore || (sc == bestScore && deg[v] > bestDeg)) {
                        bestScore = sc; bestDeg = deg[v]; next_v = v;
                    }
                }
            } else {
                // GRASP: choose randomly among top R candidates by score
                const int R = 6;
                // Maintain top R as (score, deg, vertex)
                array<int, R> topScore; topScore.fill(INT_MIN);
                array<int, R> topDeg; topDeg.fill(INT_MIN);
                array<int, R> topV; topV.fill(-1);

                for (int v = 0; v < N; ++v) if (cand.test(v)) {
                    int sc = (int)(g[v] & cand).count();
                    // find position of minimum in current top
                    int minPos = 0;
                    for (int i = 1; i < R; ++i) {
                        if (topScore[i] < topScore[minPos] ||
                           (topScore[i] == topScore[minPos] && topDeg[i] < topDeg[minPos])) {
                            minPos = i;
                        }
                    }
                    if (sc > topScore[minPos] || (sc == topScore[minPos] && deg[v] > topDeg[minPos])) {
                        topScore[minPos] = sc;
                        topDeg[minPos] = deg[v];
                        topV[minPos] = v;
                    }
                }
                // collect valid entries
                vector<pair<int,int>> candList;
                candList.reserve(R);
                for (int i = 0; i < R; ++i) if (topV[i] != -1) candList.emplace_back(topScore[i], topV[i]);
                if (candList.empty()) break;
                // choose among top few
                // sort descending by score to ensure best are first
                sort(candList.begin(), candList.end(), [&](const pair<int,int>& A, const pair<int,int>& B){
                    if (A.first != B.first) return A.first > B.first;
                    return deg[A.second] > deg[B.second];
                });
                int take = (int)candList.size();
                if (take > 3) take = 3; // restrict randomness to top 3
                static thread_local mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count() ^ (uint64_t)(uintptr_t)&rng);
                uniform_int_distribution<int> dist(0, take - 1);
                next_v = candList[dist(rng)].second;
            }

            if (next_v == -1) break;
            clique.push_back(next_v);
            cand &= g[next_v];
        }

        return clique;
    };

    // Stage 1: deterministic seeds by degree
    for (int idx = 0; idx < N; ++idx) {
        if (timeElapsed() > TIME_LIMIT_SEC) break;
        int v = order[idx];
        if (deg[v] + 1 <= bestSize) break; // further seeds won't help as order is by non-increasing degree
        vector<int> cur = build_from_seed(v, false);
        if ((int)cur.size() > bestSize) {
            bestSize = (int)cur.size();
            bestClique = move(cur);
        }
    }

    // Stage 2: randomized GRASP restarts
    {
        static thread_local mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count() ^ 0x9e3779b97f4a7c15ULL);
        vector<int> topSeeds;
        int T = min(N, 200);
        topSeeds.reserve(T);
        for (int i = 0; i < T; ++i) topSeeds.push_back(order[i]);
        uniform_int_distribution<int> dist(0, (int)topSeeds.size() - 1);

        while (timeElapsed() < TIME_LIMIT_SEC) {
            int seed = topSeeds[dist(rng)];
            if (deg[seed] + 1 <= bestSize) {
                // Try another seed that may still tie or match; but we focus on improving, break if many are below bound
                // Continue to sample a few times
                bool found = false;
                for (int t = 0; t < 3; ++t) {
                    int s2 = topSeeds[dist(rng)];
                    if (deg[s2] + 1 > bestSize) { seed = s2; found = true; break; }
                }
                if (!found && timeElapsed() > TIME_LIMIT_SEC) break;
            }
            vector<int> cur = build_from_seed(seed, true);
            if ((int)cur.size() > bestSize) {
                bestSize = (int)cur.size();
                bestClique = move(cur);
            }
        }
    }

    vector<int> ans(N, 0);
    for (int v : bestClique) ans[v] = 1;

    // Fallback: ensure at least one vertex selected
    if (bestSize == 0) {
        int mx = max_element(deg.begin(), deg.end()) - deg.begin();
        ans[mx] = 1;
    }

    // Output
    for (int i = 0; i < N; ++i) {
        cout << ans[i] << '\n';
    }
    return 0;
}