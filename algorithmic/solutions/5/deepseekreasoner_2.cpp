#include <cstdio>
#include <vector>
#include <algorithm>
#include <random>

using namespace std;

int main() {
    int n, m;
    scanf("%d %d", &n, &m);
    int a[10];
    for (int i = 0; i < 10; i++) {
        scanf("%d", &a[i]);
    }
    
    vector<pair<int, int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; i++) {
        int u, v;
        scanf("%d %d", &u, &v);
        u--; v--;
        edges.emplace_back(u, v);
    }
    
    // DSU arrays
    vector<int> parent(n);
    vector<int> sz(n, 1);
    vector<int> head(n);
    vector<int> nxt(n, -1);
    vector<int> prv(n, -1);
    
    for (int i = 0; i < n; i++) {
        parent[i] = i;
        head[i] = i;
    }
    
    // iterative find with path compression
    auto find = [&](int x) {
        int root = x;
        while (parent[root] != root) {
            root = parent[root];
        }
        // path compression
        while (x != root) {
            int next = parent[x];
            parent[x] = root;
            x = next;
        }
        return root;
    };
    
    auto try_merge = [&](int u, int v) -> bool {
        if (nxt[u] != -1 || prv[v] != -1) {
            return false;
        }
        int ru = find(u);
        int rv = find(v);
        if (ru == rv) {
            return false;
        }
        // union by size
        if (sz[ru] < sz[rv]) {
            // merge ru into rv
            parent[ru] = rv;
            nxt[u] = v;
            prv[v] = u;
            head[rv] = head[ru];
            sz[rv] += sz[ru];
        } else {
            // merge rv into ru
            parent[rv] = ru;
            nxt[u] = v;
            prv[v] = u;
            // head[ru] remains the same
            sz[ru] += sz[rv];
        }
        return true;
    };
    
    // Random number generator
    random_device rd;
    mt19937 g(rd());
    
    int max_iter = 10;
    bool changed = true;
    for (int iter = 0; iter < max_iter && changed; iter++) {
        changed = false;
        shuffle(edges.begin(), edges.end(), g);
        for (const auto& e : edges) {
            if (try_merge(e.first, e.second)) {
                changed = true;
            }
        }
    }
    
    // Find the largest component
    int best_root = -1;
    int best_size = 0;
    for (int i = 0; i < n; i++) {
        if (find(i) == i) {
            if (sz[i] > best_size) {
                best_size = sz[i];
                best_root = i;
            }
        }
    }
    
    // Reconstruct the path from head of best_root
    vector<int> path;
    int cur = head[best_root];
    while (cur != -1) {
        path.push_back(cur);
        cur = nxt[cur];
    }
    
    // Output
    printf("%d\n", (int)path.size());
    for (size_t i = 0; i < path.size(); i++) {
        if (i > 0) printf(" ");
        printf("%d", path[i] + 1);
    }
    printf("\n");
    
    return 0;
}