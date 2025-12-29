#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <map>
#include <set>
#include <queue>
#include <chrono>

using namespace std;

const int MAX_COORD = 100000;

struct Point {
    int x, y;

    bool operator<(const Point& other) const {
        if (x != other.x) return x < other.x;
        return y < other.y;
    }
    bool operator==(const Point& other) const {
        return x == other.x && y == other.y;
    }
     bool operator!=(const Point& other) const {
        return !(*this == other);
    }
};

struct Fish {
    Point p;
    bool is_mackerel;
};

int N;
vector<Fish> all_fish;
vector<Point> best_polygon;
int best_score = -1e9;

auto start_time = chrono::high_resolution_clock::now();

bool is_inside(const Point& p, const vector<Point>& polygon) {
    if (polygon.empty()) return false;

    bool on_edge = false;
    for (size_t i = 0; i < polygon.size(); ++i) {
        Point p1 = polygon[i];
        Point p2 = polygon[(i + 1) % polygon.size()];
        if (p1.x == p2.x) { // Vertical
            if (p.x == p1.x && p.y >= min(p1.y, p2.y) && p.y <= max(p1.y, p2.y)) {
                on_edge = true;
                break;
            }
        } else { // Horizontal
            if (p.y == p1.y && p.x >= min(p1.x, p2.x) && p.x <= max(p1.x, p2.x)) {
                on_edge = true;
                break;
            }
        }
    }
    if (on_edge) return true;

    int crossings = 0;
    for (size_t i = 0; i < polygon.size(); ++i) {
        Point p1 = polygon[i];
        Point p2 = polygon[(i + 1) % polygon.size()];
        if (p1.y == p2.y) continue;
        if (p.y < min(p1.y, p2.y) || p.y >= max(p1.y, p2.y)) continue;
        if (p.x > p1.x && p.x > p2.x) continue;
        if (p1.x > p.x && p2.x > p.x) {
             crossings++;
        }
    }
    return (crossings % 2) == 1;
}

void update_best_polygon(const vector<Point>& polygon) {
    if (polygon.empty() || polygon.size() < 4) return;
    long long perimeter = 0;
    for (size_t i = 0; i < polygon.size(); ++i) {
        Point p1 = polygon[i];
        Point p2 = polygon[(i + 1) % polygon.size()];
        perimeter += abs(p1.x - p2.x) + abs(p1.y - p2.y);
    }
    if (polygon.size() > 1000 || perimeter > 400000) {
        return;
    }

    int score = 0;
    for (const auto& fish : all_fish) {
        if (is_inside(fish.p, polygon)) {
            score += (fish.is_mackerel ? 1 : -1);
        }
    }
    
    if (score > best_score) {
        best_score = score;
        best_polygon = polygon;
    }
}


void solve_rect() {
    const int GRID_SIZE = 400;
    const int CELL_SIZE = (MAX_COORD / GRID_SIZE) + 1;

    vector<vector<int>> grid_scores(GRID_SIZE, vector<int>(GRID_SIZE, 0));
    for (const auto& fish : all_fish) {
        int gx = min(GRID_SIZE - 1, fish.p.x / CELL_SIZE);
        int gy = min(GRID_SIZE - 1, fish.p.y / CELL_SIZE);
        grid_scores[gx][gy] += (fish.is_mackerel ? 1 : -1);
    }
    
    vector<vector<int>> prefix_sum(GRID_SIZE + 1, vector<int>(GRID_SIZE + 1, 0));
    for (int i = 0; i < GRID_SIZE; ++i) {
        for (int j = 0; j < GRID_SIZE; ++j) {
            prefix_sum[i+1][j+1] = grid_scores[i][j] + prefix_sum[i][j+1] + prefix_sum[i+1][j] - prefix_sum[i][j];
        }
    }
    
    int max_rect_score = -1e9;
    int best_x1 = -1, best_y1 = -1, best_x2 = -1, best_y2 = -1;

    for (int y1 = 0; y1 < GRID_SIZE; ++y1) {
        for (int y2 = y1; y2 < GRID_SIZE; ++y2) {
            int current_sum = 0;
            int current_x1 = 0;
            for (int x2 = 0; x2 < GRID_SIZE; ++x2) {
                int col_sum = prefix_sum[x2+1][y2+1] - prefix_sum[x2][y2+1] - prefix_sum[x2+1][y1] + prefix_sum[x2][y1];
                current_sum += col_sum;
                if (current_sum > max_rect_score) {
                    max_rect_score = current_sum;
                    best_x1 = current_x1; best_y1 = y1; best_x2 = x2; best_y2 = y2;
                }
                if (current_sum < 0) {
                    current_sum = 0;
                    current_x1 = x2 + 1;
                }
            }
        }
    }

    if (best_x1 != -1) {
        int r_x1 = best_x1 * CELL_SIZE;
        int r_y1 = best_y1 * CELL_SIZE;
        int r_x2 = (best_x2 + 1) * CELL_SIZE;
        int r_y2 = (best_y2 + 1) * CELL_SIZE;
        r_x2 = min(r_x2, MAX_COORD);
        r_y2 = min(r_y2, MAX_COORD);
        vector<Point> rect_poly = {{r_x1, r_y1}, {r_x2, r_y1}, {r_x2, r_y2}, {r_x1, r_y2}};
        update_best_polygon(rect_poly);
    }
}


void solve_greedy() {
    const int GRID_SIZE = 200;
    const int CELL_SIZE = (MAX_COORD / GRID_SIZE) + 1;

    vector<vector<int>> grid_scores(GRID_SIZE, vector<int>(GRID_SIZE, 0));
    for (const auto& fish : all_fish) {
        int gx = min(GRID_SIZE - 1, fish.p.x / CELL_SIZE);
        int gy = min(GRID_SIZE - 1, fish.p.y / CELL_SIZE);
        grid_scores[gx][gy] += (fish.is_mackerel ? 1 : -1);
    }

    vector<pair<int, pair<int, int>>> positive_cells;
    for (int i = 0; i < GRID_SIZE; ++i) {
        for (int j = 0; j < GRID_SIZE; ++j) {
            if (grid_scores[i][j] > 0) {
                positive_cells.push_back({grid_scores[i][j], {i, j}});
            }
        }
    }
    sort(positive_cells.rbegin(), positive_cells.rend());

    int K_SEEDS = min((int)positive_cells.size(), 15);
    
    for (int k = 0; k < K_SEEDS; ++k) {
        auto now = chrono::high_resolution_clock::now();
        if (chrono::duration_cast<chrono::milliseconds>(now - start_time).count() > 2800) break;

        set<pair<int, int>> R;
        priority_queue<pair<int, pair<int, int>>> pq;
        set<pair<int, int>> pq_set;

        pair<int, int> seed = positive_cells[k].second;
        R.insert(seed);
        int dx[] = {0, 0, 1, -1}, dy[] = {1, -1, 0, 0};
        for(int i=0; i<4; ++i) {
            int nx = seed.first + dx[i], ny = seed.second + dy[i];
            if(nx >=0 && nx < GRID_SIZE && ny >= 0 && ny < GRID_SIZE) {
                pq.push({grid_scores[nx][ny], {nx,ny}});
                pq_set.insert({nx,ny});
            }
        }

        while (!pq.empty()) {
            auto top = pq.top(); pq.pop();
            if (top.first <= 0) break;
            
            pair<int, int> curr = top.second;
            R.insert(curr);
            
            for (int i = 0; i < 4; ++i) {
                int nx = curr.first + dx[i], ny = curr.second + dy[i];
                if (nx >= 0 && nx < GRID_SIZE && ny >= 0 && ny < GRID_SIZE && R.find({nx, ny}) == R.end() && pq_set.find({nx,ny}) == pq_set.end()) {
                   pq.push({grid_scores[nx][ny], {nx, ny}});
                   pq_set.insert({nx,ny});
                }
            }
        }
        if (R.empty()) continue;

        map<Point, vector<Point>> adj;
        {
            map<int, vector<pair<int, int>>> horz_segs, vert_segs;
            for (auto const& cell : R) {
                int i = cell.first, j = cell.second;
                if (R.find({i, j - 1}) == R.end()) horz_segs[j].push_back({i, i + 1});
                if (R.find({i, j + 1}) == R.end()) horz_segs[j + 1].push_back({i, i + 1});
                if (R.find({i - 1, j}) == R.end()) vert_segs[i].push_back({j, j + 1});
                if (R.find({i + 1, j}) == R.end()) vert_segs[i + 1].push_back({j, j + 1});
            }

            auto merge_segs = [](auto& segs_map){
                for (auto& pair : segs_map) {
                    auto& segs = pair.second;
                    if(segs.empty()) continue;
                    sort(segs.begin(), segs.end());
                    vector<pair<int,int>> merged;
                    merged.push_back(segs[0]);
                    for(size_t i = 1; i < segs.size(); ++i) {
                        if(segs[i].first == merged.back().second) merged.back().second = segs[i].second;
                        else merged.push_back(segs[i]);
                    }
                    segs = merged;
                }
            };
            merge_segs(horz_segs);
            merge_segs(vert_segs);

            for (auto const& [y, segs] : horz_segs) for (auto const& seg : segs) {
                Point p1 = {min(MAX_COORD, seg.first * CELL_SIZE), min(MAX_COORD, y * CELL_SIZE)};
                Point p2 = {min(MAX_COORD, seg.second * CELL_SIZE), min(MAX_COORD, y * CELL_SIZE)};
                if (p1 == p2) continue;
                adj[p1].push_back(p2); adj[p2].push_back(p1);
            }
            for (auto const& [x, segs] : vert_segs) for (auto const& seg : segs) {
                Point p1 = {min(MAX_COORD, x * CELL_SIZE), min(MAX_COORD, seg.first * CELL_SIZE)};
                Point p2 = {min(MAX_COORD, x * CELL_SIZE), min(MAX_COORD, seg.second * CELL_SIZE)};
                if (p1 == p2) continue;
                adj[p1].push_back(p2); adj[p2].push_back(p1);
            }
        }
        
        if (adj.empty()) continue;

        set<Point> visited_nodes;
        Point start_node = adj.begin()->first;
        Point current_node = start_node;
        Point prev_node = {-1, -1};

        vector<Point> polygon;
        while (visited_nodes.find(current_node) == visited_nodes.end()) {
            polygon.push_back(current_node);
            visited_nodes.insert(current_node);
            bool found_next = false;
            for (const auto& next_node : adj[current_node]) {
                if (next_node != prev_node) {
                    prev_node = current_node;
                    current_node = next_node;
                    found_next = true;
                    break;
                }
            }
            if(!found_next || current_node == start_node) break;
        }
        update_best_polygon(polygon);
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N;
    for (int i = 0; i < 2 * N; ++i) {
        int x, y;
        cin >> x >> y;
        all_fish.push_back({{x, y}, i < N});
    }

    solve_rect();
    solve_greedy();
    
    if (best_polygon.empty()) {
        cout << 4 << endl;
        cout << "0 0" << endl;
        cout << "1 0" << endl;
        cout << "1 1" << endl;
        cout << "0 1" << endl;
    } else {
        cout << best_polygon.size() << endl;
        for (const auto& p : best_polygon) {
            cout << p.x << " " << p.y << endl;
        }
    }

    return 0;
}