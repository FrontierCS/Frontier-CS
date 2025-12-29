#include <bits/stdc++.h>
using namespace std;

struct XorShift64 {
    uint64_t x;
    XorShift64(uint64_t seed = 88172645463325252ull) : x(seed) {}
    uint64_t nextU64() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    uint32_t nextU32() { return (uint32_t)nextU64(); }
    int nextInt(int n) { return (int)(nextU64() % (uint64_t)n); }
};

static inline long long now_us() {
    using namespace std::chrono;
    return duration_cast<microseconds>(steady_clock::now().time_since_epoch()).count();
}

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
    // coordinates not used
    for (int i = 0; i < N; i++) {
        int x, y;
        cin >> x >> y;
    }

    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    stable_sort(order.begin(), order.end(), [&](int i, int j) {
        if (A[i] != A[j]) return A[i] < A[j];
        return i < j;
    });

    int K = min(50, N);

    XorShift64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count() * 1181783497276652981ull);

    auto build = [&](int root, double eps, vector<int>& outPar, long long &outScore) {
        vector<int> par(N, -1), dep(N, 0);
        vector<unsigned char> vis(N, 0);

        vector<int> st;
        st.reserve(N);

        auto start_component = [&](int r) {
            vis[r] = 1;
            par[r] = -1;
            dep[r] = 0;
            st.clear();
            st.push_back(r);
            while (!st.empty()) {
                int v = st.back();
                int childDepth = dep[v] + 1;
                int coeff = (childDepth % (H + 1)) + 1;

                int best = -1;
                long long bestScore = LLONG_MIN;
                vector<int> cand;
                cand.reserve(g[v].size());
                for (int u : g[v]) {
                    if (vis[u]) continue;
                    cand.push_back(u);
                    long long s = 1000LL * (long long)coeff * (long long)A[u] + (long long)(rng.nextU32() % 1000u);
                    if (s > bestScore) {
                        bestScore = s;
                        best = u;
                    }
                }

                if (best == -1) {
                    st.pop_back();
                    continue;
                }

                bool takeRandom = (rng.nextU32() % 1000u) < (uint32_t)(eps * 1000.0);
                int nxt = best;
                if (takeRandom && !cand.empty()) nxt = cand[rng.nextInt((int)cand.size())];

                vis[nxt] = 1;
                par[nxt] = v;
                dep[nxt] = dep[v] + 1;
                st.push_back(nxt);
            }
        };

        start_component(root);
        // Robustness: if somehow not all visited, start new components with low beauty nodes.
        for (int idx : order) {
            if (!vis[idx]) start_component(idx);
        }

        long long score = 0;
        vector<int> resPar(N, -1);
        for (int v = 0; v < N; v++) {
            int d = dep[v] % (H + 1);
            score += (long long)(d + 1) * (long long)A[v];
            if (d == 0) resPar[v] = -1;
            else resPar[v] = par[v];
        }

        outPar.swap(resPar);
        outScore = score;
    };

    vector<int> bestPar(N, -1);
    long long bestScore = -1;

    long long start = now_us();
    const long long TIME_LIMIT_US = 1850000; // ~1.85 sec

    int attempt = 0;
    while (now_us() - start < TIME_LIMIT_US) {
        attempt++;
        int root;
        if (attempt == 1) root = order[0];
        else {
            int pick = rng.nextInt(K);
            root = order[pick];
        }

        double eps = (attempt <= 5 ? 0.02 : 0.10);
        vector<int> par;
        long long score;
        build(root, eps, par, score);
        if (score > bestScore) {
            bestScore = score;
            bestPar = std::move(par);
        }
    }

    for (int i = 0; i < N; i++) {
        if (i) cout << ' ';
        cout << bestPar[i];
    }
    cout << '\n';
    return 0;
}