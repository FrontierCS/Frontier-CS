#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <random>

using namespace std;

const int MAXN = 1005;

int N, M, H;
int A[MAXN];
vector<int> adj[MAXN];
int X[MAXN], Y[MAXN];

// State
int parent[MAXN];
vector<int> children[MAXN];
int depth[MAXN];
int height[MAXN]; // max distance to leaf in subtree
long long sub_sumA[MAXN]; // sum of A in subtree

// Random
unsigned long long rng_state = 123456789;
inline unsigned long long xorshift() {
    rng_state ^= (rng_state << 13);
    rng_state = (rng_state >> 7);
    rng_state ^= (rng_state << 17);
    return rng_state;
}
inline double rand_double() {
    return (double)xorshift() / __UINT64_MAX__;
}
inline int rand_int(int n) {
    return xorshift() % n;
}

// Helpers
void update_subtree_depth(int u, int current_depth) {
    depth[u] = current_depth;
    for (int v : children[u]) {
        update_subtree_depth(v, current_depth + 1);
    }
}

// Recalculate height for u from children
void recalc_height(int u) {
    int max_h = -1;
    for (int v : children[u]) {
        if (height[v] > max_h) max_h = height[v];
    }
    height[u] = max_h + 1;
}

// Propagate height changes up
void propagate_height(int u) {
    while (u != -1) {
        int old_h = height[u];
        recalc_height(u);
        if (height[u] == old_h) break;
        u = parent[u];
    }
}

// Propagate sumA changes up
void propagate_sumA(int u, long long diff) {
    while (u != -1) {
        sub_sumA[u] += diff;
        u = parent[u];
    }
}

bool is_ancestor(int u, int v) {
    // Check if u is ancestor of v
    if (depth[v] < depth[u]) return false;
    
    int curr = v;
    while (curr != -1) {
        if (curr == u) return true;
        if (depth[curr] < depth[u]) return false; 
        curr = parent[curr];
    }
    return false;
}

long long current_score = 0;

void compute_initial_state() {
    for (int i = 0; i < N; ++i) {
        parent[i] = -1;
        children[i].clear();
        depth[i] = 0;
        height[i] = 0;
        sub_sumA[i] = A[i];
    }
    
    current_score = 0;
    for(int i=0; i<N; ++i) current_score += (long long)(depth[i] + 1) * A[i];
}

int best_parent[MAXN];
long long best_score = -1;

void save_solution() {
    if (current_score > best_score) {
        best_score = current_score;
        for(int i=0; i<N; ++i) best_parent[i] = parent[i];
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
    for (int i = 0; i < N; ++i) cin >> X[i] >> Y[i];

    compute_initial_state();
    save_solution();

    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.90;
    double temp_start = 2500.0;
    double temp_end = 0.0;
    
    int iter = 0;
    
    while (true) {
        iter++;
        if ((iter & 1023) == 0) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - start_time).count();
            if (elapsed > time_limit) break;
        }

        // Optimization: Calculate temp inside the batch check? 
        // For smoother annealing, calculating every step is fine, 
        // but to save clock calls we can approximate or use iter count if total iters known.
        // Since we don't know total iters, we'll check clock occasionally and interpolate.
        // Or simply:
        static double current_temp = temp_start;
        if ((iter & 1023) == 0) {
             double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start_time).count();
             current_temp = temp_start + (temp_end - temp_start) * (elapsed / time_limit);
             if (current_temp < 0.0001) current_temp = 0.0001;
        }

        // Pick random node v
        int v = rand_int(N);
        int old_p = parent[v];
        
        // Pick random neighbor or -1
        int new_p = -1;
        int sz = adj[v].size();
        if (sz > 0) {
            int idx = rand_int(sz + 1); // +1 for -1 option
            if (idx < sz) new_p = adj[v][idx];
        }

        if (new_p == old_p) continue;

        // Check validity
        // 1. Cycle check: if new_p is in subtree of v (i.e., v is ancestor of new_p)
        if (new_p != -1) {
             if (is_ancestor(v, new_p)) continue;
        }

        // 2. Depth constraint
        int new_depth_v = (new_p == -1) ? 0 : depth[new_p] + 1;
        if (new_depth_v + height[v] > H) continue;

        // Calculate score delta
        long long score_diff = sub_sumA[v] * (long long)(new_depth_v - depth[v]);

        if (score_diff >= 0 || rand_double() < exp(score_diff / current_temp)) {
            // Apply move
            
            // 1. Remove from old parent
            if (old_p != -1) {
                // remove v from children[old_p]
                for(size_t i=0; i<children[old_p].size(); ++i) {
                    if (children[old_p][i] == v) {
                        children[old_p][i] = children[old_p].back();
                        children[old_p].pop_back();
                        break;
                    }
                }
                propagate_sumA(old_p, -sub_sumA[v]);
                propagate_height(old_p);
            }

            // 2. Add to new parent
            if (new_p != -1) {
                children[new_p].push_back(v);
                propagate_sumA(new_p, sub_sumA[v]);
                propagate_height(new_p);
            }

            // 3. Update parent pointer
            parent[v] = new_p;

            // 4. Update depths in subtree
            update_subtree_depth(v, new_depth_v);

            current_score += score_diff;
            if (current_score > best_score) {
                save_solution();
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << best_parent[i] << (i == N - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}