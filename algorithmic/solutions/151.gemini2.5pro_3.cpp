#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <map>
#include <cmath>
#include <algorithm>
#include <chrono>
#include <random>

using namespace std;

const int INF = 1e9;
int N;
int si, sj;
vector<string> C;
vector<vector<int>> cost;
vector<vector<bool>> is_road;
vector<pair<int, int>> road_squares;
map<pair<int, int>, int> road_square_to_idx;

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char move_char[] = {'U', 'D', 'L', 'R'};

struct State {
    int r, c, t;
};

bool operator>(const State& a, const State& b) {
    return a.t > b.t;
}

// Timer
chrono::high_resolution_clock::time_point start_time;
long long time_limit_ms = 1950;

bool is_time_up() {
    auto now = chrono::high_resolution_clock::now();
    auto duration = chrono::duration_cast<chrono::milliseconds>(now - start_time).count();
    return duration > time_limit_ms;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    start_time = chrono::high_resolution_clock::now();

    cin >> N >> si >> sj;
    C.resize(N);
    cost.assign(N, vector<int>(N, 0));
    is_road.assign(N, vector<bool>(N, false));
    int total_road_squares = 0;

    for (int i = 0; i < N; ++i) {
        cin >> C[i];
        for (int j = 0; j < N; ++j) {
            if (C[i][j] != '#') {
                is_road[i][j] = true;
                cost[i][j] = C[i][j] - '0';
                road_squares.push_back({i, j});
                road_square_to_idx[{i, j}] = road_squares.size() - 1;
                total_road_squares++;
            }
        }
    }

    int R = road_squares.size();

    vector<vector<pair<int, int>>> visible_sets(R);
    for (int i = 0; i < R; ++i) {
        int r = road_squares[i].first;
        int c = road_squares[i].second;

        vector<pair<int, int>> current_visible;
        // Horizontal
        int left = c, right = c;
        while (left > 0 && is_road[r][left - 1]) left--;
        while (right < N - 1 && is_road[r][right + 1]) right++;
        for (int j = left; j <= right; ++j) {
            current_visible.push_back({r, j});
        }
        // Vertical
        int up = r, down = r;
        while (up > 0 && is_road[up - 1][c]) up--;
        while (down < N - 1 && is_road[down + 1][c]) down++;
        for (int j = up; j <= down; ++j) {
            if (j != r) {
                current_visible.push_back({j, c});
            }
        }
        visible_sets[i] = current_visible;
    }
    
    vector<vector<int>> dist(R, vector<int>(R));
    vector<vector<vector<pair<int, int>>>> parent(R, vector<vector<pair<int, int>>>(N, vector<pair<int, int>>(N, {-1, -1})));

    for (int i = 0; i < R; ++i) {
        priority_queue<State, vector<State>, greater<State>> pq;
        vector<vector<int>> d(N, vector<int>(N, INF));

        int start_r = road_squares[i].first;
        int start_c = road_squares[i].second;

        d[start_r][start_c] = 0;
        pq.push({start_r, start_c, 0});

        while (!pq.empty()) {
            State current = pq.top();
            pq.pop();

            if (current.t > d[current.r][current.c]) {
                continue;
            }

            for (int k = 0; k < 4; ++k) {
                int nr = current.r + dr[k];
                int nc = current.c + dc[k];

                if (nr >= 0 && nr < N && nc >= 0 && nc < N && is_road[nr][nc]) {
                    if (d[nr][nc] > current.t + cost[nr][nc]) {
                        d[nr][nc] = current.t + cost[nr][nc];
                        parent[i][nr][nc] = {current.r, current.c};
                        pq.push({nr, nc, d[nr][nc]});
                    }
                }
            }
        }
        for (int j = 0; j < R; ++j) {
            dist[i][j] = d[road_squares[j].first][road_squares[j].second];
        }
    }

    vector<bool> is_covered(total_road_squares, false);
    int uncovered_count = total_road_squares;
    vector<int> tour_indices;

    int start_node_idx = road_square_to_idx[{si, sj}];
    tour_indices.push_back(start_node_idx);

    for (auto& p : visible_sets[start_node_idx]) {
        int idx = road_square_to_idx[p];
        if (!is_covered[idx]) {
            is_covered[idx] = true;
            uncovered_count--;
        }
    }

    int current_node_idx = start_node_idx;
    while (uncovered_count > 0) {
        int best_next_idx = -1;
        double max_score = -1.0;

        for (int i = 0; i < R; ++i) {
            if (dist[current_node_idx][i] == 0) continue;
            
            int newly_covered = 0;
            for (auto& p : visible_sets[i]) {
                if (!is_covered[road_square_to_idx[p]]) {
                    newly_covered++;
                }
            }

            if (newly_covered > 0) {
                double score = pow(newly_covered, 2.0) / dist[current_node_idx][i];
                if (score > max_score) {
                    max_score = score;
                    best_next_idx = i;
                }
            }
        }

        if (best_next_idx == -1) {
            int min_dist = INF;
            for(int i = 0; i < R; ++i) {
                if (!is_covered[i] && dist[current_node_idx][i] < min_dist) {
                    min_dist = dist[current_node_idx][i];
                    best_next_idx = i;
                }
            }
            if(best_next_idx == -1) break; 
        }

        current_node_idx = best_next_idx;
        tour_indices.push_back(current_node_idx);
        for (auto& p : visible_sets[current_node_idx]) {
            int idx = road_square_to_idx[p];
            if (!is_covered[idx]) {
                is_covered[idx] = true;
                uncovered_count--;
            }
        }
    }
    
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    if (tour_indices.size() > 2) {
        while (!is_time_up()) {
            int size = tour_indices.size();
            int i = 1 + rng() % (size - 1);
            int j = 1 + rng() % (size - 1);
            if (i == j) continue;
            if (i > j) swap(i, j);
            
            long long current_cost, new_cost;
            
            if (i == 1 && j == size - 1) { 
                 current_cost = (long long)dist[tour_indices[0]][tour_indices[1]] + dist[tour_indices[j]][tour_indices[0]];
                 new_cost = (long long)dist[tour_indices[0]][tour_indices[j]] + dist[tour_indices[1]][tour_indices[0]];
            } else if (i == 1) { 
                current_cost = (long long)dist[tour_indices[0]][tour_indices[1]] + dist[tour_indices[j]][tour_indices[j+1]];
                new_cost = (long long)dist[tour_indices[0]][tour_indices[j]] + dist[tour_indices[1]][tour_indices[j+1]];
            } else if (j == size - 1) { 
                current_cost = (long long)dist[tour_indices[i-1]][tour_indices[i]] + dist[tour_indices[j]][tour_indices[0]];
                new_cost = (long long)dist[tour_indices[i-1]][tour_indices[j]] + dist[tour_indices[i]][tour_indices[0]];
            } else { 
                current_cost = (long long)dist[tour_indices[i-1]][tour_indices[i]] + dist[tour_indices[j]][tour_indices[j+1]];
                new_cost = (long long)dist[tour_indices[i-1]][tour_indices[j]] + dist[tour_indices[i]][tour_indices[j+1]];
            }

            if (new_cost < current_cost) {
                reverse(tour_indices.begin() + i, tour_indices.begin() + j + 1);
            }
        }
    }

    string path_str = "";
    
    for (size_t i = 1; i < tour_indices.size(); ++i) {
        int from_idx = tour_indices[i-1];
        int to_idx = tour_indices[i];
        
        pair<int, int> target = road_squares[to_idx];
        string segment_path = "";
        pair<int, int> curr = target;
        while(curr.first != road_squares[from_idx].first || curr.second != road_squares[from_idx].second) {
            pair<int, int> prev = parent[from_idx][curr.first][curr.second];
            int dr_move = curr.first - prev.first;
            int dc_move = curr.second - prev.second;
            for(int k=0; k<4; ++k) {
                if (dr[k] == dr_move && dc[k] == dc_move) {
                    segment_path += move_char[k];
                    break;
                }
            }
            curr = prev;
        }
        reverse(segment_path.begin(), segment_path.end());
        path_str += segment_path;
    }

    // Path back to start
    int from_idx = tour_indices.back();
    pair<int, int> target = road_squares[start_node_idx];
    string segment_path = "";
    pair<int, int> curr = target;
     while(curr.first != road_squares[from_idx].first || curr.second != road_squares[from_idx].second) {
        pair<int, int> prev = parent[from_idx][curr.first][curr.second];
        int dr_move = curr.first - prev.first;
        int dc_move = curr.second - prev.second;
        for(int k=0; k<4; ++k) {
            if (dr[k] == dr_move && dc[k] == dc_move) {
                segment_path += move_char[k];
                break;
            }
        }
        curr = prev;
    }
    reverse(segment_path.begin(), segment_path.end());
    path_str += segment_path;

    cout << path_str << endl;

    return 0;
}