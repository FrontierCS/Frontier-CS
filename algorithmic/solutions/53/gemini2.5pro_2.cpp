#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Global interactor helper
int n_global;
int ask_query(const vector<int>& q) {
    cout << "?";
    for (int x : q) {
        cout << " " << x;
    }
    cout << endl;
    int response;
    cin >> response;
    if (response == -1) exit(0);
    return response;
}

void solve() {
    cin >> n_global;
    int n = n_global;
    
    // We must select a constant k. Let's pick k=1.
    // The query will count pairs (i, j) with i < j, p[q_i] = q_j, i != 1.
    // This means any link starting from the element at index 1 of q (q[0]) is not counted.
    cout << 1 << endl;

    vector<int> p(n + 1, 0);
    vector<bool> p_found(n + 1, false);
    int found_count = 0;

    // Find p[i] for i = 2, ..., n. Then p[1] is determined.
    // To find p[i], we can make it so the link p[i]=j is the only thing that changes
    // between two queries.
    // Let's find the cycle decomposition.
    
    vector<bool> visited(n + 1, false);

    for (int i = 1; i <= n; ++i) {
        if (visited[i]) {
            continue;
        }

        // Trace the cycle starting with i
        vector<int> path;
        int current = i;
        while (!visited[current]) {
            visited[current] = true;
            path.push_back(current);

            vector<int> q(n);
            iota(q.begin(), q.end(), 1);

            // To find p[current], we query with q_1 = current.
            // This ignores any link p[current] = j.
            // We compare this with a query where q_1 = something else, e.g. 1 (or any other fixed value).
            // Let's try to find p_inv[current] instead.
            
            int next_in_cycle = -1;
            
            // Query with q_1 = current.
            // This disables counting any link starting from p[current].
            q[0] = current;
            int other_idx = 1;
            for(int val = 1; val <=n; ++val) {
                if (val != current) {
                    q[other_idx++] = val;
                }
            }
            int res_ignore_current = ask_query(q);
            
            // Now, for each potential predecessor x, query with q_1 = x.
            // This disables counting links from p[x].
            // If p[x] = current, then a link is formed.
            // We want to find x such that p[x] = current.
            for (int x = 1; x <= n; ++x) {
                if (x == current) continue;
                bool x_is_visited = false;
                for(int node : path) if(node == x) x_is_visited = true;
                if(x_is_visited) continue;

                q[0] = x;
                other_idx = 1;
                for(int val = 1; val <= n; ++val) {
                    if (val != x) {
                        q[other_idx++] = val;
                    }
                }
                
                int res_ignore_x = ask_query(q);

                // Let's analyze the change.
                // q_base: [1, 2, ..., n]. k=1. Links from p[1] ignored.
                // q_curr: [current, ...]. k=1. Links from p[current] ignored.
                // q_x:    [x, ...]. k=1. Links from p[x] ignored.
                // This seems complex. A simpler method is needed.

                // Let's try another approach. We want to find p_inv[y].
                // Set q_1 = y. Ask. res_y.
                // Now swap q_1 and q_2. q' = [q_2, y, ...]. Ask. res_swap.
                // The difference might reveal something about p[q_2]=y.

                vector<int> q_base(n);
                q_base[0] = current;
                int idx = 1;
                for(int val=1; val<=n; ++val) if(val != current) q_base[idx++] = val;
                
                vector<int> q_swap = q_base;
                if (q_swap[1] == x) { // x is already at index 2
                    // do nothing
                } else {
                    for(int k=2; k<n; ++k) {
                        if (q_swap[k] == x) {
                            swap(q_swap[1], q_swap[k]);
                            break;
                        }
                    }
                }
                
                int res_base = ask_query(q_base);
                int res_swapped = ask_query(q_swap);
                if (res_swapped > res_base) {
                    // p[x] = current
                    int prev_in_cycle = x;
                    p[prev_in_cycle] = current;
                    current = prev_in_cycle; // trace backward
                    goto found_predecessor;
                }
            }
            // if we are here, p_inv[current] is in the path. it must be i.
            p[i] = current;
            break;

            found_predecessor:;
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