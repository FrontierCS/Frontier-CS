#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <chrono>
#include <random>

using namespace std;

// Constants
const int MAX_N = 1000;
const int MAX_H = 10;
const double TIME_LIMIT = 1.95;

// Global Data
int N, M, H;
int A[MAX_N];
struct Point { int x, y; } coords[MAX_N];
vector<int> adj[MAX_N];

// State
int parent[MAX_N];
vector<int> children[MAX_N];
int depth[MAX_N];
int height[MAX_N]; // max distance to a leaf in the subtree
int height_counts[MAX_N][MAX_H + 2]; // height_counts[u][k] is num children with height k-1
long long subtree_beauty[MAX_N];
long long current_score = 0;

// Random number generator
unsigned long long rng_seed = 123456789;
unsigned long long xorshift64() {
    unsigned long long x = rng_seed;
    x ^= x << 13;
    x ^= x >> 7;
    x ^= x << 17;
    return rng_seed = x;
}
int rand_int(int l, int r) { // [l, r]
    return l + (xorshift64() % (r - l + 1));
}
double rand_double() {
    return (xorshift64() % 1000000) / 1000000.0;
}

// Timer
auto start_time = chrono::high_resolution_clock::now();
double get_time() {
    auto now = chrono::high_resolution_clock::now();
    return chrono::duration<double>(now - start_time).count();
}

// Helper: Calculate initial score and auxiliary data from parent array
void rebuild_state() {
    // Reset data
    for (int i = 0; i < N; ++i) {
        children[i].clear();
        depth[i] = 0;
        height[i] = 0;
        subtree_beauty[i] = A[i];
        for (int k = 0; k <= H + 1; ++k) height_counts[i][k] = 0;
    }
    
    // Build children
    vector<int> roots;
    for (int i = 0; i < N; ++i) {
        if (parent[i] != -1) {
            children[parent[i]].push_back(i);
        } else {
            roots.push_back(i);
        }
    }

    // DFS for depths
    vector<int> stk;
    vector<int> order; // post-order for bottom-up calculation
    
    for (int r : roots) {
        stk.push_back(r);
        depth[r] = 0;
    }
    
    while (!stk.empty()) {
        int u = stk.back();
        stk.pop_back();
        order.push_back(u);
        for (int v : children[u]) {
            depth[v] = depth[u] + 1;
            stk.push_back(v);
        }
    }
    
    reverse(order.begin(), order.end());
    
    current_score = 0;
    for (int u : order) {
        height[u] = 0;
        subtree_beauty[u] = A[u];
        for (int v : children[u]) {
            int h_v = height[v] + 1;
            if (h_v <= H + 1) height_counts[u][h_v]++;
            height[u] = max(height[u], h_v);
            subtree_beauty[u] += subtree_beauty[v];
        }
        current_score += (long long)(depth[u] + 1) * A[u];
    }
}

// Update depths in subtree of u
void update_depths_bfs(int root, int start_depth) {
    static int q[MAX_N];
    int head = 0, tail = 0;
    
    depth[root] = start_depth;
    q[tail++] = root;
    
    while(head < tail) {
        int u = q[head++];
        int d = depth[u];
        for(int v : children[u]) {
            depth[v] = d + 1;
            q[tail++] = v;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M >> H)) return 0;
    for (int i = 0; i < N; ++i) cin >> A[i];
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    for (int i = 0; i < N; ++i) cin >> coords[i].x >> coords[i].y;

    // Initialization
    for (int i = 0; i < N; ++i) parent[i] = -1;
    rebuild_state();

    // Greedy Construction
    vector<int> sorted_idx(N);
    iota(sorted_idx.begin(), sorted_idx.end(), 0);
    sort(sorted_idx.begin(), sorted_idx.end(), [&](int i, int j){ return A[i] < A[j]; });

    for(int u : sorted_idx) {
        // Since we process from small A to large A, and initially all are roots,
        // we can try to attach u to an existing tree to maximize its depth.
        // u is currently a root (singleton).
        
        int best_v = -1;
        int max_d = -1;
        
        // Shuffle neighbors to avoid bias? Not strictly necessary but good.
        // Skipping shuffle for speed, simple iteration is fine.
        
        for(int v : adj[u]) {
            // Valid if depth[v] + 1 <= H (since height[u]=0)
            if (depth[v] + 1 <= H) {
                if (depth[v] > max_d) {
                    max_d = depth[v];
                    best_v = v;
                }
            }
        }
        
        if (best_v != -1) {
            // Link u to best_v
            parent[u] = best_v;
            children[best_v].push_back(u);
            depth[u] = depth[best_v] + 1;
            
            // Incremental update up
            int curr = best_v;
            int add_val = 1; // height[u]+1
            int remove_val = -1;
            
            while(curr != -1) {
                subtree_beauty[curr] += A[u];
                
                if(remove_val != -1 && remove_val <= H+1) height_counts[curr][remove_val]--;
                if(add_val <= H+1) height_counts[curr][add_val]++;
                
                int new_h = 0;
                for(int k=H+1; k>=1; --k) if(height_counts[curr][k] > 0) { new_h=k; break; }
                
                if(new_h == height[curr]) {
                    // Height didn't change, but we must propagate beauty update.
                    // Just continue loop to update beauty.
                    // But height logic stops here.
                    // We can optimize: separate loops?
                    // For now, simple loop is fine.
                    // But we must stop updating height_counts further up if height didn't change.
                    remove_val = -1; // stop remove
                    add_val = -1; // stop add
                    // Beauty still needs update, continue loop
                } else {
                    remove_val = height[curr] + 1;
                    height[curr] = new_h;
                    add_val = height[curr] + 1;
                }
                curr = parent[curr];
            }
        }
    }
    
    // Ensure everything is consistent
    rebuild_state();

    double t = get_time();
    double start_temp = 200.0;
    double end_temp = 0.0;
    
    int iter = 0;
    while (true) {
        iter++;
        if ((iter & 255) == 0) {
            t = get_time();
            if (t > TIME_LIMIT) break;
        }

        double progress = t / TIME_LIMIT;
        double temp = start_temp + (end_temp - start_temp) * progress;

        int u = rand_int(0, N - 1);
        int old_p = parent[u];
        
        // Pick random neighbor or -1
        int new_p = -1;
        if (!adj[u].empty()) {
            int idx = rand_int(0, (int)adj[u].size()); 
            if (idx < adj[u].size()) new_p = adj[u][idx];
        }
        
        if (new_p == old_p) continue;

        // Validity Checks
        // 1. Cycle: u cannot be ancestor of new_p
        if (new_p != -1) {
            bool cycle = false;
            int curr = new_p;
            while (curr != -1) {
                if (curr == u) { cycle = true; break; }
                curr = parent[curr];
            }
            if (cycle) continue;
        }
        
        // 2. Depth Constraint
        int new_depth_u = (new_p == -1 ? 0 : depth[new_p] + 1);
        if (new_depth_u + height[u] > H) continue;

        // Score Diff
        int delta_depth = new_depth_u - depth[u];
        long long score_diff = delta_depth * subtree_beauty[u];
        
        if (score_diff >= 0 || exp(score_diff / temp) > rand_double()) {
            // Apply Move
            
            // Remove u from old_p
            if (old_p != -1) {
                for (size_t k = 0; k < children[old_p].size(); ++k) {
                    if (children[old_p][k] == u) {
                        children[old_p].erase(children[old_p].begin() + k);
                        break;
                    }
                }
                
                // Update ancestors of old_p
                int curr = old_p;
                int remove_val = height[u] + 1;
                int add_val = -1;
                
                while(curr != -1) {
                    subtree_beauty[curr] -= subtree_beauty[u];
                    
                    if (remove_val <= H+1) height_counts[curr][remove_val]--;
                    if (add_val != -1 && add_val <= H+1) height_counts[curr][add_val]++;
                    
                    int new_h = 0;
                    for(int k=H+1; k>=1; --k) if(height_counts[curr][k] > 0) { new_h=k; break; }
                    
                    if(new_h == height[curr]) {
                        remove_val = -1; add_val = -1; // stop propagating height changes
                    } else {
                        remove_val = height[curr] + 1;
                        height[curr] = new_h;
                        add_val = height[curr] + 1;
                    }
                    curr = parent[curr];
                }
            }
            
            parent[u] = new_p;
            
            // Add u to new_p
            if (new_p != -1) {
                children[new_p].push_back(u);
                
                int curr = new_p;
                int remove_val = -1;
                int add_val = height[u] + 1;
                
                while(curr != -1) {
                    subtree_beauty[curr] += subtree_beauty[u];
                    
                    if (remove_val != -1 && remove_val <= H+1) height_counts[curr][remove_val]--;
                    if (add_val <= H+1) height_counts[curr][add_val]++;
                    
                    int new_h = 0;
                    for(int k=H+1; k>=1; --k) if(height_counts[curr][k] > 0) { new_h=k; break; }
                    
                    if(new_h == height[curr]) {
                        remove_val = -1; add_val = -1; 
                    } else {
                        remove_val = height[curr] + 1;
                        height[curr] = new_h;
                        add_val = height[curr] + 1;
                    }
                    curr = parent[curr];
                }
            }
            
            // Update depths
            if (delta_depth != 0) {
                update_depths_bfs(u, new_depth_u);
            }
            
            current_score += score_diff;
        }
    }

    // Output
    for (int i = 0; i < N; ++i) {
        cout << parent[i] << (i == N - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}