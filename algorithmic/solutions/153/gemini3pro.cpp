#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <iomanip>

using namespace std;

// Fast RNG using Xorshift algorithm
struct Xorshift {
    unsigned int x = 123456789;
    unsigned int y = 362436069;
    unsigned int z = 521288629;
    unsigned int w = 88675123;
    unsigned int next() {
        unsigned int t = x ^ (x << 11);
        x = y; y = z; z = w;
        return w = (w ^ (w >> 19)) ^ (t ^ (t >> 8));
    }
    // range [L, R] inclusive
    int range(int L, int R) {
        if (L >= R) return L;
        return L + (next() % (R - L + 1));
    }
} rng;

struct Point {
    int x, y;
};

struct Edge {
    int u, v, id;
    int d;
};

struct SimEdge {
    int u, v, w;
    bool operator<(const SimEdge& other) const {
        return w < other.w;
    }
};

struct DSU {
    vector<int> parent;
    DSU(int n) : parent(n) {
        iota(parent.begin(), parent.end(), 0);
    }
    void reset() {
        iota(parent.begin(), parent.end(), 0);
    }
    // Copy state from another DSU
    void copy_from(const DSU& other) {
        parent = other.parent;
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
    bool connected(int i, int j) {
        return find(i) == find(j);
    }
};

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int N = 400;
    int M = 1995;

    // Read coordinates
    vector<Point> points(N);
    for (int i = 0; i < N; ++i) {
        cin >> points[i].x >> points[i].y;
    }

    // Read edges and calculate Euclidean distances
    vector<Edge> edges(M);
    for (int i = 0; i < M; ++i) {
        cin >> edges[i].u >> edges[i].v;
        edges[i].id = i;
        double dist = sqrt(pow(points[edges[i].u].x - points[edges[i].v].x, 2) + 
                           pow(points[edges[i].u].y - points[edges[i].v].y, 2));
        edges[i].d = (int)round(dist);
    }

    // Sort a copy of edges by d for pruning in simulations
    vector<Edge> sorted_edges = edges;
    sort(sorted_edges.begin(), sorted_edges.end(), [](const Edge& a, const Edge& b){
        return a.d < b.d;
    });

    vector<bool> used(M, false);
    DSU main_dsu(N);
    DSU sim_dsu(N);
    vector<SimEdge> candidates;
    candidates.reserve(M);

    // Number of simulations per step
    // Tuned to balance precision and time limit
    int K = 70; 

    for (int i = 0; i < M; ++i) {
        int l_i;
        cin >> l_i;
        
        Edge& curr = edges[i];
        used[i] = true;

        // If vertices are already connected, we don't need this edge
        if (main_dsu.connected(curr.u, curr.v)) {
            cout << 0 << endl;
            continue;
        }

        int wins = 0; // count scenarios where taking the current edge is better

        // Monte Carlo Simulation
        for (int k = 0; k < K; ++k) {
            candidates.clear();
            
            // Collect relevant future edges
            for (const auto& e : sorted_edges) {
                if (used[e.id]) continue;
                // Optimization: if min possible weight of edge e is >= l_i,
                // it cannot help to form a path cheaper than l_i.
                if (e.d >= l_i) break; 
                
                // Generate random weight for future edge
                int w = rng.range(e.d, 3 * e.d);
                if (w < l_i) {
                    candidates.push_back({e.u, e.v, w});
                }
            }

            // If we have candidates, check if they can connect u and v
            if (candidates.empty()) {
                // No edges cheaper than l_i exist, so we must take l_i (unless it's a bridge, but here we compare costs)
                // If we can't connect u-v with edges < l_i, then bottleneck >= l_i.
                // So taking l_i (cost l_i) is better or equal to the alternative.
                wins++;
            } else {
                sort(candidates.begin(), candidates.end());

                sim_dsu.copy_from(main_dsu);
                bool connected_in_sim = false;
                
                for (const auto& e : candidates) {
                    if (sim_dsu.unite(e.u, e.v)) {
                        if (sim_dsu.connected(curr.u, curr.v)) {
                            connected_in_sim = true;
                            break;
                        }
                    }
                }
                
                // If not connected using edges < l_i, it means the alternative path is more expensive
                if (!connected_in_sim) {
                    wins++;
                }
            }
        }

        // Majority vote
        if (wins * 2 > K) {
            cout << 1 << endl;
            main_dsu.unite(curr.u, curr.v);
        } else {
            cout << 0 << endl;
        }
    }

    return 0;
}