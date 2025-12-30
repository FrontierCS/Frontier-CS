#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <cmath>

const int N = 10;

// Represents the grid state
using Grid = std::vector<std::vector<int>>;

// Function to place a new candy
void place_candy(Grid& grid, int p, int flavor) {
    int empty_count = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] == 0) {
                empty_count++;
                if (empty_count == p) {
                    grid[i][j] = flavor;
                    return;
                }
            }
        }
    }
}

// Function to simulate a tilt
Grid tilt(const Grid& original_grid, char dir) {
    Grid grid = original_grid;
    if (dir == 'F') { // Forward (Up)
        for (int j = 0; j < N; ++j) {
            int current = 0;
            for (int i = 0; i < N; ++i) {
                if (grid[i][j] != 0) {
                    if (current != i) {
                        grid[current][j] = grid[i][j];
                        grid[i][j] = 0;
                    }
                    current++;
                }
            }
        }
    } else if (dir == 'B') { // Backward (Down)
        for (int j = 0; j < N; ++j) {
            int current = N - 1;
            for (int i = N - 1; i >= 0; --i) {
                if (grid[i][j] != 0) {
                    if (current != i) {
                        grid[current][j] = grid[i][j];
                        grid[i][j] = 0;
                    }
                    current--;
                }
            }
        }
    } else if (dir == 'L') { // Left
        for (int i = 0; i < N; ++i) {
            int current = 0;
            for (int j = 0; j < N; ++j) {
                if (grid[i][j] != 0) {
                    if (current != j) {
                        grid[i][current] = grid[i][j];
                        grid[i][j] = 0;
                    }
                    current++;
                }
            }
        }
    } else if (dir == 'R') { // Right
        for (int i = 0; i < N; ++i) {
            int current = N - 1;
            for (int j = N - 1; j >= 0; --j) {
                if (grid[i][j] != 0) {
                    if (current != j) {
                        grid[i][current] = grid[i][j];
                        grid[i][j] = 0;
                    }
                    current--;
                }
            }
        }
    }
    return grid;
}

// DFS for finding connected components
int dfs(int r, int c, int flavor, const Grid& grid, std::vector<std::vector<bool>>& visited) {
    if (r < 0 || r >= N || c < 0 || c >= N || visited[r][c] || grid[r][c] != flavor) {
        return 0;
    }
    visited[r][c] = true;
    int size = 1;
    int dr[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};
    for(int i = 0; i < 4; ++i) {
        size += dfs(r + dr[i], c + dc[i], flavor, grid, visited);
    }
    return size;
}

// Calculate sum of squared component sizes
long long calculate_cluster_score(const Grid& grid) {
    long long score = 0;
    std::vector<std::vector<bool>> visited(N, std::vector<bool>(N, false));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] != 0 && !visited[i][j]) {
                long long component_size = dfs(i, j, grid[i][j], grid, visited);
                score += component_size * component_size;
            }
        }
    }
    return score;
}

// Target regions definitions
int flavor_to_region[4];
int region_row_starts[4];
int region_row_ends[4];

// Calculate penalty for being outside target region
long long calculate_region_penalty(const Grid& grid) {
    long long dist_sum = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] != 0) {
                int flavor = grid[i][j];
                int region_idx = flavor_to_region[flavor];
                int start = region_row_starts[region_idx];
                int end = region_row_ends[region_idx];
                int dist = 0;
                if (i < start) {
                    dist = start - i;
                } else if (i > end) {
                    dist = i - end;
                }
                dist_sum += dist * dist;
            }
        }
    }
    return dist_sum;
}

// Evaluate a grid state
double evaluate(const Grid& grid, int turn) {
    long long cluster_score = calculate_cluster_score(grid);
    long long region_penalty = calculate_region_penalty(grid);
    
    // Weight for region penalty, decreases as game progresses
    double C = 5.0 * pow((100.0 - turn) / 100.0, 2.0);

    return (double)cluster_score - C * region_penalty;
}

// Setup target regions for each flavor
void setup_regions(const std::vector<int>& f) {
    std::vector<int> counts(4, 0);
    for (int flavor : f) {
        counts[flavor]++;
    }

    std::vector<std::pair<int, int>> sorted_flavors;
    for(int i=1; i<=3; ++i) {
        sorted_flavors.push_back({counts[i], i});
    }
    std::sort(sorted_flavors.rbegin(), sorted_flavors.rend());

    flavor_to_region[sorted_flavors[0].second] = 1;
    flavor_to_region[sorted_flavors[1].second] = 2;
    flavor_to_region[sorted_flavors[2].second] = 3;

    int total_candies = 100;
    int r1_boundary = round(1.0 * N * counts[sorted_flavors[0].second] / total_candies);
    int r2_boundary = round(1.0 * N * (counts[sorted_flavors[0].second] + counts[sorted_flavors[1].second]) / total_candies);
    
    region_row_starts[1] = 0;
    region_row_ends[1] = r1_boundary - 1;
    
    region_row_starts[2] = r1_boundary;
    region_row_ends[2] = r2_boundary - 1;
    
    region_row_starts[3] = r2_boundary;
    region_row_ends[3] = N - 1;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::vector<int> flavors(100);
    for (int i = 0; i < 100; ++i) {
        std::cin >> flavors[i];
    }

    setup_regions(flavors);

    Grid grid(N, std::vector<int>(N, 0));

    for (int t = 0; t < 100; ++t) {
        int p;
        std::cin >> p;
        
        place_candy(grid, p, flavors[t]);

        char best_dir = 'F';
        double max_score = -1e18;

        const char dirs[] = {'F', 'B', 'L', 'R'};
        for (char dir : dirs) {
            Grid next_grid = tilt(grid, dir);
            double current_score = evaluate(next_grid, t);
            if (current_score > max_score) {
                max_score = current_score;
                best_dir = dir;
            }
        }
        
        std::cout << best_dir << std::endl;
        
        grid = tilt(grid, best_dir);
    }

    return 0;
}