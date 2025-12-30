#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <algorithm>

// Fast I/O
void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

const int INF = 1e9;

struct State {
    int r, c, cost;

    bool operator>(const State& other) const {
        return cost > other.cost;
    }
};

struct Point {
    int r, c;
};

int N;
Point start_pos;
std::vector<std::string> grid;
std::vector<std::vector<int>> cost_grid;

// For corridors
std::vector<std::vector<int>> horiz_corridor_id;
std::vector<std::vector<int>> vert_corridor_id;
int num_horiz_corridors = 0;
int num_vert_corridors = 0;
std::vector<bool> is_corridor_covered;
std::vector<std::vector<Point>> corridor_members;

// Dijkstra
std::vector<std::vector<int>> dist;
std::vector<std::vector<Point>> parent;

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char move_char[] = {'U', 'D', 'L', 'R'};

void dijkstra(Point start) {
    dist.assign(N, std::vector<int>(N, INF));
    parent.assign(N, std::vector<Point>(N, {-1, -1}));
    std::priority_queue<State, std::vector<State>, std::greater<State>> pq;

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

            if (nr >= 0 && nr < N && nc >= 0 && nc < N && grid[nr][nc] != '#') {
                int new_cost = current.cost + cost_grid[nr][nc];
                if (new_cost < dist[nr][nc]) {
                    dist[nr][nc] = new_cost;
                    parent[nr][nc] = {current.r, current.c};
                    pq.push({nr, nc, new_cost});
                }
            }
        }
    }
}

std::string reconstruct_path(Point from, Point to) {
    if (from.r == to.r && from.c == to.c) {
        return "";
    }
    
    std::string path_segment = "";
    Point curr = to;
    while (curr.r != from.r || curr.c != from.c) {
        Point prev = parent[curr.r][curr.c];
        for (int i = 0; i < 4; ++i) {
            if (prev.r + dr[i] == curr.r && prev.c + dc[i] == curr.c) {
                path_segment += move_char[i];
                break;
            }
        }
        curr = prev;
    }
    std::reverse(path_segment.begin(), path_segment.end());
    return path_segment;
}

int main() {
    fast_io();

    int si, sj;
    std::cin >> N >> si >> sj;
    start_pos = {si, sj};
    grid.resize(N);
    for (int i = 0; i < N; ++i) {
        std::cin >> grid[i];
    }

    cost_grid.assign(N, std::vector<int>(N));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] != '#') {
                cost_grid[i][j] = grid[i][j] - '0';
            }
        }
    }

    horiz_corridor_id.assign(N, std::vector<int>(N, -1));
    vert_corridor_id.assign(N, std::vector<int>(N, -1));

    // Identify horizontal corridors
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] != '#' && (j == 0 || grid[i][j - 1] == '#')) {
                std::vector<Point> members;
                int k = j;
                while (k < N && grid[i][k] != '#') {
                    horiz_corridor_id[i][k] = num_horiz_corridors;
                    members.push_back({i, k});
                    k++;
                }
                corridor_members.push_back(members);
                num_horiz_corridors++;
            }
        }
    }
    // Identify vertical corridors
    for (int j = 0; j < N; ++j) {
        for (int i = 0; i < N; ++i) {
            if (grid[i][j] != '#' && (i == 0 || grid[i - 1][j] == '#')) {
                std::vector<Point> members;
                int k = i;
                while (k < N && grid[k][j] != '#') {
                    vert_corridor_id[k][j] = num_vert_corridors;
                    members.push_back({k, j});
                    k++;
                }
                corridor_members.push_back(members);
                num_vert_corridors++;
            }
        }
    }

    int total_corridors = num_horiz_corridors + num_vert_corridors;
    is_corridor_covered.assign(total_corridors, false);

    Point current_pos = start_pos;
    std::string total_path = "";
    int num_covered = 0;

    int h_id_start = horiz_corridor_id[current_pos.r][current_pos.c];
    if (h_id_start != -1 && !is_corridor_covered[h_id_start]) {
        is_corridor_covered[h_id_start] = true;
        num_covered++;
    }
    int v_id_start = vert_corridor_id[current_pos.r][current_pos.c];
    if (v_id_start != -1 && !is_corridor_covered[v_id_start + num_horiz_corridors]) {
        is_corridor_covered[v_id_start + num_horiz_corridors] = true;
        num_covered++;
    }

    std::vector<Point> candidates;
    std::vector<bool> candidate_added(N * N);

    while (num_covered < total_corridors) {
        dijkstra(current_pos);

        Point best_target = {-1, -1};
        double max_score = -1.0;
        
        candidates.clear();
        std::fill(candidate_added.begin(), candidate_added.end(), false);

        for (int i = 0; i < total_corridors; ++i) {
            if (!is_corridor_covered[i]) {
                for (const auto& p : corridor_members[i]) {
                    if (!candidate_added[p.r * N + p.c]) {
                        candidates.push_back(p);
                        candidate_added[p.r * N + p.c] = true;
                    }
                }
            }
        }

        for (const auto& p : candidates) {
            if (dist[p.r][p.c] == INF || (p.r == current_pos.r && p.c == current_pos.c)) {
                continue;
            }

            int new_covers = 0;
            int h_id_p = horiz_corridor_id[p.r][p.c];
            if (h_id_p != -1 && !is_corridor_covered[h_id_p]) {
                new_covers++;
            }
            int v_id_p = vert_corridor_id[p.r][p.c];
            if (v_id_p != -1 && !is_corridor_covered[v_id_p + num_horiz_corridors]) {
                new_covers++;
            }

            if (new_covers == 0) continue;

            double score = pow(new_covers, 2) / (double)dist[p.r][p.c];

            if (score > max_score) {
                max_score = score;
                best_target = p;
            }
        }

        if (best_target.r == -1) {
             break; // Should not happen in a connected map.
        }

        total_path += reconstruct_path(current_pos, best_target);
        current_pos = best_target;

        int h_id_curr = horiz_corridor_id[current_pos.r][current_pos.c];
        if (h_id_curr != -1 && !is_corridor_covered[h_id_curr]) {
            is_corridor_covered[h_id_curr] = true;
            num_covered++;
        }
        int v_id_curr = vert_corridor_id[current_pos.r][current_pos.c];
        if (v_id_curr != -1 && !is_corridor_covered[v_id_curr + num_horiz_corridors]) {
            is_corridor_covered[v_id_curr + num_horiz_corridors] = true;
            num_covered++;
        }
    }

    dijkstra(current_pos);
    total_path += reconstruct_path(current_pos, start_pos);

    std::cout << total_path << std::endl;

    return 0;
}