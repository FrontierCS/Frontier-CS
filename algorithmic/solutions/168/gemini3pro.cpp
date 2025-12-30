#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Maximum expected number of vertices and height
const int N_MAX = 1000;
const int H_LIMIT = 10;
const double TIME_LIMIT = 1.90; // Time limit for optimization

struct Node {
    int id;
    int beauty;
    int x, y;
    vector<int> adj;
    
    int parent = -1;
    vector<int> children;
    int child_pos = -1; // index in parent's children vector for O(1) removal
    
    long long sum_A; // Sum of beauty in the subtree
    int height = 0; // Max distance to a leaf in the subtree
    int h_counts[12]; // Histogram of children heights
};

int N, M, H;
Node nodes[N_MAX];
long long current_score = 0;
mt19937 rng(12345);

// Calculate depth of u (root is depth 0)
int get_depth_val(int u) {
    int d = 0;
    while (u != -1) {
        if (nodes[u].parent != -1) d++;
        u = nodes[u].parent;
    }
    return d;
}

// Check if v is an ancestor of u to prevent cycles
bool is_ancestor(int v, int u) {
    while (u != -1) {
        if (u == v) return true;
        u = nodes[u].parent;
    }
    return false;
}

// Update sum_A for ancestors
void update_sum_A(int u, long long delta) {
    while (u != -1) {
        nodes[u].sum_A += delta;
        u = nodes[u].parent;
    }
}

// Update height for ancestors based on children heights
void update_height(int u) {
    while (u != -1) {
        int old_h = nodes[u].height;
        int max_h = -1;
        // Find max height among children
        for (int h = H_LIMIT; h >= 0; --h) {
            if (nodes[u].h_counts[h] > 0) {
                max_h = h;
                break;
            }
        }
        int new_h = max_h + 1;
        if (new_h == old_h) break; // No change, stop propagation
        
        nodes[u].height = new_h;
        int p = nodes[u].parent;
        if (p != -1) {
            nodes[p].h_counts[old_h]--;
            nodes[p].h_counts[new_h]++;
        }
        u = p;
    }
}

void remove_child_from_vector(int p, int v) {
    int pos = nodes[v].child_pos;
    int last_v = nodes[p].children.back();
    nodes[p].children[pos] = last_v;
    nodes[last_v].child_pos = pos;
    nodes[p].children.pop_back();
}

void add_child_to_vector(int p, int v) {
    nodes[p].children.push_back(v);
    nodes[v].child_pos = nodes[p].children.size() - 1;
}

long long calculate_total_score() {
    long long score = 0;
    for (int i = 0; i < N; ++i) {
        score += (long long)(get_depth_val(i) + 1) * nodes[i].beauty;
    }
    return score;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> N >> M >> H)) return 0;
    for (int i = 0; i < N; ++i) cin >> nodes[i].beauty;
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        nodes[u].adj.push_back(v);
        nodes[v].adj.push_back(u);
    }
    for (int i = 0; i < N; ++i) cin >> nodes[i].x >> nodes[i].y;
    
    // Initialize with all roots
    for (int i = 0; i < N; ++i) {
        nodes[i].sum_A = nodes[i].beauty;
        nodes[i].height = 0;
        nodes[i].parent = -1;
        nodes[i].id = i;
        for(int j=0; j<=H; ++j) nodes[i].h_counts[j] = 0;
    }
    
    current_score = calculate_total_score();
    auto start_time = chrono::steady_clock::now();
    long long best_score = current_score;
    vector<int> best_parents(N, -1);
    
    double start_temp = 50.0; 
    double end_temp = 0.0;
    
    int iter = 0;
    while (true) {
        iter++;
        // Check time every 1024 iterations
        if ((iter & 1023) == 0) {
            auto curr_time = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(curr_time - start_time).count();
            if (elapsed > TIME_LIMIT) break;
        }
        
        // Pick random vertex v and random neighbor u (or -1)
        int v = rng() % N;
        int idx = rng() % (nodes[v].adj.size() + 1);
        int u = (idx == nodes[v].adj.size()) ? -1 : nodes[v].adj[idx];
        
        if (u == nodes[v].parent) continue;
        if (u == v) continue;
        if (u != -1 && is_ancestor(v, u)) continue; // Cycle check
        
        // Check depth constraint
        int depth_u = (u == -1) ? -1 : get_depth_val(u);
        int new_depth_v = (u == -1) ? 0 : depth_u + 1;
        if (new_depth_v + nodes[v].height > H) continue;
        
        // Calculate score delta
        int old_depth_v = get_depth_val(v);
        long long delta = (long long)(new_depth_v - old_depth_v) * nodes[v].sum_A;
        
        // Acceptance criteria (Simulated Annealing)
        bool accept = false;
        if (delta >= 0) accept = true;
        else {
            auto curr_time = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(curr_time - start_time).count();
            double progress = elapsed / TIME_LIMIT;
            double temp = start_temp + (end_temp - start_temp) * progress;
            if (exp(delta / temp) > (double)(rng()%10000)/10000.0) accept = true;
        }
        
        if (accept) {
            int old_p = nodes[v].parent;
            long long sub_sum = nodes[v].sum_A;
            int h_v = nodes[v].height;
            
            // Remove v from old parent
            if (old_p != -1) {
                remove_child_from_vector(old_p, v);
                nodes[old_p].h_counts[h_v]--;
                update_sum_A(old_p, -sub_sum);
                update_height(old_p);
            }
            
            nodes[v].parent = u;
            
            // Add v to new parent
            if (u != -1) {
                add_child_to_vector(u, v);
                nodes[u].h_counts[h_v]++;
                update_sum_A(u, sub_sum);
                update_height(u);
            }
            
            current_score += delta;
            
            // Update best solution found so far
            if (current_score > best_score) {
                best_score = current_score;
                for(int i=0; i<N; ++i) best_parents[i] = nodes[i].parent;
            }
        }
    }
    
    // Output best solution
    for (int i = 0; i < N; ++i) {
        cout << best_parents[i] << (i == N - 1 ? "" : " ");
    }
    cout << endl;
    return 0;
}