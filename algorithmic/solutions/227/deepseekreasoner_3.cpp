#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n;
    cin >> n;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        cin >> p[i];
    }
    
    // last values for each group: a,c increasing (start with 0); b,d decreasing (start with n+1)
    vector<int> last(4);
    last[0] = 0; last[2] = 0;
    last[1] = n + 1; last[3] = n + 1;
    
    // subsequences
    vector<vector<int>> subs(4);
    
    for (int x : p) {
        // try increasing groups (0 and 2)
        vector<int> inc_cand;
        if (x > last[0]) inc_cand.push_back(0);
        if (x > last[2]) inc_cand.push_back(2);
        if (!inc_cand.empty()) {
            // choose the one with larger last
            int g = inc_cand[0];
            if (inc_cand.size() == 2) {
                if (last[2] > last[0]) g = 2;
                else g = 0; // tie -> choose 0
            }
            last[g] = x;
            subs[g].push_back(x);
            continue;
        }
        
        // try decreasing groups (1 and 3)
        vector<int> dec_cand;
        if (x < last[1]) dec_cand.push_back(1);
        if (x < last[3]) dec_cand.push_back(3);
        if (!dec_cand.empty()) {
            // choose the one with smaller last
            int g = dec_cand[0];
            if (dec_cand.size() == 2) {
                if (last[1] < last[3]) g = 1;
                else g = 3; // tie -> choose 1
            }
            last[g] = x;
            subs[g].push_back(x);
            continue;
        }
        
        // otherwise, choose group with minimal cost
        int best_g = 0;
        int best_cost = INT_MAX;
        for (int g = 0; g < 4; ++g) {
            int cost;
            if (g == 0 || g == 2) { // increasing group
                if (x > last[g]) cost = 0;
                else cost = last[g] - x;
            } else { // decreasing group
                if (x < last[g]) cost = 0;
                else cost = x - last[g];
            }
            if (cost < best_cost) {
                best_cost = cost;
                best_g = g;
            }
        }
        last[best_g] = x;
        subs[best_g].push_back(x);
    }
    
    // output
    cout << subs[0].size() << " " << subs[1].size() << " "
         << subs[2].size() << " " << subs[3].size() << "\n";
    for (int g = 0; g < 4; ++g) {
        if (subs[g].empty()) {
            cout << "\n";
        } else {
            for (size_t i = 0; i < subs[g].size(); ++i) {
                if (i > 0) cout << " ";
                cout << subs[g][i];
            }
            cout << "\n";
        }
    }
    
    return 0;
}