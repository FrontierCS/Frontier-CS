#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <queue>

using namespace std;

const long long INF = 1e18;

struct Edge {
    int to;
    int capacity;
    int flow;
    int cost;
    int rev;
};

vector<vector<Edge>> adj;
vector<long long> dist;
vector<int> parent_edge;
vector<int> parent_node;

void add_edge(int u, int v, int cap, int cost) {
    adj[u].push_back({v, cap, 0, cost, (int)adj[v].size()});
    adj[v].push_back({u, 0, 0, -cost, (int)adj[u].size() - 1});
}

bool spfa(int s, int t, int &flow, long long &cost, int N_nodes) {
    dist.assign(N_nodes, INF);
    parent_node.assign(N_nodes, -1);
    parent_edge.assign(N_nodes, -1);
    vector<bool> in_queue(N_nodes, false);
    queue<int> q;

    dist[s] = 0;
    q.push(s);
    in_queue[s] = true;

    while (!q.empty()) {
        int u = q.front();
        q.pop();
        in_queue[u] = false;

        for (int i = 0; i < adj[u].size(); ++i) {
            Edge &e = adj[u][i];
            if (e.capacity - e.flow > 0 && dist[e.to] > dist[u] + e.cost) {
                dist[e.to] = dist[u] + e.cost;
                parent_node[e.to] = u;
                parent_edge[e.to] = i;
                if (!in_queue[e.to]) {
                    q.push(e.to);
                    in_queue[e.to] = true;
                }
            }
        }
    }

    if (dist[t] == INF) return false;

    int push = 1; 
    flow += push;
    cost += (long long)push * dist[t];
    int cur = t;
    while (cur != s) {
        int prev = parent_node[cur];
        int edge_idx = parent_edge[cur];
        adj[prev][edge_idx].flow += push;
        int rev_idx = adj[prev][edge_idx].rev;
        adj[cur][rev_idx].flow -= push;
        cur = prev;
    }

    return true;
}

struct Item {
    int id;
    int current_pos;
    int val;
    int target_final_pos; // The position in B
    int target_val;       // B[target_final_pos]
    
    // For handling D=0, u!=v cases (cost 2)
    bool intermediate_mode;
    int intermediate_target;
};

int main() {
    int N;
    if (!(cin >> N)) return 0;

    vector<int> A(N), B(N);
    long long sumA = 0, sumB = 0;
    for (int i = 0; i < N; ++i) { cin >> A[i]; sumA += A[i]; }
    for (int i = 0; i < N; ++i) { cin >> B[i]; sumB += B[i]; }

    if (sumA != sumB) {
        cout << "No" << endl;
        return 0;
    }

    int source = 2 * N;
    int sink = 2 * N + 1;
    adj.assign(2 * N + 2, vector<Edge>());

    for (int i = 0; i < N; ++i) {
        add_edge(source, i, 1, 0);
        add_edge(N + i, sink, 1, 0);
        for (int j = 0; j < N; ++j) {
            int D = B[j] - A[i];
            int cost = -1;
            
            if (D > 0) {
                if (j - i >= D) cost = D;
            } else if (D < 0) {
                if (i - j >= -D) cost = -D;
            } else { // D == 0
                if (i == j) cost = 0;
                else {
                    // Need cost 2 pivot
                    if (i < j) {
                        if (j < N - 1) cost = 2; // Pivot > j
                    } else {
                        if (j > 0) cost = 2; // Pivot < j
                    }
                }
            }

            if (cost != -1) {
                add_edge(i, N + j, 1, cost);
            }
        }
    }

    int flow = 0;
    long long cost = 0;
    while (spfa(source, sink, flow, cost, 2 * N + 2));

    if (flow != N) {
        cout << "No" << endl;
        return 0;
    }

    cout << "Yes" << endl;

    vector<Item> items(N);
    vector<int> p(N); // Permutation of items currently in array slots
    for(int i=0; i<N; ++i) p[i] = i;

    // Retrieve matching
    for (int u = 0; u < N; ++u) {
        for (const auto& e : adj[u]) {
            if (e.to >= N && e.to < 2 * N && e.flow == 1) {
                int v = e.to - N;
                items[u].id = u;
                items[u].current_pos = u;
                items[u].val = A[u];
                items[u].target_final_pos = v;
                items[u].target_val = B[v];
                items[u].intermediate_mode = false;

                if (A[u] == B[v] && u != v) {
                    items[u].intermediate_mode = true;
                    if (u < v) items[u].intermediate_target = v + 1; // Pivot
                    else items[u].intermediate_target = v - 1;       // Pivot
                }
                break;
            }
        }
    }

    vector<pair<int, int>> ops;
    
    // Helper to get type: 1=R, -1=L, 0=S
    auto getType = [&](int idx) -> int {
        int item_idx = p[idx];
        Item& it = items[item_idx];
        int target;
        int target_val;
        
        if (it.intermediate_mode) {
            target = it.intermediate_target;
            // Value goal? R-move needs +1, L-move -1.
            // If u < v, pivot is v+1 (Right). u -> v+1 is Right.
            // If u > v, pivot is v-1 (Left). u -> v-1 is Left.
            // But value change for intermediate:
            // R-move (+1) -> L-type? 
            // Wait, we just follow position.
            // R means pos < target. L means pos > target.
            // S means pos == target.
        } else {
            target = it.target_final_pos;
        }

        if (it.current_pos < target) return 1; // R
        if (it.current_pos > target) return -1; // L
        return 0; // S
    };

    while (true) {
        // Check if done
        bool done = true;
        for(int i=0; i<N; ++i) {
            if (getType(i) != 0) { done = false; break; }
        }
        if (done) break;

        int best_i = -1;
        // Priority 1: Adjacent (R, L)
        for (int i = 0; i < N - 1; ++i) {
            if (getType(i) == 1 && getType(i+1) == -1) {
                best_i = i;
                break;
            }
        }
        
        if (best_i == -1) {
            // Priority 2: Rightmost R adjacent to S or L (but no L) -> R S swap
            for (int i = N - 2; i >= 0; --i) {
                if (getType(i) == 1) {
                    best_i = i;
                    break;
                }
            }
            // Or Leftmost L adjacent to S?
            if (best_i == -1) {
                 for (int i = 0; i < N - 1; ++i) {
                    if (getType(i+1) == -1) {
                        best_i = i;
                        break;
                    }
                }
            }
        }
        
        if (best_i == -1) break; // Should not happen if not done

        int i = best_i;
        int j = i + 1;
        
        ops.push_back({i + 1, j + 1}); // 1-based output

        int u_idx = p[i];
        int v_idx = p[j];

        // Update items
        items[u_idx].current_pos = j;
        items[u_idx].val += 1; // Moved Right
        items[v_idx].current_pos = i;
        items[v_idx].val -= 1; // Moved Left

        // Update permutation
        swap(p[i], p[j]);

        // Check intermediate reached
        if (items[u_idx].intermediate_mode) {
            if (items[u_idx].current_pos == items[u_idx].intermediate_target) {
                items[u_idx].intermediate_mode = false;
            }
        }
        if (items[v_idx].intermediate_mode) {
            if (items[v_idx].current_pos == items[v_idx].intermediate_target) {
                items[v_idx].intermediate_mode = false;
            }
        }
    }

    cout << ops.size() << endl;
    for (auto& op : ops) {
        cout << op.first << " " << op.second << endl;
    }

    return 0;
}