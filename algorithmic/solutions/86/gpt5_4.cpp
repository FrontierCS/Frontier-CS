#include <bits/stdc++.h>
using namespace std;

// NOTE: This solution is designed for an interactive-style problem adapted to offline judging.
// It communicates via standard input/output: prints queries, flushes stdout, and reads answers.

// Median query cache
struct TripleKey {
    int a, b, c;
    TripleKey(int x, int y, int z) {
        int t[3] = {x, y, z};
        sort(t, t + 3);
        a = t[0]; b = t[1]; c = t[2];
    }
    bool operator==(const TripleKey& other) const {
        return a == other.a && b == other.b && c == other.c;
    }
};

struct TripleKeyHasher {
    size_t operator()(const TripleKey& k) const {
        // pack into 64-bit
        // n <= 1000 => fit in 10 bits each; use 21 bits each safe in 64 bits
        return (uint64_t)k.a * 1315423911u ^ (uint64_t)k.b * 2654435761u ^ (uint64_t)k.c * 97531u;
    }
};

static unordered_map<TripleKey, int, TripleKeyHasher> cache;

int n;
long long query_count = 0;

int median_query(int x, int y, int z) {
    // require distinct
    if (x == y || y == z || x == z) {
        // Should not happen; but guard: if duplicates, no valid query. Return something arbitrary.
        // However, code paths avoid duplicates.
        if (x == y) return x;
        if (x == z) return x;
        return y;
    }
    TripleKey key(x, y, z);
    auto it = cache.find(key);
    if (it != cache.end()) return it->second;

    cout << "0 " << x << " " << y << " " << z << endl;
    cout.flush();

    int ans;
    if (!(cin >> ans)) {
        // In case of I/O failure
        exit(0);
    }
    cache.emplace(key, ans);
    query_count++;
    return ans;
}

// Edge set to avoid duplicates
struct EdgeHasher {
    size_t operator()(const uint64_t& k) const {
        return k * 11400714819323198485ull;
    }
};

static unordered_set<uint64_t, EdgeHasher> edge_set;
static vector<pair<int,int>> edges;

inline void add_edge(int u, int v) {
    if (u == v) return;
    if (u > v) swap(u, v);
    uint64_t key = ((uint64_t)u << 20) | (uint64_t)v; // n <= 1000 fits
    if (edge_set.insert(key).second) {
        edges.emplace_back(u, v);
    }
}

mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

// Helper: pick random distinct element from vector not equal to given 'avoid'
int pick_random_except(const vector<int>& vec, int avoid) {
    if (vec.size() == 1 && vec[0] == avoid) return -1;
    while (true) {
        int idx = (int)(rng() % vec.size());
        if (vec[idx] != avoid) return vec[idx];
    }
}

// Comparator for sorting nodes along path using fixed anchor 'a':
struct PathComparator {
    int a;
    PathComparator(int anchor) : a(anchor) {}
    bool operator()(int x, int y) const {
        if (x == y) return false;
        if (x == a) return true;
        if (y == a) return false;
        int m = median_query(a, x, y);
        // median(a, x, y) equals the one closer to 'a' among x and y
        return m == x;
    }
};

// Choose b that maximizes estimated path length with 'a' using sampling
int choose_b_with_sampling(const vector<int>& nodes, int a) {
    int K = min((int)nodes.size() - 1, 10);
    int R = min((int)nodes.size() - 2, 12);
    vector<int> cand;
    cand.reserve(K);
    // Prepare candidate set
    // Ensure we pick distinct from 'a'
    unordered_set<int> used;
    while ((int)cand.size() < K) {
        int b = nodes[rng() % nodes.size()];
        if (b == a) continue;
        if (used.insert(b).second) cand.push_back(b);
    }
    // Prepare sample set X
    vector<int> samp;
    samp.reserve(R);
    unordered_set<int> usedx;
    while ((int)samp.size() < R) {
        int x = nodes[rng() % nodes.size()];
        if (x == a) continue;
        if (usedx.insert(x).second) samp.push_back(x);
    }
    int best_b = cand[0];
    int best_score = -1;
    for (int b : cand) {
        int score = 0;
        for (int x : samp) {
            if (x == b) continue;
            int m = median_query(x, a, b);
            if (m == x) score++; // x lies on path a-b
        }
        if (score > best_score) {
            best_score = score;
            best_b = b;
        }
    }
    return best_b;
}

// Attempt to detect a deeper branch from center 'u' by sampling candidates t and testing path u-t
// Returns -1 if no deeper path found; otherwise returns t
int find_deep_branch_candidate(const vector<int>& nodes, int u) {
    int T = min((int)nodes.size() - 1, 20);
    int R = min((int)nodes.size() - 2, 15);
    unordered_set<int> tried;
    for (int iter = 0; iter < T; ++iter) {
        int t;
        do {
            t = nodes[rng() % nodes.size()];
        } while (t == u || !tried.insert(t).second);
        // sample R random x; if any lies on path u-t (i.e., median(x,u,t) == x), we found deeper path
        int hits = 0;
        for (int j = 0; j < R; ++j) {
            int x;
            do {
                x = nodes[rng() % nodes.size()];
            } while (x == u || x == t);
            int m = median_query(x, u, t);
            if (m == x) {
                hits++;
                if (hits >= 1) return t;
            }
        }
    }
    return -1;
}

void solve_cluster(const vector<int>& nodes) {
    if (nodes.size() <= 1) return;
    if (nodes.size() == 2) {
        add_edge(nodes[0], nodes[1]);
        return;
    }

    // Choose anchors a and b
    int a = nodes[rng() % nodes.size()];
    int b = choose_b_with_sampling(nodes, a);
    if (b == a) {
        // fallback to pick any different
        b = pick_random_except(nodes, a);
    }

    // Projection p[x] = median(x, a, b), for x != a, b
    unordered_map<int, vector<int>> attach; // attach[u] = nodes projecting to u
    vector<int> path_nodes;
    path_nodes.reserve(nodes.size());
    // Always on path:
    path_nodes.push_back(a);
    if (b != a) path_nodes.push_back(b);
    // We also gather value counts to help in star detection
    // Compute projections
    for (int x : nodes) {
        if (x == a || x == b) continue;
        int p = median_query(x, a, b);
        attach[p].push_back(x);
        if (p == x) {
            path_nodes.push_back(x);
        }
    }

    // If path_nodes size == 2, it means only a and b on path (no internal nodes)
    // This can happen if all other nodes not on a-b path.
    // In such case, the center might not be included as an internal node? But tree path must include internal nodes present in nodes set.
    // However, it's possible when 'nodes' subset is such that path a-b includes only a and b (subset excludes internal nodes), but here nodes is a cluster covering the entire tree partition at this level.
    // To handle gracefully, we will proceed without star detection and simply split to attachments of a and b.
    if (path_nodes.size() == 2) {
        // Attach groups for 'a' and 'b'
        // Add edge (a,b) since they are adjacent only if no internal nodes between them. But we don't know.
        // We cannot directly add (a,b), so instead, we attempt to refine by finding deeper branch from 'a' or 'b'.
        // Try find deeper from 'a'
        int t = find_deep_branch_candidate(nodes, a);
        if (t != -1) {
            // Recurse with better anchors (a, t)
            // Build new projection under (a,t)
            unordered_map<int, vector<int>> attach2;
            vector<int> path_nodes2;
            path_nodes2.push_back(a);
            path_nodes2.push_back(t);
            for (int x : nodes) {
                if (x == a || x == t) continue;
                int p = median_query(x, a, t);
                attach2[p].push_back(x);
                if (p == x) path_nodes2.push_back(x);
            }
            // sort path nodes by anchor 'a'
            sort(path_nodes2.begin(), path_nodes2.end(), PathComparator(a));
            // add edges along path
            for (size_t i = 0; i + 1 < path_nodes2.size(); ++i) add_edge(path_nodes2[i], path_nodes2[i + 1]);
            // recurse attachments
            for (int u : path_nodes2) {
                vector<int> sub;
                sub.push_back(u);
                auto it = attach2.find(u);
                if (it != attach2.end()) {
                    for (int v : it->second) if (v != u) sub.push_back(v);
                }
                if (sub.size() >= 2) solve_cluster(sub);
            }
            return;
        }
        // Try deeper from 'b'
        t = find_deep_branch_candidate(nodes, b);
        if (t != -1) {
            unordered_map<int, vector<int>> attach2;
            vector<int> path_nodes2;
            path_nodes2.push_back(b);
            path_nodes2.push_back(t);
            for (int x : nodes) {
                if (x == b || x == t) continue;
                int p = median_query(x, b, t);
                attach2[p].push_back(x);
                if (p == x) path_nodes2.push_back(x);
            }
            sort(path_nodes2.begin(), path_nodes2.end(), PathComparator(b));
            for (size_t i = 0; i + 1 < path_nodes2.size(); ++i) add_edge(path_nodes2[i], path_nodes2[i + 1]);
            for (int u : path_nodes2) {
                vector<int> sub;
                sub.push_back(u);
                auto it = attach2.find(u);
                if (it != attach2.end()) {
                    for (int v : it->second) if (v != u) sub.push_back(v);
                }
                if (sub.size() >= 2) solve_cluster(sub);
            }
            return;
        }
        // Couldn't refine; fall back: treat as star centered at the common projection if exists
        // Determine center u by seeing which node collects most attachments
        int center = -1;
        size_t best = 0;
        for (auto &kv : attach) {
            if (kv.second.size() > best) {
                best = kv.second.size();
                center = kv.first;
            }
        }
        if (center == -1) {
            // Fallback: connect a with all others
            for (int v : nodes) if (v != a) add_edge(a, v);
            return;
        } else {
            // Connect center to all nodes
            for (int v : nodes) if (v != center) add_edge(center, v);
            return;
        }
    }

    // If path_nodes size == 3 and all non-(a,b) project to the same center, check for deeper branch
    if (path_nodes.size() == 3) {
        int center = -1;
        for (int u : path_nodes) if (u != a && u != b) center = u;
        bool all_to_center = true;
        for (auto &kv : attach) {
            int u = kv.first;
            if (u == a || u == b) continue;
            if (u != center && u != 0) { all_to_center = false; break; }
        }
        if (all_to_center) {
            // Try find deeper path from center
            int t = find_deep_branch_candidate(nodes, center);
            if (t == -1) {
                // It's a star centered at 'center'
                for (int v : nodes) if (v != center) add_edge(center, v);
                return;
            } else {
                // Recompute with anchors (center, t)
                unordered_map<int, vector<int>> attach2;
                vector<int> path_nodes2;
                path_nodes2.push_back(center);
                path_nodes2.push_back(t);
                for (int x : nodes) {
                    if (x == center || x == t) continue;
                    int p = median_query(x, center, t);
                    attach2[p].push_back(x);
                    if (p == x) path_nodes2.push_back(x);
                }
                sort(path_nodes2.begin(), path_nodes2.end(), PathComparator(center));
                for (size_t i = 0; i + 1 < path_nodes2.size(); ++i) add_edge(path_nodes2[i], path_nodes2[i + 1]);
                for (int u : path_nodes2) {
                    vector<int> sub;
                    sub.push_back(u);
                    auto it = attach2.find(u);
                    if (it != attach2.end()) {
                        for (int v : it->second) if (v != u) sub.push_back(v);
                    }
                    if (sub.size() >= 2) solve_cluster(sub);
                }
                return;
            }
        }
    }

    // General case: sort path nodes along the path using anchor 'a'
    sort(path_nodes.begin(), path_nodes.end(), PathComparator(a));

    // Add edges along the path
    for (size_t i = 0; i + 1 < path_nodes.size(); ++i) add_edge(path_nodes[i], path_nodes[i + 1]);

    // Recurse on attachments for each path node
    for (int u : path_nodes) {
        vector<int> sub;
        sub.push_back(u);
        auto it = attach.find(u);
        if (it != attach.end()) {
            for (int v : it->second) if (v != u) sub.push_back(v);
        }
        if (sub.size() >= 2) solve_cluster(sub);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) {
        return 0;
    }

    vector<int> nodes(n);
    iota(nodes.begin(), nodes.end(), 1);

    solve_cluster(nodes);

    // Ensure exactly n-1 edges; if less, try to connect remaining nodes arbitrarily (shouldn't happen)
    if ((int)edges.size() > n - 1) {
        // Deduplicate already ensured; but just in case, truncate
        edges.resize(n - 1);
    } else if ((int)edges.size() < n - 1) {
        // Attempt to connect arbitrary missing edges using a spanning tree over components
        // Build DSU
        vector<int> parent(n + 1);
        iota(parent.begin(), parent.end(), 0);
        function<int(int)> findp = [&](int x) {
            return parent[x] == x ? x : parent[x] = findp(parent[x]);
        };
        auto unite = [&](int a, int b) {
            a = findp(a); b = findp(b);
            if (a != b) parent[a] = b;
        };
        for (auto &e : edges) unite(e.first, e.second);
        for (int i = 2; i <= n; ++i) {
            if (findp(1) != findp(i)) {
                add_edge(1, i);
                unite(1, i);
            }
        }
        if ((int)edges.size() > n - 1) edges.resize(n - 1);
    }

    cout << "1";
    for (auto &e : edges) {
        cout << " " << e.first << " " << e.second;
    }
    cout << endl;
    cout.flush();
    return 0;
}