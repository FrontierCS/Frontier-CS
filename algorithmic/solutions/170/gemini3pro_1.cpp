#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <random>
#include <chrono>

using namespace std;

// Structures to manage the problem data
struct Item {
    int id;
    int weight;
    int type; // 0 for odd (a), 1 for even (b)
    int owner;
    int assigned_bin;
};

struct Bin {
    int id;
    int capacity;
    int current_load;
};

// Global variables
int N;
int L = 500000;
vector<int> T;
vector<Item> items;
vector<Bin> bins;

// Fast Random Number Generator
uint64_t xorshift64() {
    static uint64_t x = 88172645463325252ull;
    x ^= x << 13;
    x ^= x >> 7;
    x ^= x << 17;
    return x;
}

int rand_int(int l, int r) {
    if (l > r) return l;
    return l + (xorshift64() % (r - l + 1));
}

double rand_double() {
    return (double)xorshift64() / (double)0xFFFFFFFFFFFFFFFFull;
}

// Score calculation
// Minimizes flow balance error + penalty for unreachable nodes
long long calculate_score(const vector<Item>& current_items, const vector<Bin>& current_bins, bool check_reachability) {
    long long flow_error = 0;
    for (const auto& b : current_bins) {
        flow_error += abs(b.current_load - b.capacity);
    }
    
    if (!check_reachability) return flow_error;

    // Check reachability from node 0 using BFS
    static vector<pair<int, int>> graph(105);
    for (const auto& item : current_items) {
        if (item.type == 0) graph[item.owner].first = item.assigned_bin;
        else graph[item.owner].second = item.assigned_bin;
    }

    static vector<bool> visited(105);
    fill(visited.begin(), visited.begin() + N, false);
    
    static int q[105];
    int head = 0, tail = 0;
    
    q[tail++] = 0;
    visited[0] = true;
    
    while(head < tail){
        int u = q[head++];
        int v1 = graph[u].first;
        if (!visited[v1]) {
            visited[v1] = true;
            q[tail++] = v1;
        }
        int v2 = graph[u].second;
        if (!visited[v2]) {
            visited[v2] = true;
            q[tail++] = v2;
        }
    }

    long long unreachable_mass = 0;
    for(int i=0; i<N; ++i){
        if(!visited[i]) unreachable_mass += T[i];
    }

    // Heavy penalty for unreachable mass
    return flow_error + unreachable_mass * 100;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> L)) return 0;
    T.resize(N);
    int max_t = -1;
    int last_node = -1;
    for (int i = 0; i < N; ++i) {
        cin >> T[i];
        if (T[i] > max_t) {
            max_t = T[i];
            last_node = i;
        }
    }

    // Create bins
    bins.resize(N);
    for (int i = 0; i < N; ++i) {
        bins[i].id = i;
        bins[i].capacity = T[i];
        if (i == 0) bins[i].capacity--;
        bins[i].current_load = 0;
    }

    // Create items
    items.clear();
    items.reserve(2 * N);
    for (int i = 0; i < N; ++i) {
        int w_odd = (T[i] + 1) / 2;
        int w_even = T[i] / 2;
        
        // Adjust for the assumed last node
        if (i == last_node) {
            if (T[i] % 2 != 0) w_odd--;
            else w_even--;
        }

        Item item_odd;
        item_odd.id = 2 * i;
        item_odd.weight = w_odd;
        item_odd.type = 0;
        item_odd.owner = i;
        item_odd.assigned_bin = 0; 
        items.push_back(item_odd);

        Item item_even;
        item_even.id = 2 * i + 1;
        item_even.weight = w_even;
        item_even.type = 1;
        item_even.owner = i;
        item_even.assigned_bin = 0; 
        items.push_back(item_even);
    }

    // Greedy initialization
    // Sort items by weight descending to solve bin packing roughly
    vector<int> p(items.size());
    iota(p.begin(), p.end(), 0);
    sort(p.begin(), p.end(), [&](int a, int b) {
        return items[a].weight > items[b].weight;
    });

    for (int idx : p) {
        int best_bin = -1;
        long long best_diff = -1;
        
        // Find best bin
        for (int j = 0; j < N; ++j) {
            long long current_err = abs(bins[j].current_load - bins[j].capacity);
            long long next_err = abs(bins[j].current_load + items[idx].weight - bins[j].capacity);
            long long diff = next_err - current_err;
            if (best_bin == -1 || diff < best_diff) {
                best_diff = diff;
                best_bin = j;
            }
        }
        items[idx].assigned_bin = best_bin;
        bins[best_bin].current_load += items[idx].weight;
    }

    // Simulated Annealing
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.85; 
    
    long long current_score = calculate_score(items, bins, true);
    long long best_score = current_score;
    vector<Item> best_items = items;
    vector<Bin> best_bins = bins; 

    double temp_start = 2000.0;
    double temp_end = 1.0;
    double temp = temp_start;

    int iter = 0;
    while (true) {
        if ((iter & 511) == 0) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - start_time).count();
            if (elapsed > time_limit) break;
            double ratio = elapsed / time_limit;
            temp = temp_start * pow(temp_end / temp_start, ratio);
        }
        iter++;

        int type = rand_int(0, 2); 

        if (type == 0) {
            // Move: Move one item to another bin
            int item_idx = rand_int(0, (int)items.size() - 1);
            int old_bin = items[item_idx].assigned_bin;
            int new_bin = rand_int(0, N - 1);
            if (old_bin == new_bin) continue;

            int w = items[item_idx].weight;
            
            // Apply
            items[item_idx].assigned_bin = new_bin;
            bins[old_bin].current_load -= w;
            bins[new_bin].current_load += w;

            long long new_score = calculate_score(items, bins, true);
            
            if (new_score < current_score || rand_double() < exp((current_score - new_score) / temp)) {
                current_score = new_score;
                if (current_score < best_score) {
                    best_score = current_score;
                    best_items = items;
                    best_bins = bins;
                }
            } else {
                // Revert
                items[item_idx].assigned_bin = old_bin;
                bins[old_bin].current_load += w;
                bins[new_bin].current_load -= w;
            }
        } else if (type == 1) {
            // Swap: Swap assignment of two items
            int i1 = rand_int(0, (int)items.size() - 1);
            int i2 = rand_int(0, (int)items.size() - 1);
            if (i1 == i2) continue;
            
            int b1 = items[i1].assigned_bin;
            int b2 = items[i2].assigned_bin;
            if (b1 == b2) continue;

            int w1 = items[i1].weight;
            int w2 = items[i2].weight;

            // Apply
            items[i1].assigned_bin = b2;
            items[i2].assigned_bin = b1;
            bins[b1].current_load += (w2 - w1);
            bins[b2].current_load += (w1 - w2);

            long long new_score = calculate_score(items, bins, true);
             if (new_score < current_score || rand_double() < exp((current_score - new_score) / temp)) {
                current_score = new_score;
                if (current_score < best_score) {
                    best_score = current_score;
                    best_items = items;
                    best_bins = bins;
                }
            } else {
                // Revert
                items[i1].assigned_bin = b1;
                items[i2].assigned_bin = b2;
                bins[b1].current_load -= (w2 - w1);
                bins[b2].current_load -= (w1 - w2);
            }
        } else {
            // Fix Reachability Move
            // Identify unreachable
            static vector<pair<int, int>> graph(105);
            for (const auto& item : items) {
                if (item.type == 0) graph[item.owner].first = item.assigned_bin;
                else graph[item.owner].second = item.assigned_bin;
            }
            static vector<bool> visited(105);
            fill(visited.begin(), visited.begin() + N, false);
            static int q[105];
            int head = 0, tail = 0;
            q[tail++] = 0;
            visited[0] = true;
            
            // To pick a visited node quickly, store them
            static int visited_nodes[105];
            int visited_count = 0;
            
            while(head < tail){
                int u = q[head++];
                visited_nodes[visited_count++] = u;
                int v1 = graph[u].first;
                if (!visited[v1]) { visited[v1] = true; q[tail++] = v1; }
                int v2 = graph[u].second;
                if (!visited[v2]) { visited[v2] = true; q[tail++] = v2; }
            }

            vector<int> unreachable;
            unreachable.reserve(N);
            for(int i=0; i<N; ++i) if(!visited[i] && T[i] > 0) unreachable.push_back(i);

            if (unreachable.empty()) continue; 

            int target_node = unreachable[rand_int(0, unreachable.size()-1)];
            
            // Pick a visited node to redirect edge from
            int u = visited_nodes[rand_int(0, visited_count - 1)];
            
            // Pick an item from u
            int item_idx = 2 * u + rand_int(0, 1);
            
            int old_bin = items[item_idx].assigned_bin;
            int new_bin = target_node;
            if(old_bin == new_bin) continue;
            
            int w = items[item_idx].weight;
            items[item_idx].assigned_bin = new_bin;
            bins[old_bin].current_load -= w;
            bins[new_bin].current_load += w;

            long long new_score = calculate_score(items, bins, true);
            
            // High acceptance for reachability improvement
            if (new_score < current_score || rand_double() < exp((current_score - new_score) / temp)) {
                current_score = new_score;
                if (current_score < best_score) {
                    best_score = current_score;
                    best_items = items;
                    best_bins = bins;
                }
            } else {
                items[item_idx].assigned_bin = old_bin;
                bins[old_bin].current_load += w;
                bins[new_bin].current_load -= w;
            }
        }
    }

    // Output
    vector<pair<int, int>> ans(N);
    for (const auto& item : best_items) {
        if (item.type == 0) ans[item.owner].first = item.assigned_bin;
        else ans[item.owner].second = item.assigned_bin;
    }

    for (int i = 0; i < N; ++i) {
        cout << ans[i].first << " " << ans[i].second << "\n";
    }

    return 0;
}