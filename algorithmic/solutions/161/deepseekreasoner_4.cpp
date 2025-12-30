#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <random>
#include <numeric>
#include <cassert>
#include <tuple>

using namespace std;

using ll = long long;

const int MAX_N = 100;
const int MAX_K = 5000;
const int MAX_P = 5000;
const ll INF = 1e18;

int N, M, K;
vector<int> x, y;
vector<int> a, b;

struct Edge {
    int u, v, w;
    int idx;
};
vector<Edge> edges;

// MST data
vector<vector<pair<int, int>>> tree; // to, edge_index
vector<int> parent; // parent node
vector<int> parent_edge_idx; // index in edges of the edge to parent
vector<int> edge_weight_to_parent; // weight of edge to parent
vector<int> depth;

// DSU for MST
struct DSU {
    vector<int> p;
    DSU(int n) : p(n, -1) {}
    int find(int x) {
        return p[x] < 0 ? x : p[x] = find(p[x]);
    }
    bool unite(int x, int y) {
        x = find(x); y = find(y);
        if (x == y) return false;
        if (p[x] > p[y]) swap(x, y);
        p[x] += p[y];
        p[y] = x;
        return true;
    }
};

// data for residents
vector<vector<ll>> sqdist; // [vertex][resident]
vector<vector<pair<ll, int>>> resident_order; // for each resident, list of (sqdist, vertex) sorted

// solution state
vector<bool> is_active; // P_i > 0
vector<int> assign; // resident -> vertex
vector<vector<int>> residents_at; // vertex -> list of resident indices
vector<ll> max_sq; // vertex: max sqdist among assigned residents
vector<int> P; // output strength

// tree helper
vector<int> active_count; // number of active vertices in subtree

// costs
ll total_P_cost;
ll total_edge_cost;
ll total_cost;

// random generator
random_device rd;
mt19937 rng(rd());

// utilities
int ceil_sqrt(ll x) {
    if (x <= 0) return 0;
    ll r = sqrt(x);
    while (r * r < x) ++r;
    if (r > MAX_P) r = MAX_P;
    return r;
}

void compute_P_from_max_sq(int i) {
    P[i] = ceil_sqrt(max_sq[i]);
}

// build MST (Kruskal)
void build_mst() {
    sort(edges.begin(), edges.end(), [](const Edge& e1, const Edge& e2) {
        return e1.w < e2.w;
    });
    DSU dsu(N);
    tree.assign(N, {});
    parent.assign(N, -1);
    parent_edge_idx.assign(N, -1);
    edge_weight_to_parent.assign(N, 0);
    int edge_count = 0;
    for (const Edge& e : edges) {
        if (dsu.unite(e.u, e.v)) {
            tree[e.u].push_back({e.v, e.idx});
            tree[e.v].push_back({e.u, e.idx});
            ++edge_count;
            if (edge_count == N-1) break;
        }
    }
    // root at 0 (vertex 1)
    depth.assign(N, 0);
    vector<int> stack = {0};
    parent[0] = -1;
    while (!stack.empty()) {
        int u = stack.back(); stack.pop_back();
        for (auto& [v, idx] : tree[u]) {
            if (v == parent[u]) continue;
            parent[v] = u;
            parent_edge_idx[v] = idx;
            edge_weight_to_parent[v] = edges[idx].w;
            depth[v] = depth[u] + 1;
            stack.push_back(v);
        }
    }
}

// precompute sqdist and resident_order
void precompute_distances() {
    sqdist.assign(N, vector<ll>(K));
    for (int i = 0; i < N; ++i) {
        for (int k = 0; k < K; ++k) {
            ll dx = x[i] - a[k];
            ll dy = y[i] - b[k];
            sqdist[i][k] = dx*dx + dy*dy;
        }
    }
    resident_order.assign(K, {});
    for (int k = 0; k < K; ++k) {
        vector<pair<ll, int>> order;
        for (int i = 0; i < N; ++i) {
            order.emplace_back(sqdist[i][k], i);
        }
        sort(order.begin(), order.end());
        resident_order[k] = move(order);
    }
}

// initial assignment: each resident to closest vertex
void initial_assignment() {
    assign.assign(K, -1);
    residents_at.assign(N, {});
    max_sq.assign(N, 0);
    is_active.assign(N, true);
    for (int k = 0; k < K; ++k) {
        int best = resident_order[k][0].second;
        assign[k] = best;
        residents_at[best].push_back(k);
        max_sq[best] = max(max_sq[best], sqdist[best][k]);
    }
    for (int i = 0; i < N; ++i) {
        compute_P_from_max_sq(i);
    }
}

// compute active_count from scratch
void compute_active_count() {
    active_count.assign(N, 0);
    // post-order traversal
    vector<int> order;
    vector<int> stack = {0};
    parent[0] = -1;
    while (!stack.empty()) {
        int u = stack.back(); stack.pop_back();
        order.push_back(u);
        for (auto& [v, _] : tree[u]) {
            if (v == parent[u]) continue;
            parent[v] = u;
            stack.push_back(v);
        }
    }
    reverse(order.begin(), order.end());
    for (int u : order) {
        active_count[u] = (is_active[u] ? 1 : 0);
        for (auto& [v, _] : tree[u]) {
            if (v == parent[u]) continue;
            active_count[u] += active_count[v];
        }
    }
}

// compute total edge cost based on active_count
ll compute_total_edge_cost() {
    ll cost = 0;
    for (int i = 1; i < N; ++i) {
        if (active_count[i] > 0) {
            cost += edge_weight_to_parent[i];
        }
    }
    return cost;
}

// initialize costs
void initialize_costs() {
    total_P_cost = 0;
    for (int i = 0; i < N; ++i) {
        total_P_cost += (ll)P[i] * P[i];
    }
    compute_active_count();
    total_edge_cost = compute_total_edge_cost();
    total_cost = total_P_cost + total_edge_cost;
}

// find closest active vertex for resident k, excluding 'exclude'
int find_closest_active(int k, int exclude) {
    for (auto& [_, i] : resident_order[k]) {
        if (i == exclude) continue;
        if (is_active[i]) return i;
    }
    return -1; // should not happen
}

// try to deactivate vertex v, return delta cost and updates (if beneficial)
pair<bool, ll> try_remove(int v) {
    if (!is_active[v]) return {false, 0};
    // temporarily store new max_sq for other vertices
    vector<ll> new_max_sq = max_sq;
    vector<bool> affected(N, false);
    // check each resident assigned to v
    for (int k : residents_at[v]) {
        int j = find_closest_active(k, v);
        if (j == -1) return {false, 0}; // cannot cover
        ll s = sqdist[j][k];
        if (s > new_max_sq[j]) {
            new_max_sq[j] = s;
            affected[j] = true;
        }
    }
    // compute new P for affected vertices and check limit
    for (int j = 0; j < N; ++j) {
        if (affected[j]) {
            int new_P = ceil_sqrt(new_max_sq[j]);
            if (new_P > MAX_P) return {false, 0};
        }
    }
    // compute delta P cost
    ll delta_P = -(ll)P[v] * P[v];
    for (int j = 0; j < N; ++j) {
        if (affected[j]) {
            int new_P = ceil_sqrt(new_max_sq[j]);
            delta_P += (ll)new_P * new_P - (ll)P[j] * P[j];
        }
    }
    // compute edge saving: traverse path from v to root
    ll saving_edge = 0;
    int cur = v;
    while (cur != 0) {
        if (active_count[cur] == 1) {
            saving_edge += edge_weight_to_parent[cur];
        }
        cur = parent[cur];
    }
    ll delta = delta_P - saving_edge;
    if (delta < 0) {
        return {true, delta};
    } else {
        return {false, 0};
    }
}

// apply removal of vertex v (assumes beneficial)
void apply_remove(int v) {
    // reassign residents
    for (int k : residents_at[v]) {
        int j = find_closest_active(k, v);
        assert(j != -1);
        assign[k] = j;
        residents_at[j].push_back(k);
        if (sqdist[j][k] > max_sq[j]) {
            max_sq[j] = sqdist[j][k];
            int old_P = P[j];
            compute_P_from_max_sq(j);
            total_P_cost += (ll)P[j] * P[j] - (ll)old_P * old_P;
        }
    }
    residents_at[v].clear();
    // update active state
    is_active[v] = false;
    total_P_cost -= (ll)P[v] * P[v];
    P[v] = 0;
    // update active_count along path
    int cur = v;
    while (cur != -1) {
        --active_count[cur];
        cur = parent[cur];
    }
    // update edge cost: edges that became unused
    cur = v;
    while (cur != 0) {
        if (active_count[cur] == 0) {
            total_edge_cost -= edge_weight_to_parent[cur];
        }
        cur = parent[cur];
    }
    total_cost = total_P_cost + total_edge_cost;
}

// global reassignment: assign each resident to closest active vertex
void global_reassignment() {
    // clear current assignments
    for (int i = 0; i < N; ++i) {
        residents_at[i].clear();
        max_sq[i] = 0;
    }
    // reassign
    for (int k = 0; k < K; ++k) {
        int j = -1;
        for (auto& [_, i] : resident_order[k]) {
            if (is_active[i]) {
                j = i;
                break;
            }
        }
        assert(j != -1);
        assign[k] = j;
        residents_at[j].push_back(k);
        max_sq[j] = max(max_sq[j], sqdist[j][k]);
    }
    // recompute P and total_P_cost
    total_P_cost = 0;
    for (int i = 0; i < N; ++i) {
        if (is_active[i]) {
            compute_P_from_max_sq(i);
            total_P_cost += (ll)P[i] * P[i];
        } else {
            P[i] = 0;
        }
    }
    total_cost = total_P_cost + total_edge_cost;
}

// deactivate vertices that have no residents
void cleanup_inactive() {
    for (int i = 0; i < N; ++i) {
        if (is_active[i] && residents_at[i].empty()) {
            is_active[i] = false;
            P[i] = 0;
            // update active_count
            int cur = i;
            while (cur != -1) {
                --active_count[cur];
                cur = parent[cur];
            }
            // update edge cost
            cur = i;
            while (cur != 0) {
                if (active_count[cur] == 0) {
                    total_edge_cost -= edge_weight_to_parent[cur];
                }
                cur = parent[cur];
            }
        }
    }
    total_cost = total_P_cost + total_edge_cost;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> M >> K;
    x.resize(N); y.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> x[i] >> y[i];
    }
    edges.resize(M);
    for (int j = 0; j < M; ++j) {
        int u, v, w;
        cin >> u >> v >> w;
        --u; --v;
        edges[j] = {u, v, w, j};
    }
    a.resize(K); b.resize(K);
    for (int k = 0; k < K; ++k) {
        cin >> a[k] >> b[k];
    }

    // build MST
    build_mst();

    // precompute distances
    precompute_distances();

    // initial assignment and costs
    initial_assignment();
    initialize_costs();

    // local search
    int max_passes = 10;
    for (int pass = 0; pass < max_passes; ++pass) {
        bool improved = false;
        vector<int> active_list;
        for (int i = 0; i < N; ++i) {
            if (is_active[i]) active_list.push_back(i);
        }
        shuffle(active_list.begin(), active_list.end(), rng);
        for (int v : active_list) {
            auto [ok, delta] = try_remove(v);
            if (ok) {
                apply_remove(v);
                improved = true;
            }
        }
        if (improved) {
            global_reassignment();
            cleanup_inactive();
        } else {
            break;
        }
    }

    // output
    for (int i = 0; i < N; ++i) {
        cout << P[i] << (i+1 == N ? '\n' : ' ');
    }
    vector<int> B(M, 0);
    for (int i = 1; i < N; ++i) {
        if (active_count[i] > 0) {
            int idx = parent_edge_idx[i];
            B[idx] = 1;
        }
    }
    for (int j = 0; j < M; ++j) {
        cout << B[j] << (j+1 == M ? '\n' : ' ');
    }

    return 0;
}