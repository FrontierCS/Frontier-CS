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
    
    // Four groups: 0:a (inc), 1:b (dec), 2:c (inc), 3:d (dec)
    vector<int> last(4);
    last[0] = 0;
    last[2] = 0;
    last[1] = n + 1;
    last[3] = n + 1;
    
    vector<vector<int>> seq(4);
    
    for (int x : p) {
        // Try increasing groups
        int best_inc = -1;
        for (int idx : {0, 2}) {
            if (last[idx] < x) {
                if (best_inc == -1 || last[idx] > last[best_inc]) {
                    best_inc = idx;
                }
            }
        }
        if (best_inc != -1) {
            seq[best_inc].push_back(x);
            last[best_inc] = x;
            continue;
        }
        
        // Try decreasing groups
        int best_dec = -1;
        for (int idx : {1, 3}) {
            if (last[idx] > x) {
                if (best_dec == -1 || last[idx] < last[best_dec]) {
                    best_dec = idx;
                }
            }
        }
        if (best_dec != -1) {
            seq[best_dec].push_back(x);
            last[best_dec] = x;
            continue;
        }
        
        // Fallback: assign to first group (should rarely happen)
        seq[0].push_back(x);
        last[0] = x;
    }
    
    int r = seq[0].size();
    int s = seq[1].size();
    int len_c = seq[2].size();
    int q = seq[3].size();
    cout << r << " " << s << " " << len_c << " " << q << "\n";
    
    auto output = [](const vector<int>& v) {
        if (v.empty()) {
            cout << "\n";
            return;
        }
        for (size_t i = 0; i < v.size(); ++i) {
            if (i) cout << " ";
            cout << v[i];
        }
        cout << "\n";
    };
    
    output(seq[0]);
    output(seq[1]);
    output(seq[2]);
    output(seq[3]);
    
    return 0;
}