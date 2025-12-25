#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

using namespace std;

int N, R;
vector<pair<int, int>> adj;
vector<int> parent;

// Global state for recursive forcing
string current_s;

void force_output(int u, int val) {
    if (u >= N) {
        current_s[u] = val + '0';
        return;
    }
    
    // To get a predictable slot output, we make its inputs equal.
    // Let's force them to 0, which makes slot_output 0 for both AND and OR.
    force_output(adj[u].first, 0);
    force_output(adj[u].second, 0);
    
    // Now slot_output is 0.
    // output(u) = slot_output ^ s[u] = 0 ^ s[u]
    // We want output(u) = val, so s[u] should be val.
    current_s[u] = val + '0';
}

int do_query(const string& s) {
    cout << "? " << s << endl;
    int result;
    cin >> result;
    return result;
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> R;
    adj.resize(N);
    parent.assign(2 * N + 1, -1);

    for (int i = 0; i < N; ++i) {
        cin >> adj[i].first >> adj[i].second;
        parent[adj[i].first] = i;
        parent[adj[i].second] = i;
    }
    
    string ans(N, ' ');
    vector<int> path_nodes;
    vector<int> side_nodes;

    for (int i = 0; i < N; ++i) {
        path_nodes.clear();
        side_nodes.clear();
        int curr = i;
        while (parent[curr] != -1) {
            int p = parent[curr];
            if (adj[p].first == curr) {
                side_nodes.push_back(adj[p].second);
            } else {
                side_nodes.push_back(adj[p].first);
            }
            curr = p;
        }

        // --- Test with side branches forced to 0 ---
        // Query A: inputs (0,1), sides 0
        current_s = string(2 * N + 1, '0');
        force_output(adj[i].first, 0);
        force_output(adj[i].second, 1);
        for(int node : side_nodes) {
            force_output(node, 0);
        }
        int out_A = do_query(current_s);
        
        // Query B: inputs (0,0), sides 0
        current_s = string(2 * N + 1, '0');
        force_output(adj[i].first, 0);
        force_output(adj[i].second, 0);
        for(int node : side_nodes) {
            force_output(node, 0);
        }
        int out_B = do_query(current_s);

        bool diff_side0 = (out_A != out_B);

        // --- Test with side branches forced to 1 ---
        // Query C: inputs (0,1), sides 1
        current_s = string(2 * N + 1, '0');
        force_output(adj[i].first, 0);
        force_output(adj[i].second, 1);
        for(int node : side_nodes) {
            force_output(node, 1);
        }
        int out_C = do_query(current_s);
        
        // Query D: inputs (0,0), sides 1
        current_s = string(2 * N + 1, '0');
        force_output(adj[i].first, 0);
        force_output(adj[i].second, 0);
        for(int node : side_nodes) {
            force_output(node, 1);
        }
        int out_D = do_query(current_s);

        bool diff_side1 = (out_C != out_D);

        // A difference in output implies the gate is OR, as AND would produce 0 for both (0,1) and (0,0) inputs.
        // This is only detectable if the path to output is sensitive.
        // By trying both side=0 and side=1, we try to create a sensitive path for both OR-heavy and AND-heavy paths.
        if (diff_side0 || diff_side1) {
            ans[i] = '|';
        } else {
            ans[i] = '&';
        }
    }

    cout << "! " << ans << endl;

    return 0;
}