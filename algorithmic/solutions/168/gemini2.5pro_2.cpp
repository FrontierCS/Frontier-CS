#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <chrono>
#include <random>
#include <cmath>

using namespace std;

const int N_MAX = 1000;
int N, M, H;
vector<int> A;
vector<vector<int>> adj;
vector<pair<int, int>> edges;
vector<int> x, y;

// State
vector<int> parent;
vector<vector<int>> children;
vector<int> height;
vector<long long> subtree_A;
vector<int> max_subtree_d;
vector<int> roots;
vector<int> q_bfs;

long long current_score;
vector<int> best_parent;
long long best_score;

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

void dfs_compute(int u, int h) {
    height[u] = h;
    subtree_A[u] = A[u];
    max_subtree_d[u] = 0;
    for (int v : children[u]) {
        dfs_compute(v, h + 1);
        subtree_A[u] += subtree_A[v];
        max_subtree_d[u] = max(max_subtree_d[u], 1 + max_subtree_d[v]);
    }
}

void compute_aux_data() {
    children.assign(N, vector<int>());
    roots.clear();
    for (int i = 0; i < N; ++i) {
        if (parent[i] == -1) {
            roots.push_back(i);
        } else {
            children[parent[i]].push_back(i);
        }
    }

    height.assign(N, 0);
    subtree_A.assign(N, 0);
    max_subtree_d.assign(N, 0);
    for (int root : roots) {
        dfs_compute(root, 0);
    }
}

long long calculate_score() {
    long long score = 0;
    for (int i = 0; i < N; ++i) {
        score += (long long)(height[i] + 1) * A[i];
    }
    return score;
}

void initial_solution() {
    parent.assign(N, -2); // -2: unassigned
    vector<int> p(N);
    iota(p.begin(), p.end(), 0);
    sort(p.begin(), p.end(), [&](int i, int j) {
        return A[i] > A[j];
    });

    for (int i = 0; i < N; ++i) {
        int start_node = p[i];
        if (parent[start_node] != -2) continue;

        vector<int> path;
        path.push_back(start_node);
        int curr = start_node;

        for (int k = 0; k < H; ++k) {
            int best_neighbor = -1;
            int max_A = -1;
            for (int neighbor : adj[curr]) {
                if (parent[neighbor] == -2) {
                    if (A[neighbor] > max_A) {
                        max_A = A[neighbor];
                        best_neighbor = neighbor;
                    }
                }
            }
            if (best_neighbor == -1) break;
            path.push_back(best_neighbor);
            curr = best_neighbor;
        }

        reverse(path.begin(), path.end());
        parent[path[0]] = -1;
        for (size_t j = 0; j < path.size() - 1; ++j) {
            parent[path[j+1]] = path[j];
        }
    }

    height.assign(N, -1);
    vector<vector<int>> current_children(N);
    vector<int> current_roots;
    q_bfs.clear();
    
    for(int i=0; i<N; ++i){
        if(parent[i] >= 0) current_children[parent[i]].push_back(i);
        else if(parent[i] == -1) current_roots.push_back(i);
    }
    
    for(int r : current_roots){
        height[r] = 0;
        q_bfs.push_back(r);
    }

    int head = 0;
    while(head < q_bfs.size()){
        int u = q_bfs[head++];
        for(int v : current_children[u]){
             if(height[v] == -1){
                height[v] = height[u] + 1;
                q_bfs.push_back(v);
             }
        }
    }
    
    q_bfs.clear();
    for(int i=0; i<N; ++i) if(parent[i] != -2) q_bfs.push_back(i);
    
    head = 0;
    while(head < q_bfs.size()){
        int u = q_bfs[head++];
        if (height[u] >= H) continue;
        for (int v : adj[u]) {
            if (parent[v] == -2) {
                parent[v] = u;
                height[v] = height[u] + 1;
                q_bfs.push_back(v);
            }
        }
    }
    
    for (int i = 0; i < N; ++i) {
        if (parent[i] == -2) {
            parent[i] = -1;
        }
    }
}

bool is_descendant(int u_check, int v_target) {
    if (u_check == -1) return false;
    int curr = u_check;
    while (parent[curr] != -1) {
        curr = parent[curr];
        if (curr == v_target) return true;
    }
    return false;
}

void dfs_update_height(int u, int diff) {
    height[u] += diff;
    for (int v : children[u]) {
        dfs_update_height(v, diff);
    }
}

void update_ancestors(int u, long long val_A_change, bool subtract) {
    int curr = u;
    while (curr != -1) {
        if (subtract) subtree_A[curr] -= val_A_change;
        else subtree_A[curr] += val_A_change;

        int old_max_d = max_subtree_d[curr];
        int new_max_d = 0;
        for (int child : children[curr]) {
            new_max_d = max(new_max_d, 1 + max_subtree_d[child]);
        }
        max_subtree_d[curr] = new_max_d;
        
        if (old_max_d == new_max_d && parent[curr] != -1) break;
        curr = parent[curr];
    }
}


void simulated_annealing() {
    auto start_time = chrono::steady_clock::now();
    
    compute_aux_data();
    current_score = calculate_score();
    best_parent = parent;
    best_score = current_score;

    double T_start = 100, T_end = 0.1;
    uniform_real_distribution<> dist_double(0.0, 1.0);

    while (true) {
        auto now = chrono::steady_clock::now();
        double time_elapsed = chrono::duration_cast<chrono::milliseconds>(now - start_time).count();
        if (time_elapsed > 2800) break;

        double progress = time_elapsed / 2800.0;
        double T = T_start * pow(T_end / T_start, progress);

        int v = rng() % N;

        int old_p = parent[v];
        int new_p = -1;
        if (adj[v].empty()){
            continue;
        }

        int neighbor_idx = rng() % (adj[v].size() + 1);
        if (neighbor_idx < adj[v].size()){
            new_p = adj[v][neighbor_idx];
        }

        if (new_p == old_p) continue;
        
        if (new_p != -1) {
            if (is_descendant(new_p, v)) continue;
            if (height[new_p] + 1 + max_subtree_d[v] > H) continue;
        }
        
        long long h_v_old = height[v];
        long long h_v_new = (new_p == -1) ? 0 : height[new_p] + 1;
        long long delta_score = (h_v_new - h_v_old) * subtree_A[v];

        if (delta_score > 0 || exp(delta_score / T) > dist_double(rng)) {
            // Apply move
            current_score += delta_score;

            long long A_v_subtree = subtree_A[v];
            
            // Update ancestors
            if (old_p != -1) {
                update_ancestors(old_p, A_v_subtree, true);
            }
            if (new_p != -1) {
                update_ancestors(new_p, A_v_subtree, false);
            }
            
            // Update parent and children
            if (old_p != -1) {
                children[old_p].erase(find(children[old_p].begin(), children[old_p].end(), v));
            }
            parent[v] = new_p;
            if (new_p != -1) {
                children[new_p].push_back(v);
            }
            
            // Update height
            long long h_diff = h_v_new - h_v_old;
            if (h_diff != 0) {
                dfs_update_height(v, h_diff);
            }
            
            if (current_score > best_score) {
                best_score = current_score;
                best_parent = parent;
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> M >> H;
    A.resize(N);
    adj.resize(N);
    x.resize(N);
    y.resize(N);
    for (int i = 0; i < N; ++i) cin >> A[i];
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.push_back({u, v});
    }
    for (int i = 0; i < N; ++i) cin >> x[i] >> y[i];

    initial_solution();

    simulated_annealing();

    for (int i = 0; i < N; ++i) {
        cout << best_parent[i] << (i == N - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}