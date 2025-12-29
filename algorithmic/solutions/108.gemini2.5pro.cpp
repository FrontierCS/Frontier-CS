#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int query(int x, int d) {
    cout << "? " << x << " " << d << endl;
    int a;
    cin >> a;
    return a;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    cin >> n >> m;

    int total_sections = n * m;
    
    vector<vector<bool>> uncovered_by_others(n, vector<bool>(total_sections));

    for (int i = 0; i < n; ++i) {
        vector<int> deltas;
        int first_val = query(i, 1);
        int last_val = first_val;

        for (int k = 1; k < total_sections; ++k) {
            int val = query(i, 1);
            deltas.push_back(val - last_val);
            last_val = val;
        }
        deltas.push_back(first_val - last_val);
        
        for (int r = 0; r < m; ++r) {
            vector<int> seq;
            seq.push_back(0);
            int z_count = 1;
            int current_val = 0;

            for (int k = 0; k < n - 1; ++k) {
                int delta_idx = (r + k * m);
                current_val -= deltas[delta_idx];
                seq.push_back(current_val);
                if (current_val == 0) {
                    z_count++;
                }
            }

            bool flip = false;
            if (n > 2) {
                if (z_count != n - 1) {
                    flip = true;
                }
            } else { // n = 2
                if (z_count != 1) {
                    flip = true;
                }
            }
            
            for (int k = 0; k < n; ++k) {
                int val = seq[k];
                if (flip) {
                    val = 1 - val;
                }
                uncovered_by_others[i][(r + k * m)] = (val == 1);
            }
        }
    }
    
    vector<int> s(n, -1);
    
    vector<bool> is_P_zero(total_sections, false);
    for(int p = 0; p < total_sections; ++p) {
        bool is_p_in_any_U_i = false;
        for(int i = 0; i < n; ++i) {
            if(!uncovered_by_others[i][p]) { // p is in U_i
                is_p_in_any_U_i = true;
                break;
            }
        }
        if(is_p_in_any_U_i) {
            is_P_zero[p] = true;
        }
    }

    for (int k = 0; k < n; ++k) {
        vector<bool> is_in_Sk(total_sections, false);
        for(int p = 0; p < total_sections; ++p) {
            if(is_P_zero[p] && uncovered_by_others[k][p]) {
                is_in_Sk[p] = true;
            }
        }
        for(int p = 0; p < total_sections; ++p) {
            if(is_in_Sk[p] && !is_in_Sk[(p - 1 + total_sections) % total_sections]) {
                s[k] = p;
                break;
            }
        }
    }

    cout << "! ";
    for (int i = 1; i < n; ++i) {
        long long p_i = (long long)s[i] - s[0] + total_sections;
        cout << p_i % total_sections << (i == n - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}