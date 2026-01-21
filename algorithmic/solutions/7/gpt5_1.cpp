#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int to, w;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int L, R;
    if (!(cin >> L >> R)) return 0;

    // Graph: 1-indexed nodes
    vector<vector<Edge>> g(1); // g[0] unused

    auto addNode = [&]() -> int {
        g.push_back({});
        return (int)g.size() - 1;
    };
    auto addEdge = [&](int u, int v, int w) {
        g[u].push_back({v, w});
    };

    auto getBits = [&](int x) -> vector<int> {
        vector<int> b;
        while (x > 0) {
            b.push_back(x & 1);
            x >>= 1;
        }
        reverse(b.begin(), b.end());
        if (b.empty()) b.push_back(0);
        return b;
    };

    vector<int> Lbits = getBits(L);
    vector<int> Rbits = getBits(R);
    int kL = (int)Lbits.size();
    int kR = (int)Rbits.size();

    int start = addNode(); // node 1

    // A[k]: node representing "k free bits remaining" (exactly k edges to sink), A[0] is sink placeholder 0
    vector<int> A(1, -1); // we'll resize dynamically; A[0] will be 0 (placeholder for sink)
    function<int(int)> getA = [&](int k) -> int {
        if (k == 0) return 0; // placeholder for sink
        if ((int)A.size() <= k) A.resize(k + 1, -1);
        if (A[k] != -1) return A[k];
        int child = getA(k - 1);
        int u = addNode();
        A[k] = u;
        addEdge(u, child, 0);
        addEdge(u, child, 1);
        return u;
    };

    // Lower-bound DP (length = kL), states indexed by idx (next bit position), tight to L
    int lowK = 0;
    vector<int> lowerMemo;
    vector<int>* pLbits = nullptr;
    function<int(int)> lowerNode;

    lowerNode = [&](int idx) -> int {
        if (idx == lowK) return getA(0);
        if (lowerMemo[idx] != -1) return lowerMemo[idx];
        int u = addNode();
        lowerMemo[idx] = u;
        int lb = (*pLbits)[idx];
        if (lb == 0) {
            addEdge(u, lowerNode(idx + 1), 0);
            addEdge(u, getA(lowK - idx - 1), 1);
        } else {
            addEdge(u, lowerNode(idx + 1), 1);
        }
        return u;
    };

    // Upper-bound DP (length = kR), states indexed by idx (next bit position), tight to R
    int upK = 0;
    vector<int> upperMemo;
    vector<int>* pRbits = nullptr;
    function<int(int)> upperNode;

    upperNode = [&](int idx) -> int {
        if (idx == upK) return getA(0);
        if (upperMemo[idx] != -1) return upperMemo[idx];
        int u = addNode();
        upperMemo[idx] = u;
        int rb = (*pRbits)[idx];
        if (rb == 0) {
            addEdge(u, upperNode(idx + 1), 0);
        } else {
            addEdge(u, upperNode(idx + 1), 1);
            addEdge(u, getA(upK - idx - 1), 0);
        }
        return u;
    };

    // Both-bounds DP (length = kR == kL), states (idx, tL, tU)
    int bothK = 0;
    vector<vector<vector<int>>> bothMemo;
    vector<int>* pLL = nullptr;
    vector<int>* pRR = nullptr;
    function<int(int,int,int)> bothNode;

    bothNode = [&](int idx, int tL, int tU) -> int {
        if (idx == bothK) return getA(0);
        if (bothMemo[idx][tL][tU] != -1) return bothMemo[idx][tL][tU];
        int u = addNode();
        bothMemo[idx][tL][tU] = u;
        int lb = (*pLL)[idx];
        int rb = (*pRR)[idx];
        for (int b = 0; b <= 1; ++b) {
            if (tL == 1 && b < lb) continue;
            if (tU == 1 && b > rb) continue;
            int ntL = tL ? (b == lb) : 0;
            int ntU = tU ? (b == rb) : 0;
            if (idx + 1 == bothK) {
                addEdge(u, getA(0), b);
            } else if (ntL == 0 && ntU == 0) {
                addEdge(u, getA(bothK - idx - 1), b);
            } else {
                addEdge(u, bothNode(idx + 1, ntL, ntU), b);
            }
        }
        return u;
    };

    // Build from start
    if (kL == kR) {
        bothK = kR;
        bothMemo.assign(bothK + 1, vector<vector<int>>(2, vector<int>(2, -1)));
        pLL = &Lbits;
        pRR = &Rbits;
        if (bothK == 1) {
            addEdge(start, getA(0), 1);
        } else {
            int node = bothNode(1, 1, 1); // after first '1'
            addEdge(start, node, 1);
        }
    } else {
        // Intermediate lengths: allow all with first bit 1
        for (int len = kL + 1; len <= kR - 1; ++len) {
            addEdge(start, getA(len - 1), 1);
        }
        // Lower-bound for length kL
        lowK = kL;
        lowerMemo.assign(lowK + 1, -1);
        pLbits = &Lbits;
        if (lowK == 1) {
            addEdge(start, getA(0), 1);
        } else {
            int node = lowerNode(1); // after first '1'
            addEdge(start, node, 1);
        }
        // Upper-bound for length kR
        upK = kR;
        upperMemo.assign(upK + 1, -1);
        pRbits = &Rbits;
        if (upK == 1) {
            addEdge(start, getA(0), 1);
        } else {
            int node = upperNode(1); // after first '1'
            addEdge(start, node, 1);
        }
    }

    // Create sink as the last node
    int sink = addNode();
    // Replace placeholder 0 with sink id
    for (int u = 1; u < (int)g.size(); ++u) {
        for (auto &e : g[u]) if (e.to == 0) e.to = sink;
    }

    // Output
    int n = (int)g.size() - 1;
    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        cout << g[i].size();
        for (auto &e : g[i]) {
            cout << " " << e.to << " " << e.w;
        }
        cout << "\n";
    }

    return 0;
}