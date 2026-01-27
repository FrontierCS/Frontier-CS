#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline char readChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') { neg = true; c = readChar(); }

        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readChar();
        }
        out = neg ? -val : val;
        return true;
    }
};

static inline bool isAdjacent(const vector<vector<int>> &adj, int a, int b) {
    const auto &A = adj[a];
    const auto &B = adj[b];
    if (A.size() < B.size()) return binary_search(A.begin(), A.end(), b);
    return binary_search(B.begin(), B.end(), a);
}

static vector<char> greedyMIS(const vector<vector<int>> &adj, const vector<int> &deg, mt19937_64 &rng) {
    int n = (int)adj.size() - 1;
    vector<int> order(n);
    iota(order.begin(), order.end(), 1);

    vector<uint32_t> rnd(n + 1);
    for (int i = 1; i <= n; i++) rnd[i] = (uint32_t)rng();

    sort(order.begin(), order.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] < deg[b];
        return rnd[a] < rnd[b];
    });

    vector<unsigned char> state(n + 1, 0); // 0=free, 1=in IS, 2=blocked
    for (int v : order) {
        if (state[v] != 0) continue;
        state[v] = 1;
        for (int u : adj[v]) if (state[u] == 0) state[u] = 2;
    }

    vector<char> inIS(n + 1, 0);
    for (int i = 1; i <= n; i++) inIS[i] = (state[i] == 1);
    return inIS;
}

static void makeIndependentAndMaximal(const vector<vector<int>> &adj, vector<char> &inIS) {
    int n = (int)adj.size() - 1;

    // Enforce independence by breaking any conflicts.
    for (int v = 1; v <= n; v++) {
        if (!inIS[v]) continue;
        for (int u : adj[v]) {
            if (u <= v) continue;
            if (!inIS[v] || !inIS[u]) continue;
            int rem = (adj[v].size() > adj[u].size()) ? v : u;
            inIS[rem] = 0;
            if (rem == v) break;
        }
    }

    // Recompute counts and greedily add any vertex with 0 IS-neighbors (maximality).
    vector<int> cnt(n + 1, 0);
    for (int v = 1; v <= n; v++) if (inIS[v]) {
        for (int u : adj[v]) cnt[u]++;
    }

    vector<int> q;
    q.reserve(n);
    for (int v = 1; v <= n; v++) if (!inIS[v] && cnt[v] == 0) q.push_back(v);

    while (!q.empty()) {
        int v = q.back();
        q.pop_back();
        if (inIS[v] || cnt[v] != 0) continue;
        inIS[v] = 1;
        for (int u : adj[v]) cnt[u]++;
        // No need to push neighbors; only vertices that might become 0 are those losing IS neighbors, which doesn't happen here.
    }
}

static void localImprove12Swap(const vector<vector<int>> &adj, vector<char> &inIS, mt19937_64 &rng,
                              chrono::steady_clock::time_point start, double timeLimitSec) {
    int n = (int)adj.size() - 1;

    vector<int> cnt(n + 1, 0);
    for (int v = 1; v <= n; v++) if (inIS[v]) {
        for (int u : adj[v]) cnt[u]++;
    }

    vector<int> q;
    q.reserve(n);

    auto addToIS = [&](int v) {
        inIS[v] = 1;
        for (int u : adj[v]) cnt[u]++;
    };
    auto removeFromIS = [&](int v) {
        inIS[v] = 0;
        for (int u : adj[v]) {
            cnt[u]--;
            if (!inIS[u] && cnt[u] == 0) q.push_back(u);
        }
    };
    auto processQueue = [&]() {
        while (!q.empty()) {
            int v = q.back();
            q.pop_back();
            if (inIS[v] || cnt[v] != 0) continue;
            addToIS(v);
        }
    };
    auto timeExceeded = [&]() -> bool {
        double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start).count();
        return elapsed > timeLimitSec;
    };

    int swaps = 0;
    const int maxSwaps = 600;

    while (!timeExceeded() && swaps < maxSwaps) {
        bool improved = false;
        vector<int> isVerts;
        isVerts.reserve(n);
        for (int v = 1; v <= n; v++) if (inIS[v]) isVerts.push_back(v);
        shuffle(isVerts.begin(), isVerts.end(), rng);

        for (int x : isVerts) {
            if (timeExceeded()) break;
            if (!inIS[x]) continue;

            vector<int> cand;
            cand.reserve(adj[x].size());
            for (int u : adj[x]) if (!inIS[u] && cnt[u] == 1) cand.push_back(u);
            if ((int)cand.size() < 2) continue;

            sort(cand.begin(), cand.end(), [&](int a, int b) {
                if (adj[a].size() != adj[b].size()) return adj[a].size() < adj[b].size();
                return a < b;
            });

            int limI = min<int>(cand.size(), 28);
            int limJ = min<int>(cand.size(), 180);

            int a = -1, b = -1;
            for (int i = 0; i < limI && a == -1; i++) {
                int va = cand[i];
                for (int j = i + 1; j < limJ; j++) {
                    int vb = cand[j];
                    if (!isAdjacent(adj, va, vb)) { a = va; b = vb; break; }
                }
            }
            if (a == -1) continue;

            // Swap: remove x, add a and b, then greedily add newly free vertices.
            q.clear();
            removeFromIS(x);

            // After removal, a and b should have cnt==0 (since their only IS neighbor was x).
            if (inIS[a] || inIS[b] || cnt[a] != 0 || cnt[b] != 0 || isAdjacent(adj, a, b)) {
                // Shouldn't happen; repair by rebuilding to a clean maximal independent set state.
                makeIndependentAndMaximal(adj, inIS);
                for (int v = 1; v <= n; v++) cnt[v] = 0;
                for (int v = 1; v <= n; v++) if (inIS[v]) for (int u : adj[v]) cnt[u]++;
                improved = true;
                swaps++;
                break;
            }

            addToIS(a);
            addToIS(b);
            processQueue();

            improved = true;
            swaps++;
            break;
        }

        if (!improved) break;
    }

    makeIndependentAndMaximal(adj, inIS);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int N;
    int M;
    if (!fs.readInt(N)) return 0;
    fs.readInt(M);

    vector<vector<int>> adj(N + 1);
    vector<int> deg(N + 1, 0);
    adj.reserve(N + 1);

    for (int i = 0; i < M; i++) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
        deg[u]++; deg[v]++;
    }

    for (int i = 1; i <= N; i++) {
        auto &v = adj[i];
        sort(v.begin(), v.end());
        v.erase(unique(v.begin(), v.end()), v.end());
        deg[i] = (int)v.size();
    }

    mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());
    auto start = chrono::steady_clock::now();

    vector<char> bestIS(N + 1, 0);
    int bestSize = -1;

    int maxTrials = 25;
    for (int t = 0; t < maxTrials; t++) {
        double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start).count();
        if (elapsed > 0.75) break;

        vector<char> inIS = greedyMIS(adj, deg, rng);
        int sz = 0;
        for (int i = 1; i <= N; i++) sz += inIS[i] ? 1 : 0;
        if (sz > bestSize) {
            bestSize = sz;
            bestIS.swap(inIS);
        }
    }

    makeIndependentAndMaximal(adj, bestIS);

    localImprove12Swap(adj, bestIS, rng, start, 1.85);

    // Output vertex cover: complement of independent set
    string out;
    out.reserve((size_t)N * 2);
    for (int i = 1; i <= N; i++) {
        out.push_back(bestIS[i] ? '0' : '1');
        out.push_back('\n');
    }
    cout << out;
    return 0;
}