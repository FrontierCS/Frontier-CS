#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <numeric>
#include <chrono>
#include <random>

using namespace std;

// Structure to hold vertex data
struct Vertex {
    int id;
    int a;
    int x, y;
    vector<int> adj;
};

// Global variables for problem data and state
int N, M, H;
vector<Vertex> vertices;
vector<int> parent;
vector<vector<int>> children;
vector<int> depth;
vector<long long> sub_sum_a;
vector<int> sub_height; // Max distance to a leaf in the subtree

long long current_score = 0;
mt19937 rng(12345);

// Recompute sub_sum_a and sub_height for node u based on its children
void update_subtree_info(int u) {
    long long sum = vertices[u].a;
    int h = 0;
    for (int c : children[u]) {
        sum += sub_sum_a[c];
        h = max(h, sub_height[c] + 1);
    }
    sub_sum_a[u] = sum;
    sub_height[u] = h;
}

// Update info for u and its ancestors
void update_path_up(int u) {
    int curr = u;
    while (curr != -1) {
        update_subtree_info(curr);
        curr = parent[curr];
    }
}

// Recursively update depths for u and its descendants
void update_depths(int u, int d) {
    depth[u] = d;
    for (int c : children[u]) {
        update_depths(c, d + 1);
    }
}

// Calculate total score from scratch (for validation)
long long calculate_total_score() {
    long long score = 0;
    for (int i = 0; i < N; ++i) {
        score += (long long)(depth[i] + 1) * vertices[i].a;
    }
    return score;
}

// Check if target is in the subtree of u (i.e., u is an ancestor of target)
bool is_descendant(int u, int target) {
    int curr = u;
    while (curr != -1) {
        if (curr == target) return true;
        curr = parent[curr];
    }
    return false;
}

void solve() {
    // Fast IO
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M >> H)) return;

    vertices.resize(N);
    for (int i = 0; i < N; ++i) {
        vertices[i].id = i;
        cin >> vertices[i].a;
    }
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        vertices[u].adj.push_back(v);
        vertices[v].adj.push_back(u);
    }
    for (int i = 0; i < N; ++i) {
        cin >> vertices[i].x >> vertices[i].y;
    }

    // Initialize state
    parent.assign(N, -1);
    children.assign(N, vector<int>());
    depth.assign(N, 0);
    sub_sum_a.assign(N, 0);
    sub_height.assign(N, 0);

    // Initial Solution Construction: Greedy
    // Sort vertices by beauty value A ascending
    // We want low beauty nodes to be roots/high up, high beauty nodes to be deep
    vector<int> sorted_indices(N);
    iota(sorted_indices.begin(), sorted_indices.end(), 0);
    sort(sorted_indices.begin(), sorted_indices.end(), [&](int i, int j) {
        return vertices[i].a < vertices[j].a;
    });

    vector<bool> placed(N, false);
    for (int i : sorted_indices) {
        int best_p = -1;
        int max_d = -1;
        
        // Look for a placed neighbor to attach to
        for (int neighbor : vertices[i].adj) {
            if (placed[neighbor]) {
                if (depth[neighbor] + 1 <= H) {
                    // We prefer deeper parents to maximize depth of i
                    if (depth[neighbor] > max_d) {
                        max_d = depth[neighbor];
                        best_p = neighbor;
                    }
                }
            }
        }
        
        if (best_p != -1) {
            parent[i] = best_p;
            children[best_p].push_back(i);
            depth[i] = max_d + 1;
        } else {
            // Become a root
            parent[i] = -1;
            depth[i] = 0;
        }
        placed[i] = true;
    }
    
    // Compute initial subtree info (post-order / bottom-up logic needed)
    auto compute_info_dfs = [&](auto&& self, int u) -> void {
         long long sum = vertices[u].a;
         int h = 0;
         for(int c : children[u]){
             self(self, c);
             sum += sub_sum_a[c];
             h = max(h, sub_height[c] + 1);
         }
         sub_sum_a[u] = sum;
         sub_height[u] = h;
    };
    
    for(int i=0; i<N; ++i) {
        if(parent[i] == -1) compute_info_dfs(compute_info_dfs, i);
    }

    current_score = calculate_total_score();
    
    // Hill Climbing / Simulated Annealing
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.95; 
    
    // SA Parameters
    double start_temp = 200.0;
    double end_temp = 0.0;
    
    long long best_score = current_score;
    vector<int> best_parent = parent;

    int iter_count = 0;

    while (true) {
        iter_count++;
        if ((iter_count & 127) == 0) {
            auto curr_time = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(curr_time - start_time).count();
            if (elapsed > time_limit) break;
        }

        // Pick a random node
        int v = rng() % N;
        int old_p = parent[v];
        
        // Pick a random new parent from neighbors + {-1}
        const vector<int>& adj = vertices[v].adj;
        if (adj.empty()) continue; 
        
        int idx = rng() % (adj.size() + 1);
        int new_p = (idx == adj.size()) ? -1 : adj[idx];
        
        if (new_p == old_p) continue;

        // Validity Checks
        // 1. Cycle Check: new_p must not be in subtree of v
        if (new_p != -1) {
            if (is_descendant(new_p, v)) continue;
        }

        // 2. Height Constraint Check
        int new_depth_v = (new_p == -1) ? 0 : depth[new_p] + 1;
        int depth_diff = new_depth_v - depth[v];
        
        if (depth_diff > 0) {
            // Check if moving v here makes its subtree too deep
            // The max depth relative to v is sub_height[v].
            // Absolute max depth will be new_depth_v + sub_height[v].
            if (new_depth_v + sub_height[v] > H) continue;
        }

        // Calculate Score Delta
        // Delta = shift * sum of A in subtree
        long long delta = (long long)depth_diff * sub_sum_a[v];

        bool accept = false;
        if (delta >= 0) {
            accept = true;
        } else {
            auto curr_time = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(curr_time - start_time).count();
            double temp = start_temp + (end_temp - start_temp) * (elapsed / time_limit);
            if (temp > 0.00001) {
                double prob = exp(delta / temp);
                if (generate_canonical<double, 10>(rng) < prob) {
                    accept = true;
                }
            }
        }

        if (accept) {
            // Update Data Structures
            
            // Remove from old parent's children
            if (old_p != -1) {
                auto& kids = children[old_p];
                for (size_t k = 0; k < kids.size(); ++k) {
                    if (kids[k] == v) {
                        kids[k] = kids.back();
                        kids.pop_back();
                        break;
                    }
                }
            }
            
            // Add to new parent's children
            if (new_p != -1) {
                children[new_p].push_back(v);
            }
            
            parent[v] = new_p;
            
            // Update depths in subtree
            update_depths(v, new_depth_v);
            
            // Update sub_sum and sub_height for ancestors
            if (old_p != -1) update_path_up(old_p);
            if (new_p != -1) update_path_up(new_p);
            
            current_score += delta;
            
            if (current_score > best_score) {
                best_score = current_score;
                best_parent = parent;
            }
        }
    }

    // Output best solution
    for (int i = 0; i < N; ++i) {
        cout << best_parent[i] << (i == N - 1 ? "" : " ");
    }
    cout << endl;
}

int main() {
    solve();
    return 0;
}