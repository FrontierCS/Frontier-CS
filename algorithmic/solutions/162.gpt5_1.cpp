#include <bits/stdc++.h>
using namespace std;

struct PQItem {
    int key; // -deltaE
    int idx; // edge index
    int gen; // generation of this edge when computed
    bool operator<(const PQItem& other) const {
        return key < other.key; // max-heap by key
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    const int N = 30;
    const int TOT = N * (N + 1) / 2;

    // Row start indices
    static int rowStart[N + 1];
    for (int x = 0; x <= N; ++x) rowStart[x] = x * (x + 1) / 2;
    auto idOf = [&](int x, int y) -> int { return rowStart[x] + y; };

    // id -> (x, y)
    static int id2x[TOT], id2y[TOT];
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y <= x; ++y) {
            int id = idOf(x, y);
            id2x[id] = x;
            id2y[id] = y;
        }
    }

    // Read input and flatten
    static int bval[TOT];
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y <= x; ++y) {
            int t;
            if (!(cin >> t)) t = 0;
            bval[idOf(x, y)] = t;
        }
    }

    // Parents and children per node (at most 2 each)
    static int parentCnt[TOT], childCnt[TOT];
    static int parents[TOT][2];
    static int children[TOT][2];
    for (int id = 0; id < TOT; ++id) {
        parentCnt[id] = childCnt[id] = 0;
    }
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y <= x; ++y) {
            int u = idOf(x, y);
            if (x > 0) {
                if (y - 1 >= 0) parents[u][parentCnt[u]++] = idOf(x - 1, y - 1);
                if (y <= x - 1) parents[u][parentCnt[u]++] = idOf(x - 1, y);
            }
            if (x < N - 1) {
                children[u][childCnt[u]++] = idOf(x + 1, y);
                children[u][childCnt[u]++] = idOf(x + 1, y + 1);
            }
        }
    }

    // Compute initial E
    auto compute_global_E = [&]() -> int {
        int E = 0;
        for (int x = 0; x < N - 1; ++x) {
            for (int y = 0; y <= x; ++y) {
                int p = idOf(x, y);
                int c1 = idOf(x + 1, y);
                int c2 = idOf(x + 1, y + 1);
                if (bval[p] > bval[c1]) ++E;
                if (bval[p] > bval[c2]) ++E;
            }
        }
        return E;
    };
    int Eglobal = compute_global_E();

    // Build adjacency edges (swap candidates)
    struct Edge { int u, v; };
    vector<Edge> edges;
    edges.reserve(3 * N * (N - 1) / 2);
    // Horizontal within rows
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y < x; ++y) {
            int a = idOf(x, y);
            int b = idOf(x, y + 1);
            edges.push_back({a, b});
        }
    }
    // Down-left
    for (int x = 0; x < N - 1; ++x) {
        for (int y = 0; y <= x; ++y) {
            int a = idOf(x, y);
            int b = idOf(x + 1, y);
            edges.push_back({a, b});
        }
    }
    // Down-right
    for (int x = 0; x < N - 1; ++x) {
        for (int y = 0; y <= x; ++y) {
            int a = idOf(x, y);
            int b = idOf(x + 1, y + 1);
            edges.push_back({a, b});
        }
    }
    int M = (int)edges.size();

    // Incident edges per node
    vector<vector<int>> incEdges(TOT);
    for (int i = 0; i < M; ++i) {
        incEdges[edges[i].u].push_back(i);
        incEdges[edges[i].v].push_back(i);
    }

    auto edgeKey = [](int a, int b) -> uint64_t {
        return (uint64_t)((uint64_t)(uint32_t)a << 32) | (uint64_t)(uint32_t)b;
    };

    auto computeDelta = [&](int u, int v) -> int {
        // Collect directed E-edges incident to positions u or v, deduplicated
        uint64_t keys[16];
        int k = 0;
        for (int i = 0; i < parentCnt[u]; ++i) keys[k++] = edgeKey(parents[u][i], u);
        for (int i = 0; i < childCnt[u]; ++i) keys[k++] = edgeKey(u, children[u][i]);
        for (int i = 0; i < parentCnt[v]; ++i) keys[k++] = edgeKey(parents[v][i], v);
        for (int i = 0; i < childCnt[v]; ++i) keys[k++] = edgeKey(v, children[v][i]);
        sort(keys, keys + k);
        int m = (int)(unique(keys, keys + k) - keys);

        int before = 0, after = 0;
        int val_u = bval[u], val_v = bval[v];
        for (int i = 0; i < m; ++i) {
            int a = (int)(keys[i] >> 32);
            int b = (int)(keys[i] & 0xffffffffu);
            int va_bef = bval[a];
            int vb_bef = bval[b];
            if (va_bef > vb_bef) ++before;

            int va_aft = (a == u ? val_v : (a == v ? val_u : bval[a]));
            int vb_aft = (b == u ? val_v : (b == v ? val_u : bval[b]));
            if (va_aft > vb_aft) ++after;
        }
        return after - before;
    };

    // Priority queue for best-improving swap edges
    vector<int> edgeGen(M, 0);
    priority_queue<PQItem> pq;
    pq = priority_queue<PQItem>();
    for (int i = 0; i < M; ++i) {
        int u = edges[i].u, v = edges[i].v;
        int delta = computeDelta(u, v);
        pq.push(PQItem{ -delta, i, edgeGen[i] });
    }

    // Helpers for updating neighborhood
    static int nodeSeen[TOT];
    static int edgeSeen[5000]; // M ~ 1305, so 5000 is safe
    int nodeStamp = 1;
    int edgeStamp = 1;
    auto addNode = [&](vector<int>& nodes, int w) {
        if (nodeSeen[w] != nodeStamp) { nodeSeen[w] = nodeStamp; nodes.push_back(w); }
    };
    auto updateNeighborhoodEdges = [&](int u, int v) {
        nodeStamp++;
        vector<int> nodes; nodes.reserve(16);
        addNode(nodes, u);
        addNode(nodes, v);
        for (int i = 0; i < parentCnt[u]; ++i) addNode(nodes, parents[u][i]);
        for (int i = 0; i < childCnt[u]; ++i) addNode(nodes, children[u][i]);
        for (int i = 0; i < parentCnt[v]; ++i) addNode(nodes, parents[v][i]);
        for (int i = 0; i < childCnt[v]; ++i) addNode(nodes, children[v][i]);

        edgeStamp++;
        for (int w : nodes) {
            for (int ei : incEdges[w]) {
                if (edgeSeen[ei] == edgeStamp) continue;
                edgeSeen[ei] = edgeStamp;
                int a = edges[ei].u, b = edges[ei].v;
                int delta = computeDelta(a, b);
                edgeGen[ei]++;
                pq.push(PQItem{ -delta, ei, edgeGen[ei] });
            }
        }
    };

    // Random generator for shake moves
    std::mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    auto randEdgeIndex = [&]() -> int {
        return (int)(rng() % (uint64_t)M);
    };
    auto randProb = [&]() -> double {
        return (double)(rng() % 1000000) / 1000000.0;
    };

    // Operations storage
    struct Op { int x1, y1, x2, y2; };
    vector<Op> ops; ops.reserve(10000);

    // Main loop
    const int K_LIMIT = 10000;
    int K = 0;

    auto applySwap = [&](int ei, int precomputedDelta) {
        int u = edges[ei].u, v = edges[ei].v;
        // Record operation
        ops.push_back({ id2x[u], id2y[u], id2x[v], id2y[v] });
        // Update E
        Eglobal += precomputedDelta;
        // Swap values
        int vu = bval[u], vv = bval[v];
        bval[u] = vv;
        bval[v] = vu;
        // Update neighborhood PQ entries
        updateNeighborhoodEdges(u, v);
        ++K;
    };

    while (K < K_LIMIT) {
        // Pop best current item
        PQItem top;
        bool hasTop = false;
        while (!pq.empty()) {
            top = pq.top(); pq.pop();
            if (top.gen != edgeGen[top.idx]) continue;
            hasTop = true;
            break;
        }
        if (hasTop && top.key > 0) {
            int ei = top.idx;
            int delta = -top.key; // E_after - E_before (negative means improvement)
            applySwap(ei, delta);
            continue;
        }

        // No improving move found; try shaking with non-worsening moves
        bool moved = false;
        int attempts = 400; // limited shakes
        for (int t = 0; t < attempts && K < K_LIMIT; ++t) {
            int ei = randEdgeIndex();
            int u = edges[ei].u, v = edges[ei].v;
            int delta = computeDelta(u, v);
            // Accept non-worsening; occasionally accept small worsening
            bool accept = false;
            if (delta <= 0) accept = true;
            else if (delta == 1 && randProb() < 0.02) accept = true; // small chance
            else if (delta == 2 && randProb() < 0.001) accept = true;

            if (accept) {
                applySwap(ei, delta);
                moved = true;
                break;
            }
        }
        if (!moved) break; // stuck
    }

    // Output
    cout << K << '\n';
    for (int i = 0; i < K; ++i) {
        cout << ops[i].x1 << ' ' << ops[i].y1 << ' ' << ops[i].x2 << ' ' << ops[i].y2 << '\n';
    }
    return 0;
}