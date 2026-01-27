#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>
#include <chrono>
#include <cmath>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 2005;

// Adjacency matrix for G1: fast O(1) edge lookup
// Uses static memory to avoid allocation overhead
bool adj1[MAXN][MAXN]; 

// Adjacency list for G2: efficient iteration over neighbors
vector<int> adj2[MAXN];

// Degree arrays
int deg1[MAXN], deg2[MAXN];

// Structure to hold vertex info for heuristic initialization
struct VertexSignature {
    int id;
    int degree;
    vector<int> neighbor_degrees;

    // Custom comparator to sort vertices by "strength" (degree, then neighbor degrees)
    // We want to sort such that stronger vertices come first.
    // So if this > other, we return true (making this "smaller" for std::sort)
    bool operator<(const VertexSignature& other) const {
        if (degree != other.degree)
            return degree > other.degree; // Higher degree first
        return neighbor_degrees > other.neighbor_degrees; // Lexicographically larger neighbor profile first
    }
};

VertexSignature sig1[MAXN], sig2[MAXN];

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Reading edges for Graph 1
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj1[u][v] = adj1[v][u] = true;
        deg1[u]++;
        deg1[v]++;
    }

    // Reading edges for Graph 2
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
        deg2[u]++;
        deg2[v]++;
    }

    // Heuristic Initialization: Smart sorting based on degrees and neighbor degrees
    // Compute signatures for G1
    for (int i = 1; i <= n; ++i) {
        sig1[i].id = i;
        sig1[i].degree = deg1[i];
        sig1[i].neighbor_degrees.reserve(deg1[i]);
        for (int j = 1; j <= n; ++j) {
            if (adj1[i][j]) {
                sig1[i].neighbor_degrees.push_back(deg1[j]);
            }
        }
        // Sort neighbor degrees descending to create a canonical profile
        sort(sig1[i].neighbor_degrees.begin(), sig1[i].neighbor_degrees.end(), greater<int>());
    }

    // Compute signatures for G2
    for (int i = 1; i <= n; ++i) {
        sig2[i].id = i;
        sig2[i].degree = deg2[i];
        sig2[i].neighbor_degrees.reserve(deg2[i]);
        for (int v : adj2[i]) {
            sig2[i].neighbor_degrees.push_back(deg2[v]);
        }
        sort(sig2[i].neighbor_degrees.begin(), sig2[i].neighbor_degrees.end(), greater<int>());
    }

    // Sort vertices of both graphs
    sort(sig1 + 1, sig1 + n + 1);
    sort(sig2 + 1, sig2 + n + 1);

    // Initial mapping: map i-th strongest vertex of G2 to i-th strongest of G1
    // p[u] = v means vertex u of G2 maps to vertex v of G1
    vector<int> p(n + 1);
    for (int i = 1; i <= n; ++i) {
        p[sig2[i].id] = sig1[i].id;
    }

    // Calculate initial score (number of matched edges)
    int current_score = 0;
    for (int u = 1; u <= n; ++u) {
        for (int v : adj2[u]) {
            if (u < v) { // Consider each edge once
                if (adj1[p[u]][p[v]]) {
                    current_score++;
                }
            }
        }
    }

    // Keep track of best solution found
    vector<int> best_p = p;
    int best_score = current_score;
    
    // If perfect match found early, stop
    if (best_score == m && m > 0) {
        for (int i = 1; i <= n; ++i) cout << best_p[i] << (i == n ? "" : " ");
        cout << "\n";
        return 0;
    }

    // Simulated Annealing setup
    mt19937 rng(1337); 
    uniform_int_distribution<int> dist_node(1, n);
    uniform_real_distribution<double> dist_prob(0.0, 1.0);

    auto start_time = chrono::steady_clock::now();
    // Time limit slightly below typical 2.0s
    double time_limit = 1.90; 

    // Temperature parameters
    double t_start = 2.0;
    double t_end = 0.0001;
    double temp = t_start;

    long long iter = 0;
    
    // Optimization loop
    while (true) {
        // Periodically update temperature and check time limit
        if ((iter & 0x3FFF) == 0) { 
            auto now = chrono::steady_clock::now();
            chrono::duration<double> elapsed = now - start_time;
            if (elapsed.count() > time_limit) break;
            
            double progress = elapsed.count() / time_limit;
            temp = t_start * pow(t_end / t_start, progress);
        }
        iter++;

        // Select two distinct vertices to swap in G2 mapping
        int u = dist_node(rng);
        int v = dist_node(rng);
        while (u == v) {
            v = dist_node(rng);
        }

        // Current mapping targets
        int pu = p[u];
        int pv = p[v];

        // Calculate change in score (delta) efficiently
        // Only edges incident to u or v in G2 need checking.
        // The edge (u,v) itself maps to (pu, pv) -> (pv, pu), which is the same edge in undirected G1.
        int delta = 0;

        // Check neighbors of u
        for (int w : adj2[u]) {
            if (w == v) continue; 
            int pw = p[w];
            // Loss: old mapping (u,w) -> (pu, pw)
            if (adj1[pu][pw]) delta--;
            // Gain: new mapping (u,w) -> (pv, pw)
            if (adj1[pv][pw]) delta++;
        }

        // Check neighbors of v
        for (int w : adj2[v]) {
            if (w == u) continue;
            int pw = p[w];
            // Loss: old mapping (v,w) -> (pv, pw)
            if (adj1[pv][pw]) delta--;
            // Gain: new mapping (v,w) -> (pu, pw)
            if (adj1[pu][pw]) delta++;
        }

        // Metropolis criterion
        bool accept = false;
        if (delta >= 0) {
            accept = true;
        } else {
            if (dist_prob(rng) < exp(delta / temp)) {
                accept = true;
            }
        }

        if (accept) {
            // Apply swap
            p[u] = pv;
            p[v] = pu;
            current_score += delta;

            if (current_score > best_score) {
                best_score = current_score;
                best_p = p;
                if (best_score == m) break; // Found perfect isomorphism
            }
        }
    }

    // Output best permutation found
    for (int i = 1; i <= n; ++i) {
        cout << best_p[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}