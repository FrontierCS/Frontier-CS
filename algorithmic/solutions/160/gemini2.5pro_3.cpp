#include <iostream>
#include <vector>
#include <string>
#include <cstring>
#include <queue>
#include <utility>
#include <algorithm>
#include <map>

// Global state
int grid[10][10];
int flavors[100];
int flavor_map[4]; // maps flavor {1,2,3} to type {0:max, 1:mid, 2:min}

// Tilt functions
void tilt_F(int g[10][10]) {
    for (int j = 0; j < 10; ++j) {
        int next_empty = 0;
        for (int i = 0; i < 10; ++i) {
            if (g[i][j] != 0) {
                if (i != next_empty) {
                    g[next_empty][j] = g[i][j];
                    g[i][j] = 0;
                }
                next_empty++;
            }
        }
    }
}

void tilt_B(int g[10][10]) {
    for (int j = 0; j < 10; ++j) {
        int next_empty = 9;
        for (int i = 9; i >= 0; --i) {
            if (g[i][j] != 0) {
                if (i != next_empty) {
                    g[next_empty][j] = g[i][j];
                    g[i][j] = 0;
                }
                next_empty--;
            }
        }
    }
}

void tilt_L(int g[10][10]) {
    for (int i = 0; i < 10; ++i) {
        int next_empty = 0;
        for (int j = 0; j < 10; ++j) {
            if (g[i][j] != 0) {
                if (j != next_empty) {
                    g[i][next_empty] = g[i][j];
                    g[i][j] = 0;
                }
                next_empty++;
            }
        }
    }
}

void tilt_R(int g[10][10]) {
    for (int i = 0; i < 10; ++i) {
        int next_empty = 9;
        for (int j = 9; j >= 0; --j) {
            if (g[i][j] != 0) {
                if (j != next_empty) {
                    g[i][next_empty] = g[i][j];
                    g[i][j] = 0;
                }
                next_empty--;
            }
        }
    }
}

void tilt(int g[10][10], char move) {
    if (move == 'F') tilt_F(g);
    else if (move == 'B') tilt_B(g);
    else if (move == 'L') tilt_L(g);
    else if (move == 'R') tilt_R(g);
}

// Scoring functions
long long calculate_s1(const int g[10][10]) {
    bool visited[10][10] = {false};
    long long total_score = 0;
    for (int i = 0; i < 10; ++i) {
        for (int j = 0; j < 10; ++j) {
            if (g[i][j] != 0 && !visited[i][j]) {
                int component_size = 0;
                int flavor = g[i][j];
                std::queue<std::pair<int, int>> q;
                q.push({i, j});
                visited[i][j] = true;
                component_size++;
                
                int dr[] = {-1, 1, 0, 0};
                int dc[] = {0, 0, -1, 1};
                
                while (!q.empty()) {
                    std::pair<int, int> curr = q.front();
                    q.pop();
                    
                    for (int k = 0; k < 4; ++k) {
                        int nr = curr.first + dr[k];
                        int nc = curr.second + dc[k];
                        
                        if (nr >= 0 && nr < 10 && nc >= 0 && nc < 10 &&
                            !visited[nr][nc] && g[nr][nc] == flavor) {
                            visited[nr][nc] = true;
                            q.push({nr, nc});
                            component_size++;
                        }
                    }
                }
                total_score += (long long)component_size * component_size;
            }
        }
    }
    return total_score;
}

double calculate_s2(const int g[10][10]) {
    double total_dist = 0;
    for (int i = 0; i < 10; ++i) {
        for (int j = 0; j < 10; ++j) {
            if (g[i][j] != 0) {
                int flavor = g[i][j];
                int type = flavor_map[flavor];
                if (type == 0) { // max count, target bottom edge
                    total_dist += (9 - i);
                } else if (type == 1) { // mid count, target top-left
                    total_dist += i + j;
                } else { // min count, target top-right
                    total_dist += i + (9 - j);
                }
            }
        }
    }
    return -total_dist;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // Initial setup
    int d[4] = {0};
    for (int i = 0; i < 100; ++i) {
        std::cin >> flavors[i];
        d[flavors[i]]++;
    }

    std::vector<std::pair<int, int>> counts;
    for (int i = 1; i <= 3; ++i) {
        counts.push_back({d[i], i});
    }
    std::sort(counts.rbegin(), counts.rend());

    flavor_map[counts[0].second] = 0;
    flavor_map[counts[1].second] = 1;
    flavor_map[counts[2].second] = 2;

    // Main loop
    for (int t = 0; t < 100; ++t) {
        int p;
        std::cin >> p;

        int empty_count = 0;
        int r_new = -1, c_new = -1;
        bool found = false;
        for (int i = 0; i < 10; ++i) {
            for (int j = 0; j < 10; ++j) {
                if (grid[i][j] == 0) {
                    empty_count++;
                    if (empty_count == p) {
                        r_new = i;
                        c_new = j;
                        found = true;
                        break;
                    }
                }
            }
            if(found) break;
        }

        char best_move = 'F';
        long long max_s1 = -1;
        double max_s2 = -1e18;
        
        const char moves[] = {'F', 'B', 'L', 'R'};
        for (char move : moves) {
            int temp_grid[10][10];
            memcpy(temp_grid, grid, sizeof(grid));
            temp_grid[r_new][c_new] = flavors[t];
            
            tilt(temp_grid, move);
            
            long long s1 = calculate_s1(temp_grid);
            double s2 = calculate_s2(temp_grid);
            
            if (s1 > max_s1 || (s1 == max_s1 && s2 > max_s2)) {
                max_s1 = s1;
                max_s2 = s2;
                best_move = move;
            }
        }
        
        grid[r_new][c_new] = flavors[t];
        tilt(grid, best_move);
        
        std::cout << best_move << std::endl;
    }

    return 0;
}