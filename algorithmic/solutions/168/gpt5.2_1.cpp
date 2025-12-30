#include <bits/stdc++.h>
using namespace std;

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed = 0) : x(seed) {}
    uint64_t nextU64() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint32_t nextU32() { return (uint32_t)nextU64(); }
    int nextInt(int bound) { return (int)(nextU64() % (uint64_t)bound); }
    double nextDouble() { // [0,1)
        return (nextU64() >> 11) * (1.0 / 9007199254740992.0);
    }
};

static const int HMAX = 10;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, H;
    cin >> N >> M >> H;
    vector<int> A(N);
    for (int i = 0; i < N; i++) cin >> A[i];

    vector<vector<int>> g(N);
    g.reserve(N);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        g[u].push_back(v);
        g[v].push_back(u);
    }
    for (int i = 0; i < N; i++) {
        int x, y;
        cin >> x >> y;
    }

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    SplitMix64 rng(seed);

    vector<int> depth(N, -1);

    int root = 0;
    for (int i = 1; i < N; i++) if (A[i] < A[root]) root = i;

    depth[root] = 0;
    vector<int> st;
    st.reserve(N);
    st.push_back(root);

    while (!st.empty()) {
        int v = st.back();
        int best = -1;
        int bestA = -1;
        for (int u : g[v]) {
            if (depth[u] != -1) continue;
            if (A[u] > bestA) {
                bestA = A[u];
                best = u;
            }
        }
        if (best == -1) {
            st.pop_back();
            continue;
        }
        int u = best;
        if (depth[v] < H) depth[u] = depth[v] + 1;
        else depth[u] = 0;
        st.push_back(u);
    }

    for (int i = 0; i < N; i++) if (depth[i] == -1) depth[i] = 0;

    vector<array<int, HMAX + 1>> cnt(N);
    for (int i = 0; i < N; i++) cnt[i].fill(0);

    auto recomputeCnt = [&]() {
        for (int i = 0; i < N; i++) cnt[i].fill(0);
        for (int v = 0; v < N; v++) {
            for (int u : g[v]) {
                if (u < v) continue;
                if (depth[v] < H) cnt[u][depth[v] + 1]++;
                if (depth[u] < H) cnt[v][depth[u] + 1]++;
            }
        }
    };

    recomputeCnt();

    long long curScore = 0;
    for (int i = 0; i < N; i++) curScore += 1LL * (depth[i] + 1) * A[i];

    auto setDepth = [&](int v, int nd) {
        int od = depth[v];
        if (od == nd) return;
        for (int u : g[v]) {
            if (od < H) cnt[u][od + 1]--;
            if (nd < H) cnt[u][nd + 1]++;
        }
        depth[v] = nd;
        curScore += 1LL * (nd - od) * A[v];
    };

    auto fixAll = [&]() {
        deque<int> q;
        vector<char> inq(N, 0);
        for (int i = 0; i < N; i++) {
            q.push_back(i);
            inq[i] = 1;
        }
        while (!q.empty()) {
            int v = q.front();
            q.pop_front();
            inq[v] = 0;
            if (depth[v] == 0) continue;
            if (cnt[v][depth[v]] > 0) continue;
            int k = depth[v];
            while (k > 0 && cnt[v][k] == 0) k--;
            if (k != depth[v]) {
                setDepth(v, k);
                for (int u : g[v]) if (!inq[u]) {
                    inq[u] = 1;
                    q.push_back(u);
                }
            }
        }
    };

    fixAll();

    long long bestScore = curScore;
    vector<int> bestDepth = depth;

    auto start = chrono::high_resolution_clock::now();
    const double timeLimitSec = 1.9;
    const double T0 = 2000.0, T1 = 10.0;

    vector<pair<int,int>> changed;
    changed.reserve(256);

    auto recordSetDepth = [&](int v, int nd) {
        changed.push_back({v, depth[v]});
        setDepth(v, nd);
    };

    vector<int> q;
    q.reserve(512);

    long long iter = 0;
    while (true) {
        iter++;
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed >= timeLimitSec) break;
        double t = elapsed / timeLimitSec;
        double Temp = T0 * (1.0 - t) + T1 * t;

        int v = rng.nextInt(N);
        int od = depth[v];

        int nd = od;
        int r = rng.nextInt(100);
        if (r < 70) {
            if (od < H && cnt[v][od + 1] > 0) nd = od + 1;
            else continue;
        } else if (r < 85) {
            if (od > 0) nd = od - 1;
            else continue;
        } else {
            int cand[HMAX + 1];
            int cc = 0;
            cand[cc++] = 0;
            for (int d = 1; d <= H; d++) if (cnt[v][d] > 0) cand[cc++] = d;
            nd = cand[rng.nextInt(cc)];
            if (nd == od) continue;
        }

        long long before = curScore;
        changed.clear();

        recordSetDepth(v, nd);

        q.clear();
        for (int u : g[v]) q.push_back(u);

        for (size_t head = 0; head < q.size(); head++) {
            int w = q[head];
            if (depth[w] == 0) continue;
            if (cnt[w][depth[w]] > 0) continue;
            int k = depth[w];
            while (k > 0 && cnt[w][k] == 0) k--;
            if (k != depth[w]) {
                recordSetDepth(w, k);
                for (int u : g[w]) q.push_back(u);
            }
        }

        long long after = curScore;
        long long delta = after - before;

        bool accept = false;
        if (delta >= 0) accept = true;
        else {
            double prob = exp((double)delta / Temp);
            if (rng.nextDouble() < prob) accept = true;
        }

        if (!accept) {
            for (int i = (int)changed.size() - 1; i >= 0; i--) {
                setDepth(changed[i].first, changed[i].second);
            }
        } else {
            if (curScore > bestScore) {
                bestScore = curScore;
                bestDepth = depth;
            }
        }
    }

    depth = bestDepth;

    vector<int> parent(N, -1);
    for (int v = 0; v < N; v++) {
        if (depth[v] == 0) {
            parent[v] = -1;
            continue;
        }
        int want = depth[v] - 1;
        int best = -1, bestAv = -1;
        for (int u : g[v]) {
            if (depth[u] == want) {
                if (A[u] > bestAv) {
                    bestAv = A[u];
                    best = u;
                }
            }
        }
        parent[v] = best; // if -1, treated as root
    }

    for (int i = 0; i < N; i++) {
        if (i) cout << ' ';
        cout << parent[i];
    }
    cout << '\n';
    return 0;
}