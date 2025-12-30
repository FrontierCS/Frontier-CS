#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Fast I/O
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

// Global parameters
int n, k;
double eps;
long long m;
vector<vector<int>> adj;
int max_part_size;

// Partition state
vector<int> partition;
vector<int> part_size;
vector<vector<int>> neighbor_part_counts;
vector<long long> comm_volume;
long long current_ec;
long long current_cv;

mt19937 rng;

long long calculate_f(int u, int p_u) {
    long long f = 0;
    for (int p = 1; p <= k; ++p) {
        if (p != p_u && neighbor_part_counts[u][p] > 0) {
            f++;
        }
    }
    return f;
}

void calculate_ec_cv() {
    current_ec = 0;
    for (int u = 1; u <= n; ++u) {
        for (int v : adj[u]) {
            if (u < v && partition[u] != partition[v]) {
                current_ec++;
            }
        }
    }

    fill(comm_volume.begin(), comm_volume.end(), 0);
    for (int i = 1; i <= n; ++i) {
        comm_volume[partition[i]] += calculate_f(i, partition[i]);
    }

    current_cv = 0;
    if (k > 0) {
        current_cv = *max_element(comm_volume.begin() + 1, comm_volume.end());
    }
}

void initialize_neighbor_part_counts() {
    neighbor_part_counts.assign(n + 1, vector<int>(k + 1, 0));
    for (int i = 1; i <= n; ++i) {
        for (int neighbor : adj[i]) {
            neighbor_part_counts[i][partition[neighbor]]++;
        }
    }
}

int main() {
    fast_io();
    auto start_time = chrono::high_resolution_clock::now();
    rng.seed(chrono::steady_clock::now().time_since_epoch().count());

    cin >> n >> m >> k >> eps;

    adj.resize(n + 1);
    vector<pair<int, int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        if (u != v) {
            if (u > v) swap(u, v);
            edges.push_back({u, v});
        }
    }
    sort(edges.begin(), edges.end());
    edges.erase(unique(edges.begin(), edges.end()), edges.end());

    for(const auto& edge : edges) {
        adj[edge.first].push_back(edge.second);
        adj[edge.second].push_back(edge.first);
    }

    double ideal_size = ceil((double)n / k);
    max_part_size = floor((1 + eps) * ideal_size);

    partition.resize(n + 1, 0);
    part_size.assign(k + 1, 0);
    comm_volume.resize(k + 1);

    vector<int> p_indices(n);
    iota(p_indices.begin(), p_indices.end(), 1);
    shuffle(p_indices.begin(), p_indices.end(), rng);
    
    int current_part_idx = 0;
    for(int u : p_indices) {
        int p = (current_part_idx % k) + 1;
        if(part_size[p] < max_part_size) {
            partition[u] = p;
            part_size[p]++;
        } else {
            bool assigned = false;
            for(int j=1; j<=k; ++j) {
                if(part_size[j] < max_part_size) {
                    partition[u] = j;
                    part_size[j]++;
                    assigned = true;
                    break;
                }
            }
        }
        current_part_idx++;
    }

    initialize_neighbor_part_counts();
    calculate_ec_cv();

    vector<int> vertices(n);
    iota(vertices.begin(), vertices.end(), 1);

    vector<long long> delta_comm(k + 1);

    while (true) {
        auto current_time = chrono::high_resolution_clock::now();
        if (chrono::duration_cast<chrono::milliseconds>(current_time - start_time).count() > 950) {
            break;
        }

        shuffle(vertices.begin(), vertices.end(), rng);
        bool moved = false;

        for (int u : vertices) {
            int p_from = partition[u];
            if (part_size[p_from] == 1) continue;

            long double best_gain = 1e-9;
            int best_p_to = -1;

            for (int p_to = 1; p_to <= k; ++p_to) {
                if (p_to == p_from || part_size[p_to] >= max_part_size) continue;
                
                long long delta_ec = neighbor_part_counts[u][p_from] - neighbor_part_counts[u][p_to];
                
                fill(delta_comm.begin(), delta_comm.end(), 0);

                long long f_old_u = calculate_f(u, p_from);
                long long f_new_u = calculate_f(u, p_to);
                
                delta_comm[p_from] -= f_old_u;
                delta_comm[p_to] += f_new_u;

                for (int v : adj[u]) {
                    int p_v = partition[v];
                    int c_v_p_from = neighbor_part_counts[v][p_from];
                    int c_v_p_to = neighbor_part_counts[v][p_to];
                    
                    int delta_f_v;
                    if (p_v != p_from && p_v != p_to) {
                        delta_f_v = (c_v_p_to == 0) - (c_v_p_from == 1);
                    } else if (p_v == p_from) {
                        delta_f_v = (c_v_p_to == 0);
                    } else { // p_v == p_to
                        delta_f_v = -(c_v_p_from == 1);
                    }
                    delta_comm[p_v] += delta_f_v;
                }
                
                long long new_cv = 0;
                for(int p=1; p<=k; ++p) {
                    new_cv = max(new_cv, comm_volume[p] + delta_comm[p]);
                }

                long long delta_cv = new_cv - current_cv;

                long double gain;
                if (current_ec > 0 && current_cv > 0)
                    gain = (long double)delta_ec * current_cv + (long double)delta_cv * current_ec;
                else
                    gain = delta_ec + delta_cv;

                if (gain < best_gain) {
                    best_gain = gain;
                    best_p_to = p_to;
                }
            }

            if (best_p_to != -1 && best_gain < 0) {
                int p_to = best_p_to;
                
                long long delta_ec_actual = neighbor_part_counts[u][p_from] - neighbor_part_counts[u][p_to];
                current_ec -= delta_ec_actual;

                comm_volume[p_from] -= calculate_f(u, p_from);

                for(int v : adj[u]) {
                    int p_v = partition[v];
                    long long f_old_v = calculate_f(v, p_v);
                    neighbor_part_counts[v][p_from]--;
                    neighbor_part_counts[v][p_to]++;
                    long long f_new_v = calculate_f(v, p_v);
                    comm_volume[p_v] += f_new_v - f_old_v;
                }
                
                partition[u] = p_to;
                part_size[p_from]--;
                part_size[p_to]++;
                
                comm_volume[p_to] += calculate_f(u, p_to);
                
                current_cv = 0;
                for(int p=1; p<=k; ++p) current_cv = max(current_cv, comm_volume[p]);

                moved = true;
            }
        }
        if (!moved) break;
    }
    
    for (int i = 1; i <= n; ++i) {
        cout << partition[i] << (i == n ? "" : " ");
    }
    cout << endl;

    return 0;
}