#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int ask_query(const vector<int>& q) {
    cout << "? ";
    for (size_t i = 0; i < q.size(); ++i) {
        cout << q[i] << (i == q.size() - 1 ? "" : " ");
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

    int k = 1;
    cout << k << endl;

    vector<int> p(n + 1, 0);
    vector<bool> is_in_known_cycle(n + 1, false);

    for (int i = 2; i <= n; ++i) {
        if (is_in_known_cycle[i]) {
            continue;
        }

        vector<int> cycle;
        int current = i;
        
        while (true) {
            is_in_known_cycle[current] = true;
            cycle.push_back(current);

            vector<int> candidates;
            for (int j = 1; j <= n; ++j) {
                if (!is_in_known_cycle[j]) {
                    candidates.push_back(j);
                }
            }
            if (find(candidates.begin(), candidates.end(), i) == candidates.end()) {
                 candidates.push_back(i);
            }

            if (candidates.size() == 1) {
                p[current] = candidates[0];
                break;
            }

            int next_val;
            
            while (candidates.size() > 1) {
                vector<int> c1, c2;
                int m = candidates.size();
                int m1 = m / 2;
                for(int j=0; j<m1; ++j) c1.push_back(candidates[j]);
                for(int j=m1; j<m; ++j) c2.push_back(candidates[j]);

                vector<int> q1(n), q2(n);
                
                // Construct q1 = [1, C1, current, C2]
                q1[0] = 1;
                int pos = 1;
                for(int x : c1) q1[pos++] = x;
                q1[pos++] = current;
                for(int x : c2) q1[pos++] = x;
                
                // Construct q2 = [1, C1, C2, current]
                q2[0] = 1;
                pos = 1;
                for(int x : c1) q2[pos++] = x;
                for(int x : c2) q2[pos++] = x;
                q2[pos++] = current;

                int res1 = ask_query(q1);
                int res2 = ask_query(q2);
                
                int diff = res1 - res2;
                
                if (diff == 1) {
                    candidates = c2;
                } else {
                    candidates = c1;
                }
            }
            next_val = candidates[0];
            p[current] = next_val;
            
            if (next_val == i) {
                break;
            }
            current = next_val;
        }
    }

    if (p[1] == 0) {
        vector<bool> p_inv_found(n+1, false);
        for(int i = 2; i <= n; ++i) {
            if(p[i] != 0) p_inv_found[p[i]] = true;
        }
        for(int i = 1; i <= n; ++i) {
            if (!p_inv_found[i]) {
                p[1] = i;
                break;
            }
        }
    }
    
    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << p[i] << (i == n ? "" : " ");
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