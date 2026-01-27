#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <chrono>
#include <random>

const int MAXN = 501;

int N, M;
bool adjG[MAXN][MAXN];
int best_colors[MAXN];
int min_K = MAXN;

static std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

void solve() {
    std::vector<int> p(N);
    std::iota(p.begin(), p.end(), 1);
    std::shuffle(p.begin(), p.end(), rng);

    int color[MAXN] = {0};
    bool colored[MAXN] = {false};
    int saturation[MAXN] = {0};
    bool adjacent_colors[MAXN][MAXN] = {{false}};
    int dynamic_degree_G_bar[MAXN] = {0};
    
    for (int i = 1; i <= N; ++i) {
        for (int j = i + 1; j <= N; ++j) {
            if (!adjG[i][j]) {
                dynamic_degree_G_bar[i]++;
                dynamic_degree_G_bar[j]++;
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        int u = -1;
        int max_sat = -1;
        int max_deg = -1;

        for (int v_node : p) {
            if (!colored[v_node]) {
                if (saturation[v_node] > max_sat) {
                    max_sat = saturation[v_node];
                    max_deg = dynamic_degree_G_bar[v_node];
                    u = v_node;
                } else if (saturation[v_node] == max_sat && dynamic_degree_G_bar[v_node] > max_deg) {
                    max_deg = dynamic_degree_G_bar[v_node];
                    u = v_node;
                }
            }
        }
        
        if (u == -1) {
            for (int v_node : p) {
                if (!colored[v_node]) {
                    u = v_node;
                    break;
                }
            }
        }

        colored[u] = true;

        bool used_colors[MAXN] = {false};
        for (int v = 1; v <= N; ++v) {
            if (u != v && !adjG[u][v] && color[v] != 0) {
                used_colors[color[v]] = true;
            }
        }
        
        int c = 1;
        while (used_colors[c]) {
            c++;
        }
        color[u] = c;

        for (int v = 1; v <= N; ++v) {
            if (u != v && !adjG[u][v] && !colored[v]) {
                dynamic_degree_G_bar[v]--;
                if (!adjacent_colors[v][c]) {
                    adjacent_colors[v][c] = true;
                    saturation[v]++;
                }
            }
        }
    }

    int current_K = 0;
    for (int i = 1; i <= N; ++i) {
        current_K = std::max(current_K, color[i]);
    }

    if (current_K < min_K) {
        min_K = current_K;
        for (int i = 1; i <= N; ++i) {
            best_colors[i] = color[i];
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> N >> M;
    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        adjG[u][v] = adjG[v][u] = true;
    }
    
    auto start_time = std::chrono::high_resolution_clock::now();
    double time_limit_ms = 1950.0;
    
    solve();

    while (true) {
        auto current_time = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double, std::milli> elapsed = current_time - start_time;
        if (elapsed.count() > time_limit_ms) {
            break;
        }
        solve();
    }
    
    for (int i = 1; i <= N; ++i) {
        std::cout << best_colors[i] << "\n";
    }

    return 0;
}