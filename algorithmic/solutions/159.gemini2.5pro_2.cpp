#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <queue>
#include <map>
#include <numeric>
#include <chrono>

using namespace std;

auto start_time = chrono::steady_clock::now();

int N;
double C;

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

double point_weight(const Point& p) {
    return (p.x - C) * (p.x - C) + (p.y - C) * (p.y - C) + 1;
}

struct Candidate {
    Point p1, p2, p3, p4;
    double score;
    bool is_tilted;
    bool operator<(const Candidate& other) const {
        return score > other.score;
    }
};

bool grid[62][62];
vector<Point> all_dots;
map<int, vector<pair<int, int>>> used_segments_h, used_segments_v, used_segments_d1, used_segments_d2;

bool is_in_bounds(const Point& p) {
    return p.x >= 0 && p.x < N && p.y >= 0 && p.y < N;
}

bool check_perimeter(Point p1, Point p2, Point p3, Point p4) {
    Point points[] = {p1, p2, p3, p4};
    long long dists[6];
    int k=0;
    for(int i=0; i<4; ++i) {
        for(int j=i+1; j<4; ++j) {
            dists[k++] = (long long)(points[i].x - points[j].x)*(points[i].x - points[j].x) + (long long)(points[i].y - points[j].y)*(points[i].y - points[j].y);
        }
    }
    sort(dists, dists+6);
    long long diag_dist_sq = dists[5];
    
    vector<pair<Point, Point>> edges;
    for(int i=0; i<4; ++i) {
        for(int j=i+1; j<4; ++j) {
            long long d = (long long)(points[i].x - points[j].x)*(points[i].x - points[j].x) + (long long)(points[i].y - points[j].y)*(points[i].y - points[j].y);
            if (d < diag_dist_sq) {
                edges.push_back({points[i], points[j]});
            }
        }
    }

    for (const auto& edge : edges) {
        Point A = edge.first;
        Point B = edge.second;
        int dx = B.x - A.x;
        int dy = B.y - A.y;
        if (dx == 0 && dy == 0) continue;
        int common_divisor = std::gcd(abs(dx), abs(dy));
        if (common_divisor == 0) continue;
        int step_x = dx / common_divisor;
        int step_y = dy / common_divisor;
        for (int j = 1; j < common_divisor; ++j) {
            int cur_x = A.x + j * step_x;
            int cur_y = A.y + j * step_y;
            if (grid[cur_x][cur_y]) {
                return false;
            }
        }
    }
    return true;
}

bool check_and_add_segment(map<int, vector<pair<int, int>>>& seg_map, int line_idx, int c1, int c2, bool apply) {
    int lo = min(c1, c2);
    int hi = max(c1, c2);
    if (lo == hi) return true;

    if (seg_map.count(line_idx)) {
        for (const auto& s : seg_map.at(line_idx)) {
            if (max(s.first, lo) < min(s.second, hi)) {
                return false;
            }
        }
    }

    if (apply) {
        auto& segs = seg_map[line_idx];
        segs.push_back({lo, hi});
        sort(segs.begin(), segs.end());
        if (segs.size() > 1) {
            vector<pair<int, int>> merged;
            merged.push_back(segs[0]);
            for (size_t i = 1; i < segs.size(); ++i) {
                if (segs[i].first <= merged.back().second) {
                    merged.back().second = max(merged.back().second, segs[i].second);
                } else {
                    merged.push_back(segs[i]);
                }
            }
            segs = merged;
        }
    }
    return true;
}

bool check_segments(const Point& p1, const Point& p2, const Point& p3, const Point& p4, bool is_tilted, bool apply) {
    if (!is_tilted) {
        if (!check_and_add_segment(used_segments_v, p1.x, p1.y, p2.y, apply)) return false;
        if (!check_and_add_segment(used_segments_h, p2.y, p2.x, p3.x, apply)) return false;
        if (!check_and_add_segment(used_segments_v, p3.x, p3.y, p4.y, apply)) return false;
        if (!check_and_add_segment(used_segments_h, p4.y, p4.x, p1.x, apply)) return false;
    } else {
        Point points[] = {p1, p2, p3, p4};
        long long dists[6];
        int k=0;
        for(int i=0; i<4; ++i) for(int j=i+1; j<4; ++j) dists[k++] = (long long)(points[i].x - points[j].x)*(points[i].x - points[j].x) + (long long)(points[i].y - points[j].y)*(points[i].y - points[j].y);
        sort(dists, dists+6);
        long long diag_dist_sq = dists[5];
        
        vector<pair<Point, Point>> edges;
        for(int i=0; i<4; ++i) {
            for(int j=i+1; j<4; ++j) {
                long long d = (long long)(points[i].x - points[j].x)*(points[i].x - points[j].x) + (long long)(points[i].y - points[j].y)*(points[i].y - points[j].y);
                if (d < diag_dist_sq) {
                    edges.push_back({points[i], points[j]});
                }
            }
        }
        for (const auto& edge : edges) {
            Point A = edge.first;
            Point B = edge.second;
            if ((B.y - A.y) == (B.x - A.x)) { // slope 1
                if (!check_and_add_segment(used_segments_d2, A.x - A.y, A.x, B.x, apply)) return false;
            } else { // slope -1
                if (!check_and_add_segment(used_segments_d1, A.x + A.y, A.x, B.x, apply)) return false;
            }
        }
    }
    return true;
}

void add_candidate(map<Point, Candidate>& candidates, Point p1, Point p2, Point p3, Point p4, bool is_tilted) {
    if (!is_in_bounds(p1) || grid[p1.x][p1.y]) return;
    double score = point_weight(p1);
    if (candidates.find(p1) == candidates.end() || candidates[p1].score < score) {
        candidates[p1] = {p1, p2, p3, p4, score, is_tilted};
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int M;
    cin >> N >> M;
    C = (N - 1) / 2.0;

    queue<Point> new_dots_q;
    for (int i = 0; i < M; ++i) {
        int x, y;
        cin >> x >> y;
        Point p = {x, y};
        grid[x][y] = true;
        all_dots.push_back(p);
        new_dots_q.push(p);
    }

    vector<Candidate> solutions;

    while (chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now() - start_time).count() < 2800) {
        if (new_dots_q.empty()) break;
        
        vector<Point> hot_dots;
        while (!new_dots_q.empty()) {
            hot_dots.push_back(new_dots_q.front());
            new_dots_q.pop();
        }

        map<Point, Candidate> candidates;
        
        for (size_t i = 0; i < hot_dots.size(); ++i) {
            const auto& p1 = hot_dots[i];
            for (size_t j = 0; j < all_dots.size(); ++j) {
                const auto& p2 = all_dots[j];
                if(p1.x == p2.x && p1.y == p2.y) continue;
                
                // Axis-aligned
                if (p1.x != p2.x && p1.y != p2.y) {
                    Point p3 = {p1.x, p2.y};
                    Point p4 = {p2.x, p1.y};
                    if (is_in_bounds(p3) && is_in_bounds(p4)) {
                        if (grid[p3.x][p3.y]) add_candidate(candidates, p4, p1, p2, p3, false);
                        if (grid[p4.x][p4.y]) add_candidate(candidates, p3, p1, p2, p4, false);
                    }
                }

                // 45-degree tilted
                if ((abs(p1.x - p2.x) % 2) == (abs(p1.y - p2.y) % 2)) {
                    int u1 = p1.x + p1.y, v1 = p1.x - p1.y;
                    int u2 = p2.x + p2.y, v2 = p2.x - p2.y;
                    if (u1 != u2 && v1 != v2) {
                        Point p3 = {(u1 + v2) / 2, (u1 - v2) / 2};
                        Point p4 = {(u2 + v1) / 2, (u2 - v1) / 2};
                        if (is_in_bounds(p3) && is_in_bounds(p4)) {
                           if (grid[p3.x][p3.y]) add_candidate(candidates, p4, p1, p2, p3, true);
                           if (grid[p4.x][p4.y]) add_candidate(candidates, p3, p1, p2, p4, true);
                        }
                    }
                }
            }
        }

        vector<Candidate> valid_candidates;
        for (auto const& [p, cand] : candidates) {
            if (check_perimeter(cand.p1, cand.p2, cand.p3, cand.p4)) {
                valid_candidates.push_back(cand);
            }
        }
        sort(valid_candidates.begin(), valid_candidates.end());

        bool changed = false;
        for (const auto& cand : valid_candidates) {
            if (!grid[cand.p1.x][cand.p1.y]) {
                Point p_new=cand.p1, p_A=cand.p2, p_B=cand.p3, p_C=cand.p4;
                Point rect_pts[4]; 
                if (!cand.is_tilted) {
                     rect_pts[0] = p_A; rect_pts[1] = p_C; rect_pts[2] = p_B; rect_pts[3] = p_new;
                } else {
                     rect_pts[0] = p_A; rect_pts[1] = p_C; rect_pts[2] = p_B; rect_pts[3] = p_new;
                }
                
                if (check_segments(rect_pts[0], rect_pts[1], rect_pts[2], rect_pts[3], cand.is_tilted, true)) {
                    grid[cand.p1.x][cand.p1.y] = true;
                    new_dots_q.push(cand.p1);
                    all_dots.push_back(cand.p1);
                    solutions.push_back(cand);
                    changed = true;
                }
            }
        }
        if (!changed) break;
    }

    cout << solutions.size() << endl;
    for (const auto& sol : solutions) {
        cout << sol.p1.x << " " << sol.p1.y << " "
             << sol.p2.x << " " << sol.p2.y << " "
             << sol.p3.x << " " << sol.p3.y << " "
             << sol.p4.x << " " << sol.p4.y << endl;
    }

    return 0;
}