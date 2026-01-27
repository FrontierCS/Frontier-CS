#include <bits/stdc++.h>
using namespace std;

struct Graph {
    vector<vector<pair<int,int>>> adj; // (to, weight)
    int addNode() { adj.emplace_back(); return (int)adj.size(); }
    void addEdge(int u, int v, int w) { adj[u-1].push_back({v, w}); }
    int size() const { return (int)adj.size(); }
};

struct Builder {
    Graph &G;
    int END, START;
    vector<int> F; // F[k] node ids

    Builder(Graph &graph): G(graph), END(0), START(0) {}

    int getF(int k) {
        if ((int)F.size() <= k) F.resize(k+1, -1);
        if (F[k] != -1) return F[k];
        if (k == 0) return F[k] = END;
        int id = G.addNode();
        int child = getF(k-1);
        G.addEdge(id, child, 0);
        G.addEdge(id, child, 1);
        F[k] = id;
        return id;
    }

    // Upper-only builder: generate suffix of length K respecting <= UB (vector bits of length K)
    struct Upper {
        Builder &B;
        vector<int> UB;
        int K;
        vector<int> memo; // memo[pos] for less=false states
        Upper(Builder &b, const vector<int>& ub): B(b), UB(ub), K((int)ub.size()), memo(K+1, 0) {}

        int build_pos(int pos) {
            if (pos == K) return B.END;
            if (memo[pos] != 0) return memo[pos];
            int id = B.G.addNode();
            int bit = UB[pos];
            if (bit == 0) {
                int nxt = build_pos(pos+1);
                B.G.addEdge(id, nxt, 0);
            } else { // bit == 1
                int freeNode = B.getF(K - (pos+1));
                B.G.addEdge(id, freeNode, 0); // choosing 0 makes it strictly less
                int nxt = build_pos(pos+1); // choosing 1 keeps it tight
                B.G.addEdge(id, nxt, 1);
            }
            memo[pos] = id;
            return id;
        }
    };

    // Lower-only builder: generate suffix of length K respecting >= LB (vector bits of length K)
    struct Lower {
        Builder &B;
        vector<int> LB;
        int K;
        vector<int> memo; // memo[pos] for greater=false states
        Lower(Builder &b, const vector<int>& lb): B(b), LB(lb), K((int)lb.size()), memo(K+1, 0) {}

        int build_pos(int pos) {
            if (pos == K) return B.END;
            if (memo[pos] != 0) return memo[pos];
            int id = B.G.addNode();
            int bit = LB[pos];
            if (bit == 1) {
                int nxt = build_pos(pos+1);
                B.G.addEdge(id, nxt, 1);
            } else { // bit == 0
                int nxt0 = build_pos(pos+1); // equal so far
                B.G.addEdge(id, nxt0, 0);
                int freeNode = B.getF(K - (pos+1)); // choosing 1 makes it greater
                B.G.addEdge(id, freeNode, 1);
            }
            memo[pos] = id;
            return id;
        }
    };

    // Between builder: generate suffix of length K respecting LB <= suffix <= UB
    struct Between {
        Builder &B;
        vector<int> LB, UB;
        int K;
        vector<int> memo; // only for state (pos, g=false, l=false)
        Upper &Up;
        Lower &Low;
        Between(Builder &b, const vector<int>& lb, const vector<int>& ub, Upper &up, Lower &low)
            : B(b), LB(lb), UB(ub), K((int)lb.size()), memo(K+1, 0), Up(up), Low(low) {}

        int build_pos(int pos) {
            if (pos == K) return B.END;
            if (memo[pos] != 0) return memo[pos];
            int id = B.G.addNode();
            int lb = LB[pos], ub = UB[pos];
            if (lb == 0 && ub == 0) {
                int nxt = build_pos(pos+1);
                B.G.addEdge(id, nxt, 0);
            } else if (lb == 1 && ub == 1) {
                int nxt = build_pos(pos+1);
                B.G.addEdge(id, nxt, 1);
            } else if (lb == 0 && ub == 1) {
                // choose 0 -> less becomes true -> use Lower-only remains with greater=false,l=true
                int toLow = Low.build_pos(pos+1);
                B.G.addEdge(id, toLow, 0);
                // choose 1 -> greater becomes true -> use Upper-only remains with less=false,g=true
                int toUp = Up.build_pos(pos+1);
                B.G.addEdge(id, toUp, 1);
            } else {
                // lb==1 and ub==0, impossible interval at this pos when tight both sides; no edges
            }
            memo[pos] = id;
            return id;
        }
    };
};

static int bitlen(int x) {
    int l = 0;
    while (x) { l++; x >>= 1; }
    return max(l, 1);
}

static vector<int> bits_of_len(int x, int len) {
    vector<int> b(len, 0);
    for (int i = 0; i < len; ++i) {
        int shift = len - 1 - i;
        b[i] = (x >> shift) & 1;
    }
    return b;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int L, R;
    if (!(cin >> L >> R)) return 0;

    Graph G;
    Builder B(G);

    // Create END and START nodes
    B.END = G.addNode();    // 1
    B.START = G.addNode();  // 2
    B.F.resize(1);
    B.F[0] = B.END;

    int lenL = bitlen(L);
    int lenR = bitlen(R);

    int maxK = max(lenL, lenR) - 1;
    B.getF(maxK); // ensure chain nodes exist up to maxK

    // Prepare bounds for boundary lengths
    // For len == lenL: LB = bits(L) excluding MSB; UB depends if lenL==lenR
    // For len == lenR: UB = bits(R) excluding MSB; LB depends if lenL==lenR
    vector<int> bitsL = bits_of_len(L, lenL);
    vector<int> bitsR = bits_of_len(R, lenR);
    vector<int> Lsuf, Rsuf;
    if (lenL >= 1) {
        Lsuf.assign(bitsL.begin() + 1, bitsL.end());
    }
    if (lenR >= 1) {
        Rsuf.assign(bitsR.begin() + 1, bitsR.end());
    }

    // Builders for boundary suffixes
    Builder::Upper upR(B, Rsuf);
    Builder::Lower lowL(B, Lsuf);
    Builder::Between between(B, Lsuf, Rsuf, upR, lowL);

    // Add edges from START for each allowable length
    // Case 1: lengths strictly between lenL and lenR -> free
    for (int len = lenL + 1; len <= lenR - 1; ++len) {
        int k = len - 1; // suffix bits count
        int node = B.getF(k);
        G.addEdge(B.START, node, 1);
    }

    if (lenL == lenR) {
        // both bounds apply on same length
        int k = lenL - 1;
        if (k == 0) {
            // only number is the MSB 1, so START -> END with weight 1
            G.addEdge(B.START, B.END, 1);
        } else {
            int node = between.build_pos(0);
            G.addEdge(B.START, node, 1);
        }
    } else {
        // len == lenL: only lower bound applies
        if (lenL >= 1) {
            int k = lenL - 1;
            if (k == 0) {
                G.addEdge(B.START, B.END, 1);
            } else {
                int node = lowL.build_pos(0);
                G.addEdge(B.START, node, 1);
            }
        }
        // len == lenR: only upper bound applies
        if (lenR >= 1) {
            int k = lenR - 1;
            if (k == 0) {
                G.addEdge(B.START, B.END, 1);
            } else {
                int node = upR.build_pos(0);
                G.addEdge(B.START, node, 1);
            }
        }
    }

    // Output
    int n = G.size();
    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        auto &v = G.adj[i-1];
        cout << (int)v.size();
        for (auto &e : v) {
            cout << " " << e.first << " " << e.second;
        }
        cout << "\n";
    }
    return 0;
}