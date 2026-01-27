#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr int BUFSIZE = 1 << 20;
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
    bool readInt(T &out) {
        char c;
        do {
            c = read();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = read();
        }
        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = read();
        }
        out = neg ? -val : val;
        return true;
    }
};

static inline int otherEndpoint(const vector<int>& U, const vector<int>& V, int e, int x) {
    return (U[e] == x) ? V[e] : U[e];
}

static bool validateCover(const vector<int>& U, const vector<int>& V, const vector<char>& inCover) {
    int M = (int)U.size();
    for (int e = 0; e < M; e++) {
        if (!inCover[U[e]] && !inCover[V[e]]) return false;
    }
    return true;
}

static void fixCover(const vector<int>& U, const vector<int>& V, vector<char>& inCover) {
    int M = (int)U.size();
    for (int e = 0; e < M; e++) {
        int u = U[e], v = V[e];
        if (!inCover[u] && !inCover[v]) inCover[u] = 1;
    }
}

static void pruneCover(const vector<int>& U, const vector<int>& V,
                       const vector<vector<int>>& adj, const vector<int>& deg,
                       vector<char>& inCover) {
    int N = (int)inCover.size();
    int M = (int)U.size();

    vector<int> critical(N, 0);
    critical.shrink_to_fit();
    critical.assign(N, 0);

    for (int e = 0; e < M; e++) {
        int a = U[e], b = V[e];
        if (inCover[a] && !inCover[b]) critical[a]++;
        else if (inCover[b] && !inCover[a]) critical[b]++;
    }

    using P = pair<int,int>;
    priority_queue<P, vector<P>, greater<P>> pq;
    for (int v = 0; v < N; v++) {
        if (inCover[v] && critical[v] == 0) pq.push({deg[v], v});
    }

    while (!pq.empty()) {
        auto [d, v] = pq.top();
        pq.pop();
        if (!inCover[v] || critical[v] != 0) continue;

        inCover[v] = 0;
        for (int e : adj[v]) {
            int u = otherEndpoint(U, V, e, v);
            if (inCover[u]) critical[u]++;
        }
    }
}

static int coverSize(const vector<char>& inCover) {
    int s = 0;
    for (char x : inCover) s += (x != 0);
    return s;
}

static vector<char> coverMatchingPruned(const vector<int>& U, const vector<int>& V,
                                       const vector<vector<int>>& adj, const vector<int>& deg) {
    int N = (int)adj.size();
    int M = (int)U.size();
    vector<char> matched(N, 0), inCover(N, 0);

    for (int e = 0; e < M; e++) {
        int a = U[e], b = V[e];
        if (!matched[a] && !matched[b]) {
            matched[a] = matched[b] = 1;
            inCover[a] = inCover[b] = 1;
        }
    }

    pruneCover(U, V, adj, deg, inCover);
    if (!validateCover(U, V, inCover)) {
        fixCover(U, V, inCover);
        pruneCover(U, V, adj, deg, inCover);
    }
    return inCover;
}

static vector<char> coverGreedyDegreePruned(const vector<int>& U, const vector<int>& V,
                                           const vector<vector<int>>& adj, const vector<int>& deg) {
    int N = (int)adj.size();
    int M = (int)U.size();

    vector<char> inCover(N, 0);
    vector<char> coveredEdge(M, 0);
    vector<int> uncoveredDeg = deg;

    priority_queue<pair<int,int>> pq;
    pq = priority_queue<pair<int,int>>();
    for (int v = 0; v < N; v++) pq.push({uncoveredDeg[v], v});

    int uncoveredCount = M;

    auto addVertex = [&](int v) {
        if (inCover[v]) return;
        inCover[v] = 1;
        for (int e : adj[v]) {
            if (coveredEdge[e]) continue;
            coveredEdge[e] = 1;
            uncoveredCount--;
            int u = otherEndpoint(U, V, e, v);
            if (!inCover[u]) {
                uncoveredDeg[u]--;
                pq.push({uncoveredDeg[u], u});
            }
        }
        uncoveredDeg[v] = 0;
    };

    while (uncoveredCount > 0) {
        while (!pq.empty()) {
            int v = pq.top().second;
            int d = pq.top().first;
            if (inCover[v] || d != uncoveredDeg[v]) pq.pop();
            else break;
        }

        if (pq.empty()) {
            // Fallback: pick an endpoint of any uncovered edge
            for (int e = 0; e < M; e++) {
                if (!coveredEdge[e]) {
                    int a = U[e], b = V[e];
                    int pick = (!inCover[a] ? a : b);
                    addVertex(pick);
                    break;
                }
            }
            continue;
        }

        int v = pq.top().second;
        int d = pq.top().first;
        pq.pop();
        if (inCover[v] || d != uncoveredDeg[v]) continue;

        addVertex(v);
    }

    pruneCover(U, V, adj, deg, inCover);
    if (!validateCover(U, V, inCover)) {
        fixCover(U, V, inCover);
        pruneCover(U, V, adj, deg, inCover);
    }
    return inCover;
}

static vector<char> coverStaticMIS(const vector<int>& U, const vector<int>& V,
                                  const vector<vector<int>>& adj, const vector<int>& deg) {
    int N = (int)adj.size();
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] < deg[b];
        return a < b;
    });

    vector<char> banned(N, 0);
    vector<char> chosen(N, 0); // independent set

    for (int v : order) {
        if (banned[v]) continue;
        chosen[v] = 1;
        banned[v] = 1;
        for (int e : adj[v]) {
            int u = otherEndpoint(U, V, e, v);
            banned[u] = 1;
        }
    }

    vector<char> inCover(N, 1);
    for (int i = 0; i < N; i++) if (chosen[i]) inCover[i] = 0;

    if (!validateCover(U, V, inCover)) {
        fixCover(U, V, inCover);
        pruneCover(U, V, adj, deg, inCover);
    }
    return inCover;
}

static vector<char> coverDynamicMinDegMIS(const vector<int>& U, const vector<int>& V,
                                         const vector<vector<int>>& adj, const vector<int>& deg) {
    int N = (int)adj.size();

    vector<char> active(N, 1);
    vector<char> chosen(N, 0);
    vector<int> degAct = deg;

    using P = pair<int,int>;
    priority_queue<P, vector<P>, greater<P>> pq;
    for (int v = 0; v < N; v++) pq.push({degAct[v], v});

    while (!pq.empty()) {
        auto [d, v] = pq.top();
        pq.pop();
        if (!active[v] || d != degAct[v]) continue;

        // select v into independent set
        chosen[v] = 1;
        active[v] = 0;

        // remove neighbors; for each removed vertex, update degrees of remaining active neighbors
        for (int e : adj[v]) {
            int u = otherEndpoint(U, V, e, v);
            if (!active[u]) continue;
            active[u] = 0;

            for (int e2 : adj[u]) {
                int w = otherEndpoint(U, V, e2, u);
                if (!active[w]) continue;
                degAct[w]--;
                pq.push({degAct[w], w});
            }
        }
    }

    vector<char> inCover(N, 1);
    for (int i = 0; i < N; i++) if (chosen[i]) inCover[i] = 0;

    if (!validateCover(U, V, inCover)) {
        fixCover(U, V, inCover);
        pruneCover(U, V, adj, deg, inCover);
    }
    return inCover;
}

int main() {
    FastScanner fs;
    int N, M;
    if (!fs.readInt(N)) return 0;
    fs.readInt(M);

    vector<int> U(M), V(M);
    vector<int> deg(N, 0);

    for (int i = 0; i < M; i++) {
        int a, b;
        fs.readInt(a); fs.readInt(b);
        --a; --b;
        U[i] = a; V[i] = b;
        deg[a]++; deg[b]++;
    }

    vector<vector<int>> adj(N);
    for (int v = 0; v < N; v++) adj[v].reserve(deg[v]);
    for (int e = 0; e < M; e++) {
        adj[U[e]].push_back(e);
        adj[V[e]].push_back(e);
    }

    vector<char> best;
    int bestK = INT_MAX;

    auto consider = [&](vector<char>&& cover) {
        int k = coverSize(cover);
        if (k < bestK) {
            bestK = k;
            best = std::move(cover);
        }
    };

    consider(coverMatchingPruned(U, V, adj, deg));
    consider(coverGreedyDegreePruned(U, V, adj, deg));
    consider(coverStaticMIS(U, V, adj, deg));
    consider(coverDynamicMinDegMIS(U, V, adj, deg));

    if (!validateCover(U, V, best)) {
        fixCover(U, V, best);
        pruneCover(U, V, adj, deg, best);
        if (!validateCover(U, V, best)) {
            best.assign(N, 1);
        }
    }

    string out;
    out.reserve((size_t)N * 2);
    for (int i = 0; i < N; i++) {
        out.push_back(best[i] ? '1' : '0');
        out.push_back('\n');
    }
    fwrite(out.data(), 1, out.size(), stdout);
    return 0;
}