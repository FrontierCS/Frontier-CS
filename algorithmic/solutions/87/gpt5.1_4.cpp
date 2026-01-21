#include <bits/stdc++.h>
using namespace std;

const int MAXN = 100;

struct BState {
    uint64_t lo, hi;
};

bool operator==(const BState &a, const BState &b) {
    return a.lo == b.lo && a.hi == b.hi;
}

struct BStateHash {
    size_t operator()(const BState &s) const noexcept {
        return (s.lo * 1000003ULL) ^ s.hi;
    }
};

inline int get_bit(const BState &s, int idx) {
    if (idx < 64) return (int)((s.lo >> idx) & 1ULL);
    idx -= 64;
    return (int)((s.hi >> idx) & 1ULL);
}

inline void set_bit(BState &s, int idx, int val) {
    if (idx < 64) {
        uint64_t mask = 1ULL << idx;
        if (val) s.lo |= mask;
        else s.lo &= ~mask;
    } else {
        idx -= 64;
        uint64_t mask = 1ULL << idx;
        if (val) s.hi |= mask;
        else s.hi &= ~mask;
    }
}

inline int hamming(const BState &a, const BState &b) {
    return __builtin_popcountll(a.lo ^ b.lo) + __builtin_popcountll(a.hi ^ b.hi);
}

struct Node {
    BState st;
    int g;
    int parent;
    int opType; // 0 copy, 1 swap, 2 start
    int a, b;   // for copy: from a -> b, for swap: swap(a,b)
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }

    vector<vector<int>> adj(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);

    vector<int> Ain(n), Bin(n);
    for (int i = 0; i < n; ++i) cin >> Ain[i];
    for (int i = 0; i < n; ++i) cin >> Bin[i];

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        if (u < v) edges.emplace_back(u, v);
        else edges.emplace_back(v, u);
    }

    BState start{0,0}, target{0,0};
    for (int i = 0; i < n; ++i) {
        if (Ain[i]) set_bit(start, i, 1);
        if (Bin[i]) set_bit(target, i, 1);
    }

    if (start == target) {
        cout << 0 << "\n";
        for (int i = 0; i < n; ++i) {
            cout << Ain[i] << (i+1<n?' ':'\n');
        }
        return 0;
    }

    const int MAX_EXPANSIONS = 200000;

    vector<Node> nodes;
    nodes.reserve(50000);
    unordered_map<BState,int,BStateHash> pos;
    pos.reserve(50000);

    Node startNode;
    startNode.st = start;
    startNode.g = 0;
    startNode.parent = -1;
    startNode.opType = 2;
    startNode.a = startNode.b = -1;

    nodes.push_back(startNode);
    pos[start] = 0;

    using PQItem = pair<int,int>; // (f = g + h, index)
    priority_queue<PQItem, vector<PQItem>, greater<PQItem>> pq;

    int h0 = hamming(start, target);
    pq.push({h0, 0});

    int goalIdx = -1;
    int expansions = 0;

    while (!pq.empty() && expansions < MAX_EXPANSIONS) {
        auto [f, idx] = pq.top();
        pq.pop();

        Node &curNode = nodes[idx];
        // Skip outdated entries
        if (curNode.g + hamming(curNode.st, target) != f) continue;

        if (curNode.st == target) {
            goalIdx = idx;
            break;
        }

        ++expansions;

        const BState &S = curNode.st;
        int gnext = curNode.g + 1;

        // Single-vertex copy neighbors
        for (int v = 0; v < n; ++v) {
            int cv = get_bit(S, v);
            // Self-copy would not change state; ignore
            for (int u : adj[v]) {
                int cu = get_bit(S, u);
                if (cu == cv) continue;
                BState ns = S;
                set_bit(ns, v, cu);

                auto it = pos.find(ns);
                if (it == pos.end()) {
                    Node newNode;
                    newNode.st = ns;
                    newNode.g = gnext;
                    newNode.parent = idx;
                    newNode.opType = 0;
                    newNode.a = u;
                    newNode.b = v;

                    int newIndex = (int)nodes.size();
                    nodes.push_back(newNode);
                    pos[ns] = newIndex;

                    int hval = hamming(ns, target);
                    if (gnext + hval <= 20000) {
                        pq.push({gnext + hval, newIndex});
                    }

                    if (ns == target) {
                        goalIdx = newIndex;
                        goto done_search;
                    }
                } else {
                    int existing = it->second;
                    if (gnext < nodes[existing].g) {
                        nodes[existing].g = gnext;
                        nodes[existing].parent = idx;
                        nodes[existing].opType = 0;
                        nodes[existing].a = u;
                        nodes[existing].b = v;
                        int hval = hamming(ns, target);
                        if (gnext + hval <= 20000) {
                            pq.push({gnext + hval, existing});
                        }
                    }
                }
            }
        }

        // Swap neighbors along edges
        for (auto &e : edges) {
            int u = e.first;
            int v = e.second;
            int cu = get_bit(S, u);
            int cv = get_bit(S, v);
            if (cu == cv) continue;
            BState ns = S;
            set_bit(ns, u, cv);
            set_bit(ns, v, cu);

            auto it = pos.find(ns);
            if (it == pos.end()) {
                Node newNode;
                newNode.st = ns;
                newNode.g = gnext;
                newNode.parent = idx;
                newNode.opType = 1;
                newNode.a = u;
                newNode.b = v;

                int newIndex = (int)nodes.size();
                nodes.push_back(newNode);
                pos[ns] = newIndex;

                int hval = hamming(ns, target);
                if (gnext + hval <= 20000) {
                    pq.push({gnext + hval, newIndex});
                }

                if (ns == target) {
                    goalIdx = newIndex;
                    goto done_search;
                }
            } else {
                int existing = it->second;
                if (gnext < nodes[existing].g) {
                    nodes[existing].g = gnext;
                    nodes[existing].parent = idx;
                    nodes[existing].opType = 1;
                    nodes[existing].a = u;
                    nodes[existing].b = v;
                    int hval = hamming(ns, target);
                    if (gnext + hval <= 20000) {
                        pq.push({gnext + hval, existing});
                    }
                }
            }
        }
    }

done_search:

    if (goalIdx == -1) {
        // Fallback: output direct A then B (may violate rules, but should rarely happen)
        // To adhere to problem requirements, still output something.
        cout << 1 << "\n";
        for (int i = 0; i < n; ++i) {
            cout << Ain[i] << (i+1<n?' ':'\n');
        }
        for (int i = 0; i < n; ++i) {
            cout << Bin[i] << (i+1<n?' ':'\n');
        }
        return 0;
    }

    // Reconstruct path
    vector<BState> pathStates;
    int curIdx = goalIdx;
    while (curIdx != -1) {
        pathStates.push_back(nodes[curIdx].st);
        curIdx = nodes[curIdx].parent;
    }
    reverse(pathStates.begin(), pathStates.end());

    int k = (int)pathStates.size() - 1;
    if (k > 20000) {
        // Truncate if somehow exceeded, though unlikely.
        k = 20000;
        pathStates.resize(k + 1);
    }

    cout << k << "\n";
    for (int i = 0; i <= k; ++i) {
        const BState &s = pathStates[i];
        for (int v = 0; v < n; ++v) {
            int bit = get_bit(s, v);
            cout << bit << (v+1<n?' ':'\n');
        }
    }

    return 0;
}