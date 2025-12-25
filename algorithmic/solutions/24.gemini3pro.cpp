#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

int n;
vector<vector<int>> adj;

bool solve() {
    if (!(cin >> n)) return false;
    adj.assign(n, vector<int>(n));
    for (int i = 0; i < n; ++i) {
        string row;
        cin >> row;
        for (int j = 0; j < n; ++j) {
            adj[i][j] = row[j] - '0';
        }
    }

    // Construct a path P such that edge colors are 0...01...1
    // split is the index in P such that edges P[0]->P[1]...P[split-1]->P[split] are 0
    // and P[split]->P[split+1]... are 1.
    // Range of split is 0 to P.size()-1.
    vector<int> P;
    P.push_back(0); 
    int split = 0; 

    for (int i = 1; i < n; ++i) {
        int best_pos = -1;
        int best_split = -1;
        int sz = P.size();
        
        // 1. Try prepend
        if (adj[i][P[0]] == 0) {
            best_pos = 0;
            best_split = split + 1;
        } else if (split == 0) { // adj is 1, valid if all are 1
            best_pos = 0;
            best_split = 0;
        }
        
        if (best_pos != -1) goto insert_done;

        // 2. Try append
        if (adj[P.back()][i] == 1) {
            best_pos = sz;
            best_split = split;
        } else if (split == sz - 1) { // adj is 0, valid if all are 0
            best_pos = sz;
            best_split = sz;
        }

        if (best_pos != -1) goto insert_done;

        // 3. Try insert at j
        for (int j = 1; j < sz; ++j) {
            int u = P[j-1];
            int v = P[j];
            int c1 = adj[u][i];
            int c2 = adj[i][v];
            
            if (j < split) {
                if (c1 == 0 && c2 == 0) {
                    best_pos = j;
                    best_split = split + 1;
                    goto insert_done;
                }
            } else if (j > split) {
                if (c1 == 1 && c2 == 1) {
                    best_pos = j;
                    best_split = split;
                    goto insert_done;
                }
            } else { // j == split
                if (c1 == 0 && c2 == 0) {
                    best_pos = j;
                    best_split = split + 1;
                    goto insert_done;
                }
                if (c1 == 0 && c2 == 1) {
                    best_pos = j;
                    best_split = split;
                    goto insert_done;
                }
                if (c1 == 1 && c2 == 1) {
                    best_pos = j;
                    best_split = split - 1;
                    goto insert_done;
                }
            }
        }
        
        insert_done:
        if (best_pos != -1) {
            P.insert(P.begin() + best_pos, i);
            split = best_split;
        } else {
            // Should not be reachable for n >= 3
            return false; 
        }
    }

    vector<int> best_p;

    auto check = [&](const vector<int>& p) {
        int cnt = 0;
        int prev_c = adj[p[0]][p[1]];
        for (int k = 1; k < n; ++k) {
            int u = p[k];
            int v = (k + 1 < n) ? p[k+1] : p[0];
            int curr_c = adj[u][v];
            if (curr_c != prev_c) cnt++;
            prev_c = curr_c;
        }
        if (cnt <= 1) {
            if (best_p.empty() || p < best_p) {
                best_p = p;
            }
        }
    };

    vector<int> temp = P;
    for (int k = 0; k < n; ++k) {
        check(temp);
        int front = temp.front();
        temp.erase(temp.begin());
        temp.push_back(front);
    }
    
    reverse(P.begin(), P.end());
    temp = P;
    for (int k = 0; k < n; ++k) {
        check(temp);
        int front = temp.front();
        temp.erase(temp.begin());
        temp.push_back(front);
    }

    if (best_p.empty()) {
        cout << -1 << "\n";
    } else {
        for (int i = 0; i < n; ++i) cout << best_p[i] + 1 << (i == n - 1 ? "" : " ");
        cout << "\n";
    }
    return true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    while (solve());
    return 0;
}