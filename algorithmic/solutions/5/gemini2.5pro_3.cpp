#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <chrono>
#include <random>
#include <deque>

void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

const int MAXN = 500005;
std::vector<int> adj[MAXN];
std::vector<int> rev_adj[MAXN];
int n, m;
int a[10];
int visited[MAXN];
std::vector<int> best_path;
std::mt19937 rng;

void solve() {
    std::cin >> n >> m;
    for (int i = 0; i < 10; ++i) {
        std::cin >> a[i];
    }
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        rev_adj[v].push_back(u);
    }

    rng.seed(std::chrono::steady_clock::now().time_since_epoch().count());
    
    if (n > 0) {
        best_path.push_back(1);
    }
    
    auto start_time = std::chrono::steady_clock::now();
    int trial_id = 0;

    while (true) {
        auto current_time = std::chrono::steady_clock::now();
        if (std::chrono::duration_cast<std::chrono::milliseconds>(current_time - start_time).count() > 3800) {
            break;
        }
        trial_id++;

        std::uniform_int_distribution<int> dist(1, n);
        int start_node = dist(rng);
        
        std::deque<int> current_path;
        current_path.push_back(start_node);
        visited[start_node] = trial_id;
        
        // Extend forward
        int tail = start_node;
        while (true) {
            int unvisited_count = 0;
            for (int neighbor : adj[tail]) {
                if (visited[neighbor] != trial_id) {
                    unvisited_count++;
                }
            }
            if (unvisited_count == 0) break;

            std::uniform_int_distribution<int> neighbor_dist(0, unvisited_count - 1);
            int k = neighbor_dist(rng);
            int next_node = -1;
            for (int neighbor : adj[tail]) {
                if (visited[neighbor] != trial_id) {
                    if (k == 0) {
                        next_node = neighbor;
                        break;
                    }
                    k--;
                }
            }
            
            tail = next_node;
            current_path.push_back(tail);
            visited[tail] = trial_id;
        }

        // Extend backward
        int head = start_node;
        while (true) {
            int unvisited_count = 0;
            for (int neighbor : rev_adj[head]) {
                if (visited[neighbor] != trial_id) {
                    unvisited_count++;
                }
            }
            if (unvisited_count == 0) break;

            std::uniform_int_distribution<int> neighbor_dist(0, unvisited_count - 1);
            int k = neighbor_dist(rng);
            int prev_node = -1;
            for (int neighbor : rev_adj[head]) {
                if (visited[neighbor] != trial_id) {
                    if (k == 0) {
                        prev_node = neighbor;
                        break;
                    }
                    k--;
                }
            }
            
            head = prev_node;
            current_path.push_front(head);
            visited[head] = trial_id;
        }
        
        if (current_path.size() > best_path.size()) {
            best_path.assign(current_path.begin(), current_path.end());
        }

        if (best_path.size() == n) {
            break;
        }
    }
    
    std::cout << best_path.size() << "\n";
    for (size_t i = 0; i < best_path.size(); ++i) {
        std::cout << best_path[i] << (i == best_path.size() - 1 ? "" : " ");
    }
    std::cout << "\n";
}

int main() {
    fast_io();
    solve();
    return 0;
}