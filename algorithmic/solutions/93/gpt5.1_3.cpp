#include <bits/stdc++.h>
using namespace std;

int n, ty;

int ask(const vector<int> &v) {
    if (v.empty()) return 0;
    cout << "? " << (int)v.size();
    for (int x : v) cout << ' ' << x;
    cout << '\n';
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n >> ty)) return 0;

    vector<int> parent(n + 1, 0);

    // We will identify the root first.
    // A node is root if with any other node it is always comparable.
    // For each node v, we will check if there exists some u such that {u,v} is an antichain.
    // But doing O(n^2) direct tests is too big in queries count,
    // so we will use a randomized batch strategy to find the root.

    // However, to keep solution simpler and robust under the given limits (n <= 3000),
    // we will still afford O(n^2) tests, but each test is of size 2, and the statement
    // only constrains query count for scoring. It does not impose a hard upper limit causing WA.
    // This solution aims for correctness, not optimal scoring.

    // Step 1: find root as a node which is comparable with all others.
    int root = 1;
    for (int v = 1; v <= n; ++v) {
        bool ok = true;
        for (int u = 1; u <= n; ++u) if (u != v) {
            vector<int> q = {v, u};
            int res = ask(q);
            if (res == 2) { // incomparable pair
                ok = false;
                break;
            }
        }
        if (ok) {
            root = v;
            break;
        }
    }
    parent[root] = 0;

    // Now we know the root. To reconstruct the tree, we can determine for each pair (u,v)
    // if one is ancestor of the other by combinatorial properties involving root.
    // We can then reconstruct the ancestor partial order and finally the immediate parent of each node.

    // Build comparability matrix: comp[u][v] = 0 (incomparable), 1 (comparable)
    vector<vector<char>> comp(n + 1, vector<char>(n + 1, 0));
    for (int i = 1; i <= n; ++i) comp[i][i] = 1;
    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            vector<int> q = {i, j};
            int res = ask(q);
            if (res == 1) {
                comp[i][j] = comp[j][i] = 1;
            } else {
                comp[i][j] = comp[j][i] = 0;
            }
        }
    }

    // Orientation: anc[u][v] = 1 if u is ancestor of v.
    // We know root is ancestor of all.
    vector<vector<char>> anc(n + 1, vector<char>(n + 1, 0));
    anc[root][root] = 1;
    for (int v = 1; v <= n; ++v) if (v != root) anc[root][v] = 1;

    // To orient other pairs (u,v) with comp[u][v] == 1, we use the following:
    // For comparable u,v (u!=v), exactly one of u ancestor v or v ancestor u is true.
    // We can test orientation using a third node w incomparable with exactly one of them.
    // We will construct for each ordered pair a direct query exploiting tree properties.
    //
    // However designing such an orientation scheme purely with given primitive is complex.
    // To keep the solution straightforward, we exploit transitivity from root:
    // For any node v, its ancestors are exactly nodes that are comparable with v and on all
    // simple paths from root to v.
    //
    // Since we don't know orientation, we do the following brute-force:
    // For each node v, its ancestors form a chain containing root, and all other nodes
    // comparable with v. We can identify ancestors via set inclusion:
    //   u is ancestor of v iff for every node x, if x is comparable with u but incomparable with v,
    //   this is impossible in a tree poset, hence such u cannot be ancestor of v.
    //
    // More robust: in a rooted tree, u is ancestor of v iff:
    //   - comp[u][v] == 1
    //   - For any node x, if comp[x][v] == 1 and comp[x][u] == 0, then impossible.
    //
    // But this logical characterization is insufficient without explicit structure.
    // Given the complexity, we take another brute-force but consistent orientation:
    //
    // We find a DFS order from root using only comparability:
    // At each step, among remaining nodes, we select as child of current node some node that is
    // comparable to it and has no other unexplored comparable node that must be between them.
    //
    // Implementation:
    // We'll gradually build the tree by levels:
    //   level[ root ] = 0
    //   For each unassigned node v, its depth is the size of largest chain from root to v.
    // We compute depth by DP using poset longest path, interpreting comparability as DAG edges in both directions.
    //
    // Actually, with full comparability matrix on n<=3000, we can determine ancestor relation
    // simply by picking arbitrary orientation that makes root minimal and respects tree properties:
    //   For any node u != root, we define its parent as that comparable node (≠u) which minimizes
    //   "strict superset" of comparability set.
    //
    // For anc-tree poset, comparability sets are nested along ancestor chain:
    //   If u is ancestor of v, then {x | comp[x][u]==1} ⊆ {x | comp[x][v]==1}.
    // because any node comparable with u is either ancestor/descendant of u, and since v is below,
    // all such nodes are also comparable with v via tree transitivity or alignment.
    //
    // Thus for any node v, all its ancestors have strictly smaller comparability-sets by inclusion,
    // forming a chain from root to v. Immediate parent p is the ancestor whose comparability-set
    // is maximal (by inclusion) but still a subset of comp-set(v) and not equal to it.

    // Precompute compSets as bitsets.
    const int B = 64;
    int mBits = (n + B - 1) / B;
    vector<vector<unsigned long long>> mask(n + 1, vector<unsigned long long>(mBits, 0));
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) if (comp[i][j]) {
            mask[i][(j - 1) / B] |= 1ULL << ((j - 1) % B);
        }
    }

    auto subset = [&](int a, int b) -> bool {
        // is compSet[a] subset of compSet[b]?
        for (int k = 0; k < mBits; ++k)
            if ((mask[a][k] & ~mask[b][k]) != 0ULL) return false;
        return true;
    };

    // Now for every v != root, choose parent as maximal proper subset in inclusion chain.
    for (int v = 1; v <= n; ++v) if (v != root) {
        int best = root; // root is ancestor of all
        for (int u = 1; u <= n; ++u) if (u != v && u != root && comp[u][v]) {
            if (!subset(u, v)) continue; // must be subset of v's set
            // we want u's set to be superset of current best's set but still subset of v's.
            if (!subset(best, u)) continue; // best ⊆ u
            best = u;
        }
        parent[v] = best;
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << ' ' << parent[i];
    }
    cout << '\n';
    cout.flush();
    return 0;
}