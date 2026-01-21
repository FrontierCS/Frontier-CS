#include <bits/stdc++.h>
using namespace std;

struct Graph {
    vector<vector<pair<int,int>>> adj; // 1-based
    Graph() { adj.resize(1); } // dummy 0
    int new_node() {
        adj.emplace_back();
        return (int)adj.size() - 1;
    }
    void add_edge(int u, int v, int w) {
        adj[u].push_back({v, w});
    }
    int size() const { return (int)adj.size() - 1; }
};

static Graph G;
static int S, T;

static vector<int> Lbits, Rbits;
static int lenL, lenR;

static vector<int> freeNode;   // by rem
static vector<int> lowNode;    // by pos
static vector<int> upNode;     // by pos
static vector<int> bothNode;   // by pos (when lenL == lenR)

int getFree(int rem) {
    if (rem == 0) return T;
    if (rem < (int)freeNode.size() && freeNode[rem] != 0) return freeNode[rem];
    int needSize = rem + 1;
    if ((int)freeNode.size() < needSize) freeNode.resize(needSize, 0);
    int id = G.new_node();
    freeNode[rem] = id;
    int to = getFree(rem - 1);
    G.add_edge(id, to, 0);
    G.add_edge(id, to, 1);
    return id;
}

int getLower(int pos) {
    if (pos >= lenL) return T;
    if (lowNode[pos] != 0) return lowNode[pos];
    int id = G.new_node();
    lowNode[pos] = id;
    int b = Lbits[pos];
    if (b == 0) {
        // 0 keeps tight
        int to_tight = getLower(pos + 1);
        G.add_edge(id, to_tight, 0);
        // 1 breaks tight -> free with remaining
        int rem = lenL - pos - 1;
        int to_free = getFree(rem);
        G.add_edge(id, to_free, 1);
    } else { // b == 1
        int to_tight = getLower(pos + 1);
        G.add_edge(id, to_tight, 1);
    }
    return id;
}

int getUpper(int pos) {
    if (pos >= lenR) return T;
    if (upNode[pos] != 0) return upNode[pos];
    int id = G.new_node();
    upNode[pos] = id;
    int b = Rbits[pos];
    if (b == 1) {
        // 1 keeps tight
        int to_tight = getUpper(pos + 1);
        G.add_edge(id, to_tight, 1);
        // 0 breaks tight -> free with remaining
        int rem = lenR - pos - 1;
        int to_free = getFree(rem);
        G.add_edge(id, to_free, 0);
    } else { // b == 0
        int to_tight = getUpper(pos + 1);
        G.add_edge(id, to_tight, 0);
    }
    return id;
}

int getBoth(int pos) { // only when lenL == lenR
    int len = lenR;
    if (pos >= len) return T;
    if (bothNode[pos] != 0) return bothNode[pos];
    int id = G.new_node();
    bothNode[pos] = id;
    int lb = Lbits[pos], ub = Rbits[pos];
    if (lb == ub) {
        int to = getBoth(pos + 1);
        G.add_edge(id, to, lb);
    } else { // lb=0, ub=1
        int to_low = getLower(pos + 1);
        int to_up  = getUpper(pos + 1);
        G.add_edge(id, to_low, 0);
        G.add_edge(id, to_up, 1);
    }
    return id;
}

vector<int> toBitsMSB(int x) {
    vector<int> b;
    while (x > 0) {
        b.push_back(x & 1);
        x >>= 1;
    }
    reverse(b.begin(), b.end());
    if (b.empty()) b.push_back(0);
    return b;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int L, R;
    if (!(cin >> L >> R)) return 0;

    Lbits = toBitsMSB(L);
    Rbits = toBitsMSB(R);
    lenL = (int)Lbits.size();
    lenR = (int)Rbits.size();

    // init graph with start and sink
    S = G.new_node();
    T = G.new_node();

    // prepare containers
    freeNode.resize(lenR + 1, 0);
    lowNode.assign(lenL + 1, 0);
    upNode.assign(lenR + 1, 0);
    if (lenL == lenR) bothNode.assign(lenR + 1, 0);

    // Build edges from start
    // First bit must be 1 always.
    if (lenL == lenR) {
        int to = getBoth(1);
        G.add_edge(S, to, 1);
    } else {
        // len == lenL (lower bound)
        int toLow = getLower(1);
        G.add_edge(S, toLow, 1);

        // lengths between lenL+1 and lenR-1 (free)
        for (int len = lenL + 1; len <= lenR - 1; ++len) {
            int toFree = getFree(len - 1); // remaining after first '1'
            G.add_edge(S, toFree, 1);
        }

        // len == lenR (upper bound)
        int toUp = getUpper(1);
        G.add_edge(S, toUp, 1);
    }

    // Output
    int n = G.size();
    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        cout << (int)G.adj[i].size();
        for (auto &e : G.adj[i]) {
            cout << " " << e.first << " " << e.second;
        }
        cout << "\n";
    }
    return 0;
}