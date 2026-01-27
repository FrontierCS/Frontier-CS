#include <bits/stdc++.h>
using namespace std;

struct Graph {
    vector<vector<pair<int,int>>> adj; // adj[u] = list of (v, w)
    vector<array<int,2>> child;        // trie child pointers (0/1), 0 means not created
    int n;
    int start, finish;
    vector<int> gen; // generator nodes for i bits remaining (i>=1). 0 if not created.

    Graph() {
        n = 0;
        adj.push_back({}); // 0-index unused
        child.push_back({0,0});
        start = newNode(); // 1
        finish = newNode(); // 2
        gen.assign(32, 0);
    }

    int newNode() {
        ++n;
        adj.push_back({});
        child.push_back({0,0});
        return n;
    }

    void addEdge(int u, int v, int w) {
        adj[u].push_back({v,w});
    }

    int getGen(int i) { // i >= 1
        if (gen[i]) return gen[i];
        int id = newNode();
        gen[i] = id;
        if (i == 1) {
            addEdge(id, finish, 0);
            addEdge(id, finish, 1);
        } else {
            int to = getGen(i-1);
            addEdge(id, to, 0);
            addEdge(id, to, 1);
        }
        return id;
    }

    // Build path for prefix bits; if createLastNode is false, do not create/advance at last bit.
    // Returns tuple(prev node before last bit, last bit, last node id if created else -1)
    tuple<int,int,int> buildPrefix(const vector<int>& bits, bool createLastNode) {
        int cur = start;
        int prev = start;
        int lastBit = 0;
        for (int i = 0; i < (int)bits.size(); ++i) {
            int b = bits[i];
            bool last = (i == (int)bits.size() - 1);
            if (last && !createLastNode) {
                prev = cur;
                lastBit = b;
                return {prev, lastBit, -1};
            } else {
                if (child[cur][b] == 0) {
                    int nxt = newNode();
                    addEdge(cur, nxt, b);
                    child[cur][b] = nxt;
                }
                prev = cur;
                cur = child[cur][b];
                lastBit = b;
            }
        }
        return {prev, lastBit, cur};
    }
};

vector<int> toBits(unsigned int x) {
    vector<int> bits;
    while (x) {
        bits.push_back((x & 1) ? 1 : 0);
        x >>= 1;
    }
    reverse(bits.begin(), bits.end());
    if (bits.empty()) bits.push_back(0);
    return bits;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    unsigned int L, R;
    if (!(cin >> L >> R)) return 0;

    // Decompose [L, R] into dyadic blocks (start A, size 2^t)
    vector<pair<unsigned int,int>> blocks;
    unsigned int cur = L;
    while (cur <= R) {
        int t = 0;
        while (true) {
            unsigned int sz = 1u << (t + 1);
            if ( (cur % sz) == 0 && cur + sz - 1 <= R) t++;
            else break;
        }
        blocks.push_back({cur, t});
        cur += (1u << t);
    }

    Graph G;

    for (auto [A, t] : blocks) {
        unsigned int prefixVal = A >> t;
        vector<int> bits = toBits(prefixVal);
        // ensure no leading zeros: prefixVal >= 1 always, so first bit is 1
        if (t == 0) {
            auto [prev, lastBit, u] = G.buildPrefix(bits, false);
            G.addEdge(prev, G.finish, lastBit);
        } else if (t == 1) {
            auto [prev, lastBit, u] = G.buildPrefix(bits, true);
            G.addEdge(u, G.finish, 0);
            G.addEdge(u, G.finish, 1);
        } else {
            auto [prev, lastBit, u] = G.buildPrefix(bits, true);
            int genNode = G.getGen(t - 1);
            G.addEdge(u, genNode, 0);
            G.addEdge(u, genNode, 1);
        }
    }

    cout << G.n << "\n";
    for (int i = 1; i <= G.n; ++i) {
        cout << (int)G.adj[i].size();
        for (auto &e : G.adj[i]) {
            cout << " " << e.first << " " << e.second;
        }
        cout << "\n";
    }
    return 0;
}