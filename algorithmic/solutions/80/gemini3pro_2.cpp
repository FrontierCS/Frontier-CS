#include <iostream>
#include <vector>
#include <string>
#include <cstdlib>
#include <ctime>
#include <algorithm>
#include <map>

using namespace std;

int M;
string last_response;

void read_response() {
    cin >> last_response;
    if (last_response == "treasure") {
        exit(0);
    }
}

int num_nodes = 0;
int adj[25][25]; 
bool edge_visited[25][25];
int parent[25];
int parent_edge[25];
int stone_locs[25]; 
int current_u = 0;

vector<int> get_path(int u) {
    vector<int> path;
    while (u != 0) {
        path.push_back(parent_edge[u]);
        u = parent[u];
    }
    reverse(path.begin(), path.end());
    return path;
}

// Outputs action: shifts stone so new logical pos is new_loc_logical, sets side, takes take_k_logical
// Updates tracking of current_stone_loc for the node
void action(int &current_stone_loc_var, int new_loc_logical, string side, int take_k_logical) {
    int s = (new_loc_logical - current_stone_loc_var + M) % M;
    int k_out = (take_k_logical - new_loc_logical + M) % M;
    cout << s << " " << side << " " << k_out << endl;
    current_stone_loc_var = new_loc_logical;
    read_response();
}

void find_right_node() {
    while (last_response != "right") {
        int r = rand() % M;
        cout << "0 left " << r << endl;
        read_response();
    }
}

int main() {
    srand(time(0));
    if (!(cin >> M)) return 0;
    read_response(); 

    num_nodes = 1;
    for(int i=0;i<25;i++) {
        stone_locs[i] = 0;
        for(int j=0;j<25;j++) {
            adj[i][j] = -1;
            edge_visited[i][j] = false;
        }
    }
    
    // Initialize Root: observed center. Treat current view 0 as logical 0.
    // Mark Root as Right.
    // We must take a passage to mark it.
    // Take passage 0.
    cout << "0 right 0" << endl; 
    read_response();
    
    current_u = 0; 
    int edge_taken = 0;
    
    while(true) {
        int v = -1;
        
        if (last_response == "center") {
            v = num_nodes++;
            stone_locs[v] = 0;
            adj[current_u][edge_taken] = v;
            parent[v] = current_u;
            parent_edge[v] = edge_taken;
            edge_visited[current_u][edge_taken] = true;
            
            // At new node v (Center). Mark Left, take edge 0.
            current_u = v;
            edge_taken = 0;
            action(stone_locs[v], 0, "left", 0);
            continue;
        } 
        else if (last_response == "right") {
            v = 0; // Root
            adj[current_u][edge_taken] = v;
            edge_visited[current_u][edge_taken] = true;
            
            // At Root. Need to pick next edge.
            int target_u = -1;
            int target_k = -1;
            
            // Check Root edges
            for(int k=0; k<M; k++) {
                if (!edge_visited[0][k]) {
                    target_u = 0; target_k = k; break;
                }
            }
            
            if (target_u == -1) {
                // BFS for unvisited edge
                vector<int> q; q.push_back(0);
                vector<int> dist(25, 999);
                vector<int> from(25, -1);
                vector<int> from_edge(25, -1);
                dist[0] = 0;
                int head = 0;
                bool found = false;
                while(head < q.size()) {
                    int curr = q[head++];
                    for(int k=0; k<M; k++) {
                        if (!edge_visited[curr][k]) {
                            target_u = curr; target_k = k; found = true; break;
                        }
                        int next_n = adj[curr][k];
                        if (next_n != -1 && dist[next_n] > dist[curr] + 1) {
                            dist[next_n] = dist[curr] + 1;
                            from[next_n] = curr;
                            from_edge[next_n] = k;
                            q.push_back(next_n);
                        }
                    }
                    if(found) break;
                }
                
                if (!found) {
                    // Random move if we think we are done but game not over
                    action(stone_locs[0], stone_locs[0], "right", rand()%M);
                    current_u = 0; // Lost track strictly speaking but likely close
                    continue; 
                }
                
                if (target_u == 0) {
                     current_u = 0;
                     edge_taken = target_k;
                     action(stone_locs[0], stone_locs[0], "right", target_k);
                     continue;
                } else {
                    vector<int> path_steps;
                    int curr = target_u;
                    while(curr != 0) {
                        path_steps.push_back(from_edge[curr]);
                        curr = from[curr];
                    }
                    reverse(path_steps.begin(), path_steps.end());
                    
                    int at = 0;
                    for(int edge : path_steps) {
                        action(stone_locs[at], stone_locs[at], (at==0 ? "right" : "left"), edge);
                        at = adj[at][edge];
                    }
                    current_u = target_u;
                    edge_taken = target_k;
                    action(stone_locs[current_u], stone_locs[current_u], "left", target_k);
                    continue;
                }
            } else {
                 current_u = 0;
                 edge_taken = target_k;
                 action(stone_locs[0], stone_locs[0], "right", target_k);
                 continue;
            }
        }
        else { // "left" - Visited, ID needed
            // Mark Right (assume stone logical loc is what we tracked, don't change it, just flip side)
            // But we must move.
            cout << "0 right 0" << endl; 
            read_response();
            
            // Random walk to Right node
            while(last_response != "right") {
                cout << "0 left " << (rand() % M) << endl;
                read_response();
            }

            bool success = false;
            int identified_v = -1;
            
            while (!success) {
                 // Assume current node is Root. Check candidates.
                 // We iterate candidates to check if they match 'v' (which is Right).
                 for(int c=1; c<num_nodes; c++) {
                     vector<int> path = get_path(c);
                     int curr_model = 0;
                     bool possible = true;
                     for(int edge : path) {
                         action(stone_locs[curr_model], stone_locs[curr_model], "left", edge);
                         if(last_response == "right") {
                             // Hit right prematurely or at end
                             // If at end, good.
                         }
                         if(adj[curr_model][edge] != -1) curr_model = adj[curr_model][edge];
                         else { possible = false; break; } // Should not happen
                     }
                     
                     if (possible && last_response == "right") {
                         identified_v = c;
                         success = true;
                         break;
                     }
                     
                     // Reset to Right node
                     find_right_node();
                 }
                 if(!success) find_right_node(); 
            }
            
            v = identified_v;
            adj[current_u][edge_taken] = v;
            edge_visited[current_u][edge_taken] = true;
            
            current_u = v;
            edge_taken = 0;
            action(stone_locs[v], stone_locs[v], "left", 0);
        }
    }
    return 0;
}