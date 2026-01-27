#include <bits/stdc++.h>
using namespace std;

struct Node {
    vector<pair<int,int>> edges; // (to, label 0/1)
    int next_trie[2];
    Node() { next_trie[0] = next_trie[1] = 0; }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long L, R;
    if (!(cin >> L >> R)) return 0;

    vector<pair<long long,int>> blocks; // (base, k) covering [base, base + 2^k - 1]
    long long x = L;
    while (x <= R) {
        int k = 0;
        while (true) {
            long long nextk = k + 1;
            long long size = 1LL << nextk;
            if ((x & (size - 1)) == 0 && x + size - 1 <= R) k = nextk;
            else break;
        }
        blocks.emplace_back(x, k);
        x += (1LL << k);
    }

    int maxk = 0;
    for (auto &b : blocks) maxk = max(maxk, b.second);

    vector<Node> nodes; 
    nodes.reserve(500);
    nodes.push_back(Node()); // dummy to make 1-based

    int START = 1;
    nodes.push_back(Node()); // node 1: start

    int T = (int)nodes.size(); // terminal
    nodes.push_back(Node()); // node T
    // T has outdegree 0

    // Build suffix chain nodes: Suf[d] means remaining d bits to emit arbitrarily
    vector<int> Suf(maxk + 1, 0); // Suf[0] unused, Suf[d] node id
    // We will build increasing d so transitions go to lower d
    for (int d = 1; d <= maxk; ++d) {
        int id = (int)nodes.size();
        nodes.push_back(Node());
        Suf[d] = id;
        int to = (d == 1 ? T : Suf[d-1]);
        // edges for both labels
        nodes[id].edges.emplace_back(to, 0);
        nodes[id].edges.emplace_back(to, 1);
    }

    auto ensure_child = [&](int u, int b) {
        if (nodes[u].next_trie[b] == 0) {
            int v = (int)nodes.size();
            nodes.push_back(Node());
            nodes[u].next_trie[b] = v;
            nodes[u].edges.emplace_back(v, b);
        }
        return nodes[u].next_trie[b];
    };

    auto bits_of = [&](long long p) {
        vector<int> bits;
        while (p > 0) { bits.push_back((int)(p & 1)); p >>= 1; }
        reverse(bits.begin(), bits.end());
        if (bits.empty()) bits.push_back(0); // shouldn't happen for p>=1
        return bits;
    };

    for (auto &blk : blocks) {
        long long base = blk.first;
        int k = blk.second;
        long long p = base >> k; // prefix
        vector<int> bits = bits_of(p); // MSB to LSB
        int u = START;
        int m = (int)bits.size();
        for (int i = 0; i < m - 1; ++i) {
            u = ensure_child(u, bits[i]);
        }
        int lastb = bits[m - 1];
        // ensure trie child for deeper prefixes
        int v = ensure_child(u, lastb);
        // add extra parallel edge for this block to suffix or terminal
        int dest = (k > 0 ? Suf[k] : T);
        nodes[u].edges.emplace_back(dest, lastb);
    }

    int n = (int)nodes.size() - 1;
    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        int k = (int)nodes[i].edges.size();
        cout << k;
        for (auto &e : nodes[i].edges) {
            cout << " " << e.first << " " << e.second;
        }
        cout << "\n";
    }

    return 0;
}