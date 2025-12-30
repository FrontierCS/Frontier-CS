#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

int n, m;
std::vector<std::vector<int>> adj;
std::vector<int> best_colors;
int best_b;
std::mt19937 rng;

int calculate_b(const std::vector<int>& colors) {
    int b = 0;
    for (int i = 1; i <= n; ++i) {
        for (int neighbor : adj[i]) {
            if (i < neighbor && colors[i] == colors[neighbor]) {
                b++;
            }
        }
    }
    return b;
}

bool improve_color(int u, std::vector<int>& colors) {
    int old_color = colors[u];
    int neighbor_color_counts[4] = {0, 0, 0, 0};
    for (int v : adj[u]) {
        neighbor_color_counts[colors[v]]++;
    }

    int current_conflicts = neighbor_color_counts[old_color];
    
    int min_conflicts = current_conflicts;
    std::vector<int> best_color_options;
    
    for (int c = 1; c <= 3; ++c) {
        if (c == old_color) continue;
        if (neighbor_color_counts[c] < min_conflicts) {
            min_conflicts = neighbor_color_counts[c];
            best_color_options.clear();
            best_color_options.push_back(c);
        } else if (neighbor_color_counts[c] == min_conflicts) {
            best_color_options.push_back(c);
        }
    }

    if (best_color_options.empty()) {
        return false;
    }
    
    colors[u] = best_color_options[rng() % best_color_options.size()];
    return true;
}

void solve() {
    best_b = m + 1;
    best_colors.resize(n + 1);

    auto start_time = std::chrono::steady_clock::now();
    
    std::vector<int> p(n);
    std::iota(p.begin(), p.end(), 1);

    std::vector<int> current_colors(n + 1);

    int runs = 0;
    while (std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start_time).count() < 1800) {
        for (int i = 1; i <= n; ++i) {
            current_colors[i] = (rng() % 3) + 1;
        }

        bool changed_in_pass = true;
        while (changed_in_pass) {
            changed_in_pass = false;
            std::shuffle(p.begin(), p.end(), rng);
            for (int u : p) {
                if (improve_color(u, current_colors)) {
                    changed_in_pass = true;
                }
            }
        }
        
        int current_b = calculate_b(current_colors);
        if (current_b < best_b) {
            best_b = current_b;
            best_colors = current_colors;
            if (best_b == 0) break;
        }
        runs++;
    }
    // If no run completed, use a random coloring
    if (runs == 0) {
        for (int i = 1; i <= n; ++i) {
            best_colors[i] = (rng() % 3) + 1;
        }
    }
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    rng.seed(std::chrono::steady_clock::now().time_since_epoch().count());

    std::cin >> n >> m;
    adj.resize(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            std::cout << 1 << (i == n ? "" : " ");
        }
        std::cout << "\n";
        return 0;
    }

    solve();

    for (int i = 1; i <= n; ++i) {
        std::cout << best_colors[i] << (i == n ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}