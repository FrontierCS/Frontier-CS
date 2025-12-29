#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <chrono>

// Globals for problem data
int N, M, H;
std::vector<int> A;
std::vector<std::pair<int, int>> edges;
std::vector<std::vector<int>> adj;

// Randomness
struct XorShift {
    unsigned int x, y, z, w;
    XorShift() : x(123456789), y(362436069), z(521288629), w(88675123) {}
    unsigned int next() {
        unsigned int t = x ^ (x << 11);
        x = y; y = z; z = w;
        return w = (w ^ (w >> 19)) ^ (t ^ (t >> 8));
    }
    int next_int(int n) { // [0, n-1]
        if (n == 0) return 0;
        return next() % n;
    }
    double next_double() { // [0, 1)
        return (double)next() / ((long long)1 << 32);
    }
};
XorShift rnd;

// Timer
std::chrono::steady_clock::time_point start_time;
double get_time() {
    auto now = std::chrono::steady_clock::now();
    return std::chrono::duration_cast<std::chrono::duration<double>>(now - start_time).count();
}

// DSU for greedy initialization
struct DSU {
    std::vector<int> parent;
    std::vector<int> root_node;
    std::vector<long long> sum_A;
    std::vector<int> rel_max_h;
    DSU(int n) {
        parent.resize(n);
        std::iota(parent.begin(), parent.end(), 0);
        root_node.resize(n);
        std::iota(root_node.begin(), root_node.end(), 0);
        sum_A.resize(n);
        for(int i=0; i<n; ++i) sum_A[i] = ::A[i];
        rel_max_h.assign(n, 0);
    }

    int find(int i) {
        if (parent[i] == i) return i;
        return parent[i] = find(parent[i]);
    }

    void unite(int child_vtx, int parent_vtx, const std::vector<int>& p_arr) {
        int root_child = find(child_vtx);
        int root_parent = find(parent_vtx);
        if (root_child != root_parent) {
            int h_p = 0;
            int curr = parent_vtx;
            while(p_arr[curr] != -1) {
                curr = p_arr[curr];
                h_p++;
            }
            
            parent[root_child] = root_parent;
            sum_A[root_parent] += sum_A[root_child];
            rel_max_h[root_parent] = std::max(rel_max_h[root_parent], h_p + 1 + rel_max_h[root_child]);
        }
    }
};

// State for SA
struct State {
    std::vector<int> parent;
    std::vector<std::vector<int>> children;
    std::vector<long long> subtree_A_sum;
    std::vector<int> rel_max_h;
    long long score;

    State() {
        parent.assign(N, -1);
        children.assign(N, std::vector<int>());
        subtree_A_sum.resize(N);
        rel_max_h.assign(N, 0);
        score = 0;
    }
    
    State(const State& other) = default;
    State& operator=(const State& other) = default;

    void build_from_parents() {
        for(int i=0; i<N; ++i) children[i].clear();
        std::vector<int> roots;
        for(int i=0; i<N; ++i) {
            if(parent[i] != -1) {
                children[parent[i]].push_back(i);
            } else {
                roots.push_back(i);
            }
        }
        
        std::vector<int> q;
        for(int r : roots) q.push_back(r);
        
        int head = 0;
        while(head < (int)q.size()){
            int u = q[head++];
            for(int v : children[u]) q.push_back(v);
        }

        for(int i = q.size() - 1; i >= 0; --i) {
            int u = q[i];
            subtree_A_sum[u] = A[u];
            rel_max_h[u] = 0;
            for(int v : children[u]) {
                subtree_A_sum[u] += subtree_A_sum[v];
                rel_max_h[u] = std::max(rel_max_h[u], rel_max_h[v] + 1);
            }
        }
        
        score = 0;
        std::vector<int> h(N, 0);
        for(int r : roots) {
            std::vector<int> q_bfs;
            q_bfs.push_back(r);
            h[r] = 0;
            int head_bfs = 0;
            while(head_bfs < (int)q_bfs.size()){
                int u = q_bfs[head_bfs++];
                score += (long long)(h[u] + 1) * A[u];
                for(int v : children[u]){
                    h[v] = h[u] + 1;
                    q_bfs.push_back(v);
                }
            }
        }
    }

    int get_height(int v) const {
        if (v == -1) return -1;
        int h = 0;
        while(parent[v] != -1) {
            v = parent[v];
            h++;
        }
        return h;
    }

    void apply_move(int v, int new_p) {
        int old_p = parent[v];

        if (old_p != -1) {
            auto& old_p_children = children[old_p];
            old_p_children.erase(std::remove(old_p_children.begin(), old_p_children.end(), v), old_p_children.end());
        }

        long long v_subtree_sum = subtree_A_sum[v];

        int curr = old_p;
        while(curr != -1) {
            subtree_A_sum[curr] -= v_subtree_sum;
            int old_rel_h = rel_max_h[curr];
            int new_rel_h = 0;
            for(int c : children[curr]) {
                new_rel_h = std::max(new_rel_h, rel_max_h[c] + 1);
            }
            rel_max_h[curr] = new_rel_h;
            if (old_rel_h == new_rel_h) break;
            curr = parent[curr];
        }

        parent[v] = new_p;
        if (new_p != -1) {
            children[new_p].push_back(v);
        }
        
        curr = new_p;
        while(curr != -1) {
            subtree_A_sum[curr] += v_subtree_sum;
            int old_rel_h = rel_max_h[curr];
            int new_rel_h = 0;
            for(int c : children[curr]) {
                new_rel_h = std::max(new_rel_h, rel_max_h[c] + 1);
            }
            rel_max_h[curr] = new_rel_h;
            if (old_rel_h == new_rel_h) break;
            curr = parent[curr];
        }
    }
};

void greedy_init(std::vector<int>& p_arr) {
    DSU dsu(N);
    p_arr.assign(N, -1);

    auto get_h = [&](int v) {
        if (v == -1) return -1;
        int h = 0;
        while (p_arr[v] != -1) {
            v = p_arr[v];
            h++;
        }
        return h;
    };
    
    int num_merges = N * 0.9;
    for(int i = 0; i < num_merges; ++i) {
        double best_gain = -1.0;
        int best_child_root = -1, best_parent_node = -1;

        for (const auto& edge : edges) {
            int u = edge.first;
            int v = edge.second;
            int root_u_dsu = dsu.find(u);
            int root_v_dsu = dsu.find(v);
            if (root_u_dsu == root_v_dsu) continue;

            { // u's tree under v
                int h_v = get_h(v);
                if (h_v + 1 + dsu.rel_max_h[root_u_dsu] <= H) {
                    double gain = (double)(h_v + 1) * dsu.sum_A[root_u_dsu];
                    if (gain > best_gain) {
                        best_gain = gain;
                        best_child_root = dsu.root_node[root_u_dsu];
                        best_parent_node = v;
                    }
                }
            }
            { // v's tree under u
                int h_u = get_h(u);
                if (h_u + 1 + dsu.rel_max_h[root_v_dsu] <= H) {
                    double gain = (double)(h_u + 1) * dsu.sum_A[root_v_dsu];
                    if (gain > best_gain) {
                        best_gain = gain;
                        best_child_root = dsu.root_node[root_v_dsu];
                        best_parent_node = u;
                    }
                }
            }
        }
        
        if (best_child_root == -1) break;
        p_arr[best_child_root] = best_parent_node;
        dsu.unite(best_child_root, best_parent_node, p_arr);
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    start_time = std::chrono::steady_clock::now();

    std::cin >> N >> M >> H;
    A.resize(N);
    for (int i = 0; i < N; ++i) std::cin >> A[i];
    adj.resize(N);
    edges.resize(M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges[i] = {u, v};
    }
    for (int i=0; i<N; ++i) {
        int dummy_x, dummy_y;
        std::cin >> dummy_x >> dummy_y;
    }

    State current_state;
    greedy_init(current_state.parent);
    current_state.build_from_parents();
    
    std::vector<int> best_parents = current_state.parent;
    long long best_score = current_state.score;

    double time_limit = 2.95;
    double T_start = 500, T_end = 0.1;

    while (get_time() < time_limit) {
        int v = rnd.next_int(N);
        int p_idx = rnd.next_int(adj[v].size() + 1);
        int new_p = (p_idx == (int)adj[v].size()) ? -1 : adj[v][p_idx];

        int old_p = current_state.parent[v];
        if (new_p == old_p) continue;
        
        if (new_p != -1) {
            int curr = new_p;
            bool cycle = false;
            while(curr != -1) {
                if (curr == v) { cycle=true; break; }
                curr = current_state.parent[curr];
            }
            if (cycle) continue;
        }

        int h_v_old = current_state.get_height(v);
        int h_new_p = current_state.get_height(new_p);
        int h_v_new = (new_p == -1) ? 0 : h_new_p + 1;

        if (h_v_new + current_state.rel_max_h[v] > H) continue;

        long long score_delta = (long long)(h_v_new - h_v_old) * current_state.subtree_A_sum[v];

        double temp = T_start * pow(T_end / T_start, get_time() / time_limit);
        if (score_delta > 0 || rnd.next_double() < exp(score_delta / temp)) {
            current_state.apply_move(v, new_p);
            current_state.score += score_delta;
            if (current_state.score > best_score) {
                best_score = current_state.score;
                best_parents = current_state.parent;
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        std::cout << best_parents[i] << (i == N - 1 ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}