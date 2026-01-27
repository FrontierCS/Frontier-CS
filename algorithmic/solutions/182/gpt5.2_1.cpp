#include <bits/stdc++.h>
using namespace std;

class FastScanner {
    static constexpr int BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char readChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

public:
    bool readInt(int &out) {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        int sign = 1;
        if (c == '-') {
            sign = -1;
            c = readChar();
        }

        int val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readChar();
        }
        out = val * sign;
        return true;
    }
};

struct Graph {
    int N, M;
    vector<int> U, V;
    vector<int> deg;          // 1..N
    vector<int> start;        // 1..N+1 (CSR offsets)
    vector<int> adjEdgeIdx;   // size 2M, stores edge index for each incidence
};

static inline int otherEndpoint(const Graph& g, int e, int x) {
    int a = g.U[e], b = g.V[e];
    return (a == x) ? b : a;
}

static int coverSize(const vector<char>& inCover) {
    int s = 0;
    for (size_t i = 1; i < inCover.size(); i++) s += (inCover[i] != 0);
    return s;
}

static bool validateCover(const Graph& g, const vector<char>& inCover) {
    for (int i = 0; i < g.M; i++) {
        if (!inCover[g.U[i]] && !inCover[g.V[i]]) return false;
    }
    return true;
}

static void fixCover(const Graph& g, vector<char>& inCover) {
    for (int i = 0; i < g.M; i++) {
        int u = g.U[i], v = g.V[i];
        if (!inCover[u] && !inCover[v]) {
            int pick = (g.deg[u] >= g.deg[v]) ? u : v;
            inCover[pick] = 1;
        }
    }
}

static void pruneCover(const Graph& g, vector<char>& inCover) {
    vector<uint8_t> coverCnt(g.M);
    for (int i = 0; i < g.M; i++) {
        coverCnt[i] = (uint8_t)((inCover[g.U[i]] ? 1 : 0) + (inCover[g.V[i]] ? 1 : 0));
    }

    vector<int> order;
    order.reserve(g.N);
    for (int v = 1; v <= g.N; v++) if (inCover[v]) order.push_back(v);

    sort(order.begin(), order.end(), [&](int a, int b) {
        if (g.deg[a] != g.deg[b]) return g.deg[a] < g.deg[b];
        return a < b;
    });

    for (int v : order) {
        if (!inCover[v]) continue;

        bool removable = true;
        for (int k = g.start[v]; k < g.start[v + 1]; k++) {
            int e = g.adjEdgeIdx[k];
            if (coverCnt[e] != 2) { removable = false; break; }
        }

        if (removable) {
            inCover[v] = 0;
            for (int k = g.start[v]; k < g.start[v + 1]; k++) {
                int e = g.adjEdgeIdx[k];
                if (coverCnt[e] > 0) coverCnt[e]--;
            }
        }
    }
}

static vector<char> coverByMaximalMatching(const Graph& g) {
    vector<char> inCover(g.N + 1, 0), matched(g.N + 1, 0);

    for (int i = 0; i < g.M; i++) {
        int u = g.U[i], v = g.V[i];
        if (!matched[u] && !matched[v]) {
            matched[u] = matched[v] = 1;
            inCover[u] = inCover[v] = 1;
        }
    }

    pruneCover(g, inCover);
    if (!validateCover(g, inCover)) {
        fixCover(g, inCover);
        pruneCover(g, inCover);
    }
    return inCover;
}

static vector<char> coverByIndependentSetComplement(const Graph& g) {
    vector<int> order(g.N);
    for (int i = 0; i < g.N; i++) order[i] = i + 1;

    sort(order.begin(), order.end(), [&](int a, int b) {
        if (g.deg[a] != g.deg[b]) return g.deg[a] < g.deg[b];
        return a < b;
    });

    vector<uint8_t> state(g.N + 1, 0); // 0=free, 1=in IS, 2=blocked
    for (int v : order) {
        if (state[v] != 0) continue;
        state[v] = 1;
        for (int k = g.start[v]; k < g.start[v + 1]; k++) {
            int e = g.adjEdgeIdx[k];
            int u = otherEndpoint(g, e, v);
            if (state[u] == 0) state[u] = 2;
        }
    }

    vector<char> inCover(g.N + 1, 1);
    for (int v = 1; v <= g.N; v++) if (state[v] == 1) inCover[v] = 0;

    if (!validateCover(g, inCover)) {
        fixCover(g, inCover);
        pruneCover(g, inCover);
    }
    return inCover;
}

static vector<char> coverByGreedyUncoveredDegree(const Graph& g) {
    vector<char> inCover(g.N + 1, 0);
    vector<int> degU = g.deg;
    vector<char> edgeCovered(g.M, 0);
    int remaining = g.M;

    priority_queue<pair<int,int>> pq;
    for (int v = 1; v <= g.N; v++) pq.push({degU[v], v});

    while (remaining > 0) {
        if (pq.empty()) break;

        auto [d, v] = pq.top();
        pq.pop();

        if (inCover[v]) continue;
        if (d != degU[v]) continue;

        if (d == 0) {
            int eFound = -1;
            for (int i = 0; i < g.M; i++) {
                if (!edgeCovered[i]) { eFound = i; break; }
            }
            if (eFound == -1) break;
            int a = g.U[eFound], b = g.V[eFound];
            v = (degU[a] >= degU[b]) ? a : b;
            if (inCover[v]) continue;
        }

        inCover[v] = 1;
        for (int k = g.start[v]; k < g.start[v + 1]; k++) {
            int e = g.adjEdgeIdx[k];
            if (!edgeCovered[e]) {
                edgeCovered[e] = 1;
                remaining--;
                int u = otherEndpoint(g, e, v);
                if (!inCover[u]) {
                    degU[u]--;
                    pq.push({degU[u], u});
                }
            }
        }
        degU[v] = 0;
    }

    if (remaining > 0) {
        fixCover(g, inCover);
    }
    pruneCover(g, inCover);
    if (!validateCover(g, inCover)) {
        fixCover(g, inCover);
        pruneCover(g, inCover);
    }
    return inCover;
}

int main() {
    FastScanner fs;
    int N, M;
    if (!fs.readInt(N)) return 0;
    fs.readInt(M);

    Graph g;
    g.N = N; g.M = M;
    g.U.resize(M);
    g.V.resize(M);
    g.deg.assign(N + 2, 0);

    for (int i = 0; i < M; i++) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        g.U[i] = u;
        g.V[i] = v;
        g.deg[u]++;
        g.deg[v]++;
    }

    g.start.assign(N + 3, 0);
    for (int v = 1; v <= N; v++) g.start[v + 1] = g.start[v] + g.deg[v];

    g.adjEdgeIdx.assign(2 * M, 0);
    vector<int> cur = g.start;
    for (int i = 0; i < M; i++) {
        int u = g.U[i], v = g.V[i];
        g.adjEdgeIdx[cur[u]++] = i;
        g.adjEdgeIdx[cur[v]++] = i;
    }

    vector<char> covA = coverByMaximalMatching(g);
    vector<char> covB = coverByIndependentSetComplement(g);
    vector<char> covC = coverByGreedyUncoveredDegree(g);

    int sA = coverSize(covA);
    int sB = coverSize(covB);
    int sC = coverSize(covC);

    vector<char>* best = &covA;
    int bestS = sA;

    if (sB < bestS) { bestS = sB; best = &covB; }
    if (sC < bestS) { bestS = sC; best = &covC; }

    vector<char> ans = *best;
    if (!validateCover(g, ans)) {
        fixCover(g, ans);
        pruneCover(g, ans);
        if (!validateCover(g, ans)) fixCover(g, ans);
    }

    string out;
    out.reserve((size_t)N * 2);
    for (int i = 1; i <= N; i++) {
        out.push_back(ans[i] ? '1' : '0');
        out.push_back('\n');
    }
    fwrite(out.data(), 1, out.size(), stdout);
    return 0;
}