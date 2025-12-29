#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n;
    cin >> n;
    
    if (n == 1) {
        cout << "1 1\n";
        return 0;
    }
    
    vector<int> pos_of_val(n + 1, 0);
    vector<int> val_at_pos(n + 1, 0);
    
    // Find positions of 1 and 2
    for (int i = 1; i <= n; ++i) {
        cout << "0";
        for (int j = 1; j <= n; ++j) {
            if (j == i) cout << " 2";
            else cout << " 1";
        }
        cout << endl;
        cout.flush();
        
        int a;
        cin >> a;
        if (a == 0) {
            pos_of_val[1] = i;
            val_at_pos[i] = 1;
        } else if (a == 2) {
            pos_of_val[2] = i;
            val_at_pos[i] = 2;
        }
    }
    
    vector<int> unknown;
    for (int i = 1; i <= n; ++i) {
        if (val_at_pos[i] == 0) {
            unknown.push_back(i);
        }
    }
    
    // Determine the remaining values 3..n
    for (int v = 3; v <= n; ++v) {
        int k = v - 1; // number of known values
        vector<int> U = unknown;
        while (U.size() > 1) {
            int mid = U.size() / 2;
            vector<int> L(U.begin(), U.begin() + mid);
            vector<int> R(U.begin() + mid, U.end());
            
            vector<int> q(n + 1, 1); // filler = 1
            for (int val = 1; val < v; ++val) {
                q[pos_of_val[val]] = val;
            }
            for (int p : L) {
                q[p] = v;
            }
            
            cout << "0";
            for (int i = 1; i <= n; ++i) {
                cout << " " << q[i];
            }
            cout << endl;
            cout.flush();
            
            int a;
            cin >> a;
            if (a == k + 1) {
                U = L;
            } else {
                U = R;
            }
        }
        int p = U[0];
        pos_of_val[v] = p;
        val_at_pos[p] = v;
        unknown.erase(find(unknown.begin(), unknown.end(), p));
    }
    
    cout << "1";
    for (int i = 1; i <= n; ++i) {
        cout << " " << val_at_pos[i];
    }
    cout << endl;
    cout.flush();
    
    return 0;
}