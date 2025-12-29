#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>
#include <cmath>

using namespace std;

const int N_MAX = 1000;

int N_nodes, M_edges, H_limit;
vector<int> A_beauty;
vector<vector<int>> adj;

struct Solution {
    vector<int> parent;
    vector<vector<int>> children;
    vector<int> height;
    vector<int> root;
    vector<long long> subtree_sum_A;
    vector<int> subtree_max_h;
    long long score;

    Solution() {
        parent.resize(N_nodes);
        children.resize(N_nodes);
        height.resize(N_nodes);
        root.resize(N_nodes);
        subtree_sum_A.resize(N_nodes);
        subtree_max_h.resize(N_nodes);
        score = 0;
    }
    
    Solution(const Solution& other) = default;
    Solution& operator=(const Solution& other) = default;

    void compute_derived_data() {
        for (int i = 0; i < N_nodes; ++i) {
            children[i].clear();
        }
        vector<int> roots_list;
        for (int i = 0; i < N_nodes; ++i) {
            if (parent[i] != -1) {
                if (parent[i] >= 0 && parent[i] < N_nodes)
                    children[parent[i]].push_back(i);
            } else {
                roots_list.push_back(i);
            }
        }

        vector<int> q;
        q.reserve(N_nodes);
        for (int r : roots_list) {
            height[r] = 0;
            root[r] = r;
            q.push_back(r);
        }
        
        int head = 0;
        while(head < q.size()){
            int u = q[head++];
            for(int v : children[u]){
                height[v] = height[u] + 1;
                root[v] = root[u];
                q.push_back(v);
            }
        }

        for (int i = q.size() - 1; i >= 0; --i) {
            int u = q[i];
            subtree_sum_A[u] = A_beauty[u];
            subtree_max_h[u] = 0;
            for (int v : children[u]) {
                subtree_sum_A[u] += subtree_sum_A[v];
                subtree_max_h[u] = max(subtree_max_h[u], 1 + subtree_max_h[v]);
            }
        }
    }

    void calculate_score() {
        score = 0;
        for (int i = 0; i < N_nodes; ++i) {
            score += (long long)(height[i] + 1) * A_beauty[i];
        }
    }
};

bool is_ancestor(int u, int v, const Solution& sol) {
    if (sol.root[u] != sol.root[v]) return false;
    int curr = v;
    while (sol.parent[curr] != -1) {
        curr = sol.parent[curr];
        if (curr == u) return true;
    }
    return false;
}

void generate_initial_solution(Solution& sol) {
    vector<pair<int, int>> sorted_A(N_nodes);
    for (int i = 0; i < N_nodes; ++i) sorted_A[i] = {A_beauty[i], i};
    sort(sorted_A.begin(), sorted_A.end());

    fill(sol.parent.begin(), sol.parent.end(), -2);
    vector<bool> placed(N_nodes, false);

    int num_roots = max(1, N_nodes / 20);
    for (int i = 0; i < num_roots; ++i) {
        int u = sorted_A[i].second;
        sol.parent[u] = -1;
        placed[u] = true;
    }
    
    sol.compute_derived_data();

    vector<int> processing_order;
    for (int i = 0; i < N_nodes; ++i) {
        if (!placed[i]) processing_order.push_back(i);
    }
    sort(processing_order.begin(), processing_order.end(), [&](int a, int b){
        return A_beauty[a] > A_beauty[b];
    });
    
    bool changed_in_pass = true;
    while(changed_in_pass) {
        changed_in_pass = false;
        for (int u : processing_order) {
            if (placed[u]) continue;

            int best_p = -1;
            int max_h = -1;

            for (int v : adj[u]) {
                if (placed[v]) {
                    if (sol.height[v] + 1 <= H_limit) {
                        if (sol.height[v] + 1 > max_h) {
                            max_h = sol.height[v] + 1;
                            best_p = v;
                        }
                    }
                }
            }
            if (best_p != -1) {
                sol.parent[u] = best_p;
                sol.height[u] = max_h; // This is temporary, will be recomputed
                placed[u] = true;
                changed_in_pass = true;
            }
        }
        if (changed_in_pass) sol.compute_derived_data();
    }

    for (int i = 0; i < N_nodes; ++i) {
        if (!placed[i]) sol.parent[i] = -1;
    }
    sol.compute_derived_data();
    sol.calculate_score();
}

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    auto start_time = chrono::high_resolution_clock::now();

    cin >> N_nodes >> M_edges >> H_limit;
    A_beauty.resize(N_nodes);
    adj.resize(N_nodes);
    for (int i = 0; i < N_nodes; ++i) cin >> A_beauty[i];
    for (int i = 0; i < M_edges; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    for (int i = 0; i < N_nodes; ++i) {
        int x,y; cin >> x >> y;
    }

    Solution current_sol;
    generate_initial_solution(current_sol);
    Solution best_sol = current_sol;

    double start_temp = 2000;
    double end_temp = 0.1;
    double time_limit = 1.95;

    while (true) {
        auto current_time = chrono::high_resolution_clock::now();
        double elapsed_seconds = chrono::duration_cast<chrono::duration<double>>(current_time - start_time).count();
        if (elapsed_seconds > time_limit) break;
        
        double temp = start_temp + (end_temp - start_temp) * elapsed_seconds / time_limit;

        uniform_int_distribution<int> move_dist(0, 99);
        int move_type = move_dist(rng);
        uniform_int_distribution<int> node_dist(0, N_nodes - 1);

        if (move_type < 80) { // Change parent
            int u = node_dist(rng);
            if (current_sol.parent[u] == -1 || adj[u].empty()) continue;

            uniform_int_distribution<int> neighbor_dist(0, adj[u].size() - 1);
            int v = adj[u][neighbor_dist(rng)];

            if (v == current_sol.parent[u] || is_ancestor(u, v, current_sol)) continue;
            if (current_sol.height[v] + 1 + current_sol.subtree_max_h[u] > H_limit) continue;

            long long delta_score = (long long)(current_sol.height[v] + 1 - current_sol.height[u]) * current_sol.subtree_sum_A[u];

            if (delta_score > 0 || exp(delta_score / temp) > uniform_real_distribution<double>(0.0, 1.0)(rng)) {
                current_sol.parent[u] = v;
                current_sol.compute_derived_data();
                current_sol.calculate_score();
                if (current_sol.score > best_sol.score) best_sol = current_sol;
            }
        } else if (move_type < 90) { // Promote to root
            int u = node_dist(rng);
            if (current_sol.parent[u] == -1) continue;

            long long delta_score = -(long long)current_sol.height[u] * current_sol.subtree_sum_A[u];
            
            if (delta_score > 0 || exp(delta_score / temp) > uniform_real_distribution<double>(0.0, 1.0)(rng)) {
                current_sol.parent[u] = -1;
                current_sol.compute_derived_data();
                current_sol.calculate_score();
                if (current_sol.score > best_sol.score) best_sol = current_sol;
            }
        } else { // Demote root
            int u = node_dist(rng);
            if (current_sol.parent[u] != -1 || adj[u].empty()) continue;

            uniform_int_distribution<int> neighbor_dist(0, adj[u].size() - 1);
            int v = adj[u][neighbor_dist(rng)];
            
            if (current_sol.root[u] == current_sol.root[v]) continue;
            if (current_sol.height[v] + 1 + current_sol.subtree_max_h[u] > H_limit) continue;

            long long delta_score = (long long)(current_sol.height[v] + 1) * current_sol.subtree_sum_A[u];

            if (delta_score > 0 || exp(delta_score / temp) > uniform_real_distribution<double>(0.0, 1.0)(rng)) {
                current_sol.parent[u] = v;
                current_sol.compute_derived_data();
                current_sol.calculate_score();
                if (current_sol.score > best_sol.score) best_sol = current_sol;
            }
        }
    }
    
    for (int i = 0; i < N_nodes; ++i) {
        cout << best_sol.parent[i] << (i == N_nodes - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}