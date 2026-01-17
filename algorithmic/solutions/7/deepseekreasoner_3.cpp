#include <bits/stdc++.h>
using namespace std;

struct Node {
    int next[2];
    bool term[2];
    Node() {
        next[0] = next[1] = -1;
        term[0] = term[1] = false;
    }
};

struct Signature {
    bool t0, t1;
    int c0, c1;
    bool operator==(const Signature& other) const {
        return t0 == other.t0 && t1 == other.t1 && c0 == other.c0 && c1 == other.c1;
    }
};

struct HashSig {
    size_t operator()(const Signature& s) const {
        return ((size_t)s.t0) ^ ((size_t)s.t1 << 1) ^ ((size_t)s.c0 << 2) ^ ((size_t)s.c1 << 20);
    }
};

int dfs(int u, vector<int>& canon, const vector<Node>& nodes,
        unordered_map<Signature, int, HashSig>& sig_to_id,
        vector<Signature>& new_nodes) {
    if (canon[u] != -1) return canon[u];
    int c0 = -1, c1 = -1;
    if (nodes[u].next[0] != -1)
        c0 = dfs(nodes[u].next[0], canon, nodes, sig_to_id, new_nodes);
    if (nodes[u].next[1] != -1)
        c1 = dfs(nodes[u].next[1], canon, nodes, sig_to_id, new_nodes);
    Signature sig = {nodes[u].term[0], nodes[u].term[1], c0, c1};
    auto it = sig_to_id.find(sig);
    if (it != sig_to_id.end()) {
        canon[u] = it->second;
    } else {
        int new_id = sig_to_id.size() + 1;
        sig_to_id[sig] = new_id;
        canon[u] = new_id;
        new_nodes.push_back(sig);
    }
    return canon[u];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int L, R;
    cin >> L >> R;

    vector<Node> nodes(2); // index 0 unused, 1 is root
    nodes[1] = Node();

    for (int x = L; x <= R; ++x) {
        int bitlen = 0;
        int temp = x;
        while (temp) {
            bitlen++;
            temp >>= 1;
        }
        int u = 1;
        for (int i = bitlen - 1; i >= 1; --i) {
            int bit = (x >> i) & 1;
            if (nodes[u].next[bit] == -1) {
                nodes.push_back(Node());
                nodes[u].next[bit] = nodes.size() - 1;
            }
            u = nodes[u].next[bit];
        }
        int last_bit = x & 1;
        nodes[u].term[last_bit] = true;
    }

    vector<int> canon(nodes.size(), -1);
    unordered_map<Signature, int, HashSig> sig_to_id;
    vector<Signature> new_nodes;

    dfs(1, canon, nodes, sig_to_id, new_nodes);

    int new_node_count = new_nodes.size();
    int terminal_id = new_node_count + 1;
    int n = terminal_id;

    cout << n << '\n';
    for (int i = 1; i <= new_node_count; ++i) {
        const Signature& sig = new_nodes[i - 1];
        int k = (sig.t0 ? 1 : 0) + (sig.c0 != -1 ? 1 : 0) +
                (sig.t1 ? 1 : 0) + (sig.c1 != -1 ? 1 : 0);
        cout << k;
        if (sig.t0) cout << ' ' << terminal_id << " 0";
        if (sig.c0 != -1) cout << ' ' << sig.c0 << " 0";
        if (sig.t1) cout << ' ' << terminal_id << " 1";
        if (sig.c1 != -1) cout << ' ' << sig.c1 << " 1";
        cout << '\n';
    }
    cout << "0\n"; // terminal node
    return 0;
}