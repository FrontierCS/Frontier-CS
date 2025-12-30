#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <map>
#include <set>
#include <queue>
#include <tuple>

using namespace std;

const int N = 5000;
const int MAX_COORD = 100000;

struct Point {
    int x, y;
};

struct Polygon {
    long long score;
    vector<Point> vertices;
};

Polygon solve(int grid_size, const vector<Point>& mackerels, const vector<Point>& sardines) {
    int G = grid_size;
    int cell_size = (MAX_COORD + 1 + G - 1) / G;

    vector<vector<int>> grid_scores(G, vector<int>(G, 0));
    for (const auto& p : mackerels) {
        int r = min(G - 1, p.y / cell_size);
        int c = min(G - 1, p.x / cell_size);
        grid_scores[r][c]++;
    }
    for (const auto& p : sardines) {
        int r = min(G - 1, p.y / cell_size);
        int c = min(G - 1, p.x / cell_size);
        grid_scores[r][c]--;
    }

    long long max_comp_score = 0;
    set<pair<int, int>> best_comp_cells;
    vector<vector<bool>> visited(G, vector<bool>(G, false));

    for (int r = 0; r < G; ++r) {
        for (int c = 0; c < G; ++c) {
            if (!visited[r][c] && grid_scores[r][c] > 0) {
                long long current_score = 0;
                set<pair<int, int>> current_comp_cells;
                queue<pair<int, int>> q;

                q.push({r, c});
                visited[r][c] = true;
                
                while (!q.empty()) {
                    pair<int, int> curr = q.front();
                    q.pop();
                    current_score += grid_scores[curr.first][curr.second];
                    current_comp_cells.insert(curr);

                    int dr[] = {-1, 1, 0, 0};
                    int dc[] = {0, 0, -1, 1};

                    for (int i = 0; i < 4; ++i) {
                        int nr = curr.first + dr[i];
                        int nc = curr.second + dc[i];
                        if (nr >= 0 && nr < G && nc >= 0 && nc < G && !visited[nr][nc] && grid_scores[nr][nc] > 0) {
                            visited[nr][nc] = true;
                            q.push({nr, nc});
                        }
                    }
                }

                if (current_score > max_comp_score) {
                    max_comp_score = current_score;
                    best_comp_cells = current_comp_cells;
                }
            }
        }
    }

    if (best_comp_cells.empty()) {
        return {0, {{0, 0}, {1, 0}, {1, 1}, {0, 1}}};
    }

    int min_r = G, min_c = G;
    for (const auto& cell : best_comp_cells) {
        if (cell.first < min_r) {
            min_r = cell.first;
            min_c = cell.second;
        } else if (cell.first == min_r && cell.second < min_c) {
            min_c = cell.second;
        }
    }

    int start_c = min_c, start_r = min_r;
    int cur_c = start_c, cur_r = start_r;
    int dir = 1; // 0:R, 1:U, 2:L, 3:D

    vector<Point> vertices;
    
    int dc[] = {1, 0, -1, 0};
    int dr[] = {0, 1, 0, -1};
    int left_turn[] = {1, 2, 3, 0};
    int right_turn[] = {3, 0, 1, 2};

    do {
        vertices.push_back({cur_c * cell_size, cur_r * cell_size});
        
        pair<int, int> cell_left, cell_fwd;
        if (dir == 0) { // R
            cell_left = {cur_r, cur_c};
            cell_fwd = {cur_r - 1, cur_c};
        } else if (dir == 1) { // U
            cell_left = {cur_r, cur_c - 1};
            cell_fwd = {cur_r, cur_c};
        } else if (dir == 2) { // L
            cell_left = {cur_r - 1, cur_c - 1};
            cell_fwd = {cur_r, cur_c - 1};
        } else { // D
            cell_left = {cur_r - 1, cur_c};
            cell_fwd = {cur_r - 1, cur_c - 1};
        }

        if (best_comp_cells.count(cell_left)) {
            dir = left_turn[dir];
        } else if (!best_comp_cells.count(cell_fwd)) {
            dir = right_turn[dir];
        }

        cur_c += dc[dir];
        cur_r += dr[dir];

    } while (cur_c != start_c || cur_r != start_r);
    
    vector<Point> simplified_vertices;
    if (vertices.size() > 0) {
        simplified_vertices.push_back(vertices[0]);
        for (size_t i = 1; i < vertices.size(); ++i) {
            if (simplified_vertices.size() < 2) {
                simplified_vertices.push_back(vertices[i]);
                continue;
            }
            Point p_prev = simplified_vertices[simplified_vertices.size()-2];
            Point p_mid = simplified_vertices.back();
            Point p_curr = vertices[i];
            if ((long long)(p_mid.y - p_prev.y) * (p_curr.x - p_mid.x) == (long long)(p_curr.y - p_mid.y) * (p_mid.x - p_prev.x)) {
                simplified_vertices.back() = p_curr;
            } else {
                simplified_vertices.push_back(p_curr);
            }
        }

        if (simplified_vertices.size() >= 3) {
            Point p_prev = simplified_vertices[simplified_vertices.size()-2];
            Point p_mid = simplified_vertices.back();
            Point p_curr = simplified_vertices[0];
            if ((long long)(p_mid.y - p_prev.y) * (p_curr.x - p_mid.x) == (long long)(p_curr.y - p_mid.y) * (p_mid.x - p_prev.x)) {
                simplified_vertices.pop_back();
            }
        }
        if (simplified_vertices.size() >= 3) {
            Point p_prev = simplified_vertices.back();
            Point p_mid = simplified_vertices[0];
            Point p_curr = simplified_vertices[1];
            if ((long long)(p_mid.y - p_prev.y) * (p_curr.x - p_mid.x) == (long long)(p_curr.y - p_mid.y) * (p_mid.x - p_prev.x)) {
                simplified_vertices.erase(simplified_vertices.begin());
            }
        }
    }

    long long perimeter = 0;
    for (size_t i = 0; i < simplified_vertices.size(); ++i) {
        Point p1 = simplified_vertices[i];
        Point p2 = simplified_vertices[(i + 1) % simplified_vertices.size()];
        perimeter += abs(p1.x - p2.x) + abs(p1.y - p2.y);
    }
    
    if (simplified_vertices.size() > 1000 || perimeter > 400000) {
        int r_min = G, r_max = -1, c_min = G, c_max = -1;
        long long score = 0;
        for (const auto& cell : best_comp_cells) {
            r_min = min(r_min, cell.first);
            r_max = max(r_max, cell.first);
            c_min = min(c_min, cell.second);
            c_max = max(c_max, cell.second);
        }
        for(int r = r_min; r <= r_max; ++r) {
            for(int c = c_min; c <= c_max; ++c) {
                score += grid_scores[r][c];
            }
        }

        int x1 = c_min * cell_size;
        int y1 = r_min * cell_size;
        int x2 = (c_max + 1) * cell_size;
        int y2 = (r_max + 1) * cell_size;
        return {score, {{x1, y1}, {x2, y1}, {x2, y2}, {x1, y2}}};
    }
    
    return {max_comp_score, simplified_vertices};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_dummy;
    cin >> n_dummy;

    vector<Point> mackerels(N);
    for (int i = 0; i < N; ++i) {
        cin >> mackerels[i].x >> mackerels[i].y;
    }
    vector<Point> sardines(N);
    for (int i = 0; i < N; ++i) {
        cin >> sardines[i].x >> sardines[i].y;
    }

    Polygon best_polygon = {0, {{0,0},{1,0},{1,1},{0,1}}};

    vector<int> grid_sizes = {200, 250, 300, 400};
    for (int gs : grid_sizes) {
        Polygon p = solve(gs, mackerels, sardines);
        if (p.score > best_polygon.score) {
            best_polygon = p;
        }
    }
    
    int G = 250;
    int cell_size = (MAX_COORD + 1 + G - 1) / G;
    vector<vector<int>> grid_scores(G, vector<int>(G, 0));
    for (const auto& p : mackerels) {
        int r = min(G - 1, p.y / cell_size);
        int c = min(G - 1, p.x / cell_size);
        grid_scores[r][c]++;
    }
    for (const auto& p : sardines) {
        int r = min(G - 1, p.y / cell_size);
        int c = min(G - 1, p.x / cell_size);
        grid_scores[r][c]--;
    }

    long long max_rect_score = 0;
    int best_r1 = -1, best_c1 = -1, best_r2 = -1, best_c2 = -1;
    
    for (int c1 = 0; c1 < G; ++c1) {
        vector<long long> col_sums(G, 0);
        for (int c2 = c1; c2 < G; ++c2) {
            for (int r = 0; r < G; ++r) {
                col_sums[r] += grid_scores[r][c2];
            }
            long long current_max = 0;
            long long total_max = 0;
            int current_r1 = 0, best_r1_kadane = -1, best_r2_kadane = -1;
            for (int r = 0; r < G; ++r) {
                current_max += col_sums[r];
                if (current_max <= 0) {
                    current_max = 0;
                    current_r1 = r + 1;
                }
                if (current_max > total_max) {
                    total_max = current_max;
                    best_r1_kadane = current_r1;
                    best_r2_kadane = r;
                }
            }
            if (total_max > max_rect_score) {
                max_rect_score = total_max;
                best_r1 = best_r1_kadane;
                best_r2 = best_r2_kadane;
                best_c1 = c1;
                best_c2 = c2;
            }
        }
    }

    if (max_rect_score > best_polygon.score) {
        int x1 = best_c1 * cell_size;
        int y1 = best_r1 * cell_size;
        int x2 = (best_c2 + 1) * cell_size;
        int y2 = (best_r2 + 1) * cell_size;
        best_polygon.score = max_rect_score;
        best_polygon.vertices = {{x1, y1}, {x2, y1}, {x2, y2}, {x1, y2}};
    }


    cout << best_polygon.vertices.size() << "\n";
    for (const auto& v : best_polygon.vertices) {
        cout << v.x << " " << v.y << "\n";
    }

    return 0;
}