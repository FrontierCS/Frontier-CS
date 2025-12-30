/*
    Solution for Interactive RBS
*/
#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <cstdlib>

using namespace std;

// Function to calculate f(s) locally
// f(s) is the number of non-empty regular bracket substrings
int calculate_f(const string& s) {
    int n = s.length();
    int count = 0;
    for (int i = 0; i < n; ++i) {
        int balance = 0;
        for (int j = i; j < n; ++j) {
            if (s[j] == '(') balance++;
            else balance--;
            if (balance < 0) {
                // Cannot recover from negative balance in a regular substring
                break; 
            }
            if (balance == 0) {
                count++;
            }
        }
    }
    return count;
}

// Function to calculate f(s) for a subset of indices
int calculate_f_indices(const string& s, const vector<int>& indices) {
    string t = "";
    t.reserve(indices.size());
    for (int idx : indices) {
        t += s[idx - 1];
    }
    return calculate_f(t);
}

// Function to query the interactor
int query(const vector<int>& indices) {
    cout << "0 " << indices.size();
    for (int x : indices) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

long long V(int c) {
    return 1LL * c * (c + 1) / 2;
}

long long V_low(int c) {
    return 1LL * c * (c - 1) / 2;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int n;
    if (!(cin >> n)) return 0;

    // Generate valid sequence of counts c_k
    // We need V(c_k) > sum(V(c_j)) and V_low(c_k) > sum(V_low(c_j))
    // Also constraint: sum(c_k) + m <= 500
    vector<int> C;
    long long s_high = 0;
    long long s_low = 0;
    int curr = 2; // Start from 2 to avoid V_low(1)=0 ambiguity
    int total_len = 0;

    while (true) {
        while (true) {
            if (V(curr) > s_high && V_low(curr) > s_low) break;
            curr++;
        }
        if (total_len + curr + 1 > 500) break;
        C.push_back(curr);
        s_high += V(curr);
        s_low += V_low(curr);
        total_len += curr + 1;
        curr++;
    }

    vector<int> vars;
    for (int i = 2; i <= n; ++i) vars.push_back(i);
    
    int m = C.size();
    vector<int> u_vals(n + 1, -1);
    vector<int> v_vals(n + 1, -1);
    bool u_possible = true;
    bool v_possible = true;

    // Process variables in batches
    for (int i = 0; i < (int)vars.size(); i += m) {
        int batch_size = min((int)vars.size() - i, m);
        vector<int> batch_indices;
        for (int k = 0; k < batch_size; ++k) batch_indices.push_back(vars[i + k]);

        // Construct query indices
        vector<int> q_indices;
        for (int k = 0; k < batch_size; ++k) {
            int var_idx = batch_indices[k];
            int count = C[k];
            // Appending (1, var_idx) 'count' times
            for (int r = 0; r < count; ++r) {
                q_indices.push_back(1);
                q_indices.push_back(var_idx);
            }
            // Separator (1, 1)
            q_indices.push_back(1);
            q_indices.push_back(1);
        }

        int res = query(q_indices);

        // Decode assuming s1 = '('
        if (u_possible) {
            long long temp_res = res;
            for (int k = batch_size - 1; k >= 0; --k) {
                if (temp_res >= V(C[k])) {
                    u_vals[batch_indices[k]] = 1;
                    temp_res -= V(C[k]);
                } else {
                    u_vals[batch_indices[k]] = 0;
                }
            }
            if (temp_res != 0) u_possible = false;
        }

        // Decode assuming s1 = ')'
        if (v_possible) {
            long long temp_res = res;
            for (int k = batch_size - 1; k >= 0; --k) {
                if (temp_res >= V_low(C[k])) {
                    v_vals[batch_indices[k]] = 1;
                    temp_res -= V_low(C[k]);
                } else {
                    v_vals[batch_indices[k]] = 0;
                }
            }
            if (temp_res != 0) v_possible = false;
        }
    }

    string S_A = "", S_B = "";
    
    if (u_possible) {
        S_A += '(';
        for (int i = 2; i <= n; ++i) {
            // if u=1, s_i != s_1 => s_i = ')'
            if (u_vals[i] == 1) S_A += ')';
            else S_A += '(';
        }
    }

    if (v_possible) {
        S_B += ')';
        for (int i = 2; i <= n; ++i) {
            // if v=1, s_i != s_1 => s_i = '('
            if (v_vals[i] == 1) S_B += '(';
            else S_B += ')';
        }
    }

    if (u_possible && !v_possible) {
        cout << "1 " << S_A << endl;
    } else if (!u_possible && v_possible) {
        cout << "1 " << S_B << endl;
    } else {
        // Disambiguate
        vector<int> all_indices;
        for (int i = 1; i <= n; ++i) all_indices.push_back(i);
        int f_true = query(all_indices);
        
        int f_A = calculate_f(S_A);
        int f_B = calculate_f(S_B);

        if (f_A == f_true && f_B != f_true) {
            cout << "1 " << S_A << endl;
        } else if (f_B == f_true && f_A != f_true) {
            cout << "1 " << S_B << endl;
        } else {
            // Random checks
            while (true) {
                int len = rand() % n + 1;
                vector<int> sub;
                for (int k = 0; k < len; ++k) sub.push_back(rand() % n + 1);
                
                int val_A = calculate_f_indices(S_A, sub);
                int val_B = calculate_f_indices(S_B, sub);
                
                if (val_A != val_B) {
                    int val_real = query(sub);
                    if (val_real == val_A) {
                        cout << "1 " << S_A << endl;
                    } else {
                        cout << "1 " << S_B << endl;
                    }
                    break;
                }
            }
        }
    }

    return 0;
}