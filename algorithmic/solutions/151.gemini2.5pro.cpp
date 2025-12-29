#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <algorithm>
#include <vector>

using namespace std;

const int INF = 1e9;

int N;
int si, sj;
vector<string> C;

struct Point {
    int r, c;
    bool operator==(const Point& other) const {
        return r == other.r && c == other.c;
    }
};

struct State {
    int r, c, cost;
    bool operator>(const State& other) const {
        return cost > other.cost;
    }
};

vector<Point> road_squares;
int point_to_id[70][70];
vector<vector<Point>> visible_from;
bool is_covered[70][70];
int total_road_squares = 0;
int covered_count = 0;
int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char move_chars[] = {'U', 'D', 'L', 'R'};

void precompute() {
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            point_to_id[i][j] = -1;
            is_covered[i][j] = false;
        }
    }

    int current_id = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (C[i][j] != '#') {
                road_squares.push_back({i, j});
                point_to_id[i][j] = current_id++;
            }
        }
    }
    total_road_squares = road_squares.size();
    visible_from.resize(total_road_squares);

    for (int i = 0; i < total_road_squares; ++i) {
        Point p = road_squares[i];
        vector<Point> visible;
        
        int min_c = p.c, max_c = p.c;
        while(min_c > 0 && C[p.r][min_c-1] != '#') min_c--;
        while(max_c < N-1 && C[p.r][max_c+1] != '#') max_c++;
        for(int c = min_c; c <= max_c; ++c) visible.push_back({p.r, c});
        
        int min_r = p.r, max_r = p.r;
        while(min_r > 0 && C[min_r-1][p.c] != '#') min_r--;
        while(max_r < N-1 && C[max_r+1][p.c] != '#') max_r++;
        for(int r = min_r; r <= max_r; ++r) {
            if(r != p.r) visible.push_back({r, p.c});
        }
        
        visible_from[i] = visible;
    }
}

pair<vector<vector<int>>, vector<vector<Point>>> dijkstra(Point start) {
    vector<vector<int>> dist(N, vector<int>(N, INF));
    vector<vector<Point>> prev(N, vector<Point>(N, {-1, -1}));
    priority_queue<State, vector<State>, greater<State>> pq;

    dist[start.r][start.c] = 0;
    pq.push({start.r, start.c, 0});

    while (!pq.empty()) {
        State current = pq.top();
        pq.pop();

        if (current.cost > dist[current.r][current.c]) {
            continue;
        }

        for (int i = 0; i < 4; ++i) {
            int nr = current.r + dr[i];
            int nc = current.c + dc[i];

            if (nr >= 0 && nr < N && nc >= 0 && nc < N && C[nr][nc] != '#') {
                int new_cost = current.cost + (C[nr][nc] - '0');
                if (new_cost < dist[nr][nc]) {
                    dist[nr][nc] = new_cost;
                    prev[nr][nc] = {current.r, current.c};
                    pq.push({nr, nc, new_cost});
                }
            }
        }
    }
    return {dist, prev};
}

string reconstruct_path(Point start, Point end, const vector<vector<Point>>& prev) {
    if (start == end) return "";
    string path = "";
    Point curr = end;
    while (!(curr == start)) {
        Point p = prev[curr.r][curr.c];
        if (p.r == -1) return "";
        for (int i = 0; i < 4; ++i) {
            if (p.r + dr[i] == curr.r && p.c + dc[i] == curr.c) {
                path += move_chars[i];
                break;
            }
        }
        curr = p;
    }
    reverse(path.begin(), path.end());
    return path;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> si >> sj;
    C.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> C[i];
    }

    precompute();

    Point curr = {si, sj};
    string total_path = "";

    int start_id = point_to_id[curr.r][curr.c];
    for (const auto& p : visible_from[start_id]) {
        if (!is_covered[p.r][p.c]) {
            is_covered[p.r][p.c] = true;
            covered_count++;
        }
    }

    while (covered_count < total_road_squares) {
        auto [dist, prev] = dijkstra(curr);

        Point uncovered_focus = {-1, -1};
        for (const auto& p : road_squares) {
            if (!is_covered[p.r][p.c]) {
                uncovered_focus = p;
                break;
            }
        }
        
        if (uncovered_focus.r == -1) break;

        Point best_target = {-1, -1};
        double max_score = -1.0;

        int focus_id = point_to_id[uncovered_focus.r][uncovered_focus.c];
        const auto& candidates = visible_from[focus_id];

        for (const auto& target : candidates) {
            if (dist[target.r][target.c] == INF) continue;

            int new_coverage = 0;
            int target_id = point_to_id[target.r][target.c];
            for (const auto& p : visible_from[target_id]) {
                if (!is_covered[p.r][p.c]) {
                    new_coverage++;
                }
            }

            if (new_coverage == 0) continue;
            
            double score = pow(new_coverage, 2.0) / (dist[target.r][target.c] == 0 ? 1.0 : (double)dist[target.r][target.c]);

            if (score > max_score) {
                max_score = score;
                best_target = target;
            }
        }

        if (best_target.r == -1) {
            for (const auto& target : road_squares) {
                if (dist[target.r][target.c] == INF) continue;
                int new_coverage = 0;
                int target_id = point_to_id[target.r][target.c];
                for (const auto& p : visible_from[target_id]) {
                    if (!is_covered[p.r][p.c]) new_coverage++;
                }

                if (new_coverage == 0) continue;
                double score = pow(new_coverage, 2.0) / (dist[target.r][target.c] == 0 ? 1.0 : (double)dist[target.r][target.c]);

                if (score > max_score) {
                    max_score = score;
                    best_target = target;
                }
            }
        }

        if (best_target.r == -1) break;

        string segment_path = reconstruct_path(curr, best_target, prev);
        total_path += segment_path;
        curr = best_target;

        int best_target_id = point_to_id[best_target.r][best_target.c];
        for (const auto& p : visible_from[best_target_id]) {
            if (!is_covered[p.r][p.c]) {
                is_covered[p.r][p.c] = true;
                covered_count++;
            }
        }
    }

    auto [dist, prev] = dijkstra(curr);
    total_path += reconstruct_path(curr, {si, sj}, prev);

    cout << total_path << endl;

    return 0;
}