#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <queue>
#include <set>
#include <map>
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
};

bool is_on_segment(Point p, Point a, Point b) {
    if (a.x == b.x) { // Vertical
        return p.x == a.x && min(a.y, b.y) <= p.y && p.y <= max(a.y, b.y);
    }
    if (a.y == b.y) { // Horizontal
        return p.y == a.y && min(a.x, b.x) <= p.x && p.x <= max(a.x, b.x);
    }
    return false;
}

int is_inside(Point p, const vector<Point>& polygon) {
    if (polygon.empty()) return 0;
    for (size_t i = 0; i < polygon.size(); ++i) {
        if (is_on_segment(p, polygon[i], polygon[(i + 1) % polygon.size()])) {
            return 1;
        }
    }

    int crossings = 0;
    for (size_t i = 0; i < polygon.size(); ++i) {
        Point p1 = polygon[i];
        Point p2 = polygon[(i + 1) % polygon.size()];
        if (p1.x == p2.x && p1.x > p.x) {
            if ((p1.y > p.y && p2.y <= p.y) || (p2.y > p.y && p1.y <= p.y)) {
                crossings++;
            }
        }
    }
    return (crossings % 2 == 1);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    auto start_time = chrono::high_resolution_clock::now();

    int N;
    cin >> N;
    vector<Point> mackerels(N), sardines(N);
    for (int i = 0; i < N; ++i) cin >> mackerels[i].x >> mackerels[i].y;
    for (int i = 0; i < N; ++i) cin >> sardines[i].x >> sardines[i].y;

    vector<Point> best_polygon;
    long long max_score = -1e18; 

    vector<int> grid_sizes = {100, 125, 150, 175, 200, 250};
    
    for (int C : grid_sizes) {
        auto current_time = chrono::high_resolution_clock::now();
        if (chrono::duration_cast<chrono::milliseconds>(current_time - start_time).count() > 2800) {
            break;
        }

        int W = (MAX_COORD + 1 + C - 1) / C;
        vector<vector<int>> scores(C, vector<int>(C, 0));

        for (const auto& p : mackerels) {
            int gx = min(C - 1, p.x / W);
            int gy = min(C - 1, p.y / W);
            scores[gy][gx]++;
        }
        for (const auto& p : sardines) {
            int gx = min(C - 1, p.x / W);
            int gy = min(C - 1, p.y / W);
            scores[gy][gx]--;
        }

        int max_s = 0;
        pair<int, int> start_cell = {-1, -1};
        for (int i = 0; i < C; ++i) {
            for (int j = 0; j < C; ++j) {
                if (scores[i][j] > max_s) {
                    max_s = scores[i][j];
                    start_cell = {i, j};
                }
            }
        }

        if (start_cell.first == -1) continue;
        
        vector<vector<bool>> best_region_map;
        long long current_best_grid_score = 0;

        priority_queue<pair<int, pair<int, int>>> pq;
        map<pair<int, int>, bool> visited_pq;
        
        long long current_score = 0;
        set<pair<int,int>> region_cells;
        
        pq.push({scores[start_cell.first][start_cell.second], start_cell});
        visited_pq[start_cell] = true;

        while (!pq.empty()) {
            auto top = pq.top();
            pq.pop();
            pair<int, int> cell = top.second;
            
            if (region_cells.count(cell)) continue;

            region_cells.insert(cell);
            current_score += scores[cell.first][cell.second];

            if (current_score > current_best_grid_score) {
                current_best_grid_score = current_score;
                best_region_map.assign(C, vector<bool>(C, false));
                for(auto const& c : region_cells) best_region_map[c.first][c.second] = true;
            }

            int r = cell.first;
            int c = cell.second;
            int dr[] = {-1, 1, 0, 0};
            int dc[] = {0, 0, -1, 1};

            for (int i = 0; i < 4; ++i) {
                int nr = r + dr[i];
                int nc = c + dc[i];
                if (nr >= 0 && nr < C && nc >= 0 && nc < C && !visited_pq[{nr, nc}]) {
                    pq.push({scores[nr][nc], {nr, nc}});
                    visited_pq[{nr, nc}] = true;
                }
            }
        }
        
        if (best_region_map.empty()) continue;
        
        map<Point, vector<Point>> adj;
        Point start_node = {-1, -1};

        for (int r = 0; r < C; ++r) {
            for (int c = 0; c < C; ++c) {
                bool in1 = best_region_map[r][c];
                bool in2 = (r + 1 < C) ? best_region_map[r+1][c] : false;
                if (in1 != in2) {
                    Point p1 = {c * W, (r + 1) * W};
                    Point p2 = {(c + 1) * W, (r + 1) * W};
                    adj[p1].push_back(p2);
                    adj[p2].push_back(p1);
                    if (start_node.x == -1) start_node = p1;
                }
                in2 = (c + 1 < C) ? best_region_map[r][c+1] : false;
                if (in1 != in2) {
                    Point p1 = {(c + 1) * W, r * W};
                    Point p2 = {(c + 1) * W, (r + 1) * W};
                    adj[p1].push_back(p2);
                    adj[p2].push_back(p1);
                    if (start_node.x == -1) start_node = p1;
                }
            }
        }

        if (start_node.x == -1) continue;

        vector<Point> polygon;
        Point curr = start_node;
        Point prev = {-1, -1};
        
        do {
            polygon.push_back(curr);
            bool found_next = false;
            for (Point& next : adj[curr]) {
                if (!(next == prev)) {
                    prev = curr;
                    curr = next;
                    found_next = true;
                    break;
                }
            }
            if (!found_next) break; 
        } while (!(curr == start_node));
        
        vector<Point> simplified_polygon;
        if (polygon.size() >= 2) {
            simplified_polygon.push_back(polygon[0]);
            for (size_t i = 1; i < polygon.size(); ++i) {
                Point p_prev = simplified_polygon.back();
                Point p_curr = polygon[i];
                Point p_next = polygon[(i + 1) % polygon.size()];
                if (!((p_prev.x == p_curr.x && p_curr.x == p_next.x) || (p_prev.y == p_curr.y && p_curr.y == p_next.y))) {
                    simplified_polygon.push_back(p_curr);
                }
            }
        }

        if (simplified_polygon.size() >= 3) {
            Point p_prev = simplified_polygon.back();
            Point p_curr = simplified_polygon[0];
            Point p_next = simplified_polygon[1];
            if ((p_prev.x == p_curr.x && p_curr.x == p_next.x) || (p_prev.y == p_curr.y && p_curr.y == p_next.y)) {
                simplified_polygon.erase(simplified_polygon.begin());
            }
        }

        long long total_len = 0;
        for (size_t i = 0; i < simplified_polygon.size(); ++i) {
            Point p1 = simplified_polygon[i];
            Point p2 = simplified_polygon[(i + 1) % simplified_polygon.size()];
            total_len += abs(p1.x - p2.x) + abs(p1.y - p2.y);
        }
        
        bool ok = true;
        for(const auto& p : simplified_polygon) {
            if (p.x < 0 || p.x > MAX_COORD || p.y < 0 || p.y > MAX_COORD) {
                ok = false;
                break;
            }
        }
        if (!ok || simplified_polygon.size() < 3) continue;

        if (simplified_polygon.size() > 1000 || total_len > 400000) continue;
        
        int a = 0, b = 0;
        for (const auto& fish : mackerels) if (is_inside(fish, simplified_polygon)) a++;
        for (const auto& fish : sardines) if (is_inside(fish, simplified_polygon)) b++;

        if (a - b > max_score) {
            max_score = a - b;
            best_polygon = simplified_polygon;
        }
    }

    if (best_polygon.empty()) {
        cout << 4 << endl;
        cout << "0 0\n0 1\n1 1\n1 0\n";
    } else {
        cout << best_polygon.size() << endl;
        for (const auto& p : best_polygon) {
            cout << p.x << " " << p.y << endl;
        }
    }

    return 0;
}