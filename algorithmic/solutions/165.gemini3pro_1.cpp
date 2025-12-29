#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <bitset>

using namespace std;

struct Point {
    int r, c;
};

int dist(const Point& a, const Point& b) {
    return abs(a.r - b.r) + abs(a.c - b.c);
}

int N, M;
Point start_pos;
vector<string> grid;
vector<Point> char_locs[26];
vector<string> targets;
int overlaps[200][200];

struct CostInfo {
    int cost;
    int end_inst_idx; // index in char_locs[last_char]
};

// best_suffix_costs[str_idx][overlap][start_inst_idx]
vector<CostInfo> best_suffix_costs[200][5];

void precompute() {
    // 1. Overlaps
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            if (i == j) { overlaps[i][j] = 0; continue; }
            int max_ov = 0;
            for (int len = 4; len >= 1; --len) {
                if (targets[i].substr(5 - len) == targets[j].substr(0, len)) {
                    max_ov = len;
                    break;
                }
            }
            overlaps[i][j] = max_ov;
        }
    }

    // 2. Suffix Costs
    for (int k = 0; k < M; ++k) {
        for (int ov = 0; ov < 5; ++ov) {
            int suffix_len = 5 - ov;
            char first_char = targets[k][ov];
            char last_char = targets[k][4];
            int num_starts = char_locs[first_char - 'A'].size();
            
            best_suffix_costs[k][ov].resize(num_starts);

            for (int u = 0; u < num_starts; ++u) {
                if (suffix_len == 1) {
                    best_suffix_costs[k][ov][u] = {0, u};
                    continue;
                }

                vector<int> prev_layer_costs(char_locs[targets[k][ov] - 'A'].size(), 1e9);
                prev_layer_costs[u] = 0;

                for (int i = 1; i < suffix_len; ++i) {
                    char c_prev = targets[k][ov + i - 1];
                    char c_curr = targets[k][ov + i];
                    const auto& locs_prev = char_locs[c_prev - 'A'];
                    const auto& locs_curr = char_locs[c_curr - 'A'];
                    
                    vector<int> next_layer_costs(locs_curr.size(), 1e9);
                    
                    for (int p = 0; p < locs_prev.size(); ++p) {
                        if (prev_layer_costs[p] >= 1e9) continue;
                        for (int c = 0; c < locs_curr.size(); ++c) {
                            int move = dist(locs_prev[p], locs_curr[c]) + 1;
                            if (prev_layer_costs[p] + move < next_layer_costs[c]) {
                                next_layer_costs[c] = prev_layer_costs[p] + move;
                            }
                        }
                    }
                    prev_layer_costs = next_layer_costs;
                }
                
                int best_c = 1e9;
                int best_v = -1;
                for (int v = 0; v < prev_layer_costs.size(); ++v) {
                    if (prev_layer_costs[v] < best_c) {
                        best_c = prev_layer_costs[v];
                        best_v = v;
                    }
                }
                best_suffix_costs[k][ov][u] = {best_c, best_v};
            }
        }
    }
}

struct Node {
    int parent_node_idx; 
    int str_idx;
    int overlap;
    int u_idx; 
    int v_idx; 
    int total_cost;
    Point end_pos;
    bitset<200> visited;
};

struct Candidate {
    int parent_idx;
    int str_idx;
    int overlap;
    int u_idx;
    int total_cost;
    CostInfo ci;
    Point end_pos;
    
    bool operator<(const Candidate& other) const {
        return total_cost < other.total_cost;
    }
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;
    cin >> start_pos.r >> start_pos.c;

    grid.resize(N);
    for (int i = 0; i < N; ++i) cin >> grid[i];

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            char_locs[grid[i][j] - 'A'].push_back({i, j});
        }
    }

    targets.resize(M);
    for (int i = 0; i < M; ++i) cin >> targets[i];

    precompute();

    int BEAM_WIDTH = 500; 
    vector<vector<Node>> layers(M + 1);
    
    Node start_node;
    start_node.parent_node_idx = -1;
    start_node.str_idx = -1;
    start_node.overlap = 0;
    start_node.total_cost = 0;
    start_node.end_pos = start_pos;
    start_node.visited.reset();
    
    layers[0].push_back(start_node);

    for (int depth = 0; depth < M; ++depth) {
        vector<Candidate> candidates;
        candidates.reserve(layers[depth].size() * (M - depth));

        for (int p_idx = 0; p_idx < layers[depth].size(); ++p_idx) {
            const Node& parent = layers[depth][p_idx];
            
            for (int next_k = 0; next_k < M; ++next_k) {
                if (parent.visited[next_k]) continue;

                int ov = 0;
                if (parent.str_idx != -1) {
                    ov = overlaps[parent.str_idx][next_k];
                }

                char start_c = targets[next_k][ov];
                int start_c_idx = start_c - 'A';
                const auto& starts = char_locs[start_c_idx];
                
                int best_trans_cost = 1e9;
                int best_u = -1;
                const CostInfo* best_ci = nullptr;

                for (int u = 0; u < starts.size(); ++u) {
                    const CostInfo& ci = best_suffix_costs[next_k][ov][u];
                    int move_cost = dist(parent.end_pos, starts[u]) + 1; 
                    int cost = move_cost + ci.cost;
                    
                    if (cost < best_trans_cost) {
                        best_trans_cost = cost;
                        best_u = u;
                        best_ci = &ci;
                    }
                }

                Candidate cand;
                cand.parent_idx = p_idx;
                cand.str_idx = next_k;
                cand.overlap = ov;
                cand.u_idx = best_u;
                cand.total_cost = parent.total_cost + best_trans_cost;
                cand.ci = *best_ci;
                
                char end_c = targets[next_k][4];
                cand.end_pos = char_locs[end_c - 'A'][best_ci->end_inst_idx];
                
                candidates.push_back(cand);
            }
        }
        
        if (candidates.empty()) break;
        
        int keep = min((int)candidates.size(), BEAM_WIDTH);
        nth_element(candidates.begin(), candidates.begin() + keep, candidates.end());
        
        layers[depth+1].reserve(keep);
        for (int i = 0; i < keep; ++i) {
            Node next_node;
            next_node.parent_node_idx = candidates[i].parent_idx;
            next_node.str_idx = candidates[i].str_idx;
            next_node.overlap = candidates[i].overlap;
            next_node.u_idx = candidates[i].u_idx;
            next_node.v_idx = candidates[i].ci.end_inst_idx;
            next_node.total_cost = candidates[i].total_cost;
            next_node.end_pos = candidates[i].end_pos;
            next_node.visited = layers[depth][candidates[i].parent_idx].visited;
            next_node.visited.set(candidates[i].str_idx);
            
            layers[depth+1].push_back(next_node);
        }
    }

    int best_final_idx = 0;
    int min_final_cost = 1e9;
    int last_layer = layers.size() - 1;
    while (layers[last_layer].empty() && last_layer > 0) last_layer--;
    
    for (int i = 0; i < layers[last_layer].size(); ++i) {
        if (layers[last_layer][i].total_cost < min_final_cost) {
            min_final_cost = layers[last_layer][i].total_cost;
            best_final_idx = i;
        }
    }

    struct Step {
        int str_idx;
        int overlap;
        int u_idx;
        int v_idx;
    };
    vector<Step> steps;
    
    int cur_idx = best_final_idx;
    for (int d = last_layer; d > 0; --d) {
        const Node& node = layers[d][cur_idx];
        steps.push_back({node.str_idx, node.overlap, node.u_idx, node.v_idx});
        cur_idx = node.parent_node_idx;
    }
    reverse(steps.begin(), steps.end());
    
    vector<pair<int, int>> path_coords;
    for (const auto& step : steps) {
        string s = targets[step.str_idx].substr(step.overlap);
        int len = s.length();
        
        Point curr = char_locs[s[0] - 'A'][step.u_idx];
        path_coords.push_back({curr.r, curr.c});
        
        if (len > 1) {
            vector<vector<pair<int, int>>> dp(len);
            for(int i=0; i<len; ++i) {
                dp[i].resize(char_locs[s[i]-'A'].size(), {1e9, -1});
            }
            dp[0][step.u_idx] = {0, -1};
            
            for (int i = 0; i < len - 1; ++i) {
                const auto& cur_locs = char_locs[s[i]-'A'];
                const auto& next_locs = char_locs[s[i+1]-'A'];
                
                for (int u = 0; u < cur_locs.size(); ++u) {
                    if (dp[i][u].first >= 1e9) continue;
                    for (int v = 0; v < next_locs.size(); ++v) {
                        int cost = dp[i][u].first + dist(cur_locs[u], next_locs[v]) + 1;
                        if (cost < dp[i+1][v].first) {
                            dp[i+1][v] = {cost, u};
                        }
                    }
                }
            }
            
            int curr_loc_idx = step.v_idx;
            vector<int> internal_indices(len);
            internal_indices[len-1] = curr_loc_idx;
            
            for (int i = len - 1; i > 0; --i) {
                curr_loc_idx = dp[i][curr_loc_idx].second;
                internal_indices[i-1] = curr_loc_idx;
            }
            
            for (int i = 1; i < len; ++i) {
                Point p = char_locs[s[i]-'A'][internal_indices[i]];
                path_coords.push_back({p.r, p.c});
            }
        }
    }
    
    for (const auto& p : path_coords) {
        cout << p.r << " " << p.c << "\n";
    }

    return 0;
}