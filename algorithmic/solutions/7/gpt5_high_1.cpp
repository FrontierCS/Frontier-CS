#include <bits/stdc++.h>
using namespace std;

struct TNode {
    int child[2];
    bool terminal;              // whether k=0 is allowed (accept exactly this prefix)
    vector<int> ks;             // list of k >= 1 allowed suffix lengths
    TNode() {
        child[0] = child[1] = -1;
        terminal = false;
    }
};

static vector<int> bits_of(unsigned long long a) {
    int len = 64 - __builtin_clzll(a);
    vector<int> bits;
    bits.reserve(len);
    for (int i = len - 1; i >= 0; --i) bits.push_back((a >> i) & 1);
    return bits;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long L, R;
    if (!(cin >> L >> R)) return 0;

    // Decompose [L, R] into aligned power-of-two sized blocks
    struct Block { long long a; int k; }; // numbers are [a*2^k, (a+1)*2^k - 1]
    vector<Block> blocks;
    long long cur = L;
    while (cur <= R) {
        int k = __builtin_ctzll(cur);
        while (cur + ((1LL << k) - 1) > R) --k;
        long long a = cur >> k;
        blocks.push_back({a, k});
        cur += (1LL << k);
    }

    // Build trie of all prefixes 'a'
    vector<TNode> trie(1); // root = 0
    int chain_max = 0; // maximum k>=1 used
    for (auto &b : blocks) {
        auto bits = bits_of(b.a);
        int u = 0;
        for (int bit : bits) {
            if (trie[u].child[bit] == -1) {
                trie[u].child[bit] = (int)trie.size();
                trie.emplace_back();
            }
            u = trie[u].child[bit];
        }
        if (b.k == 0) {
            trie[u].terminal = true;
        } else {
            trie[u].ks.push_back(b.k);
            chain_max = max(chain_max, b.k);
        }
    }

    // Deduplicate ks per node
    for (auto &node : trie) {
        if (!node.ks.empty()) {
            sort(node.ks.begin(), node.ks.end());
            node.ks.erase(unique(node.ks.begin(), node.ks.end()), node.ks.end());
        }
    }

    auto includeNode = [&](int idx)->bool {
        // Include node in graph if it has children or allows any k>=1 suffix (ks not empty)
        return (trie[idx].child[0] != -1) || (trie[idx].child[1] != -1) || (!trie[idx].ks.empty());
    };

    // Assign IDs to included trie nodes (exclude pure terminal-only leaves)
    vector<int> id(trie.size(), -1);
    int id_counter = 0;
    queue<int> q;
    id[0] = ++id_counter; // root
    q.push(0);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int b = 0; b <= 1; ++b) {
            int v = trie[u].child[b];
            if (v == -1) continue;
            if (id[v] == -1 && includeNode(v)) {
                id[v] = ++id_counter;
                q.push(v);
            }
        }
    }

    // Create sink and chain nodes (only for k>=1)
    int sink_id = ++id_counter;
    vector<int> Q(chain_max + 1, -1); // Q[0] = sink
    Q[0] = sink_id;
    for (int j = 1; j <= chain_max; ++j) Q[j] = ++id_counter;

    int n = id_counter;
    vector<vector<pair<int,int>>> adj(n + 1);

    auto add_edge = [&](int u, int v, int w) {
        adj[u].push_back({v, w});
    };

    // Add edges from trie structure
    for (int u = 0; u < (int)trie.size(); ++u) {
        if (id[u] == -1) continue; // node not included
        for (int b = 0; b <= 1; ++b) {
            int v = trie[u].child[b];
            if (v == -1) continue;
            // If reaching v allows terminal (k=0), add edge to sink with label b
            if (trie[v].terminal) {
                add_edge(id[u], sink_id, b);
            }
            // If child itself is included, add edge to child with label b
            if (includeNode(v)) {
                add_edge(id[u], id[v], b);
            }
        }
    }

    // Add edges from leaves for each allowed k>=1 (two edges 0 and 1 to Q[k-1])
    for (int u = 0; u < (int)trie.size(); ++u) {
        if (id[u] == -1) continue;
        if (!trie[u].ks.empty()) {
            for (int k : trie[u].ks) {
                int target = Q[k - 1]; // k >= 1 guaranteed here
                add_edge(id[u], target, 0);
                add_edge(id[u], target, 1);
            }
        }
    }

    // Add chain edges: Q[j] -> Q[j-1] with labels 0 and 1
    for (int j = 1; j <= chain_max; ++j) {
        add_edge(Q[j], Q[j - 1], 0);
        add_edge(Q[j], Q[j - 1], 1);
    }

    // Output
    cout << n << '\n';
    for (int i = 1; i <= n; ++i) {
        cout << (int)adj[i].size();
        for (auto &e : adj[i]) {
            cout << ' ' << e.first << ' ' << e.second;
        }
        cout << '\n';
    }

    return 0;
}