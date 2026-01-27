#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <chrono>
#include <random>

int N, M;
std::vector<std::vector<bool>> is_edge;
std::vector<int> initial_degree;

// Greedily colors the graph given a vertex permutation.
// This is equivalent to finding a clique cover.
std::pair<int, std::vector<int>> greedy_color(const std::vector<int>& p) {
    std::vector<int> colors(N + 1, 0);
    int max_color = 0;
    for (int v : p) {
        std::vector<bool> used_colors(N + 2, false);
        for (int u = 1; u <= N; ++u) {
            if (v == u) continue;
            // If u is colored and not adjacent to v, v cannot have the same color.
            if (colors[u] != 0 && !is_edge[v][u]) {
                used_colors[colors[u]] = true;
            }
        }
        int c = 1;
        while (used_colors[c]) {
            c++;
        }
        colors[v] = c;
        if (c > max_color) {
            max_color = c;
        }
    }
    return {max_color, colors};
}

// Generates a vertex ordering using the smallest-last heuristic on the complement graph
// with randomization for tie-breaking. The coloring order is the reverse of the removal order.
std::vector<int> get_randomized_smallest_last_order(std::mt19937& rng) {
    std::vector<int> p(N);
    std::vector<int> deg_comp(N + 1);
    for (int i = 1; i <= N; ++i) {
        deg_comp[i] = (N - 1) - initial_degree[i];
    }
    std::vector<bool> removed(N + 1, false);
    
    for (int i = N - 1; i >= 0; --i) {
        int min_deg = N + 1;
        std::vector<int> candidates;
        
        // Find minimum degree among non-removed vertices and collect candidates
        for (int j = 1; j <= N; ++j) {
            if (!removed[j]) {
                if (deg_comp[j] < min_deg) {
                    min_deg = deg_comp[j];
                    candidates.clear();
                    candidates.push_back(j);
                } else if (deg_comp[j] == min_deg) {
                    candidates.push_back(j);
                }
            }
        }
        
        // Pick one candidate randomly
        std::uniform_int_distribution<int> dist(0, candidates.size() - 1);
        int v_to_remove = candidates[dist(rng)];
        
        p[i] = v_to_remove;
        removed[v_to_remove] = true;
        
        // Update degrees of neighbors in the complement graph
        for (int u = 1; u <= N; ++u) {
            if (!removed[u] && !is_edge[v_to_remove][u]) {
                deg_comp[u]--;
            }
        }
    }
    return p;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> N >> M;
    is_edge.assign(N + 1, std::vector<bool>(N + 1, false));
    initial_degree.assign(N + 1, 0);

    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        if (!is_edge[u][v]) {
            is_edge[u][v] = is_edge[v][u] = true;
            initial_degree[u]++;
            initial_degree[v]++;
        }
    }
    for (int i = 1; i <= N; ++i) {
        is_edge[i][i] = true;
    }

    auto start_time = std::chrono::high_resolution_clock::now();
    double time_limit_sec = 1.9;

    std::vector<int> best_colors(N + 1);
    int min_K = N + 1;
    
    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    
    // Initial Heuristic 1: Welsh-Powell on complement graph (sort by degree in G ascending)
    std::vector<std::pair<int, int>> deg_pairs;
    for (int i = 1; i <= N; ++i) {
        deg_pairs.push_back({initial_degree[i], i});
    }
    std::sort(deg_pairs.begin(), deg_pairs.end());
    std::vector<int> p_deg_asc(N);
    for (int i = 0; i < N; ++i) {
        p_deg_asc[i] = deg_pairs[i].second;
    }

    auto result = greedy_color(p_deg_asc);
    min_K = result.first;
    best_colors = result.second;
    
    // Initial Heuristic 2: Reverse Welsh-Powell on complement (sort by degree in G descending)
    std::vector<int> p_deg_desc(N);
    for (int i = 0; i < N; ++i) {
        p_deg_desc[i] = deg_pairs[N - 1 - i].second;
    }
    result = greedy_color(p_deg_desc);
    if (result.first < min_K) {
        min_K = result.first;
        best_colors = result.second;
    }

    // Iteratively try to find a better coloring using randomized smallest-last
    while (true) {
        auto current_time = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = current_time - start_time;
        if (elapsed.count() > time_limit_sec) {
            break;
        }

        std::vector<int> p = get_randomized_smallest_last_order(rng);
        auto current_result = greedy_color(p);
        
        if (current_result.first < min_K) {
            min_K = current_result.first;
            best_colors = current_result.second;
        }
    }

    for (int i = 1; i <= N; ++i) {
        std::cout << best_colors[i] << "\n";
    }

    return 0;
}