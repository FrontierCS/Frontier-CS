#include <bits/stdc++.h>
using namespace std;

const int HMAX = 10;

int N, M, H;
vector<int> A;
vector<vector<int>> adj;

vector<int> parent;
vector<int> depth;
vector<long long> sum_sub;
vector<int> max_depth_sub;
vector<vector<int>> children;

// Check if u is in the subtree of v (v is ancestor of u)
bool is_in_subtree(int u, int v) {
    if (u == v) return true;
    int cur = u;
    while (cur != -1) {
        if (cur == v) return true;
        cur = parent[cur];
    }
    return false;
}

// Recompute max_depth_sub for node x from its children
void recompute_max(int x) {
    int new_max = depth[x];
    for (int c : children[x]) {
        new_max = max(new_max, max_depth_sub[c]);
    }
    max_depth_sub[x] = new_max;
}

// Recompute max_depth_sub for x and propagate upwards
void recompute_max_up(int x) {
    while (x != -1) {
        int old = max_depth_sub[x];
        recompute_max(x);
        if (max_depth_sub[x] == old) break;
        x = parent[x];
    }
}

// Add delta to depth and max_depth_sub of subtree rooted at v
void add_delta(int v, int delta) {
    depth[v] += delta;
    max_depth_sub[v] += delta;
    for (int c : children[v]) {
        add_delta(c, delta);
    }
}

// Detach v from its current parent
void detach(int v) {
    int old_p = parent[v];
    if (old_p != -1) {
        // remove v from children of old_p
        auto it = find(children[old_p].begin(), children[old_p].end(), v);
        if (it != children[old_p].end())
            children[old_p].erase(it);
        // subtract sum_sub[v] from ancestors of old_p
        int a = old_p;
        while (a != -1) {
            sum_sub[a] -= sum_sub[v];
            a = parent[a];
        }
        // recompute max_depth_sub for old_p and up
        recompute_max_up(old_p);
    }
    parent[v] = -1;
}

// Attach v as child of u
void attach(int v, int u) {
    if (u != -1) {
        parent[v] = u;
        children[u].push_back(v);
        // add sum_sub[v] to ancestors of u
        int a = u;
        while (a != -1) {
            sum_sub[a] += sum_sub[v];
            a = parent[a];
        }
        // recompute max_depth_sub for u and up
        recompute_max_up(u);
    } else {
        parent[v] = -1;
    }
}

// Reparent v to u (u becomes new parent)
void reparent(int v, int u) {
    int new_depth = depth[u] + 1;
    int delta_d = new_depth - depth[v];
    detach(v);
    add_delta(v, delta_d);
    attach(v, u);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> M >> H;
    A.resize(N);
    for (int i = 0; i < N; ++i) cin >> A[i];
    adj.resize(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    // read coordinates (unused)
    for (int i = 0; i < N; ++i) {
        int x, y;
        cin >> x >> y;
    }

    // Initialize: every vertex is a root
    parent.assign(N, -1);
    depth.assign(N, 0);
    sum_sub.resize(N);
    for (int i = 0; i < N; ++i) sum_sub[i] = A[i];
    max_depth_sub.assign(N, 0);
    children.resize(N);

    // Random number generator for shuffling
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Greedy improvement loop
    bool improved = true;
    int passes = 0;
    while (improved && passes < 100) {
        improved = false;
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        for (int v : order) {
            long long best_gain = 0;
            int best_u = -1;
            for (int u : adj[v]) {
                if (u == parent[v]) continue;
                if (is_in_subtree(u, v)) continue;
                int new_depth = depth[u] + 1;
                if (new_depth > H) continue;
                int delta_d = new_depth - depth[v];
                if (delta_d <= 0) continue;
                if (max_depth_sub[v] + delta_d > H) continue;
                long long gain = (long long)delta_d * sum_sub[v];
                if (gain > best_gain) {
                    best_gain = gain;
                    best_u = u;
                }
            }
            if (best_gain > 0) {
                reparent(v, best_u);
                improved = true;
            }
        }
        ++passes;
    }

    // Output parent array
    for (int i = 0; i < N; ++i) {
        cout << parent[i] << (i+1 == N ? '\n' : ' ');
    }
    return 0;
}