#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <chrono>
#include <random>

using namespace std;

using ll = long long;

// Parameters for the Weisfeiler-Leman algorithm and hashing
const int WL_ITERATIONS = 10;
const ll M1 = 1e9 + 7, M2 = 1e9 + 9;
const ll P1 = 313, P2 = 317; // Primes for hashing neighbor lists
const ll Q1 = 331, Q2 = 337; // Primes for combining with self-hash

int n, m;
vector<vector<int>> adj1, adj2;
vector<vector<bool>> adj1_mat;
vector<int> p;

// Computes new hashes for all vertices of a graph in one WL iteration
vector<pair<ll, ll>> compute_new_hashes(const vector<int>& current_hashes, const vector<vector<int>>& adj, int max_h) {
    vector<pair<ll, ll>> new_hashes(n + 1);
    vector<int> neighbor_h_counts(max_h + 1, 0);

    for (int i = 1; i <= n; ++i) {
        for (int neighbor : adj[i]) {
            neighbor_h_counts[current_hashes[neighbor]]++;
        }

        pair<ll, ll> neighbor_poly_hash = {0, 0};
        for (int h_val = 1; h_val <= max_h; ++h_val) {
            for (int k = 0; k < neighbor_h_counts[h_val]; ++k) {
                neighbor_poly_hash.first = (neighbor_poly_hash.first * P1 + h_val) % M1;
                neighbor_poly_hash.second = (neighbor_poly_hash.second * P2 + h_val) % M2;
            }
        }

        new_hashes[i].first = (static_cast<ll>(current_hashes[i]) * Q1 + neighbor_poly_hash.first) % M1;
        new_hashes[i].second = (static_cast<ll>(current_hashes[i]) * Q2 + neighbor_poly_hash.second) % M2;
        if (new_hashes[i].first < 0) new_hashes[i].first += M1;
        if (new_hashes[i].second < 0) new_hashes[i].second += M2;
        
        // Reset counts for the next vertex
        for (int neighbor : adj[i]) {
            neighbor_h_counts[current_hashes[neighbor]] = 0;
        }
    }
    return new_hashes;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m;

    adj1.resize(n + 1);
    adj2.resize(n + 1);
    adj1_mat.resize(n + 1, vector<bool>(n + 1, false));
    p.resize(n + 1);

    vector<int> deg1(n + 1, 0), deg2(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj1[u].push_back(v);
        adj1[v].push_back(u);
        adj1_mat[u][v] = adj1_mat[v][u] = true;
        deg1[u]++;
        deg1[v]++;
    }

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
        deg2[u]++;
        deg2[v]++;
    }

    // Weisfeiler-Leman to get initial permutation
    vector<int> h1 = deg1, h2 = deg2;

    for (int iter = 0; iter < WL_ITERATIONS; ++iter) {
        int max_h = 0;
        for (int i = 1; i <= n; ++i) {
            max_h = max({max_h, h1[i], h2[i]});
        }

        vector<pair<ll, ll>> h1_new_val = compute_new_hashes(h1, adj1, max_h);
        vector<pair<ll, ll>> h2_new_val = compute_new_hashes(h2, adj2, max_h);

        map<pair<ll, ll>, int> rank_map;
        for (int i = 1; i <= n; ++i) {
            rank_map[h1_new_val[i]] = 0;
            rank_map[h2_new_val[i]] = 0;
        }

        int current_rank = 1;
        for (auto& pair : rank_map) {
            pair.second = current_rank++;
        }

        for (int i = 1; i <= n; ++i) {
            h1[i] = rank_map[h1_new_val[i]];
            h2[i] = rank_map[h2_new_val[i]];
        }
    }

    vector<pair<int, int>> v1_sorted(n), v2_sorted(n);
    for (int i = 0; i < n; ++i) {
        v1_sorted[i] = {h1[i + 1], i + 1};
        v2_sorted[i] = {h2[i + 1], i + 1};
    }
    sort(v1_sorted.begin(), v1_sorted.end());
    sort(v2_sorted.begin(), v2_sorted.end());

    for (int i = 0; i < n; ++i) {
        p[v2_sorted[i].second] = v1_sorted[i].second;
    }

    // Local Search (Hill Climbing)
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist(1, n);
    
    auto start_time = chrono::steady_clock::now();
    
    while (chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now() - start_time).count() < 1800) {
        int i = dist(rng);
        int j = dist(rng);
        if (i == j) continue;

        int u = p[i];
        int v = p[j];

        int delta = 0;
        for (int neighbor : adj2[i]) {
            if (neighbor != j) {
                delta += adj1_mat[v][p[neighbor]] - adj1_mat[u][p[neighbor]];
            }
        }
        for (int neighbor : adj2[j]) {
            if (neighbor != i) {
                delta += adj1_mat[u][p[neighbor]] - adj1_mat[v][p[neighbor]];
            }
        }
        
        // Accept swap if score improves or stays the same
        if (delta >= 0) {
            swap(p[i], p[j]);
        }
    }

    for (int i = 1; i <= n; ++i) {
        cout << p[i] << (i == n ? "" : " ");
    }
    cout << endl;

    return 0;
}