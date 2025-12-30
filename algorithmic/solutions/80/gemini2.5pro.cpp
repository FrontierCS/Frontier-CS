#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <algorithm>

using namespace std;

int m;
int num_chambers = 0;
string chamber_mark[21];
int passages_explored[21];
int destination[21][21];
int current_chamber_id = -1;

// For BFS to find path to unexplored chamber
int parent_chamber[21];
int parent_passage[21];
bool visited_bfs[21];

string perform_action(int d, const string& side, int p) {
    cout << d << " " << side << " " << p << endl;
    string result;
    cin >> result;
    return result;
}

vector<pair<int, int>> find_path_to_unexplored(int start_node) {
    for (int i = 0; i < num_chambers; ++i) {
        visited_bfs[i] = false;
        parent_chamber[i] = -1;
        parent_passage[i] = -1;
    }

    queue<int> q;
    q.push(start_node);
    visited_bfs[start_node] = true;
    int target_node = -1;

    while (!q.empty()) {
        int u = q.front();
        q.pop();

        if (passages_explored[u] < m) {
            target_node = u;
            break;
        }

        for (int p = 0; p < m; ++p) {
            int v = destination[u][p];
            if (v != -1 && !visited_bfs[v]) {
                visited_bfs[v] = true;
                parent_chamber[v] = u;
                parent_passage[v] = p;
                q.push(v);
            }
        }
    }

    vector<pair<int, int>> path;
    if (target_node != -1) {
        int curr = target_node;
        while (curr != start_node) {
            path.push_back({parent_chamber[curr], parent_passage[curr]});
            curr = parent_chamber[curr];
        }
        reverse(path.begin(), path.end());
    }
    return path;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> m;

    string current_state;
    cin >> current_state;

    for (int i = 0; i < 21; ++i) {
        passages_explored[i] = 0;
        for (int j = 0; j < 21; ++j) {
            destination[i][j] = -1;
        }
    }

    current_chamber_id = 0;
    num_chambers = 1;
    chamber_mark[0] = "left";
    passages_explored[0] = 0;

    while (current_state != "treasure") {
        int c_id = current_chamber_id;

        if (passages_explored[c_id] < m) {
            int p_id = passages_explored[c_id];
            
            string response = perform_action(0, chamber_mark[c_id], p_id);
            
            passages_explored[c_id]++;

            if (response == "treasure") break;
            
            int dest_id = -1;
            if (response == "center") {
                dest_id = num_chambers;
                num_chambers++;
                chamber_mark[dest_id] = (dest_id % 2 == 0) ? "left" : "right";
                passages_explored[dest_id] = 0;
            } else {
                vector<int> candidates;
                for (int i = 0; i < num_chambers; ++i) {
                    if (chamber_mark[i] == response) {
                        candidates.push_back(i);
                    }
                }
                dest_id = candidates[0];
            }
            destination[c_id][p_id] = dest_id;
            current_chamber_id = dest_id;
            current_state = response;

        } else {
            vector<pair<int, int>> path = find_path_to_unexplored(c_id);
            
            if (path.empty()) {
                break;
            }

            string response;
            for (const auto& step : path) {
                int u = step.first;
                int p = step.second;
                response = perform_action(0, chamber_mark[u], p);
                
                if (response == "treasure") {
                    current_state = "treasure";
                    break;
                }
                current_chamber_id = destination[u][p];
            }
            if (current_state == "treasure") break;
            current_state = response;
        }
    }

    return 0;
}