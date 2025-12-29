#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <algorithm>
#include <map>

// Globals
int N;
int si, sj;
std::vector<std::string> grid;
const int INF = 1e9;
int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char move_char[] = {'U', 'D', 'L', 'R'};

// Algorithm state
std::vector<std::pair<int, int>> road_squares;
std::vector<std::vector<int>> h_seg_id, v_seg_id;
std::vector<std::vector<std::pair<int, int>>> h_segments, v_segments;
std::vector<int> uncovered_in_h_seg, uncovered_in_v_seg;
std::vector<std::vector<bool>> covered;
int total_road_squares = 0;
int uncovered_count = 0;

// Dijkstra results
std::vector<std::vector<int>> dist;
std::vector<std::vector<std::pair<int, int>>> prev_pos;

void precompute_segments() {
    h_seg_id.assign(N, std::vector<int>(N, -1));
    v_seg_id.assign(N, std::vector<int>(N, -1));

    int current_h_id = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] != '#' && h_seg_id[i][j] == -1) {
                h_segments.emplace_back();
                int k = j;
                while (k < N && grid[i][k] != '#') {
                    h_seg_id[i][k] = current_h_id;
                    h_segments.back().push_back({i, k});
                    k++;
                }
                current_h_id++;
            }
        }
    }

    int current_v_id = 0;
    for (int j = 0; j < N; ++j) {
        for (int i = 0; i < N; ++i) {
            if (grid[i][j] != '#' && v_seg_id[i][j] == -1) {
                v_segments.emplace_back();
                int k = i;
                while (k < N && grid[k][j] != '#') {
                    v_seg_id[k][j] = current_v_id;
                    v_segments.back().push_back({k, j});
                    k++;
                }
                current_v_id++;
            }
        }
    }
}

void update_coverage(std::pair<int, int> pos) {
    std::vector<std::pair<int, int>> to_process;

    int h_id = h_seg_id[pos.first][pos.second];
    for (const auto& sq : h_segments[h_id]) {
        to_process.push_back(sq);
    }
    int v_id = v_seg_id[pos.first][pos.second];
    for (const auto& sq : v_segments[v_id]) {
        to_process.push_back(sq);
    }
    
    std::sort(to_process.begin(), to_process.end());
    to_process.erase(std::unique(to_process.begin(), to_process.end()), to_process.end());

    for (const auto& sq : to_process) {
        if (!covered[sq.first][sq.second]) {
            covered[sq.first][sq.second] = true;
            uncovered_count--;
            uncovered_in_h_seg[h_seg_id[sq.first][sq.second]]--;
            uncovered_in_v_seg[v_seg_id[sq.first][sq.second]]--;
        }
    }
}

void dijkstra(std::pair<int, int> start_pos) {
    dist.assign(N, std::vector<int>(N, INF));
    prev_pos.assign(N, std::vector<std::pair<int, int>>(N, {-1, -1}));

    dist[start_pos.first][start_pos.second] = 0;
    std::priority_queue<std::pair<int, std::pair<int, int>>,
                        std::vector<std::pair<int, std::pair<int, int>>>,
                        std::greater<std::pair<int, std::pair<int, int>>>> pq;

    pq.push({0, start_pos});

    while (!pq.empty()) {
        auto [d, curr] = pq.top();
        pq.pop();

        int r = curr.first;
        int c = curr.second;

        if (d > dist[r][c]) {
            continue;
        }

        for (int i = 0; i < 4; ++i) {
            int nr = r + dr[i];
            int nc = c + dc[i];

            if (nr >= 0 && nr < N && nc >= 0 && nc < N && grid[nr][nc] != '#') {
                int cost = grid[nr][nc] - '0';
                if (dist[r][c] + cost < dist[nr][nc]) {
                    dist[nr][nc] = dist[r][c] + cost;
                    prev_pos[nr][nc] = {r, c};
                    pq.push({dist[nr][nc], {nr, nc}});
                }
            }
        }
    }
}

std::string reconstruct_path(std::pair<int, int> start_pos, std::pair<int, int> end_pos) {
    if (start_pos == end_pos) return "";
    
    std::string path = "";
    std::pair<int, int> curr = end_pos;
    while (curr != start_pos) {
        std::pair<int, int> prev = prev_pos[curr.first][curr.second];
        if (prev.first == -1) return "ERROR";
        
        if (prev.first == curr.first - 1) path += 'D';
        else if (prev.first == curr.first + 1) path += 'U';
        else if (prev.second == curr.second - 1) path += 'R';
        else if (prev.second == curr.second + 1) path += 'L';
        curr = prev;
    }
    std::reverse(path.begin(), path.end());
    return path;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> N >> si >> sj;
    grid.resize(N);
    for (int i = 0; i < N; ++i) {
        std::cin >> grid[i];
    }

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] != '#') {
                road_squares.push_back({i, j});
                total_road_squares++;
            }
        }
    }
    uncovered_count = total_road_squares;
    covered.assign(N, std::vector<bool>(N, false));

    precompute_segments();
    
    uncovered_in_h_seg.resize(h_segments.size());
    for (size_t i = 0; i < h_segments.size(); ++i) {
        uncovered_in_h_seg[i] = h_segments[i].size();
    }
    uncovered_in_v_seg.resize(v_segments.size());
    for (size_t i = 0; i < v_segments.size(); ++i) {
        uncovered_in_v_seg[i] = v_segments[i].size();
    }

    std::string total_path = "";
    std::pair<int, int> current_pos = {si, sj};

    update_coverage(current_pos);

    while (uncovered_count > 0) {
        dijkstra(current_pos);

        double best_score = -1.0;
        std::pair<int, int> next_pos = {-1, -1};

        for (const auto& candidate_pos : road_squares) {
            if (dist[candidate_pos.first][candidate_pos.second] == INF) continue;

            int cand_h_id = h_seg_id[candidate_pos.first][candidate_pos.second];
            int cand_v_id = v_seg_id[candidate_pos.first][candidate_pos.second];
            
            int newly_covered = uncovered_in_h_seg[cand_h_id] + uncovered_in_v_seg[cand_v_id];
            if (!covered[candidate_pos.first][candidate_pos.second]) {
                newly_covered--;
            }

            if (newly_covered == 0) continue;
            
            double d = dist[candidate_pos.first][candidate_pos.second];
            double score_den = (d + 1.0) * (d + 1.0);
            double score = (double)newly_covered / score_den;

            if (score > best_score) {
                best_score = score;
                next_pos = candidate_pos;
            }
        }
        
        if (next_pos.first == -1) {
            int min_dist = INF;
            for(const auto& r_sq : road_squares) {
                if(!covered[r_sq.first][r_sq.second] && dist[r_sq.first][r_sq.second] < min_dist) {
                    min_dist = dist[r_sq.first][r_sq.second];
                    next_pos = r_sq;
                }
            }
            if(next_pos.first == -1) break;
        }

        std::string p = reconstruct_path(current_pos, next_pos);
        total_path += p;
        current_pos = next_pos;
        update_coverage(current_pos);
    }

    dijkstra(current_pos);
    total_path += reconstruct_path(current_pos, {si, sj});

    std::cout << total_path << std::endl;

    return 0;
}