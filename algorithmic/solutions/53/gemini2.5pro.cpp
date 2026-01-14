#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int query(const vector<int>& q) {
    cout << "?";
    for (int x : q) {
        cout << " " << x;
    }
    cout << endl;
    int result;
    cin >> result;
    if (result == -1) exit(0);
    return result;
}

void solve() {
    int n;
    cin >> n;

    // We fix k=1. The element at q[0] is ignored as a source.
    cout << 1 << endl;

    vector<int> p(n + 1, 0);
    vector<bool> p_found(n + 1, false);

    for (int i = 1; i <= n; ++i) {
        if (p_found[i]) {
            continue;
        }

        int current = i;
        vector<int> path;
        while (!p_found[current]) {
            path.push_back(current);
            int next_node = -1;
            
            // Test potential successors j for current
            for (int j = 1; j <= n; ++j) {
                if (current == j) continue;
                
                // p[current] cannot be a node already in the current path,
                // unless it's the start node i, which closes the cycle.
                bool is_in_path = false;
                for(int node : path) {
                    if (node == j) {
                        is_in_path = true;
                        break;
                    }
                }
                if (is_in_path && j != i) continue;
                
                // Find a dummy element for q[0], different from current and j
                int dummy = -1;
                for (int d = 1; d <= n; ++d) {
                    if (d != current && d != j) {
                        dummy = d;
                        break;
                    }
                }

                vector<int> q1(n), q2(n);
                vector<int> rem;
                for (int l = 1; l <= n; ++l) {
                    if (l != dummy && l != current && l != j) {
                        rem.push_back(l);
                    }
                }

                q1[0] = dummy; q1[1] = current; q1[2] = j;
                for (size_t l = 0; l < rem.size(); ++l) q1[l + 3] = rem[l];
                
                q2[0] = dummy; q2[1] = j; q2[2] = current;
                for (size_t l = 0; l < rem.size(); ++l) q2[l + 3] = rem[l];

                if (query(q1) - query(q2) == 1) {
                    next_node = j;
                    break;
                }
            }
            
            p[current] = next_node;
            p_found[current] = true;
            
            // If the successor is already solved, we've connected to a known cycle.
            if (p_found[next_node]) {
                break;
            }
            current = next_node;
        }
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.flush();
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}