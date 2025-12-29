#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <set>
#include <algorithm>
#include <queue>
#include <bitset>
#include <memory>
#include <chrono>

using namespace std;

const int N = 50;
const int MAX_TILES = N * N;

int si, sj;
int t[N][N];
int p[N][N];

int tile_map[N][N];
int tile_count = 0;

struct TileInfo {
    vector<pair<int, int>> squares;
    long long score = 0;
};
vector<TileInfo> tile_info;
vector<vector<int>> tile_adj;

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};

string get_move(pair<int, int> from, pair<int, int> to) {
    if (to.first == from.first - 1 && to.second == from.second) return "U";
    if (to.first == from.first + 1 && to.second == from.second) return "D";
    if (to.first == from.first && to.second == from.second - 1) return "L";
    if (to.first == from.first && to.second == from.second + 1) return "R";
    return "";
}

void preprocess() {
    map<int, int> t_to_tile_id;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (t_to_tile_id.find(t[i][j]) == t_to_tile_id.end()) {
                t_to_tile_id[t[i][j]] = tile_count++;
            }
            tile_map[i][j] = t_to_tile_id[t[i][j]];
        }
    }

    tile_info.resize(tile_count);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int tid = tile_map[i][j];
            tile_info[tid].squares.push_back({i, j});
            tile_info[tid].score += p[i][j];
        }
    }

    vector<set<int>> adj_set(tile_count);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            for (int k = 0; k < 4; ++k) {
                int ni = i + dr[k];
                int nj = j + dc[k];
                if (ni >= 0 && ni < N && nj >= 0 && nj < N) {
                    if (tile_map[i][j] != tile_map[ni][nj]) {
                        adj_set[tile_map[i][j]].insert(tile_map[ni][nj]);
                        adj_set[tile_map[ni][nj]].insert(tile_map[i][j]);
                    }
                }
            }
        }
    }
    tile_adj.resize(tile_count);
    for (int i = 0; i < tile_count; ++i) {
        tile_adj[i] = vector<int>(adj_set[i].begin(), adj_set[i].end());
    }
}

struct Node {
    shared_ptr<Node> parent;
    int tile_id;
    long long path_score;
    bitset<MAX_TILES> visited;
};

vector<int> beam_search() {
    const int BEAM_WIDTH = 50;
    int start_tid = tile_map[si][sj];

    auto root = make_shared<Node>();
    root->parent = nullptr;
    root->tile_id = start_tid;
    root->path_score = tile_info[start_tid].score;
    root->visited.reset();
    root->visited[start_tid] = 1;

    vector<shared_ptr<Node>> beam;
    beam.push_back(root);

    shared_ptr<Node> best_node = root;

    for (int i = 0; i < N * N + 5; ++i) {
        if (beam.empty()) break;
        vector<shared_ptr<Node>> next_beam;
        for (const auto& node : beam) {
            for (int next_tid : tile_adj[node->tile_id]) {
                if (!node->visited[next_tid]) {
                    auto new_node = make_shared<Node>();
                    new_node->parent = node;
                    new_node->tile_id = next_tid;
                    new_node->path_score = node->path_score + tile_info[next_tid].score;
                    new_node->visited = node->visited;
                    new_node->visited[next_tid] = 1;
                    next_beam.push_back(new_node);
                }
            }
        }

        if (next_beam.empty()) break;

        sort(next_beam.begin(), next_beam.end(), [](const auto& a, const auto& b) {
            return a->path_score > b->path_score;
        });

        if (next_beam.size() > BEAM_WIDTH) {
            next_beam.resize(BEAM_WIDTH);
        }
        
        if (next_beam[0]->path_score > best_node->path_score) {
            best_node = next_beam[0];
        }
        beam = next_beam;
    }

    vector<int> tile_path;
    shared_ptr<Node> curr = best_node;
    while (curr != nullptr) {
        tile_path.push_back(curr->tile_id);
        curr = curr->parent;
    }
    reverse(tile_path.begin(), tile_path.end());
    return tile_path;
}

string generate_path_string(const vector<int>& tile_path) {
    if (tile_path.empty()) return "";

    string ans = "";
    pair<int, int> current_pos = {si, sj};

    for (size_t i = 0; i < tile_path.size(); ++i) {
        int current_tid = tile_path[i];
        const auto& squares_on_curr = tile_info[current_tid].squares;

        pair<int, int> entry_pos = current_pos;
        pair<int, int> exit_pos;

        if (i == tile_path.size() - 1) { // Last tile
            if (squares_on_curr.size() == 2) {
                pair<int, int> other_sq = (squares_on_curr[0] == entry_pos) ? squares_on_curr[1] : squares_on_curr[0];
                ans += get_move(current_pos, other_sq);
                current_pos = other_sq;
            }
            break;
        }

        int next_tid = tile_path[i+1];
        
        pair<int, int> next_entry_pos = {-1, -1};
        int min_dist = 100;

        for (const auto& sq_curr : squares_on_curr) {
            for (int k = 0; k < 4; ++k) {
                int ni = sq_curr.first + dr[k];
                int nj = sq_curr.second + dc[k];
                if (ni >= 0 && ni < N && nj >= 0 && nj < N && tile_map[ni][nj] == next_tid) {
                    int dist = abs(entry_pos.first - sq_curr.first) + abs(entry_pos.second - sq_curr.second);
                    if (dist < min_dist) {
                        min_dist = dist;
                        exit_pos = sq_curr;
                        next_entry_pos = {ni, nj};
                    }
                }
            }
        }
        
        if (squares_on_curr.size() == 2) {
            pair<int, int> other_sq = (squares_on_curr[0] == entry_pos) ? squares_on_curr[1] : squares_on_curr[0];
            if (entry_pos != exit_pos) {
                ans += get_move(current_pos, exit_pos);
                current_pos = exit_pos;
            } else {
                ans += get_move(current_pos, other_sq);
                current_pos = other_sq;
                ans += get_move(current_pos, exit_pos);
                current_pos = exit_pos;
            }
        }
        
        ans += get_move(current_pos, next_entry_pos);
        current_pos = next_entry_pos;
    }

    return ans;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    cin >> si >> sj;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> t[i][j];
        }
    }
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> p[i][j];
        }
    }

    preprocess();
    
    vector<int> best_tile_path = beam_search();
    
    string result = generate_path_string(best_tile_path);
    
    cout << result << endl;

    return 0;
}