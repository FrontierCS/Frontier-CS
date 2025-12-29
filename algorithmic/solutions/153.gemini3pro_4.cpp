#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <chrono>
#include <iomanip>

using namespace std;

// Structure to represent a point in 2D plane
struct Point {
    int x, y;
};

// Structure to represent an edge
struct Edge {
    int u, v;
    int d;
    int id;
};

// Disjoint Set Union (DSU) structure for efficient connectivity checks
struct DSU {
    vector<int> parent;
    DSU(int n) {
        parent.resize(n);
        iota(parent.begin(), parent.end(), 0);
    }
    int find(int x) {
        if (parent[x] == x) return x;
        return parent[x] = find(parent[x]);
    }
    void unite(int x, int y) {
        int rootX = find(x);
        int rootY = find(y);
        if (rootX != rootY) parent[rootX] = rootY;
    }
    bool same(int x, int y) {
        return find(x) == find(y);
    }
};

// Global variables
int N, M;
vector<Point> points;
vector<Edge> all_edges;
DSU accepted_dsu(0);

// Fast Pseudo-Random Number Generator (Xorshift)
uint32_t xorshift_state = 123456789;
inline uint32_t xorshift() {
    uint32_t x = xorshift_state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    xorshift_state = x;
    return x;
}

// Structure for edges used in simulation (with generated weight)
struct SimEdge {
    int u, v, w;
    bool operator<(const SimEdge& other) const {
        return w < other.w;
    }
};

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Read initial data
    if (!(cin >> N >> M)) return 0;
    points.resize(N);
    for (int i = 0; i < N; ++i) cin >> points[i].x >> points[i].y;

    all_edges.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> all_edges[i].u >> all_edges[i].v;
        double dx = points[all_edges[i].u].x - points[all_edges[i].v].x;
        double dy = points[all_edges[i].u].y - points[all_edges[i].v].y;
        all_edges[i].d = (int)round(sqrt(dx*dx + dy*dy));
        all_edges[i].id = i;
    }

    // Initialize DSU
    accepted_dsu = DSU(N);
    
    // Pre-allocate memory to avoid reallocation overhead in loop
    vector<SimEdge> sim_edges;
    sim_edges.reserve(M);
    vector<vector<pair<int, int>>> adj(N);
    vector<int> q(N); // Queue for BFS
    vector<int> parent(N);
    vector<int> path_edge_weight(N);
    vector<int> node_token(N, 0);
    int visited_token = 0;

    auto start_time = chrono::high_resolution_clock::now();
    // Time limit is 2.0s, we use 1.85s to be safe
    double time_limit = 1.85; 

    // Process edges one by one
    for (int i = 0; i < M; ++i) {
        int l_i;
        cin >> l_i;

        int u = all_edges[i].u;
        int v = all_edges[i].v;

        // If u and v are already connected by accepted edges, we don't need this edge
        if (accepted_dsu.same(u, v)) {
            cout << "0" << endl;
            continue;
        }

        // Bridge Check: If this edge is necessary for connectivity, we MUST take it.
        // We check if u and v are connected using all other available edges (accepted + future).
        DSU temp_dsu = accepted_dsu; 
        for (int j = i + 1; j < M; ++j) {
            temp_dsu.unite(all_edges[j].u, all_edges[j].v);
        }
        
        if (!temp_dsu.same(u, v)) {
            // Bridge: must accept
            cout << "1" << endl;
            accepted_dsu.unite(u, v);
            continue;
        }

        // Decision making via Simulation
        // We calculate a threshold T which is the expected weight of the max-weight edge 
        // on the path between u and v in the MST of future edges.
        // If l_i < T, we accept.
        
        auto curr_time = chrono::high_resolution_clock::now();
        chrono::duration<double> elapsed = curr_time - start_time;
        double remaining = time_limit - elapsed.count();
        double time_for_this = remaining / (M - i);
        
        int cnt = 0;
        long long sum_threshold = 0;
        
        // 1. Expected Value Simulation (Mean Field Approximation)
        {
            sim_edges.clear();
            for (int j = i + 1; j < M; ++j) {
                // We only care about edges connecting different components of accepted graph
                int root_u = accepted_dsu.find(all_edges[j].u);
                int root_v = accepted_dsu.find(all_edges[j].v);
                if (root_u != root_v) {
                    sim_edges.push_back({root_u, root_v, 2 * all_edges[j].d});
                }
            }
            sort(sim_edges.begin(), sim_edges.end());
            
            // Build MST on components
            DSU sim_dsu(N);
            for(int k=0; k<N; ++k) adj[k].clear();

            int root_u_target = accepted_dsu.find(u);
            int root_v_target = accepted_dsu.find(v);
            
            for (const auto& edge : sim_edges) {
                if (!sim_dsu.same(edge.u, edge.v)) {
                    sim_dsu.unite(edge.u, edge.v);
                    adj[edge.u].push_back({edge.v, edge.w});
                    adj[edge.v].push_back({edge.u, edge.w});
                }
            }
            
            // Find max edge on path between root_u_target and root_v_target using BFS
            int q_start = 0, q_end = 0;
            q[q_end++] = root_u_target;
            visited_token++;
            node_token[root_u_target] = visited_token;
            parent[root_u_target] = -1;
            path_edge_weight[root_u_target] = 0;
            
            bool found = false;
            while(q_start < q_end) {
                int curr = q[q_start++];
                if (curr == root_v_target) {
                    found = true;
                    break;
                }
                for (auto& neighbor : adj[curr]) {
                    int nxt = neighbor.first;
                    int w = neighbor.second;
                    if (node_token[nxt] != visited_token) {
                        node_token[nxt] = visited_token;
                        parent[nxt] = curr;
                        path_edge_weight[nxt] = w;
                        q[q_end++] = nxt;
                    }
                }
            }
            
            int max_w = 1000000000; 
            if (found) {
                max_w = 0;
                int curr = root_v_target;
                while (curr != root_u_target) {
                    if (path_edge_weight[curr] > max_w) max_w = path_edge_weight[curr];
                    curr = parent[curr];
                }
            }
            sum_threshold += max_w;
            cnt++;
        }

        // 2. Monte Carlo Simulations
        while (true) {
            // Check time budget periodically
            if ((cnt & 15) == 0) {
                 auto now = chrono::high_resolution_clock::now();
                 chrono::duration<double> t = now - start_time;
                 if ((t.count() - elapsed.count()) > time_for_this) break;
                 if (cnt > 200) break; // Limit iterations
            }
            
            sim_edges.clear();
            for (int j = i + 1; j < M; ++j) {
                int root_u = accepted_dsu.find(all_edges[j].u);
                int root_v = accepted_dsu.find(all_edges[j].v);
                if (root_u != root_v) {
                    int d = all_edges[j].d;
                    int w = d + ((uint64_t)xorshift() * (2 * d + 1) >> 32);
                    sim_edges.push_back({root_u, root_v, w});
                }
            }
            sort(sim_edges.begin(), sim_edges.end());
            
            DSU sim_dsu(N);
            for(int k=0; k<N; ++k) adj[k].clear();

            int root_u_target = accepted_dsu.find(u);
            int root_v_target = accepted_dsu.find(v);
            
            for (const auto& edge : sim_edges) {
                if (!sim_dsu.same(edge.u, edge.v)) {
                    sim_dsu.unite(edge.u, edge.v);
                    adj[edge.u].push_back({edge.v, edge.w});
                    adj[edge.v].push_back({edge.u, edge.w});
                }
            }
            
            int q_start = 0, q_end = 0;
            q[q_end++] = root_u_target;
            visited_token++;
            node_token[root_u_target] = visited_token;
            parent[root_u_target] = -1;
            
            bool found = false;
            while(q_start < q_end) {
                int curr = q[q_start++];
                if (curr == root_v_target) {
                    found = true;
                    break;
                }
                for (auto& neighbor : adj[curr]) {
                    int nxt = neighbor.first;
                    int w = neighbor.second;
                    if (node_token[nxt] != visited_token) {
                        node_token[nxt] = visited_token;
                        parent[nxt] = curr;
                        path_edge_weight[nxt] = w;
                        q[q_end++] = nxt;
                    }
                }
            }
            
            int max_w;
            if (found) {
                max_w = 0;
                int curr = root_v_target;
                while (curr != root_u_target) {
                    if (path_edge_weight[curr] > max_w) max_w = path_edge_weight[curr];
                    curr = parent[curr];
                }
            } else {
                max_w = 1000000000;
            }
            sum_threshold += max_w;
            cnt++;
        }

        double threshold = (double)sum_threshold / cnt;
        if (l_i < threshold) {
            cout << "1" << endl;
            accepted_dsu.unite(u, v);
        } else {
            cout << "0" << endl;
        }
    }

    return 0;
}