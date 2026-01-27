#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long L, R;
    if (!(cin >> L >> R)) return 0;

    // Decompose [L, R] into dyadic intervals (b, k) where size = 2^k and b divisible by 2^k
    struct Interval { long long b; int k; };
    vector<Interval> intervals;
    long long cur = L;
    int M = 0; // maximum k among intervals
    while (cur <= R) {
        int tz = __builtin_ctzll(cur); // trailing zeros
        long long rem = R - cur + 1;
        int maxk = 63 - __builtin_clzll(rem); // floor(log2(rem))
        int k = min(tz, maxk);
        intervals.push_back({cur, k});
        M = max(M, k);
        cur += 1LL << k;
    }

    // Graph structures
    // Node 1: start, Node 2: sink
    vector<vector<pair<int,int>>> adj; // adj[u] = list of (v,label)
    vector<array<int,2>> contNext; // designated continuation edges for building prefixes (per label)
    adj.resize(3); // 1-based, start with 2 nodes
    contNext.resize(3);
    contNext[1] = {0,0};
    contNext[2] = {0,0};
    int S = 1, T = 2;
    int nNodes = 2;

    auto newNode = [&]() {
        ++nNodes;
        adj.resize(nNodes+1);
        contNext.resize(nNodes+1);
        contNext[nNodes] = {0,0};
        return nNodes;
    };

    unordered_set<long long> edgeSet;
    edgeSet.reserve(4096);
    auto addEdge = [&](int u, int v, int w){
        long long key = ((long long)u << 40) ^ ((long long)v << 1) ^ (long long)w;
        if (edgeSet.insert(key).second) {
            adj[u].push_back({v, w});
        }
    };

    // Build shared free-bits chain of length M (G[0..M-1]) towards sink
    vector<int> G; // G[i] where distance to sink in edges = M - i
    if (M > 0) {
        G.resize(M);
        for (int i = 0; i < M; ++i) {
            G[i] = newNode();
        }
        for (int i = 0; i < M-1; ++i) {
            addEdge(G[i], G[i+1], 0);
            addEdge(G[i], G[i+1], 1);
        }
        addEdge(G[M-1], T, 0);
        addEdge(G[M-1], T, 1);
    }

    auto bitlen = [&](long long x)->int{
        return (x == 0) ? 0 : (64 - __builtin_clzll(x));
    };

    // Process each interval
    for (auto itv : intervals) {
        long long b = itv.b;
        int k = itv.k;
        long long p = b >> k; // prefix
        int lenp = bitlen(p);
        int curNode = S;

        for (int i = lenp - 1; i >= 0; --i) {
            int bit = (p >> i) & 1;
            if (i == 0 && k == 0) {
                // last bit and no free bits: direct to sink with this bit
                addEdge(curNode, T, bit);
            } else {
                // ensure continuation edge for this bit to next prefix node
                if (contNext[curNode][bit] == 0) {
                    int nx = newNode();
                    addEdge(curNode, nx, bit);
                    contNext[curNode][bit] = nx;
                }
                curNode = contNext[curNode][bit];
            }
        }

        if (k > 0) {
            int target = G[M - k]; // node from which exactly k-1 steps then last to sink remain
            // from the prefix node, the next bit (first free bit) can be 0 or 1 to 'target'
            addEdge(curNode, target, 0);
            addEdge(curNode, target, 1);
        }
    }

    // Output
    cout << nNodes << '\n';
    for (int u = 1; u <= nNodes; ++u) {
        cout << (int)adj[u].size();
        for (auto &e : adj[u]) {
            cout << ' ' << e.first << ' ' << e.second;
        }
        cout << '\n';
    }

    return 0;
}