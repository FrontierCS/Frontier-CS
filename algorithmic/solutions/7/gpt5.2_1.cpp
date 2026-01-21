#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int to;
    int w;
};

struct Node {
    vector<Edge> out;
};

static inline int bitlen(int x) {
    return 32 - __builtin_clz((unsigned)x);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int L, R;
    cin >> L >> R;

    vector<Node> g(1); // 1-indexed

    auto newNode = [&]() -> int {
        g.push_back(Node{});
        return (int)g.size() - 1;
    };

    auto addEdge = [&](int u, int v, int w) {
        auto &out = g[u].out;
        for (auto &e : out) if (e.to == v && e.w == w) return;
        out.push_back({v, w});
    };

    int start = newNode();
    int endNode = newNode();

    vector<int> suf(25, 0);
    suf[0] = endNode;

    function<int(int)> getS = [&](int r) -> int {
        if (r == 0) return endNode;
        if (suf[r]) return suf[r];
        int id = newNode();
        suf[r] = id;
        int child = getS(r - 1);
        addEdge(id, child, 0);
        addEdge(id, child, 1);
        return id;
    };

    unordered_map<unsigned long long, int> memo;
    memo.reserve(256);

    function<int(int,int,int)> buildRange = [&](int r, int A, int B) -> int {
        // r >= 1, 0 <= A <= B < 2^r
        if (A == 0 && B == ((1 << r) - 1)) return getS(r);

        unsigned long long key = (unsigned long long(r) << 40) | (unsigned long long(A) << 20) | (unsigned long long)B;
        auto it = memo.find(key);
        if (it != memo.end()) return it->second;

        int id = newNode();
        memo.emplace(key, id);

        if (r == 1) {
            if (A == 0) addEdge(id, endNode, 0);
            if (B == 1) addEdge(id, endNode, 1);
            return id;
        }

        int mid = 1 << (r - 1);

        // first bit = 0
        int lo0 = A;
        int hi0 = min(B, mid - 1);
        if (lo0 <= hi0) {
            if (lo0 == 0 && hi0 == mid - 1) addEdge(id, getS(r - 1), 0);
            else addEdge(id, buildRange(r - 1, lo0, hi0), 0);
        }

        // first bit = 1
        int lo1 = max(A, mid);
        int hi1 = B;
        if (lo1 <= hi1) {
            if (lo1 == mid && hi1 == (1 << r) - 1) addEdge(id, getS(r - 1), 1);
            else addEdge(id, buildRange(r - 1, lo1 - mid, hi1 - mid), 1);
        }

        return id;
    };

    int lenL = bitlen(L);
    int lenR = bitlen(R);

    auto addLengthInterval = [&](int k, int low, int high) {
        // k >= 1, both low/high within [2^(k-1), 2^k-1]
        if (k == 1) {
            // only number 1
            addEdge(start, endNode, 1);
            return;
        }
        int base = 1 << (k - 1);
        int r = k - 1;
        int A = low - base;
        int B = high - base;
        int root = buildRange(r, A, B);
        addEdge(start, root, 1);
    };

    if (lenL == lenR) {
        addLengthInterval(lenL, L, R);
    } else {
        // length lenL: [L, 2^lenL - 1]
        int maxLenL = (1 << lenL) - 1;
        addLengthInterval(lenL, L, maxLenL);

        // middle lengths full
        for (int k = lenL + 1; k <= lenR - 1; k++) {
            if (k == 1) continue;
            int r = k - 1;
            int root = getS(r);
            addEdge(start, root, 1);
        }

        // length lenR: [2^(lenR-1), R]
        int minLenR = 1 << (lenR - 1);
        addLengthInterval(lenR, minLenR, R);
    }

    // Prune unreachable nodes and renumber with start as node 1
    int oldN = (int)g.size() - 1;
    vector<char> vis(oldN + 1, 0);
    {
        vector<int> st;
        st.push_back(start);
        vis[start] = 1;
        while (!st.empty()) {
            int u = st.back();
            st.pop_back();
            for (auto &e : g[u].out) {
                int v = e.to;
                if (!vis[v]) {
                    vis[v] = 1;
                    st.push_back(v);
                }
            }
        }
    }

    vector<int> mp(oldN + 1, 0);
    mp[start] = 1;
    int nxt = 2;
    for (int i = 1; i <= oldN; i++) {
        if (i == start) continue;
        if (vis[i]) mp[i] = nxt++;
    }

    vector<Node> ng(nxt);
    auto addEdge2 = [&](int u, int v, int w) {
        auto &out = ng[u].out;
        for (auto &e : out) if (e.to == v && e.w == w) return;
        out.push_back({v, w});
    };

    for (int u = 1; u <= oldN; u++) {
        if (!vis[u]) continue;
        int nu = mp[u];
        for (auto &e : g[u].out) {
            int v = e.to;
            if (!vis[v]) continue;
            int nv = mp[v];
            addEdge2(nu, nv, e.w);
        }
    }

    g.swap(ng);
    start = 1;
    endNode = mp[endNode];

    int n = (int)g.size() - 1;

    // Sanity checks for unique start/end conditions
    vector<int> indeg(n + 1, 0), outdeg(n + 1, 0);
    for (int u = 1; u <= n; u++) {
        outdeg[u] = (int)g[u].out.size();
        for (auto &e : g[u].out) indeg[e.to]++;
    }

    int cntStart = 0, cntEnd = 0;
    for (int i = 1; i <= n; i++) {
        if (indeg[i] == 0) cntStart++;
        if (outdeg[i] == 0) cntEnd++;
    }
    // Ensure constraints; should always hold
    if (cntStart != 1 || cntEnd != 1 || outdeg[endNode] != 0 || indeg[start] != 0 || n > 100) {
        // Fallback minimal valid graph for number 1 (shouldn't happen)
        cout << 2 << "\n";
        cout << 1 << " " << 2 << " " << 1 << "\n";
        cout << 0 << "\n";
        return 0;
    }

    cout << n << "\n";
    for (int i = 1; i <= n; i++) {
        cout << g[i].out.size();
        for (auto &e : g[i].out) {
            cout << " " << e.to << " " << e.w;
        }
        cout << "\n";
    }

    return 0;
}