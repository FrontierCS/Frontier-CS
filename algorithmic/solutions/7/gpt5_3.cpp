#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long L, R;
    if (!(cin >> L >> R)) return 0;

    auto bitlen = [](long long x)->int {
        int l = 0;
        while (x) { l++; x >>= 1; }
        return max(1, l);
    };

    int lenL = bitlen(L);
    int lenR = bitlen(R);
    int M = lenR;

    vector<vector<pair<int,int>>> adj(1); // 1-indexed
    vector<int> indeg(1, 0);

    auto addNode = [&]()->int {
        adj.emplace_back();
        indeg.push_back(0);
        return (int)adj.size() - 1;
    };
    auto addEdge = [&](int u, int v, int w){
        adj[u].push_back({v, w});
        indeg[v]++;
    };

    vector<int> tail; // tail[k] = node id representing free tail of length k
    function<int(int)> getTail = [&](int k)->int {
        if ((int)tail.size() <= k) tail.resize(k + 1, -1);
        if (tail[k] != -1) return tail[k];
        if (k == 0) {
            tail[0] = addNode(); // sink with outdegree 0
            return tail[0];
        }
        int id = addNode();
        tail[k] = id;
        int child = getTail(k - 1);
        addEdge(id, child, 0);
        addEdge(id, child, 1);
        return id;
    };

    auto buildRange = [&](int m, int l, int r)->int {
        // builds a sub-DAG generating exactly m-bit strings in [l, r]
        // returns root node id (state with m bits remaining)
        vector<int> memo((m + 1) * 4, -1);
        function<int(int,int,int)> dfs = [&](int i, int low, int high)->int {
            if (i == 0) return getTail(0);
            if (!low && !high) return getTail(i);
            int key = (i << 2) | (low << 1) | high;
            if (memo[key] != -1) return memo[key];
            int id = addNode();
            memo[key] = id;
            int Lbit = (l >> (i - 1)) & 1;
            int Rbit = (r >> (i - 1)) & 1;
            if (low && high) {
                if (Lbit == Rbit) {
                    addEdge(id, dfs(i - 1, 1, 1), Lbit);
                } else {
                    addEdge(id, dfs(i - 1, 1, 0), 0);
                    addEdge(id, dfs(i - 1, 0, 1), 1);
                }
            } else if (low) {
                if (Lbit == 0) {
                    addEdge(id, dfs(i - 1, 1, 0), 0);
                    addEdge(id, getTail(i - 1), 1);
                } else {
                    addEdge(id, dfs(i - 1, 1, 0), 1);
                }
            } else { // high only
                if (Rbit == 1) {
                    addEdge(id, dfs(i - 1, 0, 1), 1);
                    addEdge(id, getTail(i - 1), 0);
                } else {
                    addEdge(id, dfs(i - 1, 0, 1), 0);
                }
            }
            return id;
        };
        return dfs(m, 1, 1);
    };

    int start = addNode();

    if (lenL == lenR) {
        int n = lenL;
        int m = n - 1;
        int lbits = (int)(L - (1LL << (n - 1)));
        int rbits = (int)(R - (1LL << (n - 1)));
        int root = buildRange(m, lbits, rbits);
        addEdge(start, root, 1);
    } else {
        // Left boundary length = lenL
        {
            int n = lenL;
            int m = n - 1;
            int lbits = (int)(L - (1LL << (n - 1)));
            int rbits = (1 << (n - 1)) - 1;
            int root = buildRange(m, lbits, rbits);
            addEdge(start, root, 1);
        }
        // Full internal lengths
        for (int n = lenL + 1; n <= lenR - 1; n++) {
            int t = getTail(n - 1);
            addEdge(start, t, 1);
        }
        // Right boundary length = lenR
        {
            int n = lenR;
            int m = n - 1;
            int lbits = 0;
            int rbits = (int)(R - (1LL << (n - 1)));
            int root = buildRange(m, lbits, rbits);
            addEdge(start, root, 1);
        }
    }

    int nNodes = (int)adj.size() - 1;
    cout << nNodes << "\n";
    for (int i = 1; i <= nNodes; i++) {
        cout << (int)adj[i].size();
        for (auto &e : adj[i]) {
            cout << " " << e.first << " " << e.second;
        }
        cout << "\n";
    }
    return 0;
}