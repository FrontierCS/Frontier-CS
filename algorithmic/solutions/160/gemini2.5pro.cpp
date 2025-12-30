#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <iomanip>

struct Grid {
    std::vector<std::vector<int>> cells;
    Grid() : cells(10, std::vector<int>(10, 0)) {}
};

struct FlavorInfo {
    int id;
    int count;
    int base_rows;
    int remainder;
};

bool compareFlavors(const FlavorInfo& a, const FlavorInfo& b) {
    if (a.remainder != b.remainder) {
        return a.remainder > b.remainder;
    }
    return a.id < b.id;
}

int boundary1 = -1;
int boundary2 = -1;

Grid apply_tilt(const Grid& current_grid, char dir) {
    Grid next_grid;
    if (dir == 'F') {
        for (int j = 0; j < 10; ++j) {
            int current_row = 0;
            for (int i = 0; i < 10; ++i) {
                if (current_grid.cells[i][j] != 0) {
                    next_grid.cells[current_row++][j] = current_grid.cells[i][j];
                }
            }
        }
    } else if (dir == 'B') {
        for (int j = 0; j < 10; ++j) {
            int current_row = 9;
            for (int i = 9; i >= 0; --i) {
                if (current_grid.cells[i][j] != 0) {
                    next_grid.cells[current_row--][j] = current_grid.cells[i][j];
                }
            }
        }
    } else if (dir == 'L') {
        for (int i = 0; i < 10; ++i) {
            int current_col = 0;
            for (int j = 0; j < 10; ++j) {
                if (current_grid.cells[i][j] != 0) {
                    next_grid.cells[i][current_col++] = current_grid.cells[i][j];
                }
            }
        }
    } else if (dir == 'R') {
        for (int i = 0; i < 10; ++i) {
            int current_col = 9;
            for (int j = 9; j >= 0; --j) {
                if (current_grid.cells[i][j] != 0) {
                    next_grid.cells[i][current_col--] = current_grid.cells[i][j];
                }
            }
        }
    }
    return next_grid;
}

double calculate_cost(const Grid& grid, int t) {
    double w1 = 20.0;
    double w2 = 1.0 + 19.0 * t / 100.0;

    double dist_cost = 0;
    for (int i = 0; i < 10; ++i) {
        for (int j = 0; j < 10; ++j) {
            int flavor = grid.cells[i][j];
            if (flavor == 0) continue;

            if (flavor == 1) {
                if (i > boundary1) dist_cost += i - boundary1;
            } else if (flavor == 2) {
                if (i <= boundary1) dist_cost += (boundary1 + 1) - i;
                else if (i > boundary2) dist_cost += i - boundary2;
            } else if (flavor == 3) {
                if (i <= boundary2) dist_cost += (boundary2 + 1) - i;
            }
        }
    }

    double compactness_cost = 0;
    for (int k = 1; k <= 3; ++k) {
        double sum_r = 0, sum_c = 0;
        int count = 0;
        for (int i = 0; i < 10; ++i) {
            for (int j = 0; j < 10; ++j) {
                if (grid.cells[i][j] == k) {
                    sum_r += i;
                    sum_c += j;
                    count++;
                }
            }
        }

        if (count > 0) {
            double avg_r = sum_r / count;
            double avg_c = sum_c / count;
            for (int i = 0; i < 10; ++i) {
                for (int j = 0; j < 10; ++j) {
                    if (grid.cells[i][j] == k) {
                        compactness_cost += std::abs(i - avg_r) + std::abs(j - avg_c);
                    }
                }
            }
        }
    }

    return w1 * dist_cost + w2 * compactness_cost;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::vector<int> f(100);
    std::vector<int> d(4, 0);
    for (int i = 0; i < 100; ++i) {
        std::cin >> f[i];
        d[f[i]]++;
    }

    std::vector<FlavorInfo> flavors(3);
    int total_base_rows = 0;
    for (int i = 0; i < 3; ++i) {
        flavors[i].id = i + 1;
        flavors[i].count = d[i+1];
        flavors[i].base_rows = d[i+1] * 10 / 100;
        flavors[i].remainder = d[i+1] * 10 % 100;
        total_base_rows += flavors[i].base_rows;
    }

    std::sort(flavors.begin(), flavors.end(), compareFlavors);

    std::vector<int> rows_alloc(4, 0);
    int remaining_rows = 10 - total_base_rows;
    for(int i = 0; i < 3; ++i) {
        rows_alloc[flavors[i].id] = flavors[i].base_rows;
    }
    for(int i = 0; i < 3; ++i) {
        if (remaining_rows > 0) {
            rows_alloc[flavors[i].id]++;
            remaining_rows--;
        }
    }

    boundary1 = rows_alloc[1] - 1;
    boundary2 = rows_alloc[1] + rows_alloc[2] - 1;
    
    Grid grid;

    for (int t = 1; t <= 100; ++t) {
        int p;
        std::cin >> p;

        int empty_count = 0;
        int placed_r = -1, placed_c = -1;
        for (int i = 0; i < 10; ++i) {
            for (int j = 0; j < 10; ++j) {
                if (grid.cells[i][j] == 0) {
                    empty_count++;
                    if (empty_count == p) {
                        grid.cells[i][j] = f[t - 1];
                        placed_r = i;
                        placed_c = j;
                        break;
                    }
                }
            }
            if (placed_r != -1) break;
        }

        if (t == 100) {
            break;
        }

        char best_dir = 'F';
        double min_cost = 1e18;
        
        const char dirs[] = {'F', 'B', 'L', 'R'};
        for (char dir : dirs) {
            Grid next_grid = apply_tilt(grid, dir);
            double cost = calculate_cost(next_grid, t);
            if (cost < min_cost) {
                min_cost = cost;
                best_dir = dir;
            }
        }
        
        std::cout << best_dir << std::endl;
        grid = apply_tilt(grid, best_dir);
    }

    return 0;
}