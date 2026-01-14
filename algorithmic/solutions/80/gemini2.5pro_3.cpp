#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <numeric>
#include <algorithm>

using namespace std;

int M;
int N_chambers = 0;
vector<vector<int>> adj;
vector<int> passage_ptr;
vector<int> parent;
vector<int> color; // 0 for left, 1 for right
int physical_chamber_id = -1;

void go_to(int target_chamber) {
    if (physical_chamber_id == target_chamber) {
        return;
    }

    vector<int> path_up;
    map<int, bool> visited_up;
    int curr = physical_chamber_id;
    while(curr != -1) {
        visited_up[curr] = true;
        path_up.push_back(curr);
        curr = parent[curr];
    }
    
    vector<int> path_down;
    curr = target_chamber;
    while(visited_up.find(curr) == visited_up.end()) {
        path_down.push_back(curr);
        curr = parent[curr];
    }
    int lca = curr;

    while(physical_chamber_id != lca) {
        int p_to_parent = -1;
        for(int i=0; i<M; ++i) {
            if(adj[parent[physical_chamber_id]][i] == physical_chamber_id) {
                p_to_parent = i;
                break;
            }
        }
        string side = (color[physical_chamber_id] == 0) ? "left" : "right";
        cout << 0 << " " << side << " " << p_to_parent << endl;
        physical_chamber_id = parent[physical_chamber_id];
        string dummy; cin >> dummy;
    }

    reverse(path_down.begin(), path_down.end());
    for(int chamber : path_down) {
        int p_to_child = -1;
        for(int i=0; i<M; ++i) {
            if(adj[physical_chamber_id][i] == chamber) {
                p_to_child = i;
                break;
            }
        }
        string side = (color[physical_chamber_id] == 0) ? "left" : "right";
        cout << 0 << " " << side << " " << p_to_child << endl;
        physical_chamber_id = chamber;
        string dummy; cin >> dummy;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> M;
    int max_chambers = 25;
    adj.assign(max_chambers, vector<int>(M, -1));
    passage_ptr.assign(max_chambers, 0);
    parent.assign(max_chambers, -1);
    color.assign(max_chambers, -1);
    
    vector<int> dfs_stack;
    
    string status;
    cin >> status; // Initial "center"

    physical_chamber_id = N_chambers++;
    color[physical_chamber_id] = 0;
    parent[physical_chamber_id] = -1;
    dfs_stack.push_back(physical_chamber_id);

    while(!dfs_stack.empty()) {
        int u = dfs_stack.back();
        
        if (passage_ptr[u] == M) {
            dfs_stack.pop_back();
            continue;
        }

        go_to(u);
        
        int p = passage_ptr[u]++;
        
        string side = (color[u] == 0) ? "left" : "right";
        cout << 0 << " " << side << " " << p << endl;

        cin >> status;
        if (status == "treasure") {
            return 0;
        }
        
        if (status == "center") {
            int v = N_chambers++;
            adj[u][p] = v;
            parent[v] = u;
            color[v] = 1 - color[u];
            physical_chamber_id = v;
            dfs_stack.push_back(v);
        } else {
            int observed_color = (status == "left" ? 0 : 1);
            // Non-tree edge. The problem is identifying which chamber we landed in.
            // A simple heuristic is to assume it's an ancestor.
            int target_v = -1;
            int curr = u;
            while(curr != -1) {
                if(color[curr] == observed_color) {
                    target_v = curr;
                    break;
                }
                curr = parent[curr];
            }
            // If no ancestor matches, it could be in another subtree.
            // This is a point of ambiguity. The heuristic might be wrong on complex graphs.
            if (target_v == -1) {
                for(int i = 0; i < N_chambers; ++i) {
                    if (color[i] == observed_color) {
                        target_v = i;
                        break;
                    }
                }
            }
            adj[u][p] = target_v;
            physical_chamber_id = target_v;
        }
    }

    return 0;
}