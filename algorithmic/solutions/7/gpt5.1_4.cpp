#include <bits/stdc++.h>
using namespace std;

vector<vector<pair<int,int>>> g; // adjacency list: (to, weight)
int startNode, sinkNode;
vector<int> suf; // suf[k] = node id for "k bits remaining", suf[0] = sink

int newNode() {
    g.push_back({});
    return (int)g.size() - 1;
}

void addEdge(int u, int v, int w) {
    g[u].push_back({v, w});
}

// Ensure suf[k] exists for k >= 1, with edges to suf[k-1]
int getSuf(int k) {
    while ((int)suf.size() <= k) {
        int idx = (int)suf.size(); // new index
        int node = newNode();
        suf.push_back(node);
        int child = suf[idx - 1];
        addEdge(node, child, 0);
        addEdge(node, child, 1);
    }
    return suf[k];
}

// Convert x to D-bit binary (MSB at index 0)
vector<int> getBits(int x, int D) {
    vector<int> bits(D);
    for (int i = D - 1; i >= 0; --i) {
        bits[i] = x & 1;
        x >>= 1;
    }
    return bits;
}

// Build DP for lower bound only, length D >= 2
int buildLowerBound(int D, const vector<int>& Lbits) {
    vector<int> node(D);
    for (int pos = 1; pos <= D - 1; ++pos) {
        node[pos] = newNode();
    }
    for (int pos = 1; pos <= D - 1; ++pos) {
        int u = node[pos];
        int rem = D - pos - 1;
        int Lnext = Lbits[pos];

        // Option 1: b = Lnext (stay equal)
        int v1 = (rem == 0) ? sinkNode : node[pos + 1];
        addEdge(u, v1, Lnext);

        // Option 2: if Lnext == 0, b = 1 (become greater -> unconstrained)
        if (Lnext == 0) {
            int v2 = (rem == 0) ? sinkNode : getSuf(rem);
            addEdge(u, v2, 1);
        }
    }
    return node[1];
}

// Build DP for upper bound only, length D >= 2
int buildUpperBound(int D, const vector<int>& Rbits) {
    vector<int> node(D);
    for (int pos = 1; pos <= D - 1; ++pos) {
        node[pos] = newNode();
    }
    for (int pos = 1; pos <= D - 1; ++pos) {
        int u = node[pos];
        int rem = D - pos - 1;
        int Rnext = Rbits[pos];

        if (Rnext == 1) {
            // b = 1 (stay equal)
            int v1 = (rem == 0) ? sinkNode : node[pos + 1];
            addEdge(u, v1, 1);
            // b = 0 (become smaller -> unconstrained)
            int v0 = (rem == 0) ? sinkNode : getSuf(rem);
            addEdge(u, v0, 0);
        } else { // Rnext == 0
            // only b = 0 allowed (stay equal)
            int v0 = (rem == 0) ? sinkNode : node[pos + 1];
            addEdge(u, v0, 0);
        }
    }
    return node[1];
}

// Build DP for both lower and upper bounds, length D >= 2
int buildBothBounds(int D, const vector<int>& Lbits, const vector<int>& Rbits) {
    vector<array<int,4>> node(D); // node[pos][mask], mask: bit0=tl, bit1=tr

    int entry = newNode();
    node[1][3] = entry; // tl = 1, tr = 1

    for (int pos = 1; pos <= D - 1; ++pos) {
        for (int mask = 0; mask < 4; ++mask) {
            int u = node[pos][mask];
            if (!u) continue;
            bool tl = mask & 1;
            bool tr = mask & 2;
            int rem = D - pos - 1;

            for (int b = 0; b <= 1; ++b) {
                if (tl && b < Lbits[pos]) continue;
                if (tr && b > Rbits[pos]) continue;

                bool newtl = tl && (b == Lbits[pos]);
                bool newtr = tr && (b == Rbits[pos]);

                if (rem == 0) {
                    addEdge(u, sinkNode, b);
                } else {
                    if (!newtl && !newtr) {
                        int v = getSuf(rem);
                        addEdge(u, v, b);
                    } else {
                        int newMask = (newtl ? 1 : 0) + (newtr ? 2 : 0);
                        int &v = node[pos + 1][newMask];
                        if (!v) v = newNode();
                        addEdge(u, v, b);
                    }
                }
            }
        }
    }
    return entry;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int L, R;
    if (!(cin >> L >> R)) return 0;

    g.clear();
    g.push_back({}); // dummy index 0

    // Create start node (index 1)
    startNode = newNode();

    // Create sink node (index 2)
    sinkNode = newNode();

    // Initialize suf[0] = sink; others created lazily
    suf.clear();
    suf.push_back(sinkNode);

    int lenL = 32 - __builtin_clz(L);
    int lenR = 32 - __builtin_clz(R);

    if (lenL == lenR) {
        int D = lenL;
        if (D == 1) {
            // Only number is 1
            addEdge(startNode, sinkNode, 1);
        } else {
            vector<int> Lbits = getBits(L, D);
            vector<int> Rbits = getBits(R, D);
            int entry = buildBothBounds(D, Lbits, Rbits);
            addEdge(startNode, entry, 1);
        }
    } else { // lenL < lenR
        int D1 = lenL;
        int D2 = lenR;

        int entryL = -1, entryR = -1;

        // Lower-bound part for length D1
        if (D1 == 1) {
            // Only number of length 1 in this range is 1
            // We'll add edge start->sink with weight 1 later
        } else {
            vector<int> Lbits = getBits(L, D1);
            entryL = buildLowerBound(D1, Lbits);
        }

        // Upper-bound part for length D2 (D2 >= 2 here)
        vector<int> Rbits = getBits(R, D2);
        entryR = buildUpperBound(D2, Rbits);

        // Connect start node
        if (D1 == 1) {
            // length 1 number: 1
            addEdge(startNode, sinkNode, 1);
        } else {
            addEdge(startNode, entryL, 1);
        }

        // Middle lengths: lenL+1 .. lenR-1
        for (int d = lenL + 1; d <= lenR - 1; ++d) {
            int k = d - 1; // bits remaining after first '1'
            int sufNode = getSuf(k);
            addEdge(startNode, sufNode, 1);
        }

        // Upper-bound length D2
        addEdge(startNode, entryR, 1);
    }

    int n = (int)g.size() - 1;
    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        int k = (int)g[i].size();
        cout << k;
        for (auto &e : g[i]) {
            cout << " " << e.first << " " << e.second;
        }
        cout << "\n";
    }

    return 0;
}