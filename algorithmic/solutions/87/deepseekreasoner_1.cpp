#include <iostream>
#include <vector>
#include <algorithm>
#include <cassert>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    vector<int> initial(n);
    for (int i = 0; i < n; ++i) cin >> initial[i];

    vector<int> target(n);
    for (int i = 0; i < n; ++i) cin >> target[i];

    vector<vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        u--; v--;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Each node can also copy from itself, so add self to neighbor list for convenience
    for (int i = 0; i < n; ++i) {
        adj[i].push_back(i);
    }

    vector<vector<int>> states;
    states.push_back(initial);

    vector<int> cur = initial;
    int steps = 0;
    const int MAX_STEPS = 20000;

    while (steps < MAX_STEPS) {
        if (cur == target) break;

        vector<int> nxt(n);
        vector<int> source(n, -1); // source chosen for each node

        // First pass: try to copy from a neighbor (or self) that gives the target color
        for (int i = 0; i < n; ++i) {
            bool found = false;
            for (int j : adj[i]) {
                if (cur[j] == target[i]) {
                    source[i] = j;
                    found = true;
                    break;
                }
            }
            if (!found) {
                source[i] = i; // stay
            }
        }

        // Apply the chosen sources
        for (int i = 0; i < n; ++i) {
            nxt[i] = cur[source[i]];
        }

        // If no change, we are stuck. Try to flip a wrong node to the opposite color.
        if (nxt == cur) {
            bool changed = false;
            // Try to flip a wrong node by copying from a neighbor with opposite color
            for (int i = 0; i < n && !changed; ++i) {
                if (cur[i] != target[i]) {
                    for (int j : adj[i]) {
                        if (cur[j] != cur[i]) {
                            nxt[i] = cur[j];
                            changed = true;
                            break;
                        }
                    }
                }
            }
            // If still no change, flip a correct node to wrong to create diversity
            if (!changed) {
                for (int i = 0; i < n && !changed; ++i) {
                    if (cur[i] == target[i]) {
                        for (int j : adj[i]) {
                            if (cur[j] != cur[i]) {
                                nxt[i] = cur[j];
                                changed = true;
                                break;
                            }
                        }
                    }
                }
            }
        }

        cur = nxt;
        steps++;
        states.push_back(cur);
    }

    // Output
    cout << steps << "\n";
    for (const auto& state : states) {
        for (int i = 0; i < n; ++i) {
            if (i > 0) cout << " ";
            cout << state[i];
        }
        cout << "\n";
    }

    return 0;
}