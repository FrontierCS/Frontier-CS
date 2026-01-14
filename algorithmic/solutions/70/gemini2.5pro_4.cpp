#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <queue>
#include <set>
#include <string>

// Using std::endl for flushing, which is required for interactive problems.
using std::cin;
using std::cout;
using std::vector;
using std::pair;
using std::map;
using std::queue;
using std::set;
using std::string;
using std::sort;
using std::min;
using std::endl;

class Solver {
public:
    int n, m, start_node, base_move_count;
    vector<vector<int>> adj;
    vector<int> degree;
    vector<bool> visited;
    vector<vector<int>> fingerprints;
    int n_visited;
    int current_pos;

    // For interaction
    int d_current;
    vector<pair<int, int>> interactor_info;
    bool info_pre_read = false;

    // For backtracking
    vector<int> backtrack_dist;

    void solve() {
        cin >> n >> m >> start_node >> base_move_count;
        adj.assign(n + 1, vector<int>());
        degree.assign(n + 1, 0);
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
            degree[u]++;
            degree[v]++;
        }

        precompute_fingerprints();

        visited.assign(n + 1, false);
        current_pos = start_node;
        visited[current_pos] = true;
        n_visited = 1;
        info_pre_read = false;

        while (n_visited < n) {
            if (!info_pre_read) {
                read_interactor_info();
            }
            info_pre_read = false;

            vector<int> candidates = find_candidates();
            
            map<int, vector<int>> candidates_by_deg;
            for (int cand : candidates) {
                candidates_by_deg[degree[cand]].push_back(cand);
            }

            int target_deg = select_best_target_degree(candidates_by_deg);
            
            const auto& landing_candidates = candidates_by_deg.at(target_deg);
            bool target_is_unvisited = !visited[landing_candidates[0]];
            int target_flag = target_is_unvisited ? 0 : 1;

            int move_idx = -1;
            for (int i = 0; i < d_current; ++i) {
                if (interactor_info[i].first == target_deg && interactor_info[i].second == target_flag) {
                    move_idx = i + 1;
                    interactor_info[i].first = -1; // Mark as used for this decision
                    break;
                }
            }
            cout << move_idx << endl;

            if (landing_candidates.size() > 1) {
                resolve_ambiguous_move(landing_candidates);
                info_pre_read = true;
            } else {
                current_pos = landing_candidates[0];
            }

            if (!visited[current_pos]) {
                visited[current_pos] = true;
                n_visited++;
            }
        }
        string verdict;
        cin >> verdict;
    }

private:
    void precompute_fingerprints() {
        fingerprints.assign(n + 1, vector<int>());
        for (int i = 1; i <= n; ++i) {
            for (int neighbor : adj[i]) {
                fingerprints[i].push_back(degree[neighbor]);
            }
            sort(fingerprints[i].begin(), fingerprints[i].end());
        }
    }

    void read_interactor_info() {
        cin >> d_current;
        interactor_info.resize(d_current);
        for (int i = 0; i < d_current; ++i) {
            cin >> interactor_info[i].first >> interactor_info[i].second;
        }
    }

    vector<int> find_candidates() {
        vector<int> unvisited_neighbors;
        for (int neighbor : adj[current_pos]) {
            if (!visited[neighbor]) {
                unvisited_neighbors.push_back(neighbor);
            }
        }

        if (!unvisited_neighbors.empty()) {
            return unvisited_neighbors;
        }

        run_backtrack_bfs();
        int min_dist = 1e9 + 7;
        for (int neighbor : adj[current_pos]) {
            if (backtrack_dist[neighbor] != -1)
                min_dist = min(min_dist, backtrack_dist[neighbor]);
        }

        vector<int> backtrack_candidates;
        if (min_dist != 1e9 + 7) {
            for (int neighbor : adj[current_pos]) {
                if (backtrack_dist[neighbor] == min_dist) {
                    backtrack_candidates.push_back(neighbor);
                }
            }
        }
        return backtrack_candidates;
    }

    void run_backtrack_bfs() {
        vector<int> frontier;
        for (int i = 1; i <= n; ++i) {
            if (visited[i]) {
                bool is_frontier = false;
                for (int neighbor : adj[i]) {
                    if (!visited[neighbor]) {
                        is_frontier = true;
                        break;
                    }
                }
                if (is_frontier) {
                    frontier.push_back(i);
                }
            }
        }

        queue<int> q;
        backtrack_dist.assign(n + 1, -1);

        for (int start_node : frontier) {
            q.push(start_node);
            backtrack_dist[start_node] = 0;
        }

        while (!q.empty()) {
            int u = q.front();
            q.pop();

            for (int v : adj[u]) {
                if (visited[v] && backtrack_dist[v] == -1) {
                    backtrack_dist[v] = backtrack_dist[u] + 1;
                    q.push(v);
                }
            }
        }
    }

    bool is_resolvable(const vector<int>& nodes) {
        if (nodes.size() <= 1) return true;
        set<vector<int>> distinct_fingerprints;
        for (int node : nodes) {
            distinct_fingerprints.insert(fingerprints[node]);
        }
        return distinct_fingerprints.size() == nodes.size();
    }

    int select_best_target_degree(const map<int, vector<int>>& candidates_by_deg) {
        vector<int> unambiguous_degs;
        for (auto const& [deg, nodes] : candidates_by_deg) {
            if (nodes.size() == 1) {
                unambiguous_degs.push_back(deg);
            }
        }
        if (!unambiguous_degs.empty()) {
            sort(unambiguous_degs.begin(), unambiguous_degs.end());
            return unambiguous_degs[0];
        }

        vector<int> resolvable_degs;
        for (auto const& [deg, nodes] : candidates_by_deg) {
            if (is_resolvable(nodes)) {
                resolvable_degs.push_back(deg);
            }
        }
        if (!resolvable_degs.empty()) {
            sort(resolvable_degs.begin(), resolvable_degs.end());
            return resolvable_degs[0];
        }
        
        return candidates_by_deg.begin()->first;
    }

    void resolve_ambiguous_move(const vector<int>& landing_candidates) {
        read_interactor_info();
        vector<int> new_neighbor_degs;
        for (const auto& p : interactor_info) {
            new_neighbor_degs.push_back(p.first);
        }
        sort(new_neighbor_degs.begin(), new_neighbor_degs.end());

        vector<int> matching_candidates;
        for (int cand : landing_candidates) {
            if (fingerprints[cand] == new_neighbor_degs) {
                matching_candidates.push_back(cand);
            }
        }

        if (matching_candidates.size() == 1) {
            current_pos = matching_candidates[0];
        } else {
            vector<int> sorted_candidates = landing_candidates;
            sort(sorted_candidates.begin(), sorted_candidates.end());
            current_pos = sorted_candidates[0];
        }
    }
};

int main() {
    std::ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int t;
    cin >> t;
    while (t--) {
        Solver s;
        s.solve();
    }

    return 0;
}