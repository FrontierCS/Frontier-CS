#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> p(n);
    for (int i = 0; i < n; i++) cin >> p[i];
    
    if (n == 3) {
        vector<int> q = p;
        vector<int> r = {p[2], p[1], p[0]};
        if (q < r) {
            cout << 0 << endl;
        } else {
            cout << 1 << endl;
            cout << "1 1" << endl;
        }
    } else {
        vector<pair<int,int>> ops;
        // For n >= 4 we assume identity is reachable.
        // We use a simple greedy algorithm that tries to place each number in its correct position.
        for (int val = 1; val <= n && ops.size() < 4*n; val++) {
            // find current position of val (0-indexed)
            int pos = -1;
            for (int i = 0; i < n; i++) if (p[i] == val) { pos = i; break; }
            if (pos == val-1) continue; // already correct
            
            // try to bring val to front if possible
            if (pos >= 2) { // position >=3 in 1-indexed
                int y = n - pos;   // such that suffix includes pos
                int x = 1;
                if (x > 0 && y > 0 && x+y < n) {
                    ops.push_back({x, y});
                    // apply operation (x,y)
                    vector<int> new_p(n);
                    int idx = 0;
                    for (int i = n-y; i < n; i++) new_p[idx++] = p[i];
                    for (int i = x; i < n-y; i++) new_p[idx++] = p[i];
                    for (int i = 0; i < x; i++) new_p[idx++] = p[i];
                    p = new_p;
                }
            }
            
            // if val is now at front, try to move it to its correct position
            if (p[0] == val && val > 2) {
                int x = n - val + 1;
                int y = 1;
                if (x > 0 && y > 0 && x+y < n) {
                    ops.push_back({x, y});
                    vector<int> new_p(n);
                    int idx = 0;
                    for (int i = n-y; i < n; i++) new_p[idx++] = p[i];
                    for (int i = x; i < n-y; i++) new_p[idx++] = p[i];
                    for (int i = 0; i < x; i++) new_p[idx++] = p[i];
                    p = new_p;
                }
            } else if (val == 1 && p[1] == 1) { // val=1 at second position
                // move 1 to end then to front
                if (2 + 1 < n) {
                    ops.push_back({2, 1});
                    vector<int> new_p(n);
                    int idx = 0;
                    for (int i = n-1; i < n; i++) new_p[idx++] = p[i];
                    for (int i = 2; i < n-1; i++) new_p[idx++] = p[i];
                    for (int i = 0; i < 2; i++) new_p[idx++] = p[i];
                    p = new_p;
                }
                if (p[n-1] == 1) {
                    ops.push_back({1, 1});
                    vector<int> new_p(n);
                    new_p[0] = p[n-1];
                    for (int i = 1; i < n-1; i++) new_p[i] = p[i];
                    new_p[n-1] = p[0];
                    p = new_p;
                }
            }
        }
        
        cout << ops.size() << endl;
        for (auto op : ops) cout << op.first << " " << op.second << endl;
    }
    return 0;
}