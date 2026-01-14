#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<int> initial(n+1);
    for(int i=1; i<=n; i++) cin >> initial[i];
    vector<int> target(n+1);
    for(int i=1; i<=n; i++) cin >> target[i];
    vector<vector<int>> adj(n+1);
    for(int i=0; i<m; i++) {
        int u,v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vector<int> fix_time(n+1, -1);
    vector<bool> is_fixed(n+1, false);
    for(int i=1; i<=n; i++) {
        if(initial[i] == target[i]) {
            fix_time[i] = 0;
            is_fixed[i] = true;
        }
    }
    int t = 0;
    while(true) {
        bool has_unfixed = false;
        for(int i=1; i<=n; i++) {
            if(!is_fixed[i]) {
                has_unfixed = true;
                break;
            }
        }
        if(!has_unfixed) break;
        t++;
        vector<int> candidates;
        for(int v=1; v<=n; v++) {
            if(is_fixed[v]) continue;
            bool can = false;
            for(int w : adj[v]) {
                int provided = (fix_time[w] != -1 ? target[w] : initial[w]);
                if(provided == target[v]) {
                    can = true;
                    break;
                }
            }
            if(can) candidates.push_back(v);
        }
        if(candidates.empty()) {
            break;
        }
        for(int v : candidates) {
            fix_time[v] = t;
            is_fixed[v] = true;
        }
    }
    int k = t;
    cout << k << endl;
    for(int s=0; s<=k; s++) {
        for(int i=1; i<=n; i++) {
            int col;
            if(fix_time[i] == -1 || fix_time[i] > s) {
                col = initial[i];
            } else {
                col = target[i];
            }
            cout << col;
            if(i < n) cout << " ";
            else cout << endl;
        }
    }
    return 0;
}