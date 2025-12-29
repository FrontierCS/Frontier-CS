#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <chrono>

using namespace std;

// Fast Random Number Generator
struct XorShift {
    unsigned int x = 123456789;
    unsigned int y = 362436069;
    unsigned int z = 521288629;
    unsigned int w = 88675123;
    inline unsigned int next() {
        unsigned int t = x ^ (x << 11);
        x = y; y = z; z = w;
        return w = (w ^ (w >> 19)) ^ (t ^ (t >> 8));
    }
    inline int next_range(int L, int R) { 
        return L + (next() % (R - L + 1));
    }
} rng;

struct Point {
    int x, y;
};

struct EdgeInfo {
    int u, v, id;
    int d;
};

struct SimEdge {
    int u, v; 
    int weight; // base distance d
};

// DSU for maintaining the main connectivity state
struct DSU {
    vector<int> parent;
    DSU(int n) : parent(n) {
        iota(parent.begin(), parent.end(), 0);
    }
    int find(int i) {
        if (parent[i] == i) return i;
        return parent[i] = find(parent[i]);
    }
    bool unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) {
            parent[root_i] = root_j;
            return true;
        }
        return false;
    }
    bool same(int i, int j) {
        return find(i) == find(j);
    }
};

// Simplified DSU for simulations (faster, fixed size)
struct SmallDSU {
    int parent[405];
    void init(int k) {
        for(int i=0; i<k; ++i) parent[i] = i;
    }
    int find(int i) {
        int root = i;
        while(root != parent[root]) root = parent[root];
        while(i != root) {
            int nxt = parent[i];
            parent[i] = root;
            i = nxt;
        }
        return root;
    }
    bool unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) {
            parent[root_i] = root_j;
            return true;
        }
        return false;
    }
};

struct Node {
    int to;
    int weight;
};

// Global variables to reduce allocation overhead
int N = 400;
int M = 1995;
const int INF = 1e9;
vector<Point> points;
vector<EdgeInfo> all_edges;
vector<SimEdge> current_sim_edges;
vector<int> buckets[3505]; // For counting sort (weights up to ~3400)
vector<int> used_weights;
vector<Node> adj[405]; // Adjacency list for MST in simulation
SmallDSU sim_dsu;

// BFS structures
int q_queue[405];
int p_parent[405];
int dist_edge[405];
bool visited[405];

// Finds the maximum weight edge on the path between start and end in the MST
int find_path_max_weight(int start, int end, int num_nodes) {
    if (start == end) return 0;
    
    for(int i=0; i<num_nodes; ++i) visited[i] = false;
    
    int head = 0, tail = 0;
    q_queue[tail++] = start;
    visited[start] = true;
    p_parent[start] = -1;
    
    bool found = false;
    while(head < tail) {
        int u = q_queue[head++];
        if (u == end) {
            found = true;
            break;
        }
        for (auto& edge : adj[u]) {
            int v = edge.to;
            if (!visited[v]) {
                visited[v] = true;
                p_parent[v] = u;
                dist_edge[v] = edge.weight;
                q_queue[tail++] = v;
            }
        }
    }
    
    if (!found) return INF;
    
    int max_w = 0;
    int curr = end;
    while(curr != start) {
        if (dist_edge[curr] > max_w) max_w = dist_edge[curr];
        curr = p_parent[curr];
    }
    return max_w;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    points.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> points[i].x >> points[i].y;
    }
    all_edges.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> all_edges[i].u >> all_edges[i].v;
        all_edges[i].id = i;
        double dx = points[all_edges[i].u].x - points[all_edges[i].v].x;
        double dy = points[all_edges[i].u].y - points[all_edges[i].v].y;
        all_edges[i].d = (int)round(sqrt(dx*dx + dy*dy));
    }

    DSU main_dsu(N);
    vector<int> comp_mapping(N);
    vector<int> root_to_id(N);
    
    used_weights.reserve(3500);
    current_sim_edges.reserve(M);

    int K_SIMS = 150; 
    auto start_time = chrono::high_resolution_clock::now();

    for (int i = 0; i < M; ++i) {
        int l_i;
        cin >> l_i;

        int u = all_edges[i].u;
        int v = all_edges[i].v;

        // If vertices are already connected, we don't need this edge (avoids cycles)
        if (main_dsu.same(u, v)) {
            cout << "0" << endl;
            continue;
        }

        // Adaptive Simulation Count based on time
        if ((i & 15) == 0) {
            auto curr_time = chrono::high_resolution_clock::now();
            long long diff = chrono::duration_cast<chrono::milliseconds>(curr_time - start_time).count();
            double progress = (double)(i + 1) / M;
            double estimated_total = diff / max(progress, 0.0001);
            if (estimated_total > 1850) {
                K_SIMS = max(10, (int)(K_SIMS * 0.7));
            }
        }

        // Map current components to 0..comp_count-1
        int comp_count = 0;
        fill(root_to_id.begin(), root_to_id.end(), -1);
        
        for(int n=0; n<N; ++n) {
            int r = main_dsu.find(n);
            if(root_to_id[r] == -1) {
                root_to_id[r] = comp_count++;
            }
            comp_mapping[n] = root_to_id[r];
        }

        int u_comp = comp_mapping[u];
        int v_comp = comp_mapping[v];

        // Filter future edges to only those connecting different components
        current_sim_edges.clear();
        for (int j = i + 1; j < M; ++j) {
            int uc = comp_mapping[all_edges[j].u];
            int vc = comp_mapping[all_edges[j].v];
            if (uc != vc) {
                current_sim_edges.push_back({uc, vc, all_edges[j].d});
            }
        }

        long long sum_max_weight = 0;
        
        // Monte Carlo Simulation
        for (int k = 0; k < K_SIMS; ++k) {
            used_weights.clear();
            
            // Assign random weights and place into buckets for Counting Sort
            for(const auto& edge : current_sim_edges) {
                 int w = rng.next_range(edge.weight, 3 * edge.weight);
                 if (buckets[w].empty()) used_weights.push_back(w);
                 buckets[w].push_back((edge.u << 16) | edge.v);
            }
            
            sort(used_weights.begin(), used_weights.end());

            sim_dsu.init(comp_count);
            for(int c=0; c<comp_count; ++c) adj[c].clear();
            
            // Kruskal's Algorithm using sorted buckets
            for(int w : used_weights) {
                for(int val : buckets[w]) {
                    int eu = val >> 16;
                    int ev = val & 0xFFFF;
                    if (sim_dsu.unite(eu, ev)) {
                        adj[eu].push_back({ev, w});
                        adj[ev].push_back({eu, w});
                    }
                }
                buckets[w].clear();
            }
            
            // Find max weight on the path between u_comp and v_comp in the MST
            int mw = find_path_max_weight(u_comp, v_comp, comp_count);
            sum_max_weight += mw;
        }

        // Decision: Accept if l_i is smaller than the expected bottleneck capacity
        // using future edges.
        if ( (long long)l_i * K_SIMS < sum_max_weight ) {
            cout << "1" << endl;
            main_dsu.unite(u, v);
        } else {
            cout << "0" << endl;
        }
    }

    return 0;
}